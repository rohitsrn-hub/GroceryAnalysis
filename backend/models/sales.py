"""
Sales-related Pydantic models.
Extracted from server.py L254-331.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SalesRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    s_no: Optional[int] = None
    gp_index_no: Optional[str] = None
    pluno: Optional[str] = None
    item_name: Optional[str] = None
    upload_source: str = "analytics"  # "analytics" or "forecast" - forecast data excluded from analytics
    w_rate: Optional[float] = None  # Wholesale Rate
    r_rate: Optional[float] = None  # Retail Rate
    qty: Optional[int] = None  # Quantity Sold
    refund_qty: Optional[int] = None
    net_qty: Optional[int] = None
    r_amt: Optional[float] = None  # Retail Amount
    w_amt: Optional[float] = None  # Wholesale Amount
    profit: Optional[float] = None
    o_b: Optional[float] = None  # Opening Balance
    closing_stock: Optional[float] = None
    net_tax: Optional[float] = None
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    upload_batch_id: Optional[str] = None  # Track which upload this came from
    data_period: Optional[str] = None  # e.g., "2024", "2024-01"
    product_group: Optional[str] = None  # Group I, II, III, IV, VI


class AnalyticsRequest(BaseModel):
    period_type: str = "yearly"  # monthly, quarterly, yearly
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    group_filter: Optional[List[str]] = None


class FastestSellingResponse(BaseModel):
    item_code: str
    item_name: str
    total_sold: int
    avg_monthly_sales: float
    group: str
    seasonal_pattern: Dict[str, float]


class InventoryAnalysisResponse(BaseModel):
    high_cost_poor_performance: List[Dict[str, Any]]
    dead_inventory: List[Dict[str, Any]]
    slow_moving: List[Dict[str, Any]]


class GroupAnalysisResponse(BaseModel):
    group: str
    total_revenue: float
    total_profit: float
    item_count: int
    top_performers: List[Dict[str, Any]]
    profit_margin: float


class UploadHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period_covered: Optional[str] = None  # "2024-08" or "2024"
    data_type: Optional[str] = None  # "monthly" or "yearly"
    upload_type: str = "historical"  # "daily" or "historical"
    data_date: Optional[datetime] = None  # The actual date this data represents
    records_count: int = 0
    status: str  # "success", "failed", "partial"
    error_message: Optional[str] = None
    uploaded_by: str = "system"  # Can be extended for multi-user
    file_size_kb: Optional[float] = None
    processing_time_seconds: Optional[float] = None
    net_amt: Optional[float] = None  # R_Amt from Report Total row for daily uploads
    w_amt: Optional[float] = None  # W_Amt from Report Total row for daily uploads
