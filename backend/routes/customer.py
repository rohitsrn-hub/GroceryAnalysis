"""
Customer routes — public customer chatbot and inventory search APIs.
Exposes restricted, secure access for end-customers to query store stock.
"""
import os
import json
import uuid
import re
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from database import db
from config import logger, CHATBOT_MAX_TOKENS, CHATBOT_TEMPERATURE, CHATBOT_MODEL
from services.semantic_service import _EMBEDDINGS_CACHE, semantic_search_items, _cosine_similarity
from services.chatbot_service import resolve_db_item_names, get_items_stock_and_sales

router = APIRouter(prefix="/api/customer", tags=["customer"])

CATEGORY_DESCRIPTIONS = {
    "Group I": "Group I - Personal Care & Shaving",
    "Group II": "Group II - Household & Cleaning",
    "Group III": "Group III - Luggage & Apparel",
    "Group IV": "Group IV - Watches & Stationery",
    "Group V": "Group V - Liquor",
    "Group VI": "Group VI - Groceries, Snacks & Food"
}

# ─── Pydantic Models ──────────────────────────────────────────────────

class CustomerChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    category_filter: Optional[str] = None

class ShoppingListCheckRequest(BaseModel):
    items: List[str]
    category_filter: Optional[str] = None
    session_id: Optional[str] = None

def parse_item_quantity(raw_item: str) -> tuple[str, int]:
    raw_item = raw_item.strip()
    # Check leading number, e.g. "3 avocados", "3x avocados", "3 pcs avocados"
    leading_match = re.match(r'^(\d+)\s*(?:x|qty:?|pcs|pc|packs|pack|pk)?\s+(.+)$', raw_item, re.IGNORECASE)
    if leading_match:
        try:
            qty = int(leading_match.group(1))
            item_query = leading_match.group(2).strip()
            if item_query:
                return item_query, qty
        except ValueError:
            pass
        
    # Check trailing number, e.g. "avocados 3", "avocados x3", "avocados qty 3"
    trailing_match = re.match(r'^(.+?)\s+(?:x|qty:?|pcs|pc|packs|pack|pk)?\s*(\d+)$', raw_item, re.IGNORECASE)
    if trailing_match:
        try:
            item_query = trailing_match.group(1).strip()
            qty = int(trailing_match.group(2))
            if item_query:
                return item_query, qty
        except ValueError:
            pass
        
    # Check format with parenthesis, e.g., "avocados (3)", "avocados (qty 3)"
    paren_match = re.match(r'^(.+?)\s*\(\s*(?:x|qty:?|pcs|pc|packs|pack|pk)?\s*(\d+)\s*\)$', raw_item, re.IGNORECASE)
    if paren_match:
        try:
            item_query = paren_match.group(1).strip()
            qty = int(paren_match.group(2))
            if item_query:
                return item_query, qty
        except ValueError:
            pass
        
    return raw_item, 1


# ─── Search Logging Helper ──────────────────────────────────────────

async def log_customer_search(
    query: str,
    category_filter: Optional[str] = None,
    matched_items: List[str] = [],
    is_available: bool = False,
    session_id: Optional[str] = None,
    search_type: str = "chat"
):
    """Log customer searches for store demand planning."""
    try:
        await db.customer_searches.insert_one({
            "query": query.strip(),
            "category_filter": category_filter,
            "timestamp": datetime.now(timezone.utc),
            "session_id": session_id or str(uuid.uuid4()),
            "matched_items": matched_items,
            "is_available": is_available,
            "search_type": search_type
        })
    except Exception as e:
        logger.error(f"Failed to log customer search: {e}")

# ─── Route Definitions ────────────────────────────────────────────────

