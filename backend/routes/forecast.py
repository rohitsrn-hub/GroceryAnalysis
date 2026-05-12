"""
Forecast routes — demand forecasting endpoints.
Extracted from server.py L3387-4100.
"""
from fastapi import APIRouter, HTTPException

from config import logger
from models.forecast import ForecastRequest
from services.forecast_service import (
    simple_trend_forecast,
    statistical_forecast,
    ai_forecast,
)

router = APIRouter(prefix="/api", tags=["forecast"])


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
        raise HTTPException(
            status_code=500,
            detail=f"Error in demand forecasting: {str(e)}",
        )
