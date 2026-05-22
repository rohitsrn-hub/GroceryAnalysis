"""
Chatbot service — data context building and LLM interaction.
Uses OpenAI Function Calling to fetch specific analytics and run custom queries.
"""
import os
import json
import uuid
import traceback
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from database import db
from config import logger, CHATBOT_MAX_TOKENS, CHATBOT_TEMPERATURE, CHATBOT_MODEL
from services.period_service import format_period_display_name
from services.analytics_service import (
    get_fastest_selling_items,
    get_abc_analysis,
    get_capital_blocking_analysis,
    get_inventory_analysis,
    get_group_analysis
)
from services.forecast_service import (
    simple_trend_forecast,
    statistical_forecast,
    ai_forecast
)
from routes.data import get_daily_sales_trend_by_period
from services.summary_service import get_summary_details
from services.semantic_service import semantic_search_items, add_manual_mapping

# ─── Tools Definition ────────────────────────────────────────────────

CHATBOT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_abc_analysis",
            "description": "Perform ABC analysis (80/20 rule) to classify inventory into A, B, and C categories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Optional period (e.g., '2026' or '2026-05'). Pass 'all' for all-time."},
                    "group": {"type": "string", "description": "Optional product group to filter by. Pass 'all' for all groups."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_capital_blocking_analysis",
            "description": "Identify slow-moving items with high inventory causing capital blocking. Use to find dead stock and risk levels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Optional period (e.g., '2026' or '2026-05'). Pass 'all' for all-time."},
                    "group": {"type": "string", "description": "Optional product group to filter by. Pass 'all' for all groups."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_health",
            "description": "Analyze inventory for dead stock and slow movers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Optional period. Pass 'all' for all-time."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_group_analysis",
            "description": "Analyze performance (revenue, profit, margin) by product groups.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Optional period. Pass 'all' for all-time."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance_metrics",
            "description": "Get fastest selling or top performing items based on sales velocity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Optional period. Pass 'all' for all-time."},
                    "limit": {"type": "integer", "description": "Number of items to return, default 10."},
                    "group": {"type": "string", "description": "Optional product group to filter by. Pass 'all' for all groups."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_sales_trend",
            "description": "Get daily sales trend for a specific monthly period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Period in exactly 'YYYY-MM' format, e.g., '2026-05'."}
                },
                "required": ["period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_forecast",
            "description": "Forecast future demand using trend, statistical, or AI methods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["trend", "statistical", "ai"], "description": "Forecasting method to use. AI is best for patterns, statistical for seasonality."},
                    "forecast_months": {"type": "integer", "description": "Number of months to forecast, default 3."}
                },
                "required": ["method"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_custom_query",
            "description": "Run a read-only MongoDB aggregation pipeline on the 'sales_records' collection. Use this ONLY for broad database analytics (e.g., total database record count, list of distinct groups, etc.). DO NOT use this tool for specific item stock, inventory levels, or quantity/revenue/profit sales of specific items. Use get_items_stock_and_sales instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pipeline_json": {
                        "type": "string", 
                        "description": "A JSON string representing the MongoDB aggregation pipeline array (e.g. '[{\"$match\": {\"data_period\": \"2026-05\"}}... ]'). NOTE: Only standard read operators allowed. DO NOT use $group, $sort, or other grouping operators as they are blocked. Always $limit to a reasonable number to avoid huge responses."
                    }
                },
                "required": ["pipeline_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_relevant_items",
            "description": "Finds specific item names that match a broad semantic category, brand, or vague search term (like 'luggage', 'noodles', 'footwear'). Always use this tool FIRST when the user asks for a general category of items, to get the exact database names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "semantic_query": {
                        "type": "string",
                        "description": "The broad search term or category, e.g. 'luggage'"
                    }
                },
                "required": ["semantic_query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "train_semantic_mapping",
            "description": "Manually maps specific exact item names to a broad category. Use this when the user corrects you or tells you 'X is also a type of Y' or 'Map Safari to luggage'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The broad category name, e.g. 'luggage'"
                    },
                    "item_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of exact item names to map to this category."
                    }
                },
                "required": ["category", "item_names"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_items_stock_and_sales",
            "description": "Retrieve aggregated stock and sales metrics (total quantity sold, revenue, profit, and latest closing stock) for a list of specific exact item names in a given period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of exact item names."
                    },
                    "period": {
                        "type": "string",
                        "description": "Optional period (e.g. '2026-05' or '2026'). Defaults to the latest period containing data for these items."
                    }
                },
                "required": ["item_names"]
            }
        }
    }
]