@router.get("/categories")
async def get_categories():
    """Get all unique product groups for the customer dropdown filter."""
    try:
        groups = await db.sales_records.distinct("product_group")
        # Filter out empty or null groups and sort alphabetically
        valid_groups = sorted([g for g in groups if g])
        
        # Append Group V for Liquor if not present in the DB groups list
        if "Group V" not in valid_groups:
            valid_groups.append("Group V")
            
        # Map to their detailed descriptive labels
        valid_groups = sorted(valid_groups)
        categories = [CATEGORY_DESCRIPTIONS.get(g, g) for g in valid_groups]
        return {"categories": categories}
    except Exception as e:
        logger.exception(f"Error fetching categories: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching categories: {str(e)}"
        )


@router.post("/chat")
async def customer_chat(request: CustomerChatRequest):
    """Secure customer-facing chatbot. Exposes only stock lookup tools."""
    from openai import AsyncOpenAI

    # Map descriptive category filter back to raw group name for database queries
    raw_category = None
    if request.category_filter:
        for raw, desc in CATEGORY_DESCRIPTIONS.items():
            if desc == request.category_filter or raw == request.category_filter:
                raw_category = raw
                break
        if not raw_category:
            raw_category = request.category_filter

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured on backend."
        )

    client = AsyncOpenAI(api_key=api_key)
    sid = request.session_id or str(uuid.uuid4())
    additions = []
    checked_items = []

    # Build customer-safe system instructions
    now_str = datetime.now().strftime('%d %B %Y')
    
    # Optional category scope instruction
    cat_scope = ""
    if request.category_filter:
        cat_scope = f"The customer has filtered their view to the '{request.category_filter}' category. Direct your answers primarily towards products in this category.\n"

    system_msg = (
        f"You are Sandy, a helpful retail shopping assistant for our grocery store.\n"
        f"Today's date is {now_str}.\n"
        f"{cat_scope}"
        f"Your job is to assist customers in checking the stock availability of items they want to buy.\n"
        f"DO NOT answer any questions about company finances, total revenues, margins, profits, forecasting, or administrative reports. "
        f"If the customer asks about these topics, politely explain that you are only programmed to help find items in stock.\n\n"
        f"You have access to three tools:\n"
        f"1. `find_relevant_items(semantic_query)`: Find database names for a general search term (e.g. 'coke', 'butter', 'popcorn').\n"
        f"2. `get_items_stock_and_sales(item_names)`: Get stock levels for exact database item names.\n"
        f"3. `add_items_to_shopping_list(items)`: Add a list of items with their quantities to the customer's shopping list. Use this when the customer explicitly asks to add items to their shopping list (e.g. 'Add 3 Hass Avocados to my list').\n\n"
        f"When a customer asks about a product, ALWAYS call `find_relevant_items` first to see what matching products we sell, "
        f"and then call `get_items_stock_and_sales` to check their quantities.\n"
        f"If a customer explicitly asks to add items to their shopping list, call `add_items_to_shopping_list` with the item names and quantities.\n"
        f"Provide helpful, friendly stock descriptions. If an item has 0 stock, tell the customer it is currently out of stock."
    )

    # Define customer-safe tools
    customer_tools = [
        {
            "type": "function",
            "function": {
                "name": "find_relevant_items",
                "description": "Finds specific database item names that match a broad query (e.g. 'noodles', 'chips', 'ghee'). Use this FIRST before checking stock.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "semantic_query": {"type": "string", "description": "The search term or product category"}
                    },
                    "required": ["semantic_query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_items_stock_and_sales",
                "description": "Retrieve stock levels for a list of exact database item names.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of exact item names"
                        }
                    },
                    "required": ["item_names"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_items_to_shopping_list",
                "description": "Add one or more items to the customer's shopping list. Use this when the customer explicitly asks to add items to their shopping list.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "item_query": {"type": "string", "description": "The description or name of the item to add, e.g. 'avocados' or 'organic eggs'."},
                                    "quantity": {"type": "integer", "description": "The quantity of the item to add, default 1."}
                                },
                                "required": ["item_query"]
                            },
                            "description": "List of items to add."
                        }
                    },
                    "required": ["items"]
                }
            }
        }
    ]

    try:
        # Load last 10 chat messages
        history = await db.chat_history.find({"session_id": sid}).sort("timestamp", -1).limit(10).to_list(10)
        messages = [{"role": "system", "content": system_msg}]
        
        for h in reversed(history):
            messages.append({"role": "user", "content": h.get("user_message", "")})
            messages.append({"role": "assistant", "content": h.get("assistant_response", "")})
        
        messages.append({"role": "user", "content": request.message})

        # OpenAI Execution loop
        completion = await client.chat.completions.create(
            model=CHATBOT_MODEL,
            messages=messages,
            tools=customer_tools,
            tool_choice="auto",
            max_tokens=CHATBOT_MAX_TOKENS,
            temperature=CHATBOT_TEMPERATURE,
        )
        
        response_message = completion.choices[0].message
        
        tool_turns = 0
        logged_items = []
        logged_query = request.message
        
        while response_message.tool_calls and tool_turns < 5:
            tool_turns += 1
            messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except:
                    args = {}
                
                # Executing tools securely
                if function_name == "find_relevant_items":
                    query_term = args.get("semantic_query", "")
                    results = await semantic_search_items(query_term)
                    
                    # Filter results by category if selected
                    if raw_category:
                        filtered_results = []
                        for name in results:
                            if raw_category == "Group V":
                                exists = await db.client["URC1oh1LiquorSales"].liquor_data.find_one({"brand_name": name})
                                if exists:
                                    filtered_results.append(name)
                            else:
                                rec = await db.sales_records.find_one({"item_name": name})
                                if rec and rec.get("product_group") == raw_category:
                                    filtered_results.append(name)
                        results = filtered_results if filtered_results else results
                    
                    tool_result = results
                    logged_query = query_term
                
                elif function_name == "get_items_stock_and_sales":
                    raw_names = args.get("item_names", [])
                    # Secure intercept: strip revenue/profit from tool responses!
                    full_res = await get_items_stock_and_sales(raw_names)
                    
                    customer_safe_res = {}
                    has_available = False
                    for k, val in full_res.items():
                        stock = val.get("current_stock", 0.0)
                        customer_safe_res[k] = {
                            "current_stock": stock,
                            "period": val.get("period")
                        }
                        if stock > 0:
                            has_available = True
                        logged_items.append(k)

                        # Populate checked_items for cards display
                        db_name = val.get("matched_db_names", [k])[0] if val.get("matched_db_names") else k
                        
                        # Find the product group from sales_records, embeddings cache, or liquor database
                        group_name = "General"
                        rec = await db.sales_records.find_one({"item_name": db_name})
                        if rec:
                            group_name = rec.get("product_group", "General")
                        else:
                            for item in _EMBEDDINGS_CACHE:
                                if item["item_name"] == db_name:
                                    group_name = item.get("product_group", "General")
                                    break
                            if group_name == "General":
                                is_liq = await db.client["URC1oh1LiquorSales"].liquor_data.find_one({"brand_name": db_name})
                                if is_liq:
                                    group_name = "Group V"
                        
                        group_name = CATEGORY_DESCRIPTIONS.get(group_name, group_name)
                        
                        # Avoid duplicates in checked_items
                        if not any(item["item_name"] == db_name for item in checked_items):
                            checked_items.append({
                                "item_name": db_name,
                                "stock": stock,
                                "category": group_name
                            })
                    
                    # Log the search
                    await log_customer_search(
                        query=logged_query,
                        category_filter=request.category_filter,
                        matched_items=logged_items,
                        is_available=has_available,
                        session_id=sid,
                        search_type="chat"
                    )
                    
                    tool_result = customer_safe_res

                elif function_name == "add_items_to_shopping_list":
                    items_to_add = args.get("items", [])
                    tool_result_items = []
                    
                    for item_obj in items_to_add:
                        item_query = item_obj.get("item_query", "")
                        qty = item_obj.get("quantity", 1)
                        
                        clean_item, parsed_qty = parse_item_quantity(item_query)
                        if parsed_qty != 1:
                            qty = parsed_qty
                            
                        # Resolve name using semantics or regex
                        results_set = []
                        try:
                            # Use OpenAI client from endpoint scope
                            emb_res = await client.embeddings.create(
                                model="text-embedding-3-small",
                                input=[clean_item]
                            )
                            query_vector = np.array(emb_res.data[0].embedding, dtype=np.float32)
                            
                            # Check manual mapping overrides first
                            override = await db.semantic_mappings.find_one({"category": {"$regex": f"^{clean_item}$", "$options": "i"}})
                            if override and "item_names" in override:
                                results_set.extend(override["item_names"])
                                
                            # Cosine similarity matching
                            if len(_EMBEDDINGS_CACHE) > 0:
                                scored_items = []
                                for emb_item in _EMBEDDINGS_CACHE:
                                    if emb_item["item_name"] in results_set:
                                        continue
                                    if raw_category and emb_item["product_group"] != raw_category:
                                        continue
                                    sim = _cosine_similarity(query_vector, emb_item["embedding"])
                                    scored_items.append((sim, emb_item["item_name"], emb_item["product_group"]))
                                scored_items.sort(reverse=True, key=lambda x: x[0])
                                for sim, name, group in scored_items[:3]:
                                    if sim > 0.28:
                                        results_set.append(name)
                        except Exception as emb_err:
                            logger.error(f"Embedding generation error in tool: {emb_err}")
                            
                        if not results_set:
                            if raw_category:
                                if raw_category == "Group V":
                                    fq = {"brand_name": {"$regex": clean_item, "$options": "i"}}
                                    fallback_names = await db.client["URC1oh1LiquorSales"].liquor_data.distinct("brand_name", fq)
                                else:
                                    fq = {"item_name": {"$regex": clean_item, "$options": "i"}, "product_group": raw_category}
                                    fallback_names = await db.sales_records.distinct("item_name", fq)
                            else:
                                fq = {"item_name": {"$regex": clean_item, "$options": "i"}}
                                fallback_names = await db.sales_records.distinct("item_name", fq)
                                # Check liquor database too as fallback
                                liq_fq = {"brand_name": {"$regex": clean_item, "$options": "i"}}
                                liq_fallbacks = await db.client["URC1oh1LiquorSales"].liquor_data.distinct("brand_name", liq_fq)
                                fallback_names.extend(liq_fallbacks)
                            results_set.extend(fallback_names[:3])
                            
                        matched_item_name = clean_item
                        stock_level = 0.0
                        cat_group = CATEGORY_DESCRIPTIONS.get(raw_category, raw_category) if raw_category else "General"
                        available = False
                        reason = "Not Found"
                        
                        if results_set:
                            stock_data = await get_items_stock_and_sales(results_set)
                            in_stock_matches = []
                            for name in results_set:
                                data = stock_data.get(name, {})
                                stock = data.get("current_stock", 0.0)
                                if stock > 0:
                                    group_name = "General"
                                    rec = await db.sales_records.find_one({"item_name": name})
                                    if rec:
                                        group_name = rec.get("product_group", "General")
                                    else:
                                        for item in _EMBEDDINGS_CACHE:
                                            if item["item_name"] == name:
                                                group_name = item.get("product_group", "General")
                                                break
                                        if group_name == "General":
                                            is_liq = await db.client["URC1oh1LiquorSales"].liquor_data.find_one({"brand_name": name})
                                            if is_liq:
                                                group_name = "Group V"
                                                
                                    group_name = CATEGORY_DESCRIPTIONS.get(group_name, group_name)
                                    in_stock_matches.append({
                                        "item_name": name,
                                        "stock": stock,
                                        "category": group_name
                                    })
                            
                            if in_stock_matches:
                                matched_item_name = in_stock_matches[0]["item_name"]
                                stock_level = in_stock_matches[0]["stock"]
                                cat_group = in_stock_matches[0]["category"]
                                available = True
                                reason = None
                            else:
                                matched_item_name = results_set[0]
                                group_name = "General"
                                rec = await db.sales_records.find_one({"item_name": matched_item_name})
                                if rec:
                                    group_name = rec.get("product_group", "General")
                                else:
                                    for item in _EMBEDDINGS_CACHE:
                                        if item["item_name"] == matched_item_name:
                                            group_name = item.get("product_group", "General")
                                            break
                                    if group_name == "General":
                                        is_liq = await db.client["URC1oh1LiquorSales"].liquor_data.find_one({"brand_name": matched_item_name})
                                        if is_liq:
                                            group_name = "Group V"
                                cat_group = CATEGORY_DESCRIPTIONS.get(group_name, group_name)
                                stock_level = 0.0
                                available = False
                                reason = "Out of Stock"
                        
                        addition_entry = {
                            "original_query": f"{qty} {clean_item}",
                            "clean_query": clean_item,
                            "requested_qty": qty,
                            "matched_item": matched_item_name,
                            "stock": stock_level,
                            "category": cat_group,
                            "available": available,
                            "reason": reason
                        }
                        
                        additions.append(addition_entry)
                        tool_result_items.append({
                            "item": matched_item_name,
                            "requested_qty": qty,
                            "status": "added" if available else ("out_of_stock" if reason == "Out of Stock" else "not_found")
                        })
                        
                    tool_result = {"status": "success", "added_items": tool_result_items}

                else:
                    tool_result = {"error": "Unauthorized tool selection"}

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result)
                })

            completion = await client.chat.completions.create(
                model=CHATBOT_MODEL,
                messages=messages,
                tools=customer_tools,
                tool_choice="auto",
                max_tokens=CHATBOT_MAX_TOKENS,
                temperature=CHATBOT_TEMPERATURE,
            )
            response_message = completion.choices[0].message
            
        final_text = response_message.content

        # Save to database chat history
        await db.chat_history.insert_one({
            "session_id": sid,
            "user_message": request.message,
            "assistant_response": final_text,
            "timestamp": datetime.now(timezone.utc)
        })

        return {
            "response": final_text,
            "session_id": sid,
            "checked_items": checked_items,
            "additions": additions
        }

    except Exception as e:
        logger.exception("Error in customer chatbot execution")
        raise HTTPException(status_code=500, detail=f"Error in chat processing: {str(e)}")


