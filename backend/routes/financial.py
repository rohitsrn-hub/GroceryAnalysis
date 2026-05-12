"""
Financial routes — CRUD endpoints for financial health data.
Extracted from server.py L5085-5460.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime

from config import logger
from models.financial import FinancialData
from services.financial_service import (
    create_financial_record,
    get_financial_data_by_date,
    get_financial_data_range,
    update_financial_record,
    delete_financial_record,
    get_previous_financial_data,
    get_previous_bank_amount,
)
from middleware.auth import require_api_key

router = APIRouter(prefix="/api", tags=["financial"])


@router.post("/financial-data")
async def create_financial_data(data: FinancialData):
    """Create or update financial data for a date."""
    try:
        result = await create_financial_record(data)
        return result
    except Exception as e:
        logger.exception("Error saving financial data")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financial-data/{date}")
async def get_financial_data(date: str):
    """Get financial data for a specific date (YYYY-MM-DD)."""
    record = await get_financial_data_by_date(date)
    if record:
        return record
    raise HTTPException(status_code=404, detail=f"No data found for {date}")


@router.get("/financial-data-range")
async def get_financial_range(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get financial data for a date range."""
    try:
        records = await get_financial_data_range(start_date, end_date, limit)
        return {"records": records, "count": len(records)}
    except Exception as e:
        logger.exception("Error fetching financial data range")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/financial-data/{record_id}")
async def update_financial_data(record_id: str, data: dict):
    """Update an existing financial record."""
    try:
        result = await update_financial_record(record_id, data)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating financial data")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/financial-data/{record_id}", dependencies=[Depends(require_api_key)])
async def delete_financial_data(record_id: str):
    """Delete a financial record. Requires API key."""
    try:
        result = await delete_financial_record(record_id)
        if result["status"] == "not_found":
            raise HTTPException(status_code=404, detail=result["message"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting financial data")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/previous-financial-data")
async def previous_financial_data(
    date: str = Query(..., description="Target date (YYYY-MM-DD)")
):
    """Get the most recent financial data before a given date."""
    try:
        result = await get_previous_financial_data(date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error fetching previous financial data")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/previous-bank-amount")
async def previous_bank_amount(
    date: str = Query(..., description="Target date (YYYY-MM-DD)")
):
    """Get previous bank amount for a specific date."""
    try:
        result = await get_previous_bank_amount(date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error fetching previous bank amount")
        raise HTTPException(status_code=500, detail=str(e))
