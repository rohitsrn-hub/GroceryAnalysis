"""
Forecast routes — demand forecasting endpoints.
Extracted from server.py L3387-4100.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional

from config import logger
from models.forecast import ForecastRequest
from services.forecast_service import (
    simple_trend_forecast,
    statistical_forecast,
    ai_forecast,
    get_forecast_requirements,
    upload_forecast_history_logic,
)
from utils.validators import validate_forecast_date

router = APIRouter(prefix="/api", tags=["forecast"])


@router.get("/forecast-requirements")
async def get_requirements():
    """Get data requirements and available data for demand forecasting."""
    try:
        return await get_forecast_requirements()
    except Exception as e:
        logger.exception("Error getting forecast requirements")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-forecast-history")
async def upload_forecast_history(
    file: UploadFile = File(...),
    period: str = Form(...),  # Format: "YYYY-MM" or "YYYY"
    override_existing: bool = Form(False)
):
    """Upload user's own historical data for forecasting."""
    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only Excel files are supported")
        
        contents = await file.read()
        result = await upload_forecast_history_logic(contents, file.filename, period, override_existing)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Error uploading forecast history")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast-demand")
async def forecast_demand(request: ForecastRequest):
    """Forecast demand using trend, statistical, or AI methods."""
    try:
        if request.method == "trend":
            return await simple_trend_forecast(request.forecast_months)
        elif request.method == "statistical":
            return await statistical_forecast(request.forecast_months)
        elif request.method == "ai":
            return await ai_forecast()
        else:
            raise HTTPException(status_code=400, detail="Invalid forecast method")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in demand forecasting")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/validate-forecast-date")
async def validate_date(year: int, month: int):
    """Validate that forecast date is not in the past."""
    result = validate_forecast_date(year, month)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"valid": True, "message": f"Forecast for {month}/{year} is valid"}
