"""
Summary & Data Summaries routes.
Extracted from server.py L3493-3592, L3713-3860.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from config import logger
from services.summary_service import (
    create_monthly_summary,
    create_yearly_summary,
    list_summaries,
    get_summary_details,
    delete_summary,
)
from services.period_service import format_period_display_name
from config import SUMMARY_ITEMS_DISPLAY_LIMIT

router = APIRouter(prefix="/api", tags=["summaries"])


class SummaryGenerationRequest(BaseModel):
    period: str  # "YYYY-MM" for monthly, "YYYY" for yearly


@router.post("/generate-monthly-summary")
async def generate_monthly_summary(year: int, month: int):
    """Generate a monthly summary for a specific month."""
    try:
        result = await create_monthly_summary(year, month)
        if result:
            return {
                "status": "success",
                "message": f"Monthly summary created for {year}-{month:02d}",
                "summary": {
                    "period": result["period"],
                    "item_count": result["item_count"],
                    "total_revenue": result["total_revenue"],
                }
            }
        raise HTTPException(
            status_code=400,
            detail=f"No data found for {year}-{month:02d}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating monthly summary")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-yearly-summary")
async def generate_yearly_summary(year: int):
    """Generate a yearly summary for a specific year."""
    try:
        result = await create_yearly_summary(year)
        if result:
            return {
                "status": "success",
                "message": f"Yearly summary created for {year}",
                "summary": {
                    "period": result["period"],
                    "item_count": result["item_count"],
                    "total_revenue": result["total_revenue"],
                }
            }
        raise HTTPException(
            status_code=400,
            detail=f"No data found for {year}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating yearly summary")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly-summaries")
async def get_monthly_summaries():
    """List all available monthly/yearly summaries."""
    try:
        return await list_summaries()
    except Exception as e:
        logger.exception("Error fetching summaries")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/monthly-summaries/{period}")
async def delete_monthly_summary(period: str):
    """Delete a summary for a specific period."""
    try:
        result = await delete_summary(period)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting summary")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly-summary-details/{period}")
async def get_monthly_summary_details(period: str):
    """Get detailed summary for a specific period."""
    try:
        summary = await get_summary_details(period)
        if summary:
            # Limit items for API response
            if "items" in summary:
                summary["items"] = summary["items"][:SUMMARY_ITEMS_DISPLAY_LIMIT]
            return summary
        raise HTTPException(
            status_code=404,
            detail=f"No summary found for {period}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching summary details")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-summary-generation")
async def trigger_summary_generation(request: SummaryGenerationRequest):
    """Trigger summary generation for a specific period."""
    try:
        period = request.period

        if len(period) == 4:
            # Yearly
            year = int(period)
            result = await create_yearly_summary(year)
        elif len(period) == 7:
            # Monthly (YYYY-MM)
            year, month = period.split("-")
            result = await create_monthly_summary(int(year), int(month))
        else:
            raise HTTPException(
                status_code=400,
                detail="Period must be 'YYYY' or 'YYYY-MM'"
            )

        if result:
            return {
                "status": "success",
                "message": f"Summary generated for {period}",
                "summary": {
                    "period": result["period"],
                    "item_count": result["item_count"],
                    "total_revenue": result["total_revenue"],
                }
            }

        raise HTTPException(
            status_code=400,
            detail=f"No data available to generate summary for {period}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error triggering summary generation")
        raise HTTPException(status_code=500, detail=str(e))
