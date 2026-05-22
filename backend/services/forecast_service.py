"""
Forecast service — demand forecasting (trend, statistical, AI).
Extracted from server.py L3869-4100.

Methods:
- Simple linear trend regression
- Statistical moving average with damped trend
- AI placeholder (LLM-powered, future)
"""
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional

# numpy and sklearn imported lazily inside forecast functions
# to avoid ImportError when sklearn is not installed

from database import db
from config import logger
from utils.formatting import extract_group_from_pluno


async def get_monthly_summary_data_for_forecast() -> Tuple[Dict, str]:
    """Get item-wise monthly data for forecasting.

    Priority:
    1. monthly_summaries collection (auto-generated or user-uploaded)
    2. Aggregating raw sales_records as fallback

    Returns:
        (items_data dict, data_source label)
    """
    monthly_summaries = await db.monthly_summaries.find(
        {"summary_type": "monthly"}
    ).sort("period", 1).to_list(None)

    if monthly_summaries and len(monthly_summaries) >= 2:
        items_data: Dict = defaultdict(
            lambda: {"periods": [], "sales": [], "metadata": {}}
        )

        for summary in monthly_summaries:
            period = summary['period']
            for item in summary.get('items', []):
                item_key = item.get('pluno') or item.get('item_name')
                if item_key:
                    items_data[item_key]["periods"].append(period)
                    items_data[item_key]["sales"].append(item.get('net_qty', 0))
                    if not items_data[item_key]["metadata"]:
                        items_data[item_key]["metadata"] = {
                            "pluno": item.get('pluno'),
                            "item_name": item.get('item_name'),
                            "product_group": item.get('product_group'),
                        }

        logger.info(
            f"Using {len(monthly_summaries)} monthly summaries for forecast "
            f"with {len(items_data)} items"
        )
        return items_data, "monthly_summaries"

    # Fallback: aggregate from raw sales_records
    logger.info("No monthly summaries found, aggregating from raw sales_records")
    periods = await db.sales_records.distinct(
        "data_period", {"upload_source": {"$ne": "forecast"}}
    )
    monthly_periods = sorted([p for p in periods if p and len(p) == 7])

    if len(monthly_periods) < 2:
        return {}, "insufficient_data"

    pipeline = [
        {
            "$match": {
                "upload_source": {"$ne": "forecast"},
                "data_period": {"$in": monthly_periods},
            }
        },
        {
            "$group": {
                "_id": {
                    "pluno": "$pluno",
                    "item_name": "$item_name",
                    "product_group": "$product_group",
                    "period": "$data_period",
                },
                "total_qty": {"$sum": "$net_qty"},
            }
        },
        {"$sort": {"_id.period": 1}},
    ]

    raw_data = await db.sales_records.aggregate(pipeline).to_list(None)

    items_data = defaultdict(lambda: {"periods": [], "sales": [], "metadata": {}})
    for record in raw_data:
        item_key = record['_id'].get('pluno') or record['_id'].get('item_name')
        if item_key:
            items_data[item_key]["periods"].append(record['_id']['period'])
            items_data[item_key]["sales"].append(record.get('total_qty', 0))
            if not items_data[item_key]["metadata"]:
                items_data[item_key]["metadata"] = {
                    "pluno": record['_id'].get('pluno'),
                    "item_name": record['_id'].get('item_name'),
                    "product_group": record['_id'].get('product_group'),
                }

    logger.info(
        f"Aggregated {len(raw_data)} records into {len(items_data)} items "
        f"from {len(monthly_periods)} periods"
    )
    return items_data, "raw_aggregation"


async def simple_trend_forecast(forecast_months: int = 4) -> Dict[str, Any]:
    """Simple linear trend forecasting using monthly summarized data."""
    items_data, data_source = await get_monthly_summary_data_for_forecast()

    if not items_data:
        return {
            "forecasts": [],
            "message": "Insufficient data. Need at least 2 months of data.",
            "data_source": data_source,
        }

    forecasts = {}
    for item_key, data in items_data.items():
        sales_data = data["sales"]
        metadata = data["metadata"]

        if len(sales_data) >= 2:
            import numpy as np
            from sklearn.linear_model import LinearRegression

            X = np.array(range(len(sales_data))).reshape(-1, 1)
            y = np.array(sales_data)

            model = LinearRegression()
            model.fit(X, y)

            future_X = np.array(
                list(range(len(sales_data), len(sales_data) + forecast_months))
            ).reshape(-1, 1)
            forecast_values = model.predict(future_X)

            forecasts[item_key] = {
                "pluno": metadata.get("pluno"),
                "item_name": metadata.get("item_name"),
                "product_group": metadata.get("product_group")
                    or extract_group_from_pluno(metadata.get("pluno", "")),
                "method": "trend",
                "historical_periods": data["periods"],
                "historical_sales": sales_data,
                "forecasted_sales": [max(0, int(f)) for f in forecast_values],
                "trend_direction": "increasing" if model.coef_[0] > 0 else "decreasing",
                "confidence": "high" if len(sales_data) >= 3 else "medium",
            }

    return {
        "forecasts": list(forecasts.values()),
        "data_source": data_source,
        "periods_used": len(next(iter(items_data.values()))["periods"]) if items_data else 0,
        "items_forecasted": len(forecasts),
    }


