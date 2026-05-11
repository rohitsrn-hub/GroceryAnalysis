"""
Forecast-related Pydantic models.
Extracted from server.py L283-292.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ForecastRequest(BaseModel):
    method: str  # "trend", "statistical", "ai"
    item_codes: Optional[List[str]] = None
    forecast_months: int = 4
    additional_data: Optional[Dict[str, Any]] = None


class ForecastDataRequirement(BaseModel):
    last_3_months_data: Optional[Dict[str, Any]] = None
    yearly_data_for_month: Optional[Dict[str, Any]] = None
    seasonal_data: Optional[List[Dict[str, Any]]] = None