@router.post("/check-list")
async def check_shopping_list(request: ShoppingListCheckRequest):
    """Check availability of a list of products. Semantic matching and stock checks."""
    from openai import AsyncOpenAI

    # Map descriptive category filter back to raw group name for database queries
    raw_category = None
    if request.category_filter:
        for raw, desc in CATEGORY_DESCRIPTIONS.items():
            if desc == request.category_filter or raw == request.category_filter:
                raw_category = raw
                break
        if not raw_category:
            raw_category = request.category_filter

    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured on backend."
        )

    client = AsyncOpenAI(api_key=api_key)
    sid = request.session_id or str(uuid.uuid4())

    input_items = [item.strip() for item in request.items if item.strip()]
    if not input_items:
        return {"available": [], "unavailable": [], "session_id": sid}

    parsed_items = [parse_item_quantity(item) for item in input_items]
    clean_items = [p[0] for p in parsed_items]

    available_list = []
    unavailable_list = []

    try:
        # Step 1: Batch generate embeddings for all list items
        logger.info(f"Generating embeddings for shopping list of {len(clean_items)} items...")
        embeddings_response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=clean_items
        )
        
        # Step 2: Iterate and match each item
        for idx, (clean_item, qty) in enumerate(parsed_items):
            original_item = input_items[idx]
            query_vector = np.array(embeddings_response.data[idx].embedding, dtype=np.float32)
            
            # Check manual mapping overrides first
            results_set = []
            override = await db.semantic_mappings.find_one({"category": {"$regex": f"^{clean_item}$", "$options": "i"}})
            if override and "item_names" in override:
                results_set.extend(override["item_names"])
                
            # Cosine similarity matching
            if len(_EMBEDDINGS_CACHE) > 0:
                scored_items = []
                for emb_item in _EMBEDDINGS_CACHE:
                    if emb_item["item_name"] in results_set:
                        continue
                    
                    # Filter by category if selected
                    if raw_category and emb_item["product_group"] != raw_category:
                        continue
                        
                    sim = _cosine_similarity(query_vector, emb_item["embedding"])
                    scored_items.append((sim, emb_item["item_name"], emb_item["product_group"]))
                    
                scored_items.sort(reverse=True, key=lambda x: x[0])
                # Append top similarities above threshold (0.28)
                for sim, name, group in scored_items[:3]:
                    if sim > 0.28:
                        results_set.append(name)
                        
            # If no embeddings cache matches, do regex fallback
            if not results_set:
                if raw_category:
                    if raw_category == "Group V":
                        fq = {"brand_name": {"$regex": clean_item, "$options": "i"}}
                        fallback_names = await db.client["URC1oh1LiquorSales"].liquor_data.distinct("brand_name", fq)
                    else:
                        fq = {"item_name": {"$regex": clean_item, "$options": "i"}, "product_group": raw_category}
                        fallback_names = await db.sales_records.distinct("item_name", fq)
                else:
                    fq = {"item_name": {"$regex": clean_item, "$options": "i"}}
                    fallback_names = await db.sales_records.distinct("item_name", fq)
                    # Check liquor database too as fallback
                    liq_fq = {"brand_name": {"$regex": clean_item, "$options": "i"}}
                    liq_fallbacks = await db.client["URC1oh1LiquorSales"].liquor_data.distinct("brand_name", liq_fq)
                    fallback_names.extend(liq_fallbacks)
                results_set.extend(fallback_names[:3])

            # Gather stock info for matched items
            if results_set:
                stock_data = await get_items_stock_and_sales(results_set)
                
                # Filter out those with stock > 0
                in_stock_matches = []
                for name in results_set:
                    data = stock_data.get(name, {})
                    stock = data.get("current_stock", 0.0)
                    if stock > 0:
                        # Find the group
                        group_name = "General"
                        rec = await db.sales_records.find_one({"item_name": name})
                        if rec:
                            group_name = rec.get("product_group", "General")
                        else:
                            for item in _EMBEDDINGS_CACHE:
                                if item["item_name"] == name:
                                    group_name = item.get("product_group", "General")
                                    break
                            if group_name == "General":
                                is_liq = await db.client["URC1oh1LiquorSales"].liquor_data.find_one({"brand_name": name})
                                if is_liq:
                                    group_name = "Group V"
                        
                        group_name = CATEGORY_DESCRIPTIONS.get(group_name, group_name)
                        
                        in_stock_matches.append({
                            "item_name": name,
                            "stock": stock,
                            "category": group_name
                        })
                
                if in_stock_matches:
                    available_list.append({
                        "original_query": original_item,
                        "clean_query": clean_item,
                        "requested_qty": qty,
                        "matched_item": in_stock_matches[0]["item_name"],
                        "stock": in_stock_matches[0]["stock"],
                        "category": in_stock_matches[0]["category"],
                        "alternatives": in_stock_matches[1:]
                    })
                    
                    # Log as successful search
                    await log_customer_search(
                        query=clean_item,
                        category_filter=request.category_filter,
                        matched_items=[m["item_name"] for m in in_stock_matches],
                        is_available=True,
                        session_id=sid,
                        search_type="list_parse"
                    )
                else:
                    # Matched but out of stock
                    # Find category name
                    db_name = results_set[0]
                    group_name = "General"
                    rec = await db.sales_records.find_one({"item_name": db_name})
                    if rec:
                        group_name = rec.get("product_group", "General")
                    else:
                        for item in _EMBEDDINGS_CACHE:
                            if item["item_name"] == db_name:
                                group_name = item.get("product_group", "General")
                                break
                        if group_name == "General":
                            is_liq = await db.client["URC1oh1LiquorSales"].liquor_data.find_one({"brand_name": db_name})
                            if is_liq:
                                group_name = "Group V"
                    group_name = CATEGORY_DESCRIPTIONS.get(group_name, group_name)
                    
                    unavailable_list.append({
                        "original_query": original_item,
                        "clean_query": clean_item,
                        "requested_qty": qty,
                        "reason": "Out of Stock",
                        "matched_item": db_name,
                        "category": group_name
                    })
                    
                    await log_customer_search(
                        query=clean_item,
                        category_filter=request.category_filter,
                        matched_items=results_set,
                        is_available=False,
                        session_id=sid,
                        search_type="list_parse"
                    )
            else:
                # No matches found at all
                unavailable_list.append({
                    "original_query": original_item,
                    "clean_query": clean_item,
                    "requested_qty": qty,
                    "reason": "Not Found",
                    "category": request.category_filter or "General"
                })
                
                await log_customer_search(
                    query=clean_item,
                    category_filter=request.category_filter,
                    matched_items=[],
                    is_available=False,
                    session_id=sid,
                    search_type="list_parse"
                )

        return {
            "available": available_list,
            "unavailable": unavailable_list,
            "session_id": sid
        }

    except Exception as e:
        logger.exception("Error checking shopping list")
        raise HTTPException(status_code=500, detail=f"Error checking shopping list: {str(e)}")