async def statistical_forecast(forecast_months: int = 4) -> Dict[str, Any]:
    """Statistical forecasting using moving averages with damped trend."""
    items_data, data_source = await get_monthly_summary_data_for_forecast()

    if not items_data:
        return {
            "forecasts": [],
            "message": "Insufficient data. Need at least 2 months of data.",
            "data_source": data_source,
        }

    forecasts = {}
    for item_key, data in items_data.items():
        sales_data = data["sales"]
        metadata = data["metadata"]

        if len(sales_data) >= 2:
            window = min(3, len(sales_data))
            moving_avg = sum(sales_data[-window:]) / window

            if len(sales_data) >= 3:
                recent_trend = (sales_data[-1] - sales_data[-3]) / 2
            else:
                recent_trend = sales_data[-1] - sales_data[-2]

            forecast = []
            for i in range(forecast_months):
                predicted = moving_avg + (recent_trend * (i + 1) * 0.5)
                forecast.append(max(0, int(predicted)))

            forecasts[item_key] = {
                "pluno": metadata.get("pluno"),
                "item_name": metadata.get("item_name"),
                "product_group": metadata.get("product_group")
                    or extract_group_from_pluno(metadata.get("pluno", "")),
                "method": "statistical",
                "historical_periods": data["periods"],
                "historical_sales": sales_data,
                "forecasted_sales": forecast,
                "moving_average": round(moving_avg, 2),
                "trend": round(recent_trend, 2),
                "trend_direction": "increasing" if recent_trend > 0 else "decreasing",
                "confidence": (
                    "high" if len(sales_data) >= 6
                    else "medium" if len(sales_data) >= 3
                    else "low"
                ),
            }

    return {
        "forecasts": list(forecasts.values()),
        "data_source": data_source,
        "periods_used": len(next(iter(items_data.values()))["periods"]) if items_data else 0,
        "items_forecasted": len(forecasts),
    }


async def get_forecast_requirements() -> Dict[str, Any]:
    """Get data requirements and available data for demand forecasting."""
    try:
        from services.period_service import format_period_display_name
        
        # Check available monthly summaries
        monthly_summaries = await db.monthly_summaries.find(
            {"summary_type": "monthly"},
            {"period": 1, "display_name": 1, "total_revenue": 1, "item_count": 1, "source": 1, "created_at": 1}
        ).sort("period", -1).to_list(None)
        
        # Check available yearly summaries
        yearly_summaries = await db.monthly_summaries.find(
            {"summary_type": "yearly"},
            {"period": 1, "display_name": 1, "total_revenue": 1, "item_count": 1, "source": 1}
        ).sort("period", -1).to_list(None)
        
        # Also check raw periods from sales_records (for data not yet summarized)
        raw_periods = await db.sales_records.distinct("data_period", {"upload_source": {"$ne": "forecast"}})
        raw_periods = [p for p in raw_periods if p]
        
        # Get unique periods from both sources
        summarized_periods = [s['period'] for s in monthly_summaries]
        unsummarized_periods = [p for p in raw_periods if p not in summarized_periods and len(p) == 7]  # YYYY-MM format
        
        # Format available data for display
        available_monthly_data = []
        for summary in monthly_summaries:
            summary['_id'] = str(summary.get('_id', ''))
            available_monthly_data.append({
                "period": summary['period'],
                "display_name": summary.get('display_name', summary['period']),
                "item_count": summary.get('item_count', 0),
                "total_revenue": summary.get('total_revenue', 0),
                "source": summary.get('source', 'unknown'),
                "status": "summarized"
            })
        
        # Add unsummarized periods
        for period in sorted(unsummarized_periods, reverse=True):
            # Get item count for this period
            count = await db.sales_records.count_documents({"data_period": period, "upload_source": {"$ne": "forecast"}})
            formatted_name = format_period_display_name(period)
            available_monthly_data.append({
                "period": period,
                "display_name": formatted_name,
                "item_count": count,
                "total_revenue": 0,  # Not calculated yet
                "source": "raw_data",
                "status": "not_summarized"
            })
        
        # Sort by period descending
        available_monthly_data.sort(key=lambda x: x['period'], reverse=True)
        
        total_records = await db.sales_records.count_documents({"upload_source": {"$ne": "forecast"}})
        
        return {
            "current_data_status": {
                "available_monthly_summaries": len(monthly_summaries),
                "available_yearly_summaries": len(yearly_summaries),
                "total_raw_records": total_records,
                "available_periods": available_monthly_data[:12],  # Last 12 periods
                "all_periods": available_monthly_data
            },
            "required_for_basic_forecast": {
                "minimum_periods": 2,
                "recommended_periods": 3,
                "description": "Need at least 2-3 months of summarized data for reliable trend analysis"
            },
            "required_for_seasonal_forecast": {
                "minimum_periods": 12,
                "recommended_periods": 24,
                "description": "Need 12-24 months of monthly data for seasonal pattern recognition"
            },
            "data_upload_instructions": {
                "format": "Excel files with same column structure as daily uploads",
                "description": "You can upload your own historical monthly summary files to override auto-generated summaries",
                "required_columns": ["GP_Index_No", "Item_Name", "Net_Qty", "R_Amt", "Profit", "Closing_Stock"]
            },
            "forecast_accuracy_levels": {
                "basic_trend": {
                    "data_needed": "2-3 months summarized",
                    "accuracy": "70-75%",
                    "best_for": "Short-term planning"
                },
                "statistical_seasonal": {
                    "data_needed": "6-12 months summarized",
                    "accuracy": "80-85%",
                    "best_for": "Medium-term planning with seasonal adjustments"
                }
            },
            "allow_user_override": True,
            "message": "You can upload your own historical data files to override or supplement the auto-generated summaries."
        }
        
    except Exception as e:
        logger.exception(f"Error getting forecast requirements: {str(e)}")
        raise e


