"""
Dashboard service — aggregation pipelines for the main dashboard.
Extracted from server.py L4282-4552.

Handles:
- Total revenue, profit, items sold
- ABC-based C-category stock valuation
- Group distribution
- Yearly averages
"""
from typing import Optional, Dict, Any
from datetime import datetime

from database import db
from config import logger


async def get_dashboard_summary(period: Optional[str] = None) -> Dict[str, Any]:
    """Get overall dashboard summary statistics with averages."""

    # Base filter — exclude forecast data
    analytics_filter: Dict[str, Any] = {"upload_source": {"$ne": "forecast"}}

    if period and period != "all":
        if "Current Year" in period:
            year = period.split(" ")[0]
            analytics_filter["data_period"] = {
                "$regex": f"({year}|{year[2:]})",
                "$options": "i",
            }
        else:
            analytics_filter["data_period"] = period

    # Total records
    total_records = await db.sales_records.count_documents(analytics_filter)

    # Distinct years for average calculations
    distinct_periods = await db.sales_records.distinct("data_period", analytics_filter)
    years = set()
    for dp in distinct_periods:
        if dp:
            year_str = str(dp).split('-')[0]
            try:
                years.add(int(year_str))
            except (ValueError, TypeError):
                pass

    num_years = len(years) if years else 1
    start_year = min(years) if years else datetime.now().year

    # Earliest month
    earliest_rec = await db.sales_records.find(
        analytics_filter
    ).sort("data_period", 1).limit(1).to_list(1)

    start_month = "Jan"
    if earliest_rec:
        ep = earliest_rec[0].get("data_period", "")
        if ep and '-' in str(ep):
            try:
                month_num = int(str(ep).split('-')[1])
                month_names = [
                    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                ]
                start_month = month_names[month_num - 1] if 1 <= month_num <= 12 else "Jan"
            except (ValueError, IndexError):
                pass

    # Revenue pipeline
    revenue_match = [
        {"upload_source": {"$ne": "forecast"}},
        {"r_amt": {"$ne": None, "$exists": True, "$gt": 0}},
        {"profit": {"$ne": None, "$exists": True}},
        {"net_qty": {"$ne": None, "$exists": True}},
    ]

    if period and period != "all":
        if "Current Year" in period:
            year = period.split(" ")[0]
            revenue_match.append({
                "data_period": {"$regex": f"({year}|{year[2:]})", "$options": "i"}
            })
        else:
            revenue_match.append({"data_period": period})

    revenue_pipeline = [
        {"$match": {"$and": revenue_match}},
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$r_amt"},
                "total_profit": {"$sum": "$profit"},
                "total_items_sold": {"$sum": "$net_qty"},
            }
        },
    ]

    revenue_result = await db.sales_records.aggregate(revenue_pipeline).to_list(1)
    revenue_data = revenue_result[0] if revenue_result else {
        "total_revenue": 0, "total_profit": 0, "total_items_sold": 0,
    }

    total_revenue = revenue_data.get("total_revenue", 0) or 0
    total_profit = revenue_data.get("total_profit", 0) or 0

    avg_yearly_revenue = total_revenue / num_years
    avg_yearly_profit = total_profit / num_years
    profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # Current stock value
    latest_fin = await db.financial_data.find_one(
        {"current_stock_value": {"$ne": None, "$exists": True}},
        sort=[("date", -1)],
    )
    current_stock_value = (latest_fin.get("current_stock_value", 0) or 0) if latest_fin else 0
    avg_yearly_stock_value = current_stock_value / num_years

    # C-category stock value via ABC classification
    abc_match = [
        {"upload_source": {"$ne": "forecast"}},
        {"r_amt": {"$ne": None, "$exists": True}},
    ]
    if period and period != "all":
        if "Current Year" in period:
            year = period.split(" ")[0]
            abc_match.append({"data_period": {"$regex": f"({year}|{year[2:]})", "$options": "i"}})
        else:
            abc_match.append({"data_period": period})

    abc_items = await db.sales_records.aggregate([
        {"$match": {"$and": abc_match}},
        {"$group": {"_id": "$pluno", "item_name": {"$first": "$item_name"}, "total_revenue": {"$sum": "$r_amt"}}},
        {"$sort": {"total_revenue": -1}},
    ]).to_list(None)

    total_abc_rev = sum(i["total_revenue"] for i in abc_items)
    cumulative = 0
    c_plu_codes = []
    for item in abc_items:
        cumulative += item["total_revenue"]
        if total_abc_rev > 0 and (cumulative / total_abc_rev * 100) > 95:
            c_plu_codes.append(item["_id"])

    c_stock_match = [
        {"upload_source": {"$ne": "forecast"}},
        {"pluno": {"$in": c_plu_codes}},
        {"closing_stock": {"$ne": None, "$exists": True, "$gt": 0}},
        {"w_rate": {"$ne": None, "$exists": True}},
    ]
    if period and period != "all":
        if "Current Year" in period:
            year = period.split(" ")[0]
            c_stock_match.append({"data_period": {"$regex": f"({year}|{year[2:]})", "$options": "i"}})
        else:
            c_stock_match.append({"data_period": period})

    c_stock_result = await db.sales_records.aggregate([
        {"$match": {"$and": c_stock_match}},
        {"$sort": {"data_period": -1}},
        {"$group": {"_id": "$pluno", "latest_closing_stock": {"$first": "$closing_stock"}, "latest_w_rate": {"$first": "$w_rate"}}},
        {"$addFields": {"stock_value": {"$multiply": [{"$ifNull": ["$latest_closing_stock", 0]}, {"$ifNull": ["$latest_w_rate", 0]}]}}},
        {"$group": {"_id": None, "total_c_stock_value": {"$sum": "$stock_value"}}},
    ]).to_list(1)

    c_category_stock_value = c_stock_result[0].get("total_c_stock_value", 0) if c_stock_result else 0
    avg_yearly_c_stock_value = c_category_stock_value / num_years

    # Group distribution
    group_distribution = await db.sales_records.aggregate([
        {"$group": {"_id": "$product_group", "count": {"$sum": 1}}},
    ]).to_list(None)

    return {
        "total_records": total_records,
        "total_revenue": total_revenue,
        "avg_yearly_revenue": avg_yearly_revenue,
        "total_profit": total_profit,
        "avg_yearly_profit": avg_yearly_profit,
        "profit_margin": profit_margin,
        "profit_percentage": profit_margin,
        "total_items_sold": revenue_data.get("total_items_sold", 0) or 0,
        "current_stock_value": current_stock_value,
        "avg_yearly_stock_value": avg_yearly_stock_value,
        "c_category_stock_value": c_category_stock_value,
        "avg_yearly_c_stock_value": avg_yearly_c_stock_value,
        "num_years": num_years,
        "start_year": start_year,
        "start_month": start_month,
        "data_from": f"{start_month} {start_year}",
        "group_distribution": group_distribution,
    }
