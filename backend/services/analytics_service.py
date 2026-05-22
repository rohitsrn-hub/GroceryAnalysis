"""
Analytics service — MongoDB aggregation pipelines for business intelligence.
Extracted from server.py L1807-2275.

Handles:
- Fastest selling items analysis
- ABC analysis (80/20 inventory classification)
- Capital blocking analysis (slow-moving high-inventory items)
- Inventory analysis (dead stock, slow movers)
- Group-wise performance analysis
"""
from typing import Optional, Dict, Any, List

from database import db
from config import logger
from utils.validators import build_period_filter


def _build_match_filter(
    group: Optional[str] = None,
    period: Optional[str] = None,
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build a standard match filter for analytics pipelines.

    Always excludes forecast data. Applies optional group and period filters.
    """
    match_filter: Dict[str, Any] = {"upload_source": {"$ne": "forecast"}}

    if group and group != "all":
        match_filter["product_group"] = group

    if period and period != "all":
        if "Current Year" in period:
            year = period.split(" ")[0]
            match_filter["data_period"] = {
                "$regex": f"({year}|{year[2:]})",
                "$options": "i",
            }
        else:
            match_filter["data_period"] = period

    if extra:
        match_filter.update(extra)

    return match_filter


# ─── Fastest Selling Items ───────────────────────────────────────────

async def get_fastest_selling_items(
    limit: int = 10,
    group: Optional[str] = None,
    period: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get fastest selling items with seasonal patterns."""
    match_filter = _build_match_filter(
        group, period,
        extra={"net_qty": {"$ne": None, "$exists": True}},
    )

    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "pluno": "$pluno",
                    "item_name": "$item_name",
                    "group": "$product_group",
                },
                "total_sold": {"$sum": "$net_qty"},
                "total_revenue": {"$sum": "$r_amt"},
                "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                "periods": {"$push": {"period": "$data_period", "qty": "$net_qty"}},
            }
        },
    ]

    results = await db.sales_records.aggregate(pipeline).to_list(None)

    # Sort in python to bypass MongoDB 32MB sort limit
    results.sort(key=lambda x: x.get("total_sold", 0), reverse=True)
    results = results[:limit]

    items = []
    for item in results:
        seasonal_pattern = {
            pd['period']: pd['qty'] for pd in item['periods']
        }
        items.append({
            "item_code": item['_id']['pluno'],
            "item_name": item['_id']['item_name'],
            "total_sold": item['total_sold'],
            "avg_monthly_sales": item['total_sold'] / max(len(item['periods']), 1),
            "group": item['_id']['group'],
            "seasonal_pattern": seasonal_pattern,
            "total_revenue": item.get('total_revenue', 0),
            "total_profit": item.get('total_profit', 0),
        })

    return items


# ─── ABC Analysis ────────────────────────────────────────────────────