async def upload_forecast_history_logic(
    file_content: bytes,
    filename: str,
    period: str,
    override_existing: bool = False
) -> Dict[str, Any]:
    """Process and save user-uploaded historical summary data for forecasting."""
    from datetime import datetime, timezone
    from services.excel_processor import process_excel_data
    
    # Determine summary type based on period format
    if len(period) == 4:  # YYYY
        summary_type = "yearly"
        year = int(period)
        month = None
        display_name = f"Year {year}"
    elif len(period) == 7:  # YYYY-MM
        summary_type = "monthly"
        year, month_str = period.split('-')
        year, month = int(year), int(month_str)
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        display_name = f"{month_names[month - 1]} {year}"
    else:
        raise ValueError("Period must be in format 'YYYY-MM' or 'YYYY'")
    
    # Check if summary already exists
    existing = await db.monthly_summaries.find_one({
        "period": period,
        "summary_type": summary_type
    })
    
    if existing and not override_existing:
        raise ValueError(f"Summary for {period} already exists. Set override_existing=true to replace it.")
    
    # Process the Excel file
    period_info = {"period": period, "start_month": month, "end_month": month, "year": year}
    records, net_amt, w_amt = process_excel_data(file_content, filename, period_info)
    
    if not records:
        raise ValueError("No valid data found in the uploaded file")
    
    # Calculate totals
    total_revenue = sum(r.get('r_amt', 0) or 0 for r in records)
    total_profit = sum(r.get('profit', 0) or 0 for r in records)
    total_qty = sum(r.get('net_qty', 0) or 0 for r in records)
    
    # Format items data
    items_data = []
    for record in records:
        items_data.append({
            "pluno": record.get('pluno'),
            "item_name": record.get('item_name'),
            "product_group": record.get('product_group'),
            "net_qty": record.get('net_qty', 0),
            "r_amt": record.get('r_amt', 0),
            "w_amt": record.get('w_amt', 0),
            "profit": record.get('profit', 0),
            "closing_stock": record.get('closing_stock', 0),
            "rate": record.get('rate', 0)
        })
    
    # Create or update summary document
    summary_doc = {
        "period": period,
        "summary_type": summary_type,
        "year": year,
        "month": month,
        "display_name": display_name,
        "created_at": datetime.now(timezone.utc),
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "total_qty_sold": total_qty,
        "item_count": len(items_data),
        "items": items_data,
        "source": "user_uploaded",
        "original_filename": filename
    }
    
    if existing:
        await db.monthly_summaries.replace_one({"_id": existing["_id"]}, summary_doc)
        action = "replaced"
    else:
        await db.monthly_summaries.insert_one(summary_doc)
        action = "created"
    
    return {
        "status": "success",
        "action": action,
        "message": f"Successfully {action} {summary_type} summary for {period}",
        "summary": {
            "period": period,
            "display_name": display_name,
            "item_count": len(items_data),
            "total_revenue": total_revenue,
            "total_profit": total_profit
        }
    }


async def ai_forecast() -> Dict[str, Any]:
    """AI-powered forecasting (placeholder for LLM integration)."""
    return {
        "forecasts": [],
        "message": "AI forecasting requires additional setup. Use trend or statistical methods.",
        "requirements": [
            "LLM API integration needed",
            "Advanced feature engineering required",
            "External market data integration",
        ],
    }