# ─── Tool Executors ──────────────────────────────────────────────────

def parse_period_to_range(period_str: str):
    """
    Parse a period string like '2026', '2026-05', or '2025-01-09' (range YYYY-MM-MM)
    into ((start_year, start_month), (end_year, end_month))
    """
    import re
    if not period_str:
        return ((0, 0), (0, 0))
    
    # 1. YYYY-MM-MM (e.g. 2025-01-09)
    range_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', period_str)
    if range_match:
        year = int(range_match.group(1))
        start_month = int(range_match.group(2))
        end_month = int(range_match.group(3))
        return ((year, start_month), (year, end_month))
        
    # 2. YYYY-MM (e.g. 2026-05)
    month_match = re.match(r'^(\d{4})-(\d{2})$', period_str)
    if month_match:
        year = int(month_match.group(1))
        month = int(month_match.group(2))
        return ((year, month), (year, month))
        
    # 3. YYYY (e.g. 2026)
    year_match = re.match(r'^(\d{4})$', period_str)
    if year_match:
        year = int(year_match.group(1))
        return ((year, 1), (year, 12))
        
    # Fallback/unknown
    return ((0, 0), (0, 0))


def is_period_match(rec_period: str, target_period: str) -> bool:
    """Check if a record's period matches the target period."""
    import re
    if not target_period or target_period == "all":
        return True
    if not rec_period:
        return False
    
    # If exact string match, it's definitely a match
    if rec_period == target_period:
        return True
        
    # Otherwise, check if target_period is a year (e.g. "2026") and rec_period falls inside that year
    target_match = re.match(r'^(\d{4})$', target_period)
    if target_match:
        target_year = int(target_match.group(1))
        rec_range = parse_period_to_range(rec_period)
        return rec_range[0][0] == target_year or rec_range[1][0] == target_year
        
    return False


_RESOLVE_FALLBACK_CACHE: List[str] = []

