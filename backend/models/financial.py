"""
Financial health Pydantic models.
Extracted from server.py L335-348.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class FinancialData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    )
    grocery_sales: float = 0.0
    liquor_sales: float = 0.0
    total_sales: float = 0.0
    previous_bank_amount: float = 0.0
    current_bank_amount: float = 0.0
    previous_stock_value: Optional[float] = None
    current_stock_value: Optional[float] = None
    notes: Optional[str] = None
    created_by: str = "system"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
