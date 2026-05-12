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