async def get_abc_analysis(
    group: Optional[str] = None,
    period: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform ABC analysis — 80/20 rule for inventory classification."""
    match_filter = _build_match_filter(
        group, period,
        extra={"net_qty": {"$ne": None, "$exists": True, "$gt": 0}},
    )

    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "pluno": "$pluno",
                    "item_name": "$item_name",
                    "group": "$product_group",
                },
                "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                "total_qty_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                "avg_closing_stock": {"$avg": "$closing_stock"},
                "avg_cost": {"$avg": "$w_rate"},
            }
        },
        {"$match": {"total_revenue": {"$gt": 0}}},
    ]

    results = await db.sales_records.aggregate(pipeline).to_list(None)
    
    # Sort in python to bypass MongoDB 32MB limit
    results.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)

    if not results:
        return {"abc_categories": {"A": [], "B": [], "C": []}, "summary": {}}

    total_revenue = sum(item['total_revenue'] for item in results)
    cumulative = 0
    categories: Dict[str, List] = {"A": [], "B": [], "C": []}

    for item in results:
        cumulative += item['total_revenue']
        pct = (cumulative / total_revenue) * 100

        item_data = {
            "pluno": item['_id']['pluno'],
            "item_name": item['_id']['item_name'],
            "group": item['_id']['group'],
            "total_revenue": item['total_revenue'],
            "total_qty_sold": item['total_qty_sold'],
            "total_profit": item['total_profit'],
            "revenue_percentage": (item['total_revenue'] / total_revenue) * 100,
            "cumulative_percentage": pct,
            "avg_closing_stock": item.get('avg_closing_stock', 0) or 0,
            "capital_blocked": (item.get('avg_closing_stock', 0) or 0)
                             * (item.get('avg_cost', 0) or 0),
        }

        if pct <= 80:
            categories["A"].append(item_data)
        elif pct <= 95:
            categories["B"].append(item_data)
        else:
            categories["C"].append(item_data)

    total_items = len(results)
    summary = {
        "total_items": total_items,
        "total_revenue": total_revenue,
        "category_A": {
            "item_count": len(categories["A"]),
            "percentage_items": (len(categories["A"]) / total_items) * 100,
            "revenue": sum(i['total_revenue'] for i in categories["A"]),
            "revenue_percentage": 80 if categories["A"] else 0,
        },
        "category_B": {
            "item_count": len(categories["B"]),
            "percentage_items": (len(categories["B"]) / total_items) * 100,
            "revenue": sum(i['total_revenue'] for i in categories["B"]),
            "revenue_percentage": 15 if categories["B"] else 0,
        },
        "category_C": {
            "item_count": len(categories["C"]),
            "percentage_items": (len(categories["C"]) / total_items) * 100,
            "revenue": sum(i['total_revenue'] for i in categories["C"]),
            "revenue_percentage": 5 if categories["C"] else 0,
        },
    }

    return {"abc_categories": categories, "summary": summary}


# ─── Capital Blocking Analysis ───────────────────────────────────────

async def get_capital_blocking_analysis(
    group: Optional[str] = None,
    period: Optional[str] = None,
) -> Dict[str, Any]:
    """Identify slow-moving items with high inventory causing capital blocking."""
    match_filter = _build_match_filter(group, period)

    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {
                    "pluno": "$pluno",
                    "item_name": "$item_name",
                    "group": "$product_group",
                },
                "total_qty_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                "avg_closing_stock": {"$avg": {"$ifNull": ["$closing_stock", 0]}},
                "avg_wholesale_rate": {"$avg": {"$ifNull": ["$w_rate", 0]}},
                "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                "periods_count": {"$sum": 1},
            }
        },
        {
            "$addFields": {
                "avg_monthly_sales": {"$divide": ["$total_qty_sold", "$periods_count"]},
                "capital_blocked": {"$multiply": ["$avg_closing_stock", "$avg_wholesale_rate"]},
                "inventory_turnover": {
                    "$cond": {
                        "if": {"$gt": ["$avg_closing_stock", 0]},
                        "then": {"$divide": ["$total_qty_sold", "$avg_closing_stock"]},
                        "else": 0,
                    }
                },
            }
        },
        {
            "$addFields": {
                "days_to_sell": {
                    "$divide": [
                        {"$multiply": ["$avg_closing_stock", 30]},
                        {"$max": ["$avg_monthly_sales", 0.001]},
                    ]
                }
            }
        },
        {
            "$match": {
                "$and": [
                    {"avg_closing_stock": {"$gt": 10}},
                    {"capital_blocked": {"$gt": 1000}},
                    {"$or": [
                        {"inventory_turnover": {"$lt": 2}},
                        {"days_to_sell": {"$gt": 180}},
                    ]},
                ]
            }
        },
    ]

    results = await db.sales_records.aggregate(pipeline).to_list(None)
    
    # Sort in python to bypass MongoDB 32MB limit
    results.sort(key=lambda x: x.get("capital_blocked", 0), reverse=True)
    results = results[:50]

    # Assign risk levels
    risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    for item in results:
        cb = item['capital_blocked']
        dts = item['days_to_sell']
        if cb > 50000 and dts > 365:
            item['risk_level'] = "CRITICAL"
        elif cb > 10000 and dts > 180:
            item['risk_level'] = "HIGH"
        elif cb > 5000 and dts > 90:
            item['risk_level'] = "MEDIUM"
        else:
            item['risk_level'] = "LOW"

    results.sort(key=lambda x: (risk_order.get(x['risk_level'], 999), -x['capital_blocked']))

    return {
        "capital_blocking_items": results,
        "summary": {
            "total_items_analyzed": len(results),
            "total_capital_blocked": sum(i['capital_blocked'] for i in results),
            "critical_items": sum(1 for i in results if i['risk_level'] == 'CRITICAL'),
            "high_risk_items": sum(1 for i in results if i['risk_level'] == 'HIGH'),
        },
    }


# ─── Inventory Analysis ─────────────────────────────────────────────

async def get_inventory_analysis(
    period: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze inventory for dead stock and slow movers."""
    match_filter = _build_match_filter(period=period)

    # High cost + poor performance
    pipeline_high_cost = [
        {"$match": {**match_filter, "w_rate": {"$gt": 0}}},
        {
            "$group": {
                "_id": {"pluno": "$pluno", "item_name": "$item_name"},
                "avg_cost": {"$avg": "$w_rate"},
                "total_sold": {"$sum": "$net_qty"},
                "total_profit": {"$sum": "$profit"},
            }
        },
        {
            "$addFields": {
                "performance_ratio": {
                    "$cond": {
                        "if": {"$gt": ["$avg_cost", 0]},
                        "then": {"$divide": ["$total_sold", "$avg_cost"]},
                        "else": 0,
                    }
                }
            }
        },
    ]

    # Dead inventory
    pipeline_dead = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {"pluno": "$pluno", "item_name": "$item_name", "group": "$product_group"},
                "total_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                "avg_closing_stock": {"$avg": {"$ifNull": ["$closing_stock", 0]}},
                "avg_cost": {"$avg": {"$ifNull": ["$w_rate", 0]}},
                "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
            }
        },
        {
            "$match": {
                "$and": [
                    {"total_sold": {"$lte": 0}},
                    {"avg_closing_stock": {"$gt": 0}},
                    {"avg_cost": {"$gt": 0}},
                ]
            }
        },
        {"$addFields": {"capital_blocked": {"$multiply": ["$avg_closing_stock", "$avg_cost"]}}}
    ]

    # Slow moving
    pipeline_slow = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {"pluno": "$pluno", "item_name": "$item_name"},
                "total_sold": {"$sum": "$net_qty"},
                "avg_cost": {"$avg": "$w_rate"},
                "periods_count": {"$sum": 1},
            }
        },
        {"$addFields": {"avg_monthly_sales": {"$divide": ["$total_sold", "$periods_count"]}}},
        {"$match": {"avg_monthly_sales": {"$gt": 0, "$lt": 5}}}
    ]

    high_cost = await db.sales_records.aggregate(pipeline_high_cost).to_list(None)
    high_cost.sort(key=lambda x: (-x.get("avg_cost", 0), x.get("performance_ratio", 0)))
    high_cost = high_cost[:20]
    
    dead = await db.sales_records.aggregate(pipeline_dead).to_list(None)
    dead.sort(key=lambda x: x.get("capital_blocked", 0), reverse=True)
    dead = dead[:20]
    
    slow = await db.sales_records.aggregate(pipeline_slow).to_list(None)
    slow.sort(key=lambda x: x.get("avg_monthly_sales", 0))
    slow = slow[:20]

    return {
        "high_cost_poor_performance": high_cost,
        "dead_inventory": dead,
        "slow_moving": slow,
    }


