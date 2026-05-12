"""
Analytics routes — business intelligence endpoints.
Extracted from server.py L1807-2275.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from config import logger
from services.analytics_service import (
    get_fastest_selling_items,
    get_abc_analysis,
    get_capital_blocking_analysis,
    get_inventory_analysis,
    get_group_analysis,
)

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/fastest-selling-items")
async def fastest_selling_items(
    limit: int = Query(10, ge=1, le=50),
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
):
    """Get fastest selling items with seasonal patterns."""
    try:
        return await get_fastest_selling_items(limit, group, period)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching fastest selling items: {str(e)}",
        )


@router.get("/abc-analysis")
async def abc_analysis(
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
):
    """Perform ABC analysis — 80/20 inventory classification."""
    try:
        return await get_abc_analysis(group, period)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in ABC analysis: {str(e)}",
        )


@router.get("/capital-blocking-analysis")
async def capital_blocking_analysis(
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
):
    """Identify slow-moving items with high inventory capital blocking."""
    try:
        return await get_capital_blocking_analysis(group, period)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in capital blocking analysis: {str(e)}",
        )


@router.get("/inventory-analysis")
async def inventory_analysis(period: Optional[str] = Query(None)):
    """Analyze inventory for dead stock and slow movers."""
    try:
        return await get_inventory_analysis(period)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in inventory analysis: {str(e)}",
        )


@router.get("/group-analysis")
async def group_analysis(period: Optional[str] = Query(None)):
    """Analyze performance by product groups."""
    try:
        return await get_group_analysis(period)
    except Exception as e:
        logger.exception("Error in group analysis")
        raise HTTPException(
            status_code=500,
            detail=f"Error in group analysis: {str(e)}",
        )