@router.get("/popular-searches")
async def get_popular_searches(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=100),
    search_type: Optional[str] = Query(None)
):
    """Aggregate customer searches to highlight future stock demands. (Admin endpoint)
    
    Uses Python-level aggregation to avoid MongoDB Atlas Free Tier restrictions
    on $group, $sort, and $project pipeline operators.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        match_query: Dict[str, Any] = {"timestamp": {"$gte": cutoff}}

        if search_type:
            match_query["search_type"] = search_type

        # Fetch raw documents — no aggregation pipeline
        raw_docs = await db.customer_searches.find(
            match_query,
            {"query": 1, "is_available": 1, "category_filter": 1,
             "matched_items": 1, "timestamp": 1, "_id": 0}
        ).to_list(5000)

        # Aggregate in Python
        buckets: Dict[str, Dict] = {}
        for doc in raw_docs:
            key = doc.get("query", "").strip().lower()
            if not key:
                continue

            if key not in buckets:
                buckets[key] = {
                    "query": doc.get("query", "").strip(),
                    "search_count": 0,
                    "available_count": 0,
                    "categories": set(),
                    "matched_items": set(),
                    "last_searched": doc.get("timestamp"),
                }

            b = buckets[key]
            b["search_count"] += 1
            if doc.get("is_available"):
                b["available_count"] += 1
            cat = doc.get("category_filter")
            if cat:
                b["categories"].add(cat)
            for item in (doc.get("matched_items") or []):
                b["matched_items"].add(item)
            ts = doc.get("timestamp")
            if ts and (b["last_searched"] is None or ts > b["last_searched"]):
                b["last_searched"] = ts

        # Build result list with availability_rate
        results = []
        for b in buckets.values():
            sc = b["search_count"]
            availability_rate = (b["available_count"] / sc * 100) if sc > 0 else 0
            results.append({
                "query": b["query"],
                "search_count": sc,
                "availability_rate": round(availability_rate, 1),
                "categories": list(b["categories"]),
                "matched_items": sorted(list(b["matched_items"])),
                "last_searched": b["last_searched"].isoformat() if b["last_searched"] else None,
            })

        # Sort by search_count descending, cap at limit
        results.sort(key=lambda x: x["search_count"], reverse=True)
        results = results[:limit]

        return {"popular_searches": results, "time_range_days": days}

    except Exception as e:
        logger.exception("Error aggregating popular searches")
        raise HTTPException(status_code=500, detail=str(e))

