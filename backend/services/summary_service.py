"""
Summary service — monthly and yearly summary generation.
Extracted from server.py L681-937, L3493-3592, L3713-3860.

Handles:
- Daily-to-monthly consolidation
- Monthly summary creation (item-wise aggregation)
- Yearly summary creation
- Summary CRUD operations
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from database import db
from config import logger
from utils.constants import MONTH_NAMES_FULL


async def consolidate_daily_to_monthly(current_upload_date: str):
    """Consolidate previous month's daily uploads into a monthly summary.

    When a new month starts (first upload of the new month), this function:
    1. Aggregates all daily data from the previous month into item-wise summary
    2. Creates a monthly summary record in monthly_summaries collection
    3. If it's January, also creates yearly summary for the previous year
    """
    try:
        current_date = datetime.strptime(current_upload_date, "%Y-%m-%d")

        # Calculate previous month
        if current_date.month == 1:
            prev_month = 12
            prev_year = current_date.year - 1
            is_new_year = True
        else:
            prev_month = current_date.month - 1
            prev_year = current_date.year
            is_new_year = False

        prev_month_period = f"{prev_year}-{prev_month:02d}"

        # Check if monthly summary already exists for previous month
        existing_summary = await db.monthly_summaries.find_one({
            "period": prev_month_period,
            "summary_type": "monthly"
        })

        if not existing_summary:
            await create_monthly_summary(prev_year, prev_month)

        # If new year, also create yearly summary for previous year
        if is_new_year:
            existing_yearly = await db.monthly_summaries.find_one({
                "period": str(prev_year),
                "summary_type": "yearly"
            })
            if not existing_yearly:
                await create_yearly_summary(prev_year)

        # Also update data_period for daily records
        result = await db.sales_records.update_many(
            {
                "upload_source": {"$in": ["daily", "analytics"]},
                "data_period": {"$regex": f"^{prev_year}-{prev_month:02d}"}
            },
            {
                "$set": {"data_period": prev_month_period}
            }
        )

        if result.modified_count > 0:
            logger.info(
                f"Consolidated {result.modified_count} daily records "
                f"to period {prev_month_period}"
            )

    except Exception as e:
        logger.error(f"Error consolidating daily to monthly: {str(e)}")
        # Don't fail the upload if consolidation fails


async def create_monthly_summary(year: int, month: int) -> Optional[Dict]:
    """Create an item-wise monthly summary from daily upload data.

    Aggregates all daily sales records for the given month into
    a summary with totals per item.
    Only uses data_period field to determine which records belong to a month.
    """
    try:
        period = f"{year}-{month:02d}"

        pipeline = [
            {
                "$match": {
                    "upload_source": {"$ne": "forecast"},
                    "data_period": {"$regex": f"^{year}-{month:02d}"}
                }
            },
            {
                "$group": {
                    "_id": {
                        "pluno": "$pluno",
                        "item_name": "$item_name",
                        "product_group": "$product_group"
                    },
                    "total_net_qty": {"$sum": "$net_qty"},
                    "total_r_amt": {"$sum": "$r_amt"},
                    "total_w_amt": {"$sum": "$w_amt"},
                    "total_profit": {"$sum": "$profit"},
                    "avg_closing_stock": {"$avg": "$closing_stock"},
                    "avg_rate": {"$avg": "$rate"},
                    "record_count": {"$sum": 1}
                }
            },
            {"$sort": {"total_r_amt": -1}}
        ]

        item_summaries = await db.sales_records.aggregate(pipeline).to_list(None)

        if not item_summaries:
            logger.info(f"No data found to create monthly summary for {period}")
            return None

        total_revenue = sum(item.get('total_r_amt', 0) or 0 for item in item_summaries)
        total_profit = sum(item.get('total_profit', 0) or 0 for item in item_summaries)
        total_qty = sum(item.get('total_net_qty', 0) or 0 for item in item_summaries)

        items_data = _format_summary_items(item_summaries)

        summary_doc = {
            "period": period,
            "summary_type": "monthly",
            "year": year,
            "month": month,
            "month_name": MONTH_NAMES_FULL[month - 1],
            "display_name": f"{MONTH_NAMES_FULL[month - 1]} {year}",
            "created_at": datetime.now(timezone.utc),
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "total_qty_sold": total_qty,
            "item_count": len(items_data),
            "items": items_data,
            "source": "auto_generated"
        }

        await db.monthly_summaries.insert_one(summary_doc)
        logger.info(
            f"Created monthly summary for {period}: "
            f"{len(items_data)} items, Revenue: {total_revenue:.2f}"
        )
        return summary_doc

    except Exception as e:
        logger.error(f"Error creating monthly summary: {str(e)}")
        return None


async def create_yearly_summary(year: int) -> Optional[Dict]:
    """Create an item-wise yearly summary from all data for the year.

    Handles multiple data_period formats:
    - 'YYYY' (e.g., '2024')
    - 'YYYY-MM' (e.g., '2025-11')
    - 'YYYY-MM-MM' (e.g., '2025-01-09' for Jan-Sep range)
    """
    try:
        period = str(year)

        pipeline = [
            {
                "$match": {
                    "upload_source": {"$ne": "forecast"},
                    "$or": [
                        {"data_period": period},
                        {"data_period": {"$regex": f"^{year}-"}}
                    ]
                }
            },
            {
                "$group": {
                    "_id": {
                        "pluno": "$pluno",
                        "item_name": "$item_name",
                        "product_group": "$product_group"
                    },
                    "total_net_qty": {"$sum": "$net_qty"},
                    "total_r_amt": {"$sum": "$r_amt"},
                    "total_w_amt": {"$sum": "$w_amt"},
                    "total_profit": {"$sum": "$profit"},
                    "avg_closing_stock": {"$avg": "$closing_stock"},
                    "avg_rate": {"$avg": "$rate"},
                    "record_count": {"$sum": 1}
                }
            },
            {"$sort": {"total_r_amt": -1}}
        ]

        item_summaries = await db.sales_records.aggregate(pipeline).to_list(None)

        if not item_summaries:
            logger.info(f"No data found to create yearly summary for {year}")
            return None

        total_revenue = sum(item.get('total_r_amt', 0) or 0 for item in item_summaries)
        total_profit = sum(item.get('total_profit', 0) or 0 for item in item_summaries)
        total_qty = sum(item.get('total_net_qty', 0) or 0 for item in item_summaries)

        items_data = _format_summary_items(item_summaries)

        summary_doc = {
            "period": period,
            "summary_type": "yearly",
            "year": year,
            "display_name": f"Year {year}",
            "created_at": datetime.now(timezone.utc),
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "total_qty_sold": total_qty,
            "item_count": len(items_data),
            "items": items_data,
            "source": "auto_generated"
        }

        await db.monthly_summaries.insert_one(summary_doc)
        logger.info(
            f"Created yearly summary for {year}: "
            f"{len(items_data)} items, Revenue: {total_revenue:.2f}"
        )
        return summary_doc

    except Exception as e:
        logger.error(f"Error creating yearly summary: {str(e)}")
        return None


async def list_summaries() -> Dict[str, Any]:
    """List all available monthly/yearly summaries."""
    summaries = await db.monthly_summaries.find(
        {},
        {
            "_id": 0, "period": 1, "display_name": 1,
            "item_count": 1, "total_revenue": 1,
            "source": 1, "summary_type": 1, "created_at": 1
        }
    ).sort("period", -1).to_list(100)

    return {"summaries": summaries, "count": len(summaries)}


async def get_summary_details(period: str) -> Optional[Dict]:
    """Get detailed summary for a specific period."""
    summary = await db.monthly_summaries.find_one(
        {"period": period},
        {"_id": 0}
    )
    return summary


async def delete_summary(period: str) -> Dict[str, Any]:
    """Delete a summary for a specific period."""
    result = await db.monthly_summaries.delete_one({"period": period})
    if result.deleted_count > 0:
        return {"status": "success", "message": f"Summary for {period} deleted"}
    return {"status": "not_found", "message": f"No summary found for {period}"}


def _format_summary_items(item_summaries: List[Dict]) -> List[Dict]:
    """Format aggregated items into summary item format.

    Eliminates duplicated formatting logic between monthly and yearly summaries.
    """
    items_data = []
    for item in item_summaries:
        items_data.append({
            "pluno": item['_id'].get('pluno'),
            "item_name": item['_id'].get('item_name'),
            "product_group": item['_id'].get('product_group'),
            "net_qty": item.get('total_net_qty', 0),
            "r_amt": item.get('total_r_amt', 0),
            "w_amt": item.get('total_w_amt', 0),
            "profit": item.get('total_profit', 0),
            "closing_stock": item.get('avg_closing_stock', 0),
            "rate": item.get('avg_rate', 0)
        })
    return items_data