async def resolve_db_item_names(item_names: List[str]) -> List[str]:
    """
    Resolve a list of item names (which may have formatting residuals like asterisks,
    extra spaces, casing differences, etc.) to the exact item names present in the database.
    """
    from services.semantic_service import _EMBEDDINGS_CACHE
    import re
    
    # Get all unique database names from embeddings cache if available
    db_names = [item["item_name"] for item in _EMBEDDINGS_CACHE] if _EMBEDDINGS_CACHE else []
    
    # Async fallback: query DB distinct items if cache is empty or loading
    if not db_names:
        global _RESOLVE_FALLBACK_CACHE
        if _RESOLVE_FALLBACK_CACHE:
            db_names = _RESOLVE_FALLBACK_CACHE
        else:
            try:
                logger.info("Embeddings cache is empty. Fetching distinct item names from database for name resolution fallback...")
                import asyncio
                db_names = await asyncio.wait_for(db.sales_records.distinct("item_name"), timeout=5.0)
                _RESOLVE_FALLBACK_CACHE = db_names
            except Exception as e:
                logger.error(f"Failed to fetch distinct item names from DB: {e}")
                try:
                    cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "item_names_cache.json")
                    if os.path.exists(cache_path):
                        logger.info(f"Loading distinct item names from offline cache: {cache_path}")
                        with open(cache_path, "r", encoding="utf-8") as f:
                            db_names = json.load(f)
                            _RESOLVE_FALLBACK_CACHE = db_names
                    else:
                        logger.warning(f"Offline cache file not found at {cache_path}")
                        db_names = []
                except Exception as ex:
                    logger.error(f"Failed to load offline distinct item names cache: {ex}")
                    db_names = []
            
    if not db_names:
        # Fallback if DB query also fails: just return input names cleaned of asterisks/extra spaces
        cleaned = []
        for name in item_names:
            name_clean = name.replace('*', '').replace('_', '').strip()
            name_clean = re.sub(r'\s+', ' ', name_clean)
            cleaned.append(name_clean)
        return cleaned

    # Build a lookup of normalized DB names
    def normalize(s: str) -> str:
        s = s.replace('*', '').replace('_', '')
        s = s.upper().strip()
        s = re.sub(r'[^A-Z0-9]', '', s)  # Keep only alphanumeric
        return s

    normalized_db = {}
    for db_name in db_names:
        norm = normalize(db_name)
        if norm:
            if norm not in normalized_db:
                normalized_db[norm] = []
            normalized_db[norm].append(db_name)

    resolved_names = []
    for name in item_names:
        # Try exact match first
        if name in db_names:
            resolved_names.append(name)
            continue
            
        # Clean/normalize name
        clean_name = name.replace('*', '').replace('_', '').strip()
        clean_name = re.sub(r'\s+', ' ', clean_name)
        
        # If clean version is exact match
        if clean_name in db_names:
            resolved_names.append(clean_name)
            continue
            
        norm_name = normalize(name)
        if norm_name in normalized_db:
            resolved_names.extend(normalized_db[norm_name])
        else:
            # Fuzzy match fallback: if it contains an alphanumeric sequence, find the closest
            matches = []
            for norm_db_name, db_orig_names in normalized_db.items():
                if norm_name and norm_db_name and (norm_name in norm_db_name or norm_db_name in norm_name):
                    matches.extend(db_orig_names)
            if matches:
                resolved_names.extend(matches)
            else:
                resolved_names.append(clean_name)
                
    # Deduplicate while preserving order
    return list(dict.fromkeys(resolved_names))

