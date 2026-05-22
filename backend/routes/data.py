"""
Data routes — dashboard, periods, database-view, daily trends.
Extracted from server.py L4114-4280, L4282-4879.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from config import logger
from database import db
from services.dashboard_service import get_dashboard_summary
from services.period_service import format_period_display_name

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/dashboard-summary")
async def dashboard_summary(period: Optional[str] = Query(None)):
    """Get overall dashboard summary statistics with averages."""
    try:
        return await get_dashboard_summary(period)
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard summary: {str(e)}")


@router.get("/available-periods")
async def get_available_periods():
    """Get list of all unique data periods available in the database."""
    try:
        periods = await db.sales_records.distinct(
            "data_period", {"upload_source": {"$ne": "forecast"}}
        )
        periods = [p for p in periods if p is not None]
        periods.sort(reverse=True)

        current_year = datetime.now().year
        has_current = any(
            str(current_year) in str(p) or str(current_year)[2:] in str(p)
            for p in periods
        )
        if has_current:
            periods.insert(0, f"{current_year} - Current Year")

        return periods
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting available periods: {str(e)}")


@router.get("/available-data-periods")
async def get_available_data_periods():
    """Get available data periods with formatted display names and upload info."""
    try:
        periods = await db.sales_records.distinct(
            "data_period",
            {"upload_source": {"$ne": "forecast"}, "data_period": {"$ne": None, "$exists": True}},
        )
        periods_sorted = sorted(periods, reverse=True)

        periods_detailed = []
        for p in periods_sorted:
            display = format_period_display_name(p)
            periods_detailed.append({"value": p, "label": display})

        # Upload info
        uploads = await db.upload_history.aggregate([
            {"$match": {"status": "success"}},
            {"$project": {
                "upload_id": "$id", "upload_type": 1, "data_date": 1,
                "period_covered": 1, "data_type": 1, "records_count": 1,
                "upload_date": 1, "filename": 1,
            }},
            {"$sort": {"upload_date": -1}},
        ]).to_list(None)

        daily_uploads = []
        historical_uploads = []
        for u in uploads:
            entry = {
                "upload_id": u.get('upload_id'),
                "records_count": u.get('records_count'),
                "upload_date": u.get('upload_date'),
                "filename": u.get('filename'),
            }
            if u.get('upload_type') == 'daily' and u.get('data_date'):
                entry["date"] = u['data_date']
                daily_uploads.append(entry)
            else:
                entry["period"] = u.get('period_covered')
                entry["data_type"] = u.get('data_type')
                historical_uploads.append(entry)

        return {
            "periods": [p["label"] for p in periods_detailed],
            "periods_detailed": periods_detailed,
            "daily_uploads": daily_uploads,
            "historical_uploads": historical_uploads,
            "total_daily": len(daily_uploads),
            "total_historical": len(historical_uploads),
            "total_periods": len(periods_detailed),
        }
    except Exception as e:
        logger.exception("Error fetching available data periods")
        raise HTTPException(status_code=500, detail=f"Error fetching data periods: {str(e)}")


@router.get("/daily-sales-trend")
async def get_daily_sales_trend(period: Optional[str] = Query(None)):
    """Get daily sales data for current quarter or specific period."""
    try:
        now = datetime.now()
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        quarter_start = datetime(now.year, quarter_start_month, 1)

        query_filter = {
            "upload_type": "daily",
            "status": "success",
            "data_date": {"$gte": quarter_start, "$lt": now + timedelta(days=1)},
        }

        if period and period != "all":
            if "Current Year" in period:
                year = int(period.split(" ")[0])
                query_filter["data_date"] = {
                    "$gte": datetime(year, 1, 1),
                    "$lt": datetime(year + 1, 1, 1),
                }
            elif len(period) == 7 and '-' in period:
                y, m = period.split('-')
                y, m = int(y), int(m)
                end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
                query_filter["data_date"] = {"$gte": datetime(y, m, 1), "$lt": end}
            elif len(period) == 4:
                y = int(period)
                query_filter["data_date"] = {
                    "$gte": datetime(y, 1, 1),
                    "$lt": datetime(y + 1, 1, 1),
                }

        daily_uploads = await db.upload_history.find(query_filter).sort("data_date", 1).to_list(None)

        monthly_data = {}
        for upload in daily_uploads:
            d = upload.get('data_date')
            if d:
                mk = d.strftime('%Y-%m')
                if mk not in monthly_data:
                    monthly_data[mk] = {"month_name": d.strftime('%B'), "month_key": mk, "data": []}
                monthly_data[mk]['data'].append({
                    "date": d.strftime('%Y-%m-%d'),
                    "sales": float(upload.get('net_amt', 0) or 0),
                    "day": d.day,
                })

        return {
            "quarter_start": quarter_start.strftime('%Y-%m-%d'),
            "current_date": now.strftime('%Y-%m-%d'),
            "months": [monthly_data[k] for k in sorted(monthly_data.keys())],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching daily sales trend: {str(e)}")


@router.get("/daily-sales-trend-by-period")
async def get_daily_sales_trend_by_period(
    period: str = Query(..., description="Period in YYYY-MM format"),
):
    """Get daily sales data for a specific monthly period."""
    try:
        if not period or len(period) != 7 or '-' not in period:
            raise HTTPException(status_code=400, detail="Period must be in YYYY-MM format")

        y, m = int(period.split('-')[0]), int(period.split('-')[1])
        start = datetime(y, m, 1)
        end = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)

        uploads = await db.upload_history.find({
            "upload_type": "daily", "status": "success",
            "data_date": {"$gte": start, "$lt": end},
        }).sort("data_date", 1).to_list(None)

        data = []
        total_sales = 0
        for u in uploads:
            d = u.get('data_date')
            if d:
                amt = float(u.get('net_amt', 0) or 0)
                total_sales += amt
                data.append({"date": d.strftime('%Y-%m-%d'), "day": d.day, "sales": amt})

        months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
        return {
            "period": period,
            "period_label": f"{months[m-1]} {y}",
            "data": data,
            "total_sales": total_sales,
            "avg_daily_sales": total_sales / len(data) if data else 0,
            "days_tracked": len(data),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/database-view")
async def get_database_view(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    group_filter: Optional[str] = Query(None),
    period_filter: Optional[str] = Query(None),
    gp_index_no: Optional[str] = Query(None),
    aggregated: bool = Query(False),
    sort_by: str = Query("upload_date"),
    sort_order: int = Query(-1),
):
    """Get paginated view of sales database with filters and aggregation."""
    try:
        fq: dict = {}
        if search:
            fq["item_name"] = {"$regex": search, "$options": "i"}
        if group_filter and group_filter != "all":
            fq["product_group"] = group_filter
        if period_filter:
            fq["data_period"] = {"$regex": period_filter, "$options": "i"}
        if gp_index_no:
            fq["gp_index_no"] = {"$regex": gp_index_no, "$options": "i"}

        if aggregated:
            valid_sorts = {
                "gp_index_no", "item_name", "product_group",
                "total_qty", "total_net_qty", "total_r_amt",
                "total_w_amt", "total_profit",
            }
            sb = sort_by if sort_by in valid_sorts else "total_r_amt"

            pipeline = [
                {"$match": fq},
                {"$sort": {"upload_date": 1}},
                {"$group": {
                    "_id": "$gp_index_no",
                    "gp_index_no": {"$first": "$gp_index_no"},
                    "item_name": {"$first": "$item_name"},
                    "product_group": {"$first": "$product_group"},
                    "total_qty": {"$sum": {"$ifNull": ["$qty", 0]}},
                    "total_net_qty": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                    "total_r_amt": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                    "total_w_amt": {"$sum": {"$ifNull": ["$w_amt", 0]}},
                    "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                    "avg_closing_stock": {"$avg": {"$ifNull": ["$closing_stock", 0]}},
                    "latest_w_rate": {"$last": "$w_rate"},
                    "latest_r_rate": {"$last": "$r_rate"},
                    "periods": {"$addToSet": "$data_period"},
                    "record_count": {"$sum": 1},
                }},
                {"$sort": {sb: sort_order}},
                {"$skip": skip},
                {"$limit": limit},
            ]
            count_result = await db.sales_records.aggregate([
                {"$match": fq}, {"$group": {"_id": "$gp_index_no"}}, {"$count": "total"},
            ]).to_list(1)
            total = count_result[0]["total"] if count_result else 0
            records = await db.sales_records.aggregate(pipeline).to_list(limit)
        else:
            total = await db.sales_records.count_documents(fq)
            records = await db.sales_records.find(fq, {"_id": 0}) \
                .sort(sort_by, sort_order).skip(skip).limit(limit).to_list(limit)

        # Periods and groups for filters
        raw_periods = await db.sales_records.aggregate([
            {"$match": {"upload_source": {"$ne": "forecast"}, "data_period": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$data_period"}},
            {"$sort": {"_id": -1}},
            {"$limit": 50},
        ]).to_list(50)

        periods_with_display = []
        for p in raw_periods:
            if p["_id"]:
                display = format_period_display_name(p["_id"])
                periods_with_display.append({"value": p["_id"], "label": display})

        groups = await db.sales_records.aggregate([
            {"$group": {"_id": "$product_group"}}, {"$sort": {"_id": 1}},
        ]).to_list(10)

        summary = {
            "total_records": total,
            "available_periods": [p["label"] for p in periods_with_display],
            "periods_detailed": periods_with_display,
            "available_groups": [g["_id"] for g in groups if g["_id"]],
            "date_range": {"earliest": None, "latest": None},
        }

        if total > 0:
            earliest = await db.sales_records.find_one(fq, sort=[("upload_date", 1)], projection={"upload_date": 1, "_id": 0})
            latest = await db.sales_records.find_one(fq, sort=[("upload_date", -1)], projection={"upload_date": 1, "_id": 0})
            if earliest and "upload_date" in earliest:
                summary["date_range"]["earliest"] = str(earliest["upload_date"])
            if latest and "upload_date" in latest:
                summary["date_range"]["latest"] = str(latest["upload_date"])

        return {"total": total, "limit": limit, "skip": skip, "records": records, "summary": summary}
    except Exception as e:
        logger.error(f"Error in database view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching database view: {str(e)}")


@router.post("/check-data-availability")
async def check_data_availability(periods: list[str]):
    """Check which periods have data available in the database.
    
    Handles both normalized (2025-09) and legacy formats (Sep 2025).
    """
    try:
        import re
        availability = {}
        
        for period in periods:
            # First try exact match
            count = await db.sales_records.count_documents({"data_period": period})
            found_period = period
            found_filename = None
            
            # If no exact match, try pattern matching for legacy formats
            if count == 0 and period:
                match = re.match(r'(\d{4})-(\d{2})', period)
                if match:
                    year = match.group(1)
                    month_int = int(match.group(2))
                    
                    month_names = {
                        1: ['jan', 'january'], 2: ['feb', 'february'], 3: ['mar', 'march'],
                        4: ['apr', 'april'], 5: ['may'], 6: ['jun', 'june'],
                        7: ['jul', 'july'], 8: ['aug', 'august'],
                        9: ['sep', 'sept', 'september'], 10: ['oct', 'october'],
                        11: ['nov', 'november'], 12: ['dec', 'december']
                    }
                    
                    target_month_names = month_names.get(month_int, [])
                    if target_month_names:
                        # Get all records for the year
                        cursor = db.sales_records.find({"data_period": {"$regex": year}})
                        matching_records_count = 0
                        async for record in cursor:
                            data_period = record.get("data_period", "").lower()
                            if any(mn in data_period for mn in target_month_names):
                                # Exclude multi-month
                                is_multi = False
                                for other_int in range(1, 13):
                                    if other_int != month_int:
                                        if any(omn in data_period for omn in month_names.get(other_int, [])):
                                            is_multi = True
                                            break
                                if not is_multi:
                                    matching_records_count += 1
                                    found_period = record.get("data_period")
                        count = matching_records_count
            
            if count > 0:
                upload_info = await db.upload_history.find_one(
                    {"period_covered": period, "status": "success"},
                    sort=[("upload_date", -1)]
                )
                
                availability[period] = {
                    "available": True,
                    "record_count": count,
                    "upload_date": upload_info.get("upload_date") if upload_info else None,
                    "filename": upload_info.get("filename") if upload_info else None,
                    "actual_period": found_period
                }
            else:
                availability[period] = {"available": False, "record_count": 0}
        
        return {"periods_checked": len(periods), "availability": availability}
    except Exception as e:
        logger.exception("Error checking data availability")
        raise HTTPException(status_code=500, detail=str(e))