# ─── Group Analysis ─────────────────────────────────────────────────

async def get_group_analysis(
    period: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Analyze performance by product groups."""
    match_filter = _build_match_filter(period=period)

    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": "$product_group",
                "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                "total_cost": {"$sum": {"$ifNull": ["$w_amt", 0]}},
                "item_count": {"$sum": 1},
                "items": {
                    "$push": {
                        "pluno": "$pluno",
                        "item_name": "$item_name",
                        "revenue": {"$ifNull": ["$r_amt", 0]},
                        "profit": {"$ifNull": ["$profit", 0]},
                        "qty": {"$ifNull": ["$net_qty", 0]},
                    }
                },
            }
        },
        {
            "$addFields": {
                "profit_margin": {
                    "$cond": {
                        "if": {"$gt": ["$total_revenue", 0]},
                        "then": {"$multiply": [{"$divide": ["$total_profit", "$total_revenue"]}, 100]},
                        "else": 0,
                    }
                }
            }
        },
        {"$match": {"_id": {"$ne": "Unknown"}}},
    ]

    results = await db.sales_records.aggregate(pipeline).to_list(None)
    
    # Sort in python
    results.sort(key=lambda x: x.get("total_revenue", 0), reverse=True)

    group_analysis = []
    for group_data in results:
        valid_items = [
            i for i in group_data['items']
            if isinstance(i.get('revenue'), (int, float))
            and isinstance(i.get('profit'), (int, float))
        ]
        top_performers = sorted(
            valid_items,
            key=lambda x: x.get('revenue', 0) or 0,
            reverse=True,
        )[:5]

        group_analysis.append({
            "group": group_data['_id'],
            "total_revenue": float(group_data.get('total_revenue', 0) or 0),
            "total_profit": float(group_data.get('total_profit', 0) or 0),
            "item_count": group_data['item_count'],
            "top_performers": top_performers,
            "profit_margin": float(group_data.get('profit_margin', 0) or 0),
        })

    return group_analysis