async def get_items_stock_and_sales(item_names: List[str], period: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve aggregated stock and sales metrics for a list of items using robust name matching."""
    input_to_db = {}
    all_db_names = []
    
    for name in item_names:
        resolved = await resolve_db_item_names([name])
        input_to_db[name] = resolved
        all_db_names.extend(resolved)
        
    all_db_names = list(set(all_db_names))
    if len(all_db_names) > 30:
        logger.info(f"Limiting resolved database query from {len(all_db_names)} to top 30 items to prevent timeouts.")
        all_db_names = all_db_names[:30]
        
    logger.info(f"Resolved input names {item_names} to database names {all_db_names}")
    
    # Query all historical records to carry forward stock levels accurately
    query = {"item_name": {"$in": all_db_names}, "upload_source": {"$ne": "forecast"}}
    
    cursor = db.sales_records.find(query)
    records = await cursor.to_list(length=1000)
    
    by_item = {}
    for r in records:
        name = r.get("item_name")
        if not name:
            continue
        if name not in by_item:
            by_item[name] = []
        by_item[name].append(r)
        
    db_results = {}
    tz_min = datetime(1, 1, 1, tzinfo=timezone.utc)
    
    # target_period_end is used for filtering stock records
    target_period_end = None
    if period and period != "all":
        _, target_period_end = parse_period_to_range(period)
        
    for name, recs in by_item.items():
        # Sort chronologically by period end date and then by upload date
        recs_sorted = sorted(recs, key=lambda x: (parse_period_to_range(x.get("data_period"))[1], x.get("upload_date") or tz_min))
        
        if not recs_sorted:
            continue
            
        # Determine the target period for this item if not specified
        if not period or period == "all":
            if period == "all":
                item_target_period = "all"
            else:
                # Default to the period of the latest record
                item_target_period = recs_sorted[-1].get("data_period")
        else:
            item_target_period = period
            
        # 1. Calculate sales metrics (total qty, revenue, profit) in the target period
        if item_target_period == "all":
            period_recs = recs_sorted
        else:
            period_recs = [r for r in recs_sorted if is_period_match(r.get("data_period"), item_target_period)]
            
        total_net_qty = sum(r.get("net_qty") or 0 for r in period_recs)
        total_revenue = sum(r.get("r_amt") or 0 for r in period_recs)
        total_profit = sum(r.get("profit") or 0 for r in period_recs)
        
        # 2. Determine closing stock level (latest record <= target_period_end)
        if period and period != "all":
            stock_recs = [r for r in recs_sorted if parse_period_to_range(r.get("data_period"))[1] <= target_period_end]
        else:
            stock_recs = recs_sorted
            
        closing_stock = None
        # Walk backward to find the latest non-None closing stock
        for r in reversed(stock_recs):
            if r.get("closing_stock") is not None:
                closing_stock = r.get("closing_stock")
                break
                
        db_results[name] = {
            "period": item_target_period,
            "current_stock": closing_stock,
            "total_qty_sold": total_net_qty,
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "num_records_aggregated": len(period_recs)
        }
        
    results = {}
    for input_name, resolved_list in input_to_db.items():
        found_results = [db_results[name] for name in resolved_list if name in db_results]
        
        if found_results:
            agg_stock = 0.0
            agg_qty = 0
            agg_revenue = 0.0
            agg_profit = 0.0
            agg_records = 0
            target_period = found_results[0]["period"]
            
            for fr in found_results:
                agg_stock += (fr["current_stock"] or 0.0)
                agg_qty += fr["total_qty_sold"]
                agg_revenue += fr["total_revenue"]
                agg_profit += fr["total_profit"]
                agg_records += fr["num_records_aggregated"]
                
            results[input_name] = {
                "period": target_period,
                "current_stock": agg_stock,
                "total_qty_sold": agg_qty,
                "total_revenue": agg_revenue,
                "total_profit": agg_profit,
                "num_records_aggregated": agg_records,
                "matched_db_names": resolved_list
            }
        else:
            results[input_name] = {
                "period": period or "unknown",
                "current_stock": 0.0,
                "total_qty_sold": 0,
                "total_revenue": 0.0,
                "total_profit": 0.0,
                "num_records_aggregated": 0,
                "message": "No records found in database",
                "matched_db_names": resolved_list
            }
            
    return results

def fix_match_document(d: Any) -> Any:
    if isinstance(d, list):
        return [fix_match_document(item) for item in d]
    if not isinstance(d, dict):
        return d
        
    fixed = {}
    known_fields = {"item_name", "pluno", "product_group", "net_qty", "closing_stock", "r_amt", "profit", "data_period"}
    
    for k, v in d.items():
        if k in ["$and", "$or", "$nor"]:
            fixed[k] = fix_match_document(v)
        elif isinstance(v, dict):
            # Inspect the keys of the nested dict
            inner_fixed = {}
            for ik, iv in v.items():
                if ik in known_fields:
                    # Move to parent level of fixed
                    fixed[ik] = fix_match_document(iv)
                else:
                    inner_fixed[ik] = fix_match_document(iv)
            if inner_fixed:
                fixed[k] = inner_fixed
        else:
            fixed[k] = v
            
    return fixed

def fix_pipeline(pipeline: list) -> list:
    fixed_pipeline = []
    for stage in pipeline:
        if not isinstance(stage, dict):
            fixed_pipeline.append(stage)
            continue
        fixed_stage = {}
        for stage_name, stage_content in stage.items():
            if stage_name == "$match" and isinstance(stage_content, dict):
                fixed_stage[stage_name] = fix_match_document(stage_content)
            else:
                fixed_stage[stage_name] = stage_content
        fixed_pipeline.append(fixed_stage)
    return fixed_pipeline

async def execute_tool(name: str, args: dict) -> Any:
    """Route tool calls to their respective handlers."""
    try:
        if name == "get_abc_analysis":
            return await get_abc_analysis(args.get("group", "all"), args.get("period", "all"))
        
        elif name == "get_capital_blocking_analysis":
            return await get_capital_blocking_analysis(args.get("group", "all"), args.get("period", "all"))
            
        elif name == "get_inventory_health":
            return await get_inventory_analysis(args.get("period", "all"))
            
        elif name == "get_group_analysis":
            return await get_group_analysis(args.get("period", "all"))
            
        elif name == "get_performance_metrics":
            return await get_fastest_selling_items(
                limit=args.get("limit", 10), 
                group=args.get("group", "all"), 
                period=args.get("period", "all")
            )
            
        elif name == "get_daily_sales_trend":
            return await get_daily_sales_trend_by_period(args["period"])
            
        elif name == "run_forecast":
            method = args["method"]
            months = args.get("forecast_months", 3)
            if method == "trend":
                return await simple_trend_forecast(months)
            elif method == "statistical":
                return await statistical_forecast(months)
            elif method == "ai":
                return await ai_forecast()
            else:
                return {"error": "Invalid forecast method"}
                
        elif name == "run_custom_query":
            pipeline_str = args["pipeline_json"]
            try:
                pipeline = json.loads(pipeline_str)
            except Exception as e:
                return {"error": f"Failed to parse pipeline JSON: {e}"}
            
            # Simple security validation
            if not isinstance(pipeline, list):
                return {"error": "Pipeline must be a list of stages."}
                
            # Apply our query fixer to handle common LLM nesting errors
            pipeline = fix_pipeline(pipeline)
            logger.info(f"Executing fixed custom query pipeline: {pipeline}")
            
            for stage in pipeline:
                stage_name = list(stage.keys())[0]
                if stage_name not in ["$match", "$limit", "$project", "$skip"]:
                    return {"error": f"Stage {stage_name} is not allowed on this database tier. DO NOT use $group, $sort, $sum, $max, etc. Just use $match to fetch the raw documents and calculate the answer yourself!"}
            
            # Force limit to prevent massive output crashing the LLM context
            if not any("$limit" in stage for stage in pipeline):
                pipeline.append({"$limit": 50})
                
            return await db.sales_records.aggregate(pipeline).to_list(50)
            
        elif name == "get_items_stock_and_sales":
            return await get_items_stock_and_sales(args["item_names"], args.get("period"))
            
        elif name == "find_relevant_items":
            return await semantic_search_items(args["semantic_query"])
            
        elif name == "train_semantic_mapping":
            return await add_manual_mapping(args["category"], args["item_names"])
            
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        logger.error(f"Tool execution error ({name}): {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

# ─── Main Chat Handler ──────────────────────────────────────────────

async def handle_chat(message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Process a chat message using OpenAI function calling."""
    from openai import AsyncOpenAI

    sid = session_id or str(uuid.uuid4())
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY.")

    client = AsyncOpenAI(api_key=api_key)
    
    # Get available periods for context
    available = await db.sales_records.distinct("data_period", {"upload_source": {"$ne": "forecast"}})
    available = sorted([p for p in available if p])
    
    now_str = datetime.now().strftime('%d %B %Y')
    system_msg = (
        f"You are Sandy, the AI assistant for URC 101 Grocery Sales Analytics Dashboard.\n"
        f"Today's date is {now_str}.\n"
        f"Available Data Periods in the system: {', '.join(available)}.\n\n"
        f"You have access to a variety of tools to pull data from the database. If the user asks a question, use the tools to find the answer!\n"
        f"When users ask about stock positions, inventory, sales quantities, revenue, or profit of specific items, ALWAYS call `get_items_stock_and_sales(item_names, period)`. DO NOT use `run_custom_query` for these under any circumstances, as it will return incomplete or out-of-order data due to MongoDB constraints and result in wrong answers.\n"
        f"IMPORTANT: If the user asks for a generic category or a list of items (like 'luggage', 'noodles', 'footwear', 'popcorn', 'ghee', etc.), ALWAYS call `find_relevant_items(semantic_query)` first to get the exact item names, and then call `get_items_stock_and_sales` with those names!\n"
        f"If the user corrects your mapping (e.g., 'Safari is also luggage'), call `train_semantic_mapping`.\n\n"
        f"CRITICAL MONGO DB RULES FOR run_custom_query:\n"
        f"1. DO NOT call `run_custom_query` if the user's query is about stock levels, quantities sold, revenue, or profit for specific items or categories. You must use `get_items_stock_and_sales` instead.\n"
        f"2. DO NOT nest field names inside other fields in $match. (e.g. {{'$match': {{'item_name': {{'$in': [...]}}, 'data_period': '2026-05'}}}} is correct. DO NOT put data_period inside item_name).\n"
        f"3. DO NOT USE $group or $sort! The database is on a Free Tier and blocks these aggregation operators. If you use $group, it will throw an error.\n"
        f"4. For general queries that don't involve specific item stock/sales, just use $match (and optionally $project) to fetch the raw documents. We return the raw JSON documents up to a limit of 50. You must calculate any final sums or filters in memory yourself!\n"
        f"5. The sales_records collection has fields: item_name, pluno, product_group, net_qty, closing_stock, r_amt (revenue), profit, data_period."
    )

    # Chat history (last 10)
    history = await db.chat_history.find({"session_id": sid}).sort("timestamp", -1).limit(10).to_list(10)
    messages = [{"role": "system", "content": system_msg}]
    for h in reversed(history):
        messages.append({"role": "user", "content": h.get("user_message", "")})
        messages.append({"role": "assistant", "content": h.get("assistant_response", "")})
    
    messages.append({"role": "user", "content": message})

    # Call OpenAI with tools
    completion = await client.chat.completions.create(
        model=CHATBOT_MODEL,
        messages=messages,
        tools=CHATBOT_TOOLS,
        tool_choice="auto",
        max_tokens=CHATBOT_MAX_TOKENS,
        temperature=CHATBOT_TEMPERATURE,
    )
    
    response_message = completion.choices[0].message
    
    # Handle Tool Calls in a loop to allow multi-step agent reasoning (e.g. semantic search -> custom query)
    tool_turns = 0
    while response_message.tool_calls and tool_turns < 5:
        tool_turns += 1
        messages.append(response_message)
        
        # Execute each tool generated in this turn
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            try:
                function_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                function_args = {}
                
            logger.info(f"Chatbot executing tool {function_name} (turn {tool_turns}) with args {function_args}")
            
            tool_result = await execute_tool(function_name, function_args)
            
            # Serialize result to JSON string
            result_str = json.dumps(tool_result, default=str)[:30000] # Cap length to avoid context overflow
            
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": result_str
            })
            
        # Call OpenAI again with the tool results, keeping tools available
        completion = await client.chat.completions.create(
            model=CHATBOT_MODEL,
            messages=messages,
            tools=CHATBOT_TOOLS,
            tool_choice="auto",
            max_tokens=CHATBOT_MAX_TOKENS,
            temperature=CHATBOT_TEMPERATURE,
        )
        response_message = completion.choices[0].message
        
    final_response = response_message.content

    # Save to history
    await db.chat_history.insert_one({
        "session_id": sid,
        "user_message": message,
        "assistant_response": final_response,
        "timestamp": datetime.now(timezone.utc),
    })

    return {"response": final_response, "session_id": sid}
