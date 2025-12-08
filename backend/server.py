from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query, Form, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
from io import BytesIO
import openpyxl
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import json
from collections import defaultdict
import io
from fastapi.responses import StreamingResponse, FileResponse
import tempfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Note: Grocery app uses URCloh1GrocerySales database
# Liquor app uses URCloh1LiquorSales database
# This provides complete data separation without collection prefixes

# Helper function for Indian Number System formatting
def format_indian_number(number, currency=False, use_rs_prefix=False):
    """Format number in Indian Number System (Lakhs, Crores)"""
    if number is None or number == 0:
        return "Rs 0" if use_rs_prefix else "₹0" if currency else "0"
    
    # Handle negative numbers
    is_negative = number < 0
    number = abs(number)
    
    # Convert to string with 2 decimal places
    num_str = f"{number:.2f}"
    
    # Split into integer and decimal parts
    parts = num_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"
    
    # Format in Indian style
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        # Last 3 digits
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        
        # Add commas every 2 digits from right to left
        groups = []
        while remaining:
            if len(remaining) > 2:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            else:
                groups.append(remaining)
                remaining = ""
        
        groups.reverse()
        formatted = ','.join(groups) + ',' + last_three
    
    # Add decimal part
    result = formatted + '.' + decimal_part
    
    # Add negative sign if needed
    if is_negative:
        result = '-' + result
    
    # Add currency symbol
    if currency:
        prefix = "Rs " if use_rs_prefix else "₹"
        result = prefix + result
    
    return result

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
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
    data_period: Optional[str] = None  # e.g., "2024", "Jan-2024"
    product_group: Optional[str] = None  # Group I, II, III, IV, VI

class AnalyticsRequest(BaseModel):
    period_type: str = "yearly"  # monthly, quarterly, yearly
    start_period: Optional[str] = None
    end_period: Optional[str] = None
    group_filter: Optional[List[str]] = None

class ForecastRequest(BaseModel):
    method: str  # "trend", "statistical", "ai"
    item_codes: Optional[List[str]] = None
    forecast_months: int = 4
    additional_data: Optional[Dict[str, Any]] = None

class ForecastDataRequirement(BaseModel):
    last_3_months_data: Optional[Dict[str, Any]] = None
    yearly_data_for_month: Optional[Dict[str, Any]] = None
    seasonal_data: Optional[List[Dict[str, Any]]] = None

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

# Phase 1: Upload History & Database View Models
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


# Phase 2: Financial Health Models
class FinancialData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
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


# Helper Functions
def prepare_for_mongo(data):
    """Convert problematic types for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if pd.isna(value) or value == 'nan':
                data[key] = None
            elif isinstance(value, (np.int64, np.int32)):
                data[key] = int(value)
            elif isinstance(value, (np.float64, np.float32)):
                data[key] = float(value)
    return data

def extract_group_from_pluno(pluno) -> str:
    """Extract group from product code"""
    if not pluno or pd.isna(pluno):
        return "Unknown"
    
    pluno_str = str(pluno).strip()
    
    # Handle different formats
    if pluno_str.startswith("VI/") or pluno_str.startswith("6/"):
        return "Group VI"
    elif pluno_str.startswith("IV/") or pluno_str.startswith("4/"):
        return "Group IV"  
    elif pluno_str.startswith("III/") or pluno_str.startswith("3/"):
        return "Group III"
    elif pluno_str.startswith("II/") or pluno_str.startswith("2/"):
        return "Group II"
    elif pluno_str.startswith("I/") or pluno_str.startswith("1/"):
        return "Group I"
    
    return "Unknown"

# Phase 1: Validation Utilities
async def check_duplicate_upload(period_covered: str) -> Optional[Dict]:
    """Check if data for this period already exists in sales_records
    
    Handles both normalized (2025-09) and legacy formats (Sep 2025, 1 Sep to 30 2025)
    Excludes multi-month/yearly data (e.g., "JAN TO SEP 2025")
    """
    # First try exact match with normalized format
    existing_records = await db.sales_records.count_documents({
        "data_period": period_covered
    })
    
    # If no exact match, try pattern matching for legacy formats
    if existing_records == 0 and period_covered:
        # Extract year and month from normalized format (YYYY-MM)
        import re
        match = re.match(r'(\d{4})-(\d{2})', period_covered)
        if match:
            year = match.group(1)
            month = match.group(2)
            month_int = int(month)
            
            # Build regex pattern to match various legacy formats
            month_names = {
                1: ['jan', 'january'],
                2: ['feb', 'february'],
                3: ['mar', 'march'],
                4: ['apr', 'april'],
                5: ['may'],
                6: ['jun', 'june'],
                7: ['jul', 'july'],
                8: ['aug', 'august'],
                9: ['sep', 'sept', 'september'],
                10: ['oct', 'october'],
                11: ['nov', 'november'],
                12: ['dec', 'december']
            }
            
            target_month_names = month_names.get(month_int, [])
            
            if target_month_names:
                # Get all records that might contain this month
                all_records = await db.sales_records.find({
                    "data_period": {"$exists": True, "$ne": None}
                }).to_list(None)
                
                # Filter to find ONLY single-month records for the target month
                matching_records = []
                for record in all_records:
                    data_period = record.get("data_period", "").lower()
                    
                    # Skip if empty
                    if not data_period:
                        continue
                    
                    # Check if it's the target year
                    if year not in data_period:
                        continue
                    
                    # Check if it contains the target month
                    has_target_month = any(month_name in data_period for month_name in target_month_names)
                    if not has_target_month:
                        continue
                    
                    # CRITICAL: Exclude multi-month patterns
                    # Look for patterns like "JAN TO SEP", "january to september", etc.
                    is_multi_month = False
                    for other_month_int in range(1, 13):
                        if other_month_int != month_int:  # Different month
                            other_month_names = month_names.get(other_month_int, [])
                            for other_month_name in other_month_names:
                                if other_month_name in data_period:
                                    # Found another month name - likely a range
                                    is_multi_month = True
                                    break
                            if is_multi_month:
                                break
                    
                    # Also check for "TO" keyword which indicates a range
                    if " to " in data_period and is_multi_month:
                        continue
                    
                    # If we got here, it's a single-month record for our target month
                    if not is_multi_month:
                        matching_records.append(record)
                
                existing_records = len(matching_records)
    
    if existing_records > 0:
        # Get upload history for this period to show when it was uploaded
        upload_history = await db.upload_history.find_one({
            "period_covered": period_covered,
            "status": "success"
        }, sort=[("upload_date", -1)])
        
        return {
            "records_count": existing_records,
            "upload_date": upload_history.get("upload_date") if upload_history else None
        }
    
    return None

def validate_forecast_date(year: int, month: int) -> Dict[str, Any]:
    """Validate that forecast date is not in the past"""
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    
    # Check if the forecast date is in the past
    if year < current_year or (year == current_year and month < current_month):
        return {
            "valid": False,
            "error": f"Cannot generate forecast for past period: {month}/{year}. Current period is {current_month}/{current_year}."
        }
    
    return {"valid": True}

def validate_excel_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate Excel file has minimum required columns"""
    required_cols = ['item_name', 'qty']  # Minimum required
    recommended_cols = ['item_name', 'qty', 'closing_stock', 'w_rate', 'r_rate']
    
    # Check what columns we have after normalization
    df_cols_lower = [str(col).lower().replace(' ', '_').replace('.', '') for col in df.columns]
    
    missing_required = []
    for col in required_cols:
        if not any(col in c for c in df_cols_lower):
            missing_required.append(col)
    
    if missing_required:
        return {
            "valid": False,
            "error": f"Missing required columns: {', '.join(missing_required)}",
            "found_columns": list(df.columns)
        }
    
    missing_recommended = []
    for col in recommended_cols:
        if not any(col in c for c in df_cols_lower):
            missing_recommended.append(col)
    
    return {
        "valid": True,
        "missing_recommended": missing_recommended,
        "total_rows": len(df)
    }

def extract_period_from_filename(filename: str) -> Dict[str, Any]:
    """Extract period information from filename with smart date range detection
    
    Examples:
    - "01 Jan to Sep 30 2025" -> Jan-Sep 2025
    - "01 to 30 Oct 25" -> Oct 2025
    - "YR 2024 C.xlsx" -> 2024
    - "Nov 2025.xlsx" -> Nov 2025
    """
    import re
    
    result = {"year": None, "month": None, "period": None, "data_type": None, "start_month": None, "end_month": None}
    
    # Month mapping
    months = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }
    
    month_names_short = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    filename_lower = filename.lower()
    
    # Extract year (4 digits or 2 digits)
    year_match = re.search(r'20(\d{2})', filename)
    if not year_match:
        year_match = re.search(r'\b(\d{2})\b', filename)  # 2-digit year like "25"
        if year_match:
            year_2digit = int(year_match.group(1))
            result["year"] = 2000 + year_2digit if year_2digit < 50 else 1900 + year_2digit
    else:
        result["year"] = int(year_match.group())
    
    # Pattern 1: Range with two month names - "01 Jan to Sep 30 2025" or "Jan to Sep 2025"
    range_pattern = r'(\w+)\s+to\s+(\w+)'
    range_match = re.search(range_pattern, filename_lower)
    
    if range_match:
        start_part = range_match.group(1)
        end_part = range_match.group(2)
        
        # Find months in the range
        start_month = None
        end_month = None
        
        for month_name, month_num in months.items():
            if month_name in start_part:
                start_month = month_num
            if month_name in end_part:
                end_month = month_num
        
        if start_month and end_month:
            result["start_month"] = start_month
            result["end_month"] = end_month
            result["data_type"] = "range"
            
            # Format: "Jan-Sep 2025"
            if result["year"]:
                start_name = month_names_short[start_month - 1]
                end_name = month_names_short[end_month - 1]
                result["period"] = f"{result['year']}-{start_month:02d}-{end_month:02d}"  # Store as range
                result["display_name"] = f"{start_name}-{end_name} {result['year']}"
            return result
    
    # Pattern 2: Single month - "Nov 2025", "October 25", "01 to 30 Oct 25"
    found_months = []
    for month_name, month_num in months.items():
        if month_name in filename_lower:
            found_months.append(month_num)
    
    if found_months:
        result["month"] = found_months[0]  # Take first found month
        result["data_type"] = "monthly"
        if result["year"]:
            result["period"] = f"{result['year']}-{result['month']:02d}"
            result["display_name"] = f"{month_names_short[result['month']-1]} {result['year']}"
        return result
    
    # Pattern 3: Yearly data - "YR 2024", "2024"
    if result["year"] and not result["month"]:
        result["period"] = str(result["year"])
        result["data_type"] = "yearly"
        result["display_name"] = str(result["year"])
        return result
    
    return result

def format_indian_currency(amount: float, use_symbol: bool = True) -> str:
    """Format number in Indian currency format with Rs. prefix
    
    Args:
        amount: The amount to format
        use_symbol: If True, use 'Rs. ', otherwise no prefix
    """
    try:
        # Handle negative numbers
        is_negative = amount < 0
        amount = abs(amount)
        
        # Split into integer and decimal parts
        amount_str = f"{amount:.2f}"
        integer_part, decimal_part = amount_str.split('.')
        
        # Indian numbering: last 3 digits, then groups of 2
        if len(integer_part) <= 3:
            formatted = integer_part
        else:
            # Last 3 digits
            last_three = integer_part[-3:]
            # Remaining digits in groups of 2
            remaining = integer_part[:-3]
            # Add commas every 2 digits from right to left
            formatted_remaining = ''
            for i in range(len(remaining) - 1, -1, -2):
                if i == 0:
                    formatted_remaining = remaining[0] + formatted_remaining
                else:
                    formatted_remaining = ',' + remaining[i-1:i+1] + formatted_remaining
            formatted = formatted_remaining.lstrip(',') + ',' + last_three
        
        # Add decimal part
        if use_symbol:
            result = f"Rs. {formatted}.{decimal_part}"
        else:
            result = f"{formatted}.{decimal_part}"
        
        # Add negative sign if needed
        if is_negative:
            result = '-' + result
            
        return result
    except Exception as e:
        logger.error(f"Error formatting currency: {str(e)}")
        return f"Rs. {amount:,.2f}"

async def format_period_display_name(period: str) -> str:
    """Format period name intelligently based on stored period format
    
    Examples:
    - Full year: "2024" -> "2024"
    - Single month: "2025-11" -> "Nov 2025"
    - Current month: "2025-12" -> "Current Period (Dec 2025)"
    - Range: "2025-01-09" -> "Jan-Sep 2025"
    """
    import re
    from datetime import datetime
    
    # If it's already a year (4 digits), return as is
    if re.match(r'^\d{4}$', period):
        return period
    
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Check for range format: YYYY-MM-MM (start month to end month)
    range_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', period)
    if range_match:
        year = range_match.group(1)
        start_month = int(range_match.group(2))
        end_month = int(range_match.group(3))
        
        # If start and end are the same, treat as single month
        if start_month == end_month:
            current_date = datetime.now()
            if int(year) == current_date.year and start_month == current_date.month:
                return f"Current Period ({month_names[start_month-1]} {year})"
            return f"{month_names[start_month-1]} {year}"
        
        # Range format
        return f"{month_names[start_month-1]}-{month_names[end_month-1]} {year}"
    
    # Single month format: YYYY-MM
    month_match = re.match(r'^(\d{4})-(\d{2})$', period)
    if month_match:
        year = month_match.group(1)
        month = int(month_match.group(2))
        
        # Check if this is current month
        current_date = datetime.now()
        if int(year) == current_date.year and month == current_date.month:
            return f"Current Period ({month_names[month-1]} {year})"
        
        # For non-current months, format as "Month Year"
        return f"{month_names[month-1]} {year}"
    
    # Fallback: return as is
    return period


def extract_net_amt_from_summary(df: pd.DataFrame) -> Optional[float]:
    """Extract Net Amt value from TReport Total row's R_Amt column"""
    try:
        # First, find the R_Amt column index
        r_amt_col_idx = None
        column_names = [str(col).strip().lower() for col in df.columns]
        
        for idx, col_name in enumerate(column_names):
            if 'r_amt' in col_name or 'r amt' in col_name:
                r_amt_col_idx = idx
                logger.info(f"Found R_Amt column at index {r_amt_col_idx}: '{df.columns[idx]}'")
                break
        
        if r_amt_col_idx is None:
            logger.warning("R_Amt column not found in Excel sheet")
            return None
        
        # Log rows around 704-710 (Excel rows 706-712) for debugging
        logger.info(f"DataFrame has {len(df)} total rows. Checking rows 700-710 for Report Total...")
        for check_idx in range(max(0, 700), min(len(df), 711)):
            first_col_val = str(df.iloc[check_idx, 0]).strip() if pd.notna(df.iloc[check_idx, 0]) else ""
            if check_idx >= 700:  # Log all rows from 700 onwards
                logger.info(f"  Pandas row {check_idx} (Excel ~{check_idx+2}), Col 0: '{first_col_val}'")
        
        # Now look for "Report Total" row - check ALL columns to be thorough
        for idx, row in df.iterrows():
            # Check ALL columns for the row label (not just first 5)
            for col_idx in range(len(row)):
                cell_value = str(row.iloc[col_idx]).strip() if pd.notna(row.iloc[col_idx]) else ""
                cell_value_lower = cell_value.lower()
                
                # Look for variations of "Report Total" (case-insensitive)
                if ('report total' in cell_value_lower) or \
                   ('report' in cell_value_lower and 'total' in cell_value_lower) or \
                   (cell_value_lower.replace(' ', '') == 'reporttotal'):
                    
                    logger.info(f"Found Report Total row at pandas index {idx} (Excel row ~{idx+2}), column {col_idx}: '{cell_value}'")
                    
                    # Extract R_Amt value from this row
                    if r_amt_col_idx < len(row):
                        r_amt_value = row.iloc[r_amt_col_idx]
                        logger.debug(f"R_Amt value in Report Total row: {r_amt_value}, type: {type(r_amt_value)}")
                        
                        if pd.notna(r_amt_value):
                            try:
                                # Handle both numeric and string values
                                if isinstance(r_amt_value, (int, float)):
                                    net_amt = float(r_amt_value)
                                else:
                                    # Clean string: remove commas, spaces, currency symbols
                                    cleaned = str(r_amt_value).replace(',', '').replace(' ', '').replace('₹', '').replace('Rs.', '').strip()
                                    net_amt = float(cleaned)
                                
                                if net_amt > 0:  # Sanity check
                                    logger.info(f"✓ Successfully extracted Net Amt from Report Total R_Amt: Rs. {net_amt:,.2f}")
                                    return net_amt
                                else:
                                    logger.warning(f"Report Total R_Amt value is not positive: {net_amt}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to convert Report Total R_Amt to float: '{r_amt_value}' - {str(e)}")
                    
                    # If we found the row but couldn't extract, log for debugging
                    logger.warning(f"Found Report Total row but couldn't extract R_Amt value")
                    break
        
        # Fallback: Try looking for "Net Amt" in Summary Details (old method)
        logger.info("Report Total not found, trying Net Amt in Summary Details...")
        for idx, row in df.iterrows():
            for col_idx in range(min(5, len(row))):
                cell_value = str(row.iloc[col_idx]).strip().lower() if pd.notna(row.iloc[col_idx]) else ""
                
                if "net amt" in cell_value or "net amount" in cell_value:
                    logger.info(f"Found 'Net Amt' label at row {idx}, column {col_idx}")
                    
                    # Try column E (index 4)
                    if len(row) > 4 and pd.notna(row.iloc[4]):
                        try:
                            col_e_value = row.iloc[4]
                            if isinstance(col_e_value, (int, float)):
                                net_amt = float(col_e_value)
                            else:
                                cleaned = str(col_e_value).replace(',', '').replace(' ', '').replace('₹', '').replace('Rs.', '').strip()
                                net_amt = float(cleaned)
                            
                            if net_amt > 0:
                                logger.info(f"✓ Successfully extracted Net Amt from Summary Details column E: Rs. {net_amt:,.2f}")
                                return net_amt
                        except (ValueError, TypeError) as e:
                            logger.debug(f"Failed to convert Net Amt column E: {str(e)}")
                    
                    # Try other columns in same row
                    for value_col_idx in range(len(row)):
                        if pd.notna(row.iloc[value_col_idx]):
                            try:
                                cell_val = row.iloc[value_col_idx]
                                if isinstance(cell_val, (int, float)):
                                    test_val = float(cell_val)
                                else:
                                    cleaned = str(cell_val).replace(',', '').replace(' ', '').replace('₹', '').replace('Rs.', '').strip()
                                    test_val = float(cleaned)
                                
                                if test_val > 1000:
                                    logger.info(f"✓ Found Net Amt at column {value_col_idx}: Rs. {test_val:,.2f}")
                                    return test_val
                            except (ValueError, TypeError):
                                continue
                    break
        
        logger.warning("Net Amt not found in TReport Total or Summary Details - will calculate from records")
        return None
    except Exception as e:
        logger.error(f"Error extracting Net Amt: {str(e)}", exc_info=True)
        return None


def extract_report_total_from_embedded_text(df: pd.DataFrame) -> Optional[Dict[str, float]]:
    """Search for Report Total embedded within cell text (handles malformed Excel files)
    
    Some Excel exports concatenate multiple rows into single cells with _x000D_ or tab characters.
    This function searches all cells for "Report Total" pattern and extracts R_Amt value.
    
    Expected format: "Report Total\t\t\t\t\t\t2,920\t4\t2916\t233,715.34\t224,581.18\t..."
    Where R_Amt is typically the 4th numeric value (after qty, refund_qty, net_qty)
    
    Returns:
        Dictionary with 'r_amt' and 'w_amt' if found, None otherwise
    """
    import re
    
    logger.info("Searching for embedded Report Total in all cells...")
    
    # Search through all cells for "Report Total" pattern
    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell_value = df.iloc[row_idx, col_idx]
            
            if pd.isna(cell_value):
                continue
            
            cell_str = str(cell_value)
            
            # Check if this cell contains "Report Total"
            if 'report total' in cell_str.lower():
                logger.info(f"Found 'Report Total' embedded in cell at row {row_idx}, col {col_idx}")
                logger.debug(f"Cell content preview: {cell_str[:200]}...")
                
                # Split by newlines/carriage returns to get individual lines
                lines = re.split(r'[\r\n]+|_x000D_', cell_str)
                for line in lines:
                    line_lower = line.lower()
                    if 'report total' in line_lower:
                        logger.debug(f"Report Total line found: {line[:200]}")
                        
                        # Split by single tabs (not tab+)
                        parts = line.split('\t')
                        
                        # Extract all numeric values
                        numeric_values = []
                        for i, part in enumerate(parts):
                            # Clean the part - remove commas, quotes, apostrophes
                            cleaned = part.replace(',', '').replace("'", '').replace('"', '').strip()
                            if cleaned and cleaned != '_x000D_':
                                try:
                                    val = float(cleaned)
                                    numeric_values.append((i, val))
                                except (ValueError, TypeError):
                                    continue
                        
                        logger.info(f"Found {len(numeric_values)} numeric values in Report Total line")
                        
                        # In the standard format:
                        # Report Total\t\t\t\t\t\t2,920\t4\t2916\t233,715.34\t224,581.18\t'9,134.16\t0.00
                        # Position: [empty tabs] [qty] [refund] [net_qty] [R_AMT] [W_AMT] [profit] [other]
                        
                        # The R_Amt is typically the 4th numeric value (after qty, refund_qty, net_qty)
                        # It's also typically > 10,000 for a day's sales
                        
                        # Filter to amounts that are likely R_Amt or W_Amt (>10,000 and have decimals)
                        amount_values = [(idx, val) for idx, val in numeric_values if val > 10000]
                        
                        logger.info(f"Found {len(amount_values)} amount values (>10000): {amount_values}")
                        
                        if amount_values:
                            # The first amount value is R_Amt
                            r_amt = amount_values[0][1] if len(amount_values) >= 1 else None
                            # The second amount value is W_Amt
                            w_amt = amount_values[1][1] if len(amount_values) >= 2 else None
                            
                            logger.info(f"✓ Extracted from embedded text - R_Amt: {r_amt}, W_Amt: {w_amt}")
                            return {'r_amt': r_amt, 'w_amt': w_amt}
    
    logger.warning("Could not find Report Total in embedded text")
    return None


def identify_special_rows(df: pd.DataFrame) -> Dict[str, int]:
    """Identify special rows like Group Total, Report Total, Summary Details
    
    Returns:
        Dictionary with row indices: {'group_totals': [idx1, idx2], 'report_total': idx, 'summary_start': idx}
    """
    special_rows = {
        'group_totals': [],
        'report_total': None,
        'summary_start': None
    }
    
    # Check first column (S.No) for special text
    first_col = df.iloc[:, 0]
    
    for idx, value in enumerate(first_col):
        if pd.isna(value):
            continue
        
        value_str = str(value).strip().lower()
        
        # Check for Group Total
        if 'group total' in value_str and 'report' not in value_str:
            special_rows['group_totals'].append(idx)
            logger.info(f"Found Group Total at row {idx} (Excel row {idx+2})")
        
        # Check for Report Total
        elif 'report total' in value_str:
            special_rows['report_total'] = idx
            logger.info(f"Found Report Total at row {idx} (Excel row {idx+2})")
        
        # Check for Summary Details
        elif 'summary details' in value_str or ('summary' in value_str and '*' in value_str):
            special_rows['summary_start'] = idx
            logger.info(f"Found Summary Details section at row {idx} (Excel row {idx+2})")
    
    return special_rows


def extract_report_total_amounts(df: pd.DataFrame, report_total_idx: int) -> Dict[str, Optional[float]]:
    """Extract R_Amt and W_Amt values from Report Total row
    
    Returns:
        Dictionary with 'r_amt' and 'w_amt' values
    """
    result = {'r_amt': None, 'w_amt': None}
    
    try:
        if report_total_idx is None:
            return result
        
        # Find R_Amt column index
        r_amt_col_idx = None
        w_amt_col_idx = None
        
        for idx, col in enumerate(df.columns):
            col_lower = str(col).lower()
            if 'r_amt' in col_lower or 'r amt' in col_lower:
                r_amt_col_idx = idx
            elif 'w_amt' in col_lower or 'w amt' in col_lower:
                w_amt_col_idx = idx
        
        # Get Report Total row
        report_total_row = df.iloc[report_total_idx]
        
        # Extract R_Amt
        if r_amt_col_idx is not None:
            r_amt_value = report_total_row.iloc[r_amt_col_idx]
            if pd.notna(r_amt_value):
                result['r_amt'] = float(r_amt_value)
                logger.info(f"✓ Extracted Report Total R_Amt: Rs. {result['r_amt']:,.2f}")
        else:
            logger.warning("R_Amt column not found for Report Total extraction")
        
        # Extract W_Amt
        if w_amt_col_idx is not None:
            w_amt_value = report_total_row.iloc[w_amt_col_idx]
            if pd.notna(w_amt_value):
                result['w_amt'] = float(w_amt_value)
                logger.info(f"✓ Extracted Report Total W_Amt: Rs. {result['w_amt']:,.2f}")
        else:
            logger.warning("W_Amt column not found for Report Total extraction")
        
        return result
    except Exception as e:
        logger.error(f"Error extracting Report Total amounts: {str(e)}")
        return result


def process_excel_data(file_content: bytes, filename: str, period_info: Optional[Dict[str, Any]] = None) -> tuple[List[Dict], Optional[float]]:
    """Process uploaded Excel file (daily/monthly format) and return structured data
    
    Daily/Monthly Excel Format:
    - Headers: S.No, Gp_Index_No, Item_Name, W_Rate, R_Rate, Qty, R_Amt, W_Amt, Profit, O_B, Closing_Stock
    - S.No can be numbers or #Number format
    - Gp_Index_No format: "Group Number/Item Number" (e.g., "I/123")
    - Special rows in S.No column: "Group Total", "Report Total", "Summary Details"
    - Report Total row contains the actual total we need
    
    Returns:
        tuple: (records list, net_amt from Report Total row)
    """
    try:
        # Determine engine based on file extension
        file_extension = filename.lower().split('.')[-1]
        
        # Try to read Excel file with explicit engine
        try:
            if file_extension == 'xlsx':
                df = pd.read_excel(BytesIO(file_content), engine='openpyxl')
            elif file_extension == 'xls':
                # First try xlrd engine
                try:
                    df = pd.read_excel(BytesIO(file_content), engine='xlrd')
                except Exception as xlrd_error:
                    # If xlrd fails, the file might be TSV/CSV with wrong extension
                    logger.warning(f"xlrd failed, trying as TSV: {str(xlrd_error)}")
                    # Try reading as tab-separated or comma-separated
                    try:
                        df = pd.read_csv(BytesIO(file_content), sep='\t', encoding='latin1')
                        logger.info(f"Successfully read as TSV file")
                    except:
                        df = pd.read_csv(BytesIO(file_content), sep=',', encoding='latin1')
                        logger.info(f"Successfully read as CSV file")
            else:
                df = pd.read_excel(BytesIO(file_content))
        except Exception as e:
            # If all engine attempts fail, try CSV/TSV as last resort
            logger.warning(f"Failed to read as Excel, trying as CSV/TSV: {str(e)}")
            try:
                df = pd.read_csv(BytesIO(file_content), sep='\t', encoding='latin1')
                logger.info(f"Successfully read as TSV file")
            except:
                df = pd.read_csv(BytesIO(file_content), sep=',', encoding='latin1')
                logger.info(f"Successfully read as CSV file")
        
        # Log initial dataframe shape
        logger.info(f"Processing file {filename}: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"Columns found: {df.columns.tolist()}")
        
        # Identify special rows (Group Total, Report Total, Summary Details)
        special_rows = identify_special_rows(df)
        
        # Extract R_Amt and W_Amt from Report Total row
        report_total_amounts = extract_report_total_amounts(df, special_rows['report_total'])
        net_amt_from_report_total = report_total_amounts['r_amt']
        w_amt_from_report_total = report_total_amounts['w_amt']
        
        # If Report Total not found in standard location, search for it in embedded text
        if net_amt_from_report_total is None:
            logger.info("Report Total not found in standard location, searching embedded text...")
            embedded_amounts = extract_report_total_from_embedded_text(df)
            if embedded_amounts:
                net_amt_from_report_total = embedded_amounts.get('r_amt')
                w_amt_from_report_total = embedded_amounts.get('w_amt')
                logger.info(f"✓ Using Report Total from embedded text: R_Amt={net_amt_from_report_total}, W_Amt={w_amt_from_report_total}")
        
        # Standardize column names (handle both underscore and space-separated formats)
        column_mapping = {
            # Serial Number variations
            'SNo': 's_no',
            'S.No': 's_no',
            'S No': 's_no',
            # GP Index / Product Code variations
            'GP_Index_No': 'gp_index_no',
            'GP_Index': 'gp_index_no',
            'GP Index No': 'gp_index_no',
            'GP Index': 'gp_index_no',
            'pluno': 'pluno',
            # Item Name variations
            'Item_Name': 'item_name',
            'Item Name': 'item_name',
            'ItemName': 'item_name',
            # Wholesale Rate variations
            'W_Rate': 'w_rate',
            'W Rate': 'w_rate',
            'WRate': 'w_rate',
            # Retail Rate variations
            'R_Rate': 'r_rate',
            'R Rate': 'r_rate',
            'RRate': 'r_rate',
            # Quantity variations
            'Qty': 'qty',
            'Quantity': 'qty',
            # Refund Quantity variations
            'Refund_Qty': 'refund_qty',
            'Refund Qty': 'refund_qty',
            'RefundQty': 'refund_qty',
            # Net Quantity variations
            'Net_Qty': 'net_qty',
            'Net Qty': 'net_qty',
            'NetQty': 'net_qty',
            # Retail Amount variations
            'R_Amt': 'r_amt',
            'R Amt': 'r_amt',
            'RAmt': 'r_amt',
            # Wholesale Amount variations
            'W_Amt': 'w_amt',
            'W Amt': 'w_amt',
            'WAmt': 'w_amt',
            # Profit variations
            'Profit': 'profit',
            # Opening Balance variations
            'O_B': 'o_b',
            'O B': 'o_b',
            'OB': 'o_b',
            'Opening_Balance': 'o_b',
            'Opening Balance': 'o_b',
            # Closing Stock variations
            'Closing_Stock': 'closing_stock',
            'Closing Stock': 'closing_stock',
            'ClosingStock': 'closing_stock',
            # Net Tax variations
            'Net_Tax': 'net_tax',
            'Net Tax': 'net_tax',
            'Net-Tax': 'net_tax',
            'NetTax': 'net_tax'
        }
        
        df = df.rename(columns=column_mapping)
        
        # If gp_index_no exists but pluno doesn't, copy gp_index_no to pluno
        if 'gp_index_no' in df.columns and 'pluno' not in df.columns:
            df['pluno'] = df['gp_index_no']
        # If pluno exists but gp_index_no doesn't, copy pluno to gp_index_no
        elif 'pluno' in df.columns and 'gp_index_no' not in df.columns:
            df['gp_index_no'] = df['pluno']
        
        # Calculate Net_Qty if not present (Qty - Refund_Qty)
        if 'net_qty' not in df.columns:
            if 'qty' in df.columns and 'refund_qty' in df.columns:
                df['net_qty'] = df['qty'] - df['refund_qty'].fillna(0)
            elif 'qty' in df.columns:
                # If no refund_qty column, net_qty = qty
                df['net_qty'] = df['qty']
        
        # Log column mapping results
        logger.info(f"After mapping, columns available: {df.columns.tolist()}")
        
        # Convert numeric columns to proper types (handle string values)
        numeric_columns = ['s_no', 'w_rate', 'r_rate', 'qty', 'refund_qty', 'net_qty', 
                          'r_amt', 'w_amt', 'profit', 'o_b', 'closing_stock', 'net_tax']
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.info(f"Converted numeric columns to proper types")
        
        # Calculate Profit AFTER numeric conversion (R_Amt - W_Amt)
        if 'r_amt' in df.columns and 'w_amt' in df.columns:
            df['profit'] = df['r_amt'].fillna(0) - df['w_amt'].fillna(0)
            logger.info(f"Calculated profit for {len(df[df['profit'].notna()])} rows")
        
        # Use normalized period from period_info, fallback to filename if not provided
        if period_info and period_info.get('period'):
            data_period = period_info['period']  # Normalized format: "2025-09" or "2024"
            logger.info(f"Using normalized data_period: {data_period}")
        else:
            # Fallback to raw filename (for backward compatibility)
            data_period = filename.replace('.xlsx', '').replace('.xls', '')
            logger.warning(f"No period_info provided, using raw filename as period: {data_period}")
        
        records = []
        skipped_rows = []
        skipped_count = 0
        
        # Create set of special row indices to skip
        special_row_indices = set(special_rows['group_totals'])
        if special_rows['report_total'] is not None:
            special_row_indices.add(special_rows['report_total'])
        if special_rows['summary_start'] is not None:
            # Skip all rows from summary section onwards
            for i in range(special_rows['summary_start'], len(df)):
                special_row_indices.add(i)
        
        for idx, row in df.iterrows():
            # Skip special rows (Group Total, Report Total, Summary Details section)
            if idx in special_row_indices:
                skipped_count += 1
                s_no_value = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
                if len(skipped_rows) < 10:
                    skipped_rows.append(f"Row {idx + 2}: '{s_no_value}' - Special row (Group/Report Total or Summary)")
                continue
            
            # Get item details
            item_name = str(row.get('item_name', '')).strip()
            gp_index_no = str(row.get('gp_index_no', '')).strip()
            
            # Use gp_index_no as the primary identifier (not pluno for daily data)
            pluno = gp_index_no
            
            # Skip rows with problematic data or round off amounts
            skip_reason = None
            if pd.isna(row.get('pluno')) and pd.isna(row.get('item_name')):
                skip_reason = "Both pluno and item_name are empty"
            elif item_name == 'nan' or pluno == 'nan':
                skip_reason = "Item name or pluno is 'nan'"
            elif len(item_name) > 100:
                skip_reason = "Item name too long (>100 chars)"
            elif '\t' in item_name or '_x000D_' in item_name:
                skip_reason = "Item name contains invalid characters"
            elif any(char in item_name for char in ['#', '$', '%']):
                skip_reason = "Item name contains special characters"
            elif len(item_name) < 3 and not item_name.isalpha():
                skip_reason = "Item name too short"
            elif 'round off' in item_name.lower() or 'roundoff' in item_name.lower():
                skip_reason = "Round off entry"
            
            # Skip rows that look like numbers instead of item names
            if not skip_reason:
                try:
                    float(item_name)
                    skip_reason = "Item name is just a number"
                except ValueError:
                    pass  # Good, it's not just a number
            
            if skip_reason:
                skipped_count += 1
                if len(skipped_rows) < 10:
                    if gp_index_no:
                        skipped_rows.append(f"Row {idx + 2}: GP#{gp_index_no}, {item_name[:30]} - {skip_reason}")
                    else:
                        skipped_rows.append(f"Row {idx + 2}: {item_name[:30]} - {skip_reason}")
                continue
                
            def safe_float(value):
                if pd.isna(value):
                    return None
                try:
                    # Handle string values with quotes or other formatting
                    if isinstance(value, str):
                        str_val = value.replace("'", "").replace('"', "").replace(",", "").strip()
                    else:
                        str_val = str(value)
                    # Handle negative values and empty strings
                    if str_val == '' or str_val == 'nan' or str_val == 'None':
                        return None
                    return float(str_val)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert value to float: {value}")
                    return None
            
            def safe_int(value):
                if pd.isna(value):
                    return None
                try:
                    str_val = str(value).replace("'", "").replace('"', "").strip()
                    return int(float(str_val)) if str_val and str_val != 'nan' else None
                except (ValueError, TypeError):
                    return None
            
            record = {
                's_no': safe_int(row.get('s_no')),
                'gp_index_no': str(row.get('gp_index_no')) if not pd.isna(row.get('gp_index_no')) else None,
                'pluno': str(row.get('pluno')) if not pd.isna(row.get('pluno')) else None,
                'item_name': str(row.get('item_name')) if not pd.isna(row.get('item_name')) else None,
                'w_rate': safe_float(row.get('w_rate')),
                'r_rate': safe_float(row.get('r_rate')),
                'qty': safe_int(row.get('qty')),
                'refund_qty': safe_int(row.get('refund_qty')),
                'net_qty': safe_int(row.get('net_qty')),
                'r_amt': safe_float(row.get('r_amt')),
                'w_amt': safe_float(row.get('w_amt')),
                'profit': safe_float(row.get('profit')),
                'o_b': safe_float(row.get('o_b')),
                'closing_stock': safe_float(row.get('closing_stock')),
                'net_tax': safe_float(row.get('net_tax')),
                'data_period': data_period,
                'product_group': extract_group_from_pluno(row.get('gp_index_no') or row.get('pluno'))
            }
            
            # Clean the record
            record = prepare_for_mongo(record)
            records.append(record)
        
        logger.info(f"Processed {len(records)} valid records from {filename}, skipped {skipped_count} rows")
        if skipped_rows:
            logger.info(f"Sample skipped rows: {skipped_rows}")
        
        if len(records) == 0:
            # Provide detailed error information
            error_details = {
                "total_rows": len(df),
                "skipped_rows": skipped_count,
                "sample_skipped": skipped_rows[:5] if skipped_rows else [],
                "columns_found": df.columns.tolist(),
                "filename": filename
            }
            raise HTTPException(
                status_code=400, 
                detail=f"No valid records found in the file. Total rows: {len(df)}, Skipped: {skipped_count}. Check data format and ensure items have valid names and product codes. Sample issues: {'; '.join(skipped_rows[:3]) if skipped_rows else 'No specific issues logged'}"
            )
        
        # Use Net Amt from Report Total row if available, otherwise sum from records
        if net_amt_from_report_total is not None:
            net_amt = net_amt_from_report_total
            logger.info(f"Using Net Amt from Report Total row: Rs. {net_amt:,.2f}")
        else:
            # Fallback: Calculate by summing R_Amt from all processed records
            net_amt = 0.0
            for record in records:
                if 'r_amt' in record and record['r_amt'] is not None:
                    try:
                        net_amt += float(record['r_amt'])
                    except (ValueError, TypeError):
                        continue
            logger.info(f"Report Total not found, calculated Net Amt from {len(records)} records: Rs. {net_amt:,.2f}")
        
        # Calculate W_Amt fallback if not in Report Total
        if w_amt_from_report_total is None:
            w_amt_from_report_total = 0.0
            for record in records:
                if 'w_amt' in record and record['w_amt'] is not None:
                    try:
                        w_amt_from_report_total += float(record['w_amt'])
                    except (ValueError, TypeError):
                        continue
        
        return records, net_amt, w_amt_from_report_total
        
    except HTTPException:
        # Re-raise HTTP exceptions with details
        raise
    except Exception as e:
        logger.error(f"Error processing Excel file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error processing Excel file: {str(e)}")

# API Routes
@api_router.post("/upload-sales-data")
async def upload_sales_data(
    file: UploadFile = File(...),
    upload_type: str = Form("historical"),  # "daily" or "historical"
    data_date: Optional[str] = Form(None),  # Format: "YYYY-MM-DD" for daily uploads
    upload_source: str = Form("analytics")  # "analytics" or "forecast"
):
    """Upload and process sales data from Excel file with history logging"""
    start_time = datetime.now()
    upload_id = str(uuid.uuid4())
    
    logger.info(f"Upload attempt: filename={file.filename}, upload_id={upload_id}, type={upload_type}, data_date={data_date}, source={upload_source}")
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=400, 
            detail="Only Excel files (.xlsx or .xls) are supported. Please upload a valid Excel file."
        )
    
    try:
        contents = await file.read()
        file_size_kb = len(contents) / 1024
        logger.info(f"File read successfully: size={file_size_kb:.2f}KB")
        
        # Check if file is not empty
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")
        
        # Extract period from filename
        period_info = extract_period_from_filename(file.filename)
        
        # Check for duplicate upload - different logic for daily vs historical
        existing = None
        if upload_type == "daily" and data_date:
            # For daily uploads, check if data for this specific date already exists
            parsed_data_date = datetime.strptime(data_date, "%Y-%m-%d")
            existing = await db.upload_history.find_one({
                "upload_type": "daily",
                "data_date": {
                    "$gte": parsed_data_date,
                    "$lt": parsed_data_date + timedelta(days=1)
                },
                "status": "success"
            })
            if existing:
                logger.warning(f"Duplicate daily upload blocked for date {data_date}")
        elif upload_type == "historical" and period_info["period"]:
            # For historical uploads, check by month/year period
            existing = await check_duplicate_upload(period_info["period"])
        
        if existing:
                upload_date_str = existing.get('upload_date')
                date_info = f" (uploaded on {upload_date_str})" if upload_date_str else ""
                
                if upload_type == "daily":
                    # More specific error for daily uploads
                    raise HTTPException(
                        status_code=400,
                        detail=f"Data for date '{data_date}' has already been uploaded{date_info}. Found {existing['records_count']} existing records. Please use UNDO on the previous upload from the Upload History tab if you want to re-upload."
                    )
                else:
                    # Error for historical uploads
                    raise HTTPException(
                        status_code=400,
                        detail=f"Data for period '{period_info['period']}' already exists in the database{date_info}. Found {existing['records_count']} existing records. Please use UNDO on the previous upload or reset database to re-upload."
                    )
        
        # Process the data with normalized period information
        records, net_amt, w_amt = process_excel_data(contents, file.filename, period_info)
        
        if records:
            # Add upload batch tracking to each record
            for record in records:
                record['upload_batch_id'] = upload_id
                record['upload_date'] = datetime.now(timezone.utc)
                # Mark source based on upload_source parameter
                record['upload_source'] = upload_source
            
            # Insert into MongoDB
            result = await db.sales_records.insert_many([SalesRecord(**record).dict() for record in records])
            
            # For daily uploads, consolidate previous month's data if we're in a new month
            if upload_type == "daily" and data_date:
                await consolidate_daily_to_monthly(data_date)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log upload history
            # Parse data_date if provided for daily uploads
            parsed_data_date = None
            if upload_type == "daily" and data_date:
                try:
                    parsed_data_date = datetime.strptime(data_date, "%Y-%m-%d")
                except ValueError:
                    logger.warning(f"Invalid data_date format: {data_date}")
            
            upload_record = UploadHistory(
                id=upload_id,
                filename=file.filename,
                period_covered=period_info["period"],
                data_type=period_info["data_type"],
                upload_type=upload_type,
                data_date=parsed_data_date,
                records_count=len(records),
                status="success",
                file_size_kb=file_size_kb,
                processing_time_seconds=processing_time,
                net_amt=net_amt,
                w_amt=w_amt
            )
            await db.upload_history.insert_one(upload_record.dict())
            
            return {
                "message": f"Successfully uploaded {len(records)} records",
                "file_name": file.filename,
                "records_count": len(records),
                "inserted_ids": len(result.inserted_ids),
                "status": "success",
                "upload_id": upload_id,
                "upload_type": upload_type,
                "upload_source": upload_source,
                "data_date": data_date,
                "period_covered": period_info["period"],
                "data_type": period_info["data_type"],
                "duplicate_warning": existing is not None,
                "net_amt": net_amt
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail="No valid records found in the file. Please check the data format."
            )
            
    except HTTPException as he:
        # Log failed upload
        processing_time = (datetime.now() - start_time).total_seconds()
        upload_record = UploadHistory(
            id=upload_id,
            filename=file.filename,
            period_covered=period_info.get("period") if 'period_info' in locals() else None,
            data_type=period_info.get("data_type") if 'period_info' in locals() else None,
            records_count=0,
            status="failed",
            error_message=str(he.detail),
            file_size_kb=len(contents) / 1024 if 'contents' in locals() else 0,
            processing_time_seconds=processing_time
        )
        await db.upload_history.insert_one(upload_record.dict())
        raise
    except Exception as e:
        # Use logging.exception to capture full stack trace
        logger.exception(f"Upload failed for file {file.filename}")
        error_message = str(e)
        
        # Provide specific error messages for common issues
        if "Excel file format cannot be determined" in error_message:
            error_message = f"Cannot read Excel file format. Please ensure '{file.filename}' is a valid .xlsx or .xls file and not corrupted."
        elif "No valid records found" in error_message:
            error_message = f"No valid data rows found in '{file.filename}'. {error_message}"
        elif "openpyxl" in error_message or "xlrd" in error_message:
            error_message = f"Excel library error: {error_message}. The file may be corrupted or in an unsupported format."
        elif "authentication" in error_message.lower() or "mongo" in error_message.lower():
            error_message = "Database connection error. Please contact support."
            logger.error("MongoDB connection issue during upload")
        
        # Log failed upload
        processing_time = (datetime.now() - start_time).total_seconds()
        try:
            upload_record = UploadHistory(
                id=upload_id,
                filename=file.filename,
                period_covered=period_info.get("period") if 'period_info' in locals() else None,
                data_type=period_info.get("data_type") if 'period_info' in locals() else None,
                records_count=0,
                status="failed",
                error_message=error_message,
                file_size_kb=len(contents) / 1024 if 'contents' in locals() else 0,
                processing_time_seconds=processing_time
            )
            await db.upload_history.insert_one(upload_record.dict())
        except Exception as log_error:
            logger.error(f"Failed to log upload history: {log_error}")
        
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to process file '{file.filename}': {error_message}"
        )

@api_router.get("/fastest-selling-items")
async def get_fastest_selling_items(
    limit: int = Query(10, ge=1, le=50),
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None)
):
    """Get fastest selling items with seasonal patterns"""
    try:
        # Build match filter - exclude forecast data
        match_filter = {
            "upload_source": {"$ne": "forecast"},  # Exclude forecast data
            "net_qty": {"$ne": None, "$exists": True}
        }
        if group and group != "all":
            match_filter["product_group"] = group
        if period and period != "all":
            if "Current Year" in period:
                year = period.split(" ")[0]
                match_filter["data_period"] = {
                    "$regex": f"({year}|{year[2:]})", 
                    "$options": "i"
                }
            else:
                match_filter["data_period"] = period
            
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {
                        "pluno": "$pluno", 
                        "item_name": "$item_name",
                        "group": "$product_group"
                    },
                    "total_sold": {"$sum": "$net_qty"},
                    "total_revenue": {"$sum": "$r_amt"},
                    "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                    "periods": {"$push": {"period": "$data_period", "qty": "$net_qty"}}
                }
            },
            {"$sort": {"total_sold": -1}},
            {"$limit": limit}
        ]
        
        results = await db.sales_records.aggregate(pipeline).to_list(None)
        
        fastest_items = []
        for item in results:
            # Calculate seasonal pattern (simplified)
            seasonal_pattern = {}
            for period_data in item['periods']:
                seasonal_pattern[period_data['period']] = period_data['qty']
            
            fastest_items.append({
                "item_code": item['_id']['pluno'],
                "item_name": item['_id']['item_name'],
                "total_sold": item['total_sold'],
                "avg_monthly_sales": item['total_sold'] / max(len(item['periods']), 1),
                "group": item['_id']['group'],
                "seasonal_pattern": seasonal_pattern,
                "total_revenue": item.get('total_revenue', 0),
                "total_profit": item.get('total_profit', 0)
            })
        
        return fastest_items
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fastest selling items: {str(e)}")

@api_router.get("/abc-analysis")
async def get_abc_analysis(
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None)
):
    """Perform ABC analysis - 80/20 rule for inventory classification"""
    try:
        # Build match filter - exclude forecast data
        match_filter = {
            "upload_source": {"$ne": "forecast"},  # Exclude forecast data
            "net_qty": {"$ne": None, "$exists": True, "$gt": 0}
        }
        if group and group != "all":
            match_filter["product_group"] = group
        if period and period != "all":
            match_filter["data_period"] = period
            
        # Get all items with revenue data
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {
                        "pluno": "$pluno",
                        "item_name": "$item_name",
                        "group": "$product_group"
                    },
                    "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                    "total_qty_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                    "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                    "avg_closing_stock": {"$avg": "$closing_stock"},
                    "avg_cost": {"$avg": "$w_rate"}
                }
            },
            {"$match": {"total_revenue": {"$gt": 0}}},
            {"$sort": {"total_revenue": -1}}
        ]
        
        results = await db.sales_records.aggregate(pipeline).to_list(None)
        
        if not results:
            return {"abc_categories": {"A": [], "B": [], "C": []}, "summary": {}}
            
        # Calculate cumulative revenue percentage
        total_revenue = sum(item['total_revenue'] for item in results)
        cumulative_revenue = 0
        
        abc_categories = {"A": [], "B": [], "C": []}
        
        for i, item in enumerate(results):
            cumulative_revenue += item['total_revenue']
            cumulative_percentage = (cumulative_revenue / total_revenue) * 100
            
            item_data = {
                "pluno": item['_id']['pluno'],
                "item_name": item['_id']['item_name'],
                "group": item['_id']['group'],
                "total_revenue": item['total_revenue'],
                "total_qty_sold": item['total_qty_sold'],
                "total_profit": item['total_profit'],
                "revenue_percentage": (item['total_revenue'] / total_revenue) * 100,
                "cumulative_percentage": cumulative_percentage,
                "avg_closing_stock": item.get('avg_closing_stock', 0) or 0,
                "capital_blocked": (item.get('avg_closing_stock', 0) or 0) * (item.get('avg_cost', 0) or 0)
            }
            
            # ABC Classification based on cumulative revenue
            if cumulative_percentage <= 80:
                abc_categories["A"].append(item_data)
            elif cumulative_percentage <= 95:
                abc_categories["B"].append(item_data)
            else:
                abc_categories["C"].append(item_data)
        
        # Calculate summary statistics
        total_items = len(results)
        summary = {
            "total_items": total_items,
            "total_revenue": total_revenue,
            "category_A": {
                "item_count": len(abc_categories["A"]),
                "percentage_items": (len(abc_categories["A"]) / total_items) * 100,
                "revenue": sum(item['total_revenue'] for item in abc_categories["A"]),
                "revenue_percentage": 80 if abc_categories["A"] else 0
            },
            "category_B": {
                "item_count": len(abc_categories["B"]),
                "percentage_items": (len(abc_categories["B"]) / total_items) * 100,
                "revenue": sum(item['total_revenue'] for item in abc_categories["B"]),
                "revenue_percentage": 15 if abc_categories["B"] else 0
            },
            "category_C": {
                "item_count": len(abc_categories["C"]),
                "percentage_items": (len(abc_categories["C"]) / total_items) * 100,
                "revenue": sum(item['total_revenue'] for item in abc_categories["C"]),
                "revenue_percentage": 5 if abc_categories["C"] else 0
            }
        }
        
        return {"abc_categories": abc_categories, "summary": summary}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in ABC analysis: {str(e)}")

@api_router.get("/capital-blocking-analysis")
async def get_capital_blocking_analysis(
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None)
):
    """Identify slow moving items with high inventory causing capital blocking"""
    try:
        match_filter = {"upload_source": {"$ne": "forecast"}}  # Exclude forecast data
        if group and group != "all":
            match_filter["product_group"] = group
        if period and period != "all":
            match_filter["data_period"] = period
            
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {
                        "pluno": "$pluno",
                        "item_name": "$item_name",
                        "group": "$product_group"
                    },
                    "total_qty_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                    "avg_closing_stock": {"$avg": {"$ifNull": ["$closing_stock", 0]}},
                    "avg_wholesale_rate": {"$avg": {"$ifNull": ["$w_rate", 0]}},
                    "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                    "periods_count": {"$sum": 1}
                }
            },
            {
                "$addFields": {
                    "avg_monthly_sales": {"$divide": ["$total_qty_sold", "$periods_count"]},
                    "capital_blocked": {"$multiply": ["$avg_closing_stock", "$avg_wholesale_rate"]},
                    "inventory_turnover": {
                        "$cond": {
                            "if": {"$gt": ["$avg_closing_stock", 0]},
                            "then": {"$divide": ["$total_qty_sold", "$avg_closing_stock"]},
                            "else": 0
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "days_to_sell": {
                        "$divide": [
                            {"$multiply": ["$avg_closing_stock", 30]},
                            {"$max": ["$avg_monthly_sales", 0.001]}  # Prevent division by zero
                        ]
                    }
                }
            },
            {
                "$match": {
                    "$and": [
                        {"avg_closing_stock": {"$gt": 10}},  # High inventory
                        {"capital_blocked": {"$gt": 1000}},   # Significant capital
                        {"$or": [
                            {"inventory_turnover": {"$lt": 2}},  # Low turnover
                            {"days_to_sell": {"$gt": 180}}      # Takes more than 6 months to sell
                        ]}
                    ]
                }
            },
            {"$sort": {"capital_blocked": -1}},
            {"$limit": 50}
        ]
        
        results = await db.sales_records.aggregate(pipeline).to_list(None)
        
        # Calculate risk levels
        for item in results:
            capital_blocked = item['capital_blocked']
            days_to_sell = item['days_to_sell']
            
            if capital_blocked > 50000 and days_to_sell > 365:
                risk_level = "CRITICAL"
            elif capital_blocked > 10000 and days_to_sell > 180:
                risk_level = "HIGH"
            elif capital_blocked > 5000 and days_to_sell > 90:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
                
            item['risk_level'] = risk_level
        
        # Sort by risk level criticality: CRITICAL -> HIGH -> MEDIUM -> LOW
        risk_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        results.sort(key=lambda x: (risk_order.get(x['risk_level'], 999), -x['capital_blocked']))
        
        return {
            "capital_blocking_items": results,
            "summary": {
                "total_items_analyzed": len(results),
                "total_capital_blocked": sum(item['capital_blocked'] for item in results),
                "critical_items": len([item for item in results if item['risk_level'] == 'CRITICAL']),
                "high_risk_items": len([item for item in results if item['risk_level'] == 'HIGH'])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in capital blocking analysis: {str(e)}")

@api_router.get("/inventory-analysis")
async def get_inventory_analysis(period: Optional[str] = Query(None)):
    """Analyze inventory for slow moving and dead stock"""
    try:
        # Build match filter
        match_filter = {"upload_source": {"$ne": "forecast"}}
        if period and period != "all":
            if "Current Year" in period:
                year = period.split(" ")[0]
                match_filter["data_period"] = {
                    "$regex": f"({year}|{year[2:]})", 
                    "$options": "i"
                }
            else:
                match_filter["data_period"] = period
        
        # Get items with poor performance vs cost
        pipeline_high_cost = [
            {"$match": {**match_filter, "w_rate": {"$gt": 0}}},
            {
                "$group": {
                    "_id": {"pluno": "$pluno", "item_name": "$item_name"},
                    "avg_cost": {"$avg": "$w_rate"},
                    "total_sold": {"$sum": "$net_qty"},
                    "total_profit": {"$sum": "$profit"}
                }
            },
            {
                "$addFields": {
                    "performance_ratio": {
                        "$cond": {
                            "if": {"$gt": ["$avg_cost", 0]},
                            "then": {"$divide": ["$total_sold", "$avg_cost"]},
                            "else": 0
                        }
                    }
                }
            },
            {"$sort": {"avg_cost": -1, "performance_ratio": 1}},
            {"$limit": 20}
        ]
        
        # Dead inventory (no sales but has closing stock)
        pipeline_dead = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {"pluno": "$pluno", "item_name": "$item_name", "group": "$product_group"},
                    "total_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}},
                    "avg_closing_stock": {"$avg": {"$ifNull": ["$closing_stock", 0]}},
                    "avg_cost": {"$avg": {"$ifNull": ["$w_rate", 0]}},
                    "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}}
                }
            },
            {
                "$match": {
                    "$and": [
                        {"total_sold": {"$lte": 0}},
                        {"avg_closing_stock": {"$gt": 0}},
                        {"avg_cost": {"$gt": 0}}
                    ]
                }
            },
            {
                "$addFields": {
                    "capital_blocked": {"$multiply": ["$avg_closing_stock", "$avg_cost"]}
                }
            },
            {"$sort": {"capital_blocked": -1}},
            {"$limit": 20}
        ]
        
        # Slow moving (low sales)
        pipeline_slow = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": {"pluno": "$pluno", "item_name": "$item_name"},
                    "total_sold": {"$sum": "$net_qty"},
                    "avg_cost": {"$avg": "$w_rate"},
                    "periods_count": {"$sum": 1}
                }
            },
            {
                "$addFields": {
                    "avg_monthly_sales": {"$divide": ["$total_sold", "$periods_count"]}
                }
            },
            {"$match": {"avg_monthly_sales": {"$gt": 0, "$lt": 5}}},
            {"$sort": {"avg_monthly_sales": 1}},
            {"$limit": 20}
        ]
        
        high_cost_items = await db.sales_records.aggregate(pipeline_high_cost).to_list(None)
        dead_inventory = await db.sales_records.aggregate(pipeline_dead).to_list(None)
        slow_moving = await db.sales_records.aggregate(pipeline_slow).to_list(None)
        
        return {
            "high_cost_poor_performance": high_cost_items,
            "dead_inventory": dead_inventory,
            "slow_moving": slow_moving
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in inventory analysis: {str(e)}")

@api_router.get("/group-analysis")
async def get_group_analysis(period: Optional[str] = Query(None)):
    """Analyze performance by product groups"""
    try:
        # Build match filter
        match_filter = {"upload_source": {"$ne": "forecast"}}  # Exclude forecast data
        if period and period != "all":
            if "Current Year" in period:
                year = period.split(" ")[0]
                match_filter["data_period"] = {
                    "$regex": f"({year}|{year[2:]})", 
                    "$options": "i"
                }
            else:
                match_filter["data_period"] = period
            
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": "$product_group",
                    "total_revenue": {"$sum": {"$ifNull": ["$r_amt", 0]}},
                    "total_profit": {"$sum": {"$ifNull": ["$profit", 0]}},
                    "total_cost": {"$sum": {"$ifNull": ["$w_amt", 0]}},
                    "item_count": {"$sum": 1},
                    "items": {
                        "$push": {
                            "pluno": "$pluno",
                            "item_name": "$item_name",
                            "revenue": {"$ifNull": ["$r_amt", 0]},
                            "profit": {"$ifNull": ["$profit", 0]},
                            "qty": {"$ifNull": ["$net_qty", 0]}
                        }
                    }
                }
            },
            {
                "$addFields": {
                    "profit_margin": {
                        "$cond": {
                            "if": {"$gt": ["$total_revenue", 0]},
                            "then": {"$multiply": [{"$divide": ["$total_profit", "$total_revenue"]}, 100]},
                            "else": 0
                        }
                    }
                }
            },
            {"$match": {"_id": {"$ne": "Unknown"}}},
            {"$sort": {"total_revenue": -1}}
        ]
        
        results = await db.sales_records.aggregate(pipeline).to_list(None)
        
        group_analysis = []
        for group in results:
            # Get top 5 performers in this group
            # Filter out items with invalid revenue/profit values
            valid_items = [
                item for item in group['items']
                if isinstance(item.get('revenue'), (int, float)) and isinstance(item.get('profit'), (int, float))
            ]
            
            top_performers = sorted(
                valid_items, 
                key=lambda x: x.get('revenue', 0) or 0, 
                reverse=True
            )[:5]
            
            # Ensure values are properly converted to float
            total_revenue = float(group.get('total_revenue', 0) or 0)
            total_profit = float(group.get('total_profit', 0) or 0)
            profit_margin = float(group.get('profit_margin', 0) or 0)
            
            group_analysis.append({
                "group": group['_id'],
                "total_revenue": total_revenue,
                "total_profit": total_profit,
                "item_count": group['item_count'],
                "top_performers": top_performers,
                "profit_margin": profit_margin
            })
        
        return group_analysis
        
    except Exception as e:
        logger.exception("Error in group analysis")
        raise HTTPException(status_code=500, detail=f"Error in group analysis: {str(e)}")

@api_router.get("/comprehensive-report")
async def generate_comprehensive_report(
    format: str = Query("excel"),
    periods: Optional[str] = Query(None)  # Comma-separated list of periods
):
    """Generate comprehensive business analysis report using existing API calculations"""
    try:
        # Parse periods parameter
        period_list = []
        if periods:
            period_list = [p.strip() for p in periods.split(',') if p.strip()]
        
        # Determine period label for report title
        if not period_list or len(period_list) == 0:
            period_label = " - All Periods"
        elif len(period_list) == 1:
            period_label = f" - {period_list[0]}"
        elif len(period_list) == 2:
            period_label = f" - {period_list[0]} & {period_list[1]}"
        elif len(period_list) <= 5:
            period_label = f" - {', '.join(period_list)}"
        else:
            # Too many periods, show range or count
            period_label = f" - {period_list[0]} to {period_list[-1]} ({len(period_list)} periods)"
        
        # Build match filter based on selected periods
        match_filter = {"upload_source": {"$ne": "forecast"}}
        if period_list and len(period_list) > 0:
            match_filter["data_period"] = {"$in": period_list}
        
        # Aggregate dashboard summary data based on selected periods
        if period_list and len(period_list) > 0:
            # Calculate aggregated metrics for selected periods
            summary_pipeline = [
                {"$match": match_filter},
                {"$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$r_amt"},
                    "total_profit": {"$sum": "$profit"},
                    "total_items_sold": {"$sum": "$net_qty"},
                    "total_records": {"$sum": 1}
                }}
            ]
            summary_result = await db.sales_records.aggregate(summary_pipeline).to_list(None)
            
            if summary_result and len(summary_result) > 0:
                result = summary_result[0]
                dashboard_summary = {
                    "total_revenue": result.get("total_revenue", 0) or 0,
                    "total_profit": result.get("total_profit", 0) or 0,
                    "total_items_sold": result.get("total_items_sold", 0) or 0,
                    "total_records": result.get("total_records", 0) or 0,
                    "profit_margin": (result.get("total_profit", 0) / result.get("total_revenue", 1) * 100) if result.get("total_revenue", 0) > 0 else 0
                }
            else:
                dashboard_summary = {
                    "total_revenue": 0,
                    "total_profit": 0,
                    "total_items_sold": 0,
                    "total_records": 0,
                    "profit_margin": 0
                }
        else:
            # Get all data
            dashboard_summary = await get_dashboard_summary(period=None)
        
        # Get ABC analysis using existing endpoint - pass None directly for group and period
        abc_response = await get_abc_analysis(group=None, period=None)
        abc_analysis = abc_response if isinstance(abc_response, dict) else {}
        
        # Get capital blocking analysis using existing endpoint - pass None directly for group and period
        capital_response = await get_capital_blocking_analysis(group=None, period=None)
        capital_analysis = capital_response if isinstance(capital_response, dict) else {}
        
        # Get group analysis - pass None directly for period
        group_analysis = await get_group_analysis(period=None)
        
        # Get fastest selling items with period filter (match_filter already defined above)
        fastest_pipeline = [
            {"$match": match_filter},
            {"$group": {
                "_id": {"item_code": "$pluno", "item_name": "$item_name", "group": "$product_group"},
                "total_sold": {"$sum": "$net_qty"},
                "total_revenue": {"$sum": "$r_amt"},
                "total_profit": {"$sum": "$profit"}
            }},
            {"$sort": {"total_sold": -1}},
            {"$limit": 20}
        ]
        fastest_raw = await db.sales_records.aggregate(fastest_pipeline).to_list(None)
        
        # Calculate number of months in data with period filter
        date_pipeline = [
            {"$match": match_filter},
            {"$group": {"_id": "$data_period"}},
            {"$count": "total_months"}
        ]
        month_count_result = await db.sales_records.aggregate(date_pipeline).to_list(None)
        num_months = month_count_result[0]["total_months"] if month_count_result else 1
        
        fastest_items = [{
            "item_code": item["_id"].get("item_code", ""),
            "item_name": item["_id"].get("item_name", "Unknown"),
            "group": item["_id"].get("group", "N/A"),
            "total_sold": item.get("total_sold", 0),
            "total_revenue": item.get("total_revenue", 0),
            "total_profit": item.get("total_profit", 0),
            "avg_monthly_sales": item.get("total_sold", 0) / max(num_months, 1),
            "profit_margin": (item.get("total_profit", 0) / item.get("total_revenue", 1) * 100) if item.get("total_revenue", 0) > 0 else 0
        } for item in fastest_raw]
        
        # Get slowest selling items (capital blockers) with period filter
        slowest_match_filter = {**match_filter, "closing_stock": {"$gt": 0}}
        slowest_pipeline = [
            {"$match": slowest_match_filter},
            {"$group": {
                "_id": {"item_code": "$pluno", "item_name": "$item_name", "group": "$product_group"},
                "total_sold": {"$sum": "$net_qty"},
                "avg_closing_stock": {"$avg": "$closing_stock"},
                "capital_blocked": {"$sum": {"$multiply": ["$closing_stock", "$w_rate"]}}
            }},
            {"$sort": {"total_sold": 1}},
            {"$limit": 20}
        ]
        slowest_items = await db.sales_records.aggregate(slowest_pipeline).to_list(None)
        
        if format == "excel":
            # Create comprehensive Excel report
            workbook = openpyxl.Workbook()
            
            # Summary Sheet
            ws_summary = workbook.active
            ws_summary.title = "Executive Summary"
            
            ws_summary.append([f"URC 101 Area - Comprehensive Sales Analysis Report{period_label}"])
            ws_summary.append(["Generated on:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            ws_summary.append([""])
            ws_summary.append(["KEY METRICS"])
            ws_summary.append(["Total Revenue", format_indian_number(dashboard_summary['total_revenue'], currency=True)])
            ws_summary.append(["Total Profit", format_indian_number(dashboard_summary['total_profit'], currency=True)])
            ws_summary.append(["Profit Margin", f"{dashboard_summary['profit_margin']:.2f}%"])
            ws_summary.append(["Total Items Sold", f"{dashboard_summary['total_items_sold']:,}"])
            ws_summary.append(["Total Records", f"{dashboard_summary['total_records']:,}"])
            
            # ABC Analysis Sheet
            ws_abc = workbook.create_sheet("ABC Analysis")
            ws_abc.append(["Category", "Items", "% of Items", "Revenue", "% of Revenue", "Recommendation"])
            
            if abc_analysis and 'summary' in abc_analysis:
                summary = abc_analysis['summary']
                total_rev = summary.get('total_revenue', 0)
                
                categories_data = [
                    ('A', summary.get('category_A', {}), "FOCUS: Ensure consistent stock availability"),
                    ('B', summary.get('category_B', {}), "MONITOR: Balance stock levels carefully"),
                    ('C', summary.get('category_C', {}), "REVIEW: Consider reducing inventory or discontinuing")
                ]
                
                for cat_name, cat_data, recommendation in categories_data:
                    item_count = cat_data.get('item_count', 0)
                    revenue = cat_data.get('revenue', 0)
                    pct_items = cat_data.get('percentage_items', 0)
                    revenue_pct = (revenue/total_rev)*100 if total_rev > 0 else 0
                    
                    ws_abc.append([
                        f"Category {cat_name}",
                        item_count,
                        f"{pct_items:.1f}%",
                        format_indian_number(revenue, currency=True),
                        f"{revenue_pct:.1f}%",
                        recommendation
                    ])
            else:
                ws_abc.append(["No ABC analysis data available", "", "", "", "", ""])
            
            # Capital Blocking Sheet
            ws_capital = workbook.create_sheet("Capital Blocking")
            ws_capital.append(["Item Code", "Item Name", "Group", "Capital Blocked", "Risk Level", "Days to Sell"])
            for item in capital_analysis['capital_blocking_items'][:50]:
                ws_capital.append([
                    item.get('_id', {}).get('pluno', 'N/A'),
                    item.get('_id', {}).get('item_name', 'Unknown'),
                    item.get('_id', {}).get('group', 'N/A'),
                    format_indian_number(item.get('capital_blocked', 0), currency=True),
                    item.get('risk_level', 'N/A'),
                    item.get('days_to_sell', 'N/A') if item.get('days_to_sell', 'N/A') != 9999 else "∞"
                ])
            
            # Group Performance Sheet
            ws_groups = workbook.create_sheet("Group Performance")
            ws_groups.append(["Group", "Items", "Revenue", "Profit", "Margin %"])
            for group in group_analysis:
                ws_groups.append([
                    group['group'],
                    group['item_count'],
                    format_indian_number(group['total_revenue'], currency=True),
                    format_indian_number(group['total_profit'], currency=True),
                    f"{group['profit_margin']:.2f}%"
                ])
            
            # Top Performers Sheet with actionable insights
            ws_top = workbook.create_sheet("Top Performers")
            ws_top.append(["Rank", "Item Code", "Item Name", "Group", "Units Sold", "Revenue", "Profit", "Margin %", "Monthly Avg", "Stock Status"])
            for i, item in enumerate(fastest_items, 1):
                # Determine stock recommendation
                monthly_avg = item['avg_monthly_sales']
                if monthly_avg > 100:
                    stock_status = "HIGH PRIORITY: Maintain 20+ days stock"
                elif monthly_avg > 50:
                    stock_status = "IMPORTANT: Maintain 15 days stock"
                else:
                    stock_status = "MONITOR: Maintain 10 days stock"
                
                ws_top.append([
                    i,
                    item['item_code'],
                    item['item_name'],
                    item['group'],
                    f"{item['total_sold']:,.0f}",
                    format_indian_number(item['total_revenue'], currency=True),
                    format_indian_number(item['total_profit'], currency=True),
                    f"{item['profit_margin']:.2f}%",
                    f"{monthly_avg:.1f}",
                    stock_status
                ])
            
            # Add Slow Movers Sheet for liquidation planning
            ws_slow = workbook.create_sheet("Items to Liquidate")
            ws_slow.append(["Rank", "Item Code", "Item Name", "Group", "Units Sold (Total)", "Avg Stock", "Capital Blocked", "Action Required"])
            for i, item in enumerate(slowest_items, 1):
                capital_blocked = item.get('capital_blocked', 0)
                action = "URGENT: Discount & Clear" if capital_blocked > 10000 else "Plan Clearance Sale"
                
                ws_slow.append([
                    i,
                    item['_id'].get('item_code', 'N/A'),
                    item['_id'].get('item_name', 'Unknown'),
                    item['_id'].get('group', 'N/A'),
                    f"{item.get('total_sold', 0):,.0f}",
                    f"{item.get('avg_closing_stock', 0):.1f}",
                    format_indian_number(capital_blocked, currency=True),
                    action
                ])
            
            # Smart Recommendations Sheet
            ws_rec = workbook.create_sheet("Smart Recommendations")
            ws_rec.append(["STRATEGIC INVENTORY & PROCUREMENT RECOMMENDATIONS"])
            ws_rec.append(["Generated on:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            ws_rec.append([""])
            
            # 1. IMMEDIATE ACTIONS (Capital Optimization)
            ws_rec.append(["1. IMMEDIATE ACTIONS - CAPITAL OPTIMIZATION"])
            ws_rec.append([""])
            if capital_analysis and 'summary' in capital_analysis:
                critical_count = capital_analysis['summary'].get('critical_items', 0)
                total_blocked = capital_analysis['summary'].get('total_capital_blocked', 0)
                ws_rec.append([f"⚠️ URGENT: {critical_count} items blocking excessive capital"])
                ws_rec.append([f"   Total Capital Blocked: {format_indian_number(total_blocked, currency=True)}"])
                ws_rec.append([""])
                ws_rec.append(["   ACTION PLAN:"])
                ws_rec.append(["   • Offer discounts (10-15%) on slow-moving high-value items"])
                ws_rec.append(["   • Create combo offers with fast-moving items"])
                ws_rec.append(["   • Stop new procurement for these items until stock reduces by 70%"])
                ws_rec.append(["   • Potential capital recovery: {}".format(format_indian_number(total_blocked * 0.7, currency=True))])
            ws_rec.append([""])
            
            # 2. PROCUREMENT STRATEGY (ABC-based)
            ws_rec.append(["2. SMART PROCUREMENT STRATEGY (Next 3 Months)"])
            ws_rec.append([""])
            if abc_analysis and 'summary' in abc_analysis:
                cat_a = abc_analysis['summary'].get('category_A', {})
                cat_b = abc_analysis['summary'].get('category_B', {})
                cat_c = abc_analysis['summary'].get('category_C', {})
                
                ws_rec.append([f"📈 CATEGORY A ({cat_a.get('item_count', 0)} items - {cat_a.get('percentage_items', 0):.1f}% of inventory)"])
                ws_rec.append([f"   Current Revenue Contribution: {format_indian_number(cat_a.get('revenue', 0), currency=True)} (80% of total)"])
                ws_rec.append(["   PROCUREMENT ACTION:"])
                ws_rec.append(["   • Maintain 15-20 days of safety stock at all times"])
                ws_rec.append(["   • Weekly monitoring and procurement trigger"])
                ws_rec.append(["   • Negotiate better rates due to high volume"])
                ws_rec.append(["   • Expected profit increase: 2-3% through better pricing"])
                ws_rec.append([""])
                
                ws_rec.append([f"📊 CATEGORY B ({cat_b.get('item_count', 0)} items - {cat_b.get('percentage_items', 0):.1f}% of inventory)"])
                ws_rec.append([f"   Current Revenue Contribution: {format_indian_number(cat_b.get('revenue', 0), currency=True)}"])
                ws_rec.append(["   PROCUREMENT ACTION:"])
                ws_rec.append(["   • Maintain 10-12 days of stock"])
                ws_rec.append(["   • Bi-weekly review and procurement"])
                ws_rec.append(["   • Monitor for potential upgrade to Category A"])
                ws_rec.append([""])
                
                ws_rec.append([f"📉 CATEGORY C ({cat_c.get('item_count', 0)} items - {cat_c.get('percentage_items', 0):.1f}% of inventory)"])
                ws_rec.append([f"   Current Revenue Contribution: {format_indian_number(cat_c.get('revenue', 0), currency=True)} (only 5% of total)"])
                ws_rec.append(["   PROCUREMENT ACTION:"])
                ws_rec.append(["   • REDUCE to 5-7 days stock or minimum order quantity"])
                ws_rec.append(["   • Consider discontinuing bottom 50% of items"])
                ws_rec.append(["   • Free up capital for Category A items"])
                ws_rec.append([f"   • Potential capital saving: {format_indian_number(cat_c.get('revenue', 0) * 0.3, currency=True)}"])
            ws_rec.append([""])
            
            # 3. GROUP-WISE STRATEGY
            ws_rec.append(["3. PRODUCT GROUP OPTIMIZATION"])
            ws_rec.append([""])
            if group_analysis and len(group_analysis) > 0:
                # Sort by profit margin
                sorted_groups = sorted(group_analysis, key=lambda x: x.get('profit_margin', 0), reverse=True)
                top_margin_group = sorted_groups[0] if sorted_groups else None
                top_revenue_group = max(group_analysis, key=lambda x: x.get('total_revenue', 0))
                
                if top_revenue_group:
                    ws_rec.append([f"💰 TOP REVENUE GROUP: {top_revenue_group['group']}"])
                    ws_rec.append([f"   Revenue: {format_indian_number(top_revenue_group['total_revenue'], currency=True)}"])
                    ws_rec.append([f"   Profit: {format_indian_number(top_revenue_group['total_profit'], currency=True)} ({top_revenue_group['profit_margin']:.2f}%)"])
                    ws_rec.append(["   STRATEGY: Expand product range, secure better supplier terms"])
                    ws_rec.append([""])
                
                if top_margin_group and top_margin_group != top_revenue_group:
                    ws_rec.append([f"⭐ HIGHEST MARGIN GROUP: {top_margin_group['group']}"])
                    ws_rec.append([f"   Margin: {top_margin_group['profit_margin']:.2f}%"])
                    ws_rec.append([f"   Revenue: {format_indian_number(top_margin_group['total_revenue'], currency=True)}"])
                    ws_rec.append(["   STRATEGY: Increase visibility and promotional efforts"])
                    ws_rec.append([""])
            
            # 4. PROFITABILITY BOOST
            ws_rec.append(["4. PROFIT MAXIMIZATION PLAN"])
            ws_rec.append([""])
            current_profit = dashboard_summary.get('total_profit', 0)
            current_margin = dashboard_summary.get('profit_margin', 0)
            
            ws_rec.append([f"Current Profit: {format_indian_number(current_profit, currency=True)} ({current_margin:.2f}%)"])
            ws_rec.append([""])
            ws_rec.append(["ACTIONS TO INCREASE PROFIT BY 15-20%:"])
            ws_rec.append([""])
            ws_rec.append(["✓ REDUCE CAPITAL BLOCKING (3-5% profit boost)"])
            ws_rec.append(["  • Liquidate slow-moving inventory"])
            ws_rec.append(["  • Redeploy capital to high-margin items"])
            ws_rec.append([f"  • Estimated additional profit: {format_indian_number(current_profit * 0.04, currency=True)}"])
            ws_rec.append([""])
            ws_rec.append(["✓ FOCUS ON CATEGORY A (5-7% profit boost)"])
            ws_rec.append(["  • Never run out of stock on top performers"])
            ws_rec.append(["  • Negotiate volume discounts (0.5-1% cost reduction)"])
            ws_rec.append([f"  • Estimated additional profit: {format_indian_number(current_profit * 0.06, currency=True)}"])
            ws_rec.append([""])
            ws_rec.append(["✓ OPTIMIZE CATEGORY C (2-3% profit boost)"])
            ws_rec.append(["  • Reduce 50% of Category C inventory"])
            ws_rec.append(["  • Eliminate holding costs and wastage"])
            ws_rec.append([f"  • Estimated additional profit: {format_indian_number(current_profit * 0.025, currency=True)}"])
            ws_rec.append([""])
            ws_rec.append(["✓ IMPROVE HIGH-MARGIN GROUPS (3-5% profit boost)"])
            ws_rec.append(["  • Increase stock and visibility of high-margin items"])
            ws_rec.append(["  • Better merchandising and placement"])
            ws_rec.append([f"  • Estimated additional profit: {format_indian_number(current_profit * 0.04, currency=True)}"])
            ws_rec.append([""])
            total_potential = current_profit * 0.18
            ws_rec.append([f"🎯 TOTAL POTENTIAL PROFIT INCREASE: {format_indian_number(total_potential, currency=True)}"])
            ws_rec.append([f"   New Projected Profit: {format_indian_number(current_profit + total_potential, currency=True)}"])
            ws_rec.append([f"   New Projected Margin: {((current_profit + total_potential) / dashboard_summary.get('total_revenue', 1) * 100):.2f}%"])
            
            # Save to temporary file for better download handling
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            workbook.save(temp_file.name)
            temp_file.close()
            
            return FileResponse(
                temp_file.name,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": "attachment; filename=URC101-Comprehensive-Analysis-Report.xlsx"},
                filename="URC101-Comprehensive-Analysis-Report.xlsx"
            )
            
        elif format == "pdf":
            # Create comprehensive HTML content matching Excel report
            
            # Prepare data safely
            abc_summary = abc_analysis.get('summary', {}) if abc_analysis else {}
            cat_a = abc_summary.get('category_A', {'item_count': 0, 'revenue': 0, 'percentage_items': 0})
            cat_b = abc_summary.get('category_B', {'item_count': 0, 'revenue': 0, 'percentage_items': 0})
            cat_c = abc_summary.get('category_C', {'item_count': 0, 'revenue': 0, 'percentage_items': 0})
            
            capital_summary = capital_analysis.get('summary', {}) if capital_analysis else {}
            critical_items = capital_summary.get('critical_items', 0)
            total_blocked = capital_summary.get('total_capital_blocked', 0)
            
            current_profit = dashboard_summary.get('total_profit', 0)
            current_revenue = dashboard_summary.get('total_revenue', 1)
            current_margin = dashboard_summary.get('profit_margin', 0)
            
            # Build Top Performers HTML
            top_performers_html = ""
            for i, item in enumerate(fastest_items[:10], 1):
                top_performers_html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{item['item_code']}</td>
                    <td>{item['item_name']}</td>
                    <td>{item['group']}</td>
                    <td>{item['total_sold']:,.0f}</td>
                    <td>{format_indian_number(item['total_revenue'], currency=True, use_rs_prefix=True)}</td>
                    <td>{format_indian_number(item['total_profit'], currency=True, use_rs_prefix=True)}</td>
                    <td>{item['profit_margin']:.2f}%</td>
                </tr>
                """
            
            # Build Group Performance HTML
            group_html = ""
            for group in group_analysis[:10]:
                group_html += f"""
                <tr>
                    <td>{group['group']}</td>
                    <td>{group['item_count']}</td>
                    <td>{format_indian_number(group['total_revenue'], currency=True, use_rs_prefix=True)}</td>
                    <td>{format_indian_number(group['total_profit'], currency=True, use_rs_prefix=True)}</td>
                    <td>{group['profit_margin']:.2f}%</td>
                </tr>
                """
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>URC 101 Area - Comprehensive Sales Analysis Report{period_label}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                    .header {{ text-align: center; margin-bottom: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
                    .section {{ margin-bottom: 30px; page-break-inside: avoid; }}
                    .section-title {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 10px; margin-bottom: 20px; }}
                    .table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; font-size: 13px; }}
                    .table th, .table td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                    .table th {{ background-color: #667eea; color: white; font-weight: bold; }}
                    .table tr:nth-child(even) {{ background-color: #f8f9fa; }}
                    .metric {{ background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                    .recommendation {{ background-color: #fff3cd; padding: 12px; margin: 8px 0; border-left: 4px solid #ffc107; border-radius: 5px; }}
                    .urgent {{ background-color: #f8d7da; border-left-color: #dc3545; }}
                    .success {{ background-color: #d4edda; border-left-color: #28a745; }}
                    .info {{ background-color: #d1ecf1; border-left-color: #17a2b8; }}
                    ul {{ list-style-type: none; padding-left: 0; }}
                    li {{ padding: 8px 0; padding-left: 25px; position: relative; }}
                    li:before {{ content: "►"; position: absolute; left: 0; color: #667eea; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏪 URC 101 Area - Comprehensive Sales Analysis Report{period_label}</h1>
                    <p style="margin: 5px 0;">Generated on: {datetime.now().strftime("%d %B %Y, %H:%M:%S")}</p>
                    <p style="margin: 5px 0; font-size: 14px;">Strategic Inventory & Procurement Intelligence</p>
                </div>
                
                <!-- EXECUTIVE SUMMARY -->
                <div class="section">
                    <h2 class="section-title">📊 Executive Summary</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="metric">
                            <div>Total Revenue</div>
                            <div class="metric-value">{format_indian_number(dashboard_summary.get('total_revenue', 0), currency=True, use_rs_prefix=True)}</div>
                        </div>
                        <div class="metric">
                            <div>Total Profit</div>
                            <div class="metric-value">{format_indian_number(current_profit, currency=True, use_rs_prefix=True)}</div>
                        </div>
                        <div class="metric">
                            <div>Profit Margin</div>
                            <div class="metric-value">{current_margin:.2f}%</div>
                        </div>
                        <div class="metric">
                            <div>Items Sold</div>
                            <div class="metric-value">{dashboard_summary.get('total_items_sold', 0):,}</div>
                        </div>
                    </div>
                </div>
                
                <!-- ABC ANALYSIS -->
                <div class="section">
                    <h2 class="section-title">📈 ABC Analysis - Inventory Classification</h2>
                    <table class="table">
                        <tr>
                            <th>Category</th>
                            <th>Items</th>
                            <th>% of Items</th>
                            <th>Revenue</th>
                            <th>% of Revenue</th>
                            <th>Strategy</th>
                        </tr>
                        <tr style="background-color: #d4edda;">
                            <td><strong>Category A (High Value)</strong></td>
                            <td>{cat_a.get('item_count', 0)}</td>
                            <td>{cat_a.get('percentage_items', 0):.1f}%</td>
                            <td>{format_indian_number(cat_a.get('revenue', 0), currency=True, use_rs_prefix=True)}</td>
                            <td>~80%</td>
                            <td>FOCUS: Ensure consistent stock</td>
                        </tr>
                        <tr style="background-color: #fff3cd;">
                            <td><strong>Category B (Medium Value)</strong></td>
                            <td>{cat_b.get('item_count', 0)}</td>
                            <td>{cat_b.get('percentage_items', 0):.1f}%</td>
                            <td>{format_indian_number(cat_b.get('revenue', 0), currency=True, use_rs_prefix=True)}</td>
                            <td>~15%</td>
                            <td>MONITOR: Balance stock levels</td>
                        </tr>
                        <tr style="background-color: #f8d7da;">
                            <td><strong>Category C (Low Value)</strong></td>
                            <td>{cat_c.get('item_count', 0)}</td>
                            <td>{cat_c.get('percentage_items', 0):.1f}%</td>
                            <td>{format_indian_number(cat_c.get('revenue', 0), currency=True, use_rs_prefix=True)}</td>
                            <td>~5%</td>
                            <td>REVIEW: Reduce or discontinue</td>
                        </tr>
                    </table>
                </div>
                
                <!-- TOP PERFORMERS -->
                <div class="section">
                    <h2 class="section-title">⭐ Top 10 Performing Items</h2>
                    <table class="table">
                        <tr>
                            <th>#</th>
                            <th>Item Code</th>
                            <th>Item Name</th>
                            <th>Group</th>
                            <th>Units Sold</th>
                            <th>Revenue</th>
                            <th>Profit</th>
                            <th>Margin %</th>
                        </tr>
                        {top_performers_html}
                    </table>
                </div>
                
                <!-- GROUP PERFORMANCE -->
                <div class="section">
                    <h2 class="section-title">🏷️ Product Group Performance</h2>
                    <table class="table">
                        <tr>
                            <th>Group</th>
                            <th>Items</th>
                            <th>Revenue</th>
                            <th>Profit</th>
                            <th>Margin %</th>
                        </tr>
                        {group_html}
                    </table>
                </div>
                
                <!-- SMART RECOMMENDATIONS -->
                <div class="section">
                    <h2 class="section-title">💡 Strategic Recommendations & Action Plan</h2>
                    
                    <h3 style="color: #dc3545; margin-top: 20px;">⚠️ 1. IMMEDIATE ACTIONS - Capital Optimization</h3>
                    <div class="recommendation urgent">
                        <strong>URGENT:</strong> {critical_items} items blocking excessive capital<br>
                        <strong>Total Capital Blocked:</strong> {format_indian_number(total_blocked, currency=True, use_rs_prefix=True)}<br>
                        <strong>Potential Recovery:</strong> {format_indian_number(total_blocked * 0.7, currency=True, use_rs_prefix=True)}
                    </div>
                    <div class="recommendation">
                        <strong>ACTION PLAN:</strong>
                        <ul>
                            <li>Offer 10-15% discounts on slow-moving high-value items</li>
                            <li>Create combo offers with fast-moving products</li>
                            <li>Stop new procurement until stock reduces by 70%</li>
                        </ul>
                    </div>
                    
                    <h3 style="color: #28a745; margin-top: 20px;">📈 2. PROCUREMENT STRATEGY (Next 3 Months)</h3>
                    
                    <div class="recommendation success">
                        <strong>CATEGORY A ({cat_a.get('item_count', 0)} items):</strong><br>
                        Revenue Contribution: {format_indian_number(cat_a.get('revenue', 0), currency=True, use_rs_prefix=True)} (80% of total)<br>
                        <strong>Actions:</strong>
                        <ul>
                            <li>Maintain 15-20 days safety stock</li>
                            <li>Weekly monitoring and procurement</li>
                            <li>Negotiate volume discounts (2-3% cost reduction possible)</li>
                            <li>Expected profit increase: 2-3%</li>
                        </ul>
                    </div>
                    
                    <div class="recommendation info">
                        <strong>CATEGORY B ({cat_b.get('item_count', 0)} items):</strong><br>
                        Revenue Contribution: {format_indian_number(cat_b.get('revenue', 0), currency=True, use_rs_prefix=True)}<br>
                        <strong>Actions:</strong>
                        <ul>
                            <li>Maintain 10-12 days stock</li>
                            <li>Bi-weekly review and procurement</li>
                            <li>Monitor for upgrade to Category A potential</li>
                        </ul>
                    </div>
                    
                    <div class="recommendation urgent">
                        <strong>CATEGORY C ({cat_c.get('item_count', 0)} items):</strong><br>
                        Revenue Contribution: {format_indian_number(cat_c.get('revenue', 0), currency=True, use_rs_prefix=True)} (only 5% of total)<br>
                        <strong>Actions:</strong>
                        <ul>
                            <li>REDUCE to 5-7 days stock or minimum order quantity</li>
                            <li>Consider discontinuing bottom 50% items</li>
                            <li>Free up capital for Category A expansion</li>
                            <li>Potential capital saving: {format_indian_number(cat_c.get('revenue', 0) * 0.3, currency=True, use_rs_prefix=True)}</li>
                        </ul>
                    </div>
                    
                    <h3 style="color: #667eea; margin-top: 20px;">🎯 3. PROFIT MAXIMIZATION PLAN</h3>
                    <div class="recommendation" style="background-color: #e7f3ff; border-left-color: #667eea;">
                        <strong>Current Performance:</strong><br>
                        Profit: {format_indian_number(current_profit, currency=True, use_rs_prefix=True)} | Margin: {current_margin:.2f}%
                        <br><br>
                        <strong>PROJECTED PROFIT INCREASE: 15-20%</strong>
                        <ul>
                            <li><strong>Reduce Capital Blocking (3-5% boost):</strong> Liquidate slow movers → Est. {format_indian_number(current_profit * 0.04, currency=True, use_rs_prefix=True)}</li>
                            <li><strong>Focus on Category A (5-7% boost):</strong> Never stock out, volume discounts → Est. {format_indian_number(current_profit * 0.06, currency=True, use_rs_prefix=True)}</li>
                            <li><strong>Optimize Category C (2-3% boost):</strong> Reduce inventory, cut holding costs → Est. {format_indian_number(current_profit * 0.025, currency=True, use_rs_prefix=True)}</li>
                            <li><strong>High-Margin Groups (3-5% boost):</strong> Better merchandising → Est. {format_indian_number(current_profit * 0.04, currency=True, use_rs_prefix=True)}</li>
                        </ul>
                        <br>
                        <div style="background-color: #28a745; color: white; padding: 15px; border-radius: 5px; text-align: center; margin-top: 15px;">
                            <strong style="font-size: 18px;">🎯 TOTAL POTENTIAL PROFIT INCREASE</strong><br>
                            <span style="font-size: 28px; font-weight: bold;">{format_indian_number(current_profit * 0.18, currency=True, use_rs_prefix=True)}</span><br>
                            <span style="font-size: 14px;">New Projected Profit: {format_indian_number(current_profit * 1.18, currency=True, use_rs_prefix=True)} | New Margin: {((current_profit * 1.18) / current_revenue * 100):.2f}%</span>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 40px; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
                    <p style="color: #667eea; font-size: 14px; margin: 5px 0;"><strong>Report Generated by URC 101 Analytics System</strong></p>
                    <p style="color: #6c757d; font-size: 12px; margin: 5px 0;">For queries, contact your system administrator</p>
                </div>
            </body>
            </html>
            """
            
            # Save HTML to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            return FileResponse(
                temp_file.name,
                media_type='text/html',
                headers={"Content-Disposition": "attachment; filename=URC101-Comprehensive-Analysis-Report.html"},
                filename="URC101-Comprehensive-Analysis-Report.html"
            )
        else:
            # Default to Excel
            return {"message": "Invalid format. Use 'excel' or 'pdf'."}
            
    except Exception as e:
        import traceback
        logger.error(f"Error generating comprehensive report: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

@api_router.get("/available-periods")
async def get_available_periods():
    """Get list of available periods from uploaded data with formatted display names"""
    try:
        # Get unique periods from sales_records, excluding forecast data
        pipeline = [
            {"$match": {"upload_source": {"$ne": "forecast"}, "data_period": {"$exists": True, "$ne": None}}},
            {"$group": {"_id": "$data_period"}},
            {"$sort": {"_id": -1}}  # Sort in descending order (most recent first)
        ]
        
        result = await db.sales_records.aggregate(pipeline).to_list(None)
        raw_periods = [item["_id"] for item in result if item.get("_id")]
        
        # Format period names for display
        periods_with_display = []
        for period in raw_periods:
            display_name = await format_period_display_name(period)
            periods_with_display.append({
                "value": period,  # Original value for filtering
                "label": display_name  # Formatted name for display
            })
        
        return {
            "available_periods": [p["label"] for p in periods_with_display],  # For backward compatibility
            "periods_detailed": periods_with_display,  # New format with value and label
            "count": len(periods_with_display)
        }
    except Exception as e:
        logger.error(f"Error fetching available periods: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching available periods: {str(e)}")

@api_router.get("/export-data/{analysis_type}")
async def export_data_to_excel(analysis_type: str, group: Optional[str] = Query(None)):
    """Export analysis data to Excel file"""
    try:
        # Create a new workbook
        workbook = openpyxl.Workbook()
        ws = workbook.active
        
        if analysis_type == "abc":
            # Get ABC analysis data
            response = await get_abc_analysis(group)
            ws.title = "ABC Analysis"
            
            # Headers
            headers = ["Item Code", "Item Name", "Group", "Category", "Revenue", "Revenue %", "Qty Sold", "Profit", "Capital Blocked"]
            ws.append(headers)
            
            # Add data from all categories
            for category_name, items in response["abc_categories"].items():
                for item in items:
                    ws.append([
                        item["pluno"],
                        item["item_name"],
                        item["group"],
                        f"Category {category_name}",
                        item["total_revenue"],
                        f"{item['revenue_percentage']:.2f}%",
                        item["total_qty_sold"],
                        item["total_profit"],
                        item["capital_blocked"]
                    ])
                    
        elif analysis_type == "capital-blocking":
            # Get capital blocking data
            response = await get_capital_blocking_analysis(group)
            ws.title = "Capital Blocking Analysis"
            
            headers = ["Item Code", "Item Name", "Group", "Capital Blocked", "Days to Sell", "Monthly Sales", "Risk Level", "Recommendation"]
            ws.append(headers)
            
            for item in response["capital_blocking_items"]:
                recommendation = "Liquidate" if item["risk_level"] == "CRITICAL" else \
                               "Discount" if item["risk_level"] == "HIGH" else "Monitor"
                ws.append([
                    item["_id"]["pluno"],
                    item["_id"]["item_name"],
                    item["_id"]["group"],
                    item["capital_blocked"],
                    item["days_to_sell"] if item["days_to_sell"] != 9999 else "∞",
                    item["avg_monthly_sales"],
                    item["risk_level"],
                    recommendation
                ])
                
        elif analysis_type == "fastest-selling":
            # Get fastest selling items
            fastest_items = await get_fastest_selling_items(50)
            ws.title = "Fastest Selling Items"
            
            headers = ["Item Code", "Item Name", "Group", "Total Sold", "Avg Monthly Sales", "Total Revenue", "Rank"]
            ws.append(headers)
            
            for i, item in enumerate(fastest_items, 1):
                ws.append([
                    item["item_code"],
                    item["item_name"],
                    item["group"],
                    item["total_sold"],
                    item["avg_monthly_sales"],
                    item["total_revenue"],
                    i
                ])
                
        elif analysis_type == "group-analysis":
            # Get group analysis
            response = await get_group_analysis()
            ws.title = "Group Performance Analysis"
            
            headers = ["Group", "Items Count", "Total Revenue", "Total Profit", "Profit Margin %", "Top Performer"]
            ws.append(headers)
            
            for group in response:
                top_performer = group["top_performers"][0]["item_name"] if group["top_performers"] else "N/A"
                ws.append([
                    group["group"],
                    group["item_count"],
                    group["total_revenue"],
                    group["total_profit"],
                    f"{group['profit_margin']:.2f}%",
                    top_performer
                ])
                
        elif analysis_type == "inventory-health":
            # Get inventory analysis
            response = await get_inventory_analysis()
            ws.title = "Inventory Health Analysis"
            
            # Dead Inventory Sheet
            headers = ["Type", "Item Code", "Item Name", "Group", "Capital Blocked", "Closing Stock", "Avg Cost"]
            ws.append(headers)
            
            for item in response.get("dead_inventory", []):
                ws.append([
                    "Dead Inventory",
                    item["_id"]["pluno"] if "pluno" in item["_id"] else "N/A",
                    item["_id"]["item_name"] if "item_name" in item["_id"] else "N/A",
                    item["_id"].get("group", "N/A"),
                    item.get("capital_blocked", 0),
                    item.get("avg_closing_stock", 0),
                    item.get("avg_cost", 0)
                ])
            
            for item in response.get("slow_moving", []):
                ws.append([
                    "Slow Moving",
                    item["_id"]["pluno"] if "pluno" in item["_id"] else "N/A",
                    item["_id"]["item_name"] if "item_name" in item["_id"] else "N/A",
                    "N/A",  # Group not available in slow moving
                    0,  # Capital blocked calculation needed
                    0,  # Closing stock not available
                    item.get("avg_cost", 0)
                ])
            
            for item in response.get("high_cost_poor_performance", []):
                ws.append([
                    "High Cost Poor Performance",
                    item["_id"]["pluno"] if "pluno" in item["_id"] else "N/A",
                    item["_id"]["item_name"] if "item_name" in item["_id"] else "N/A",
                    "N/A",  # Group not available
                    0,  # Capital blocked calculation needed
                    0,  # Closing stock not available
                    item.get("avg_cost", 0)
                ])
                
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis type")
            
        # Save to BytesIO
        excel_buffer = io.BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)
        
        # Create filename
        filename = f"{analysis_type}-analysis-{group if group else 'all'}.xlsx"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")

@api_router.get("/forecast-requirements")
async def get_forecast_requirements():
    """Get data requirements for accurate demand forecasting"""
    try:
        # Check available data periods
        periods = await db.sales_records.distinct("data_period")
        
        # Check if we have enough historical data
        total_records = await db.sales_records.count_documents({})
        
        # Get sample items to show what data we need
        sample_items = await db.sales_records.find(
            {"net_qty": {"$gt": 0}}, 
            {"item_name": 1, "pluno": 1, "product_group": 1}
        ).limit(10).to_list(None)
        
        requirements = {
            "current_data_status": {
                "available_periods": periods,
                "total_records": total_records,
                "sample_items": len(sample_items)
            },
            "required_for_basic_forecast": {
                "minimum_periods": 2,
                "recommended_periods": 3,
                "description": "Need last 3 months sales data for reliable trend analysis"
            },
            "required_for_seasonal_forecast": {
                "minimum_periods": 12,
                "recommended_periods": 24,
                "description": "Need 12-24 months of monthly data for seasonal pattern recognition"
            },
            "required_for_yearly_comparison": {
                "years_needed": ["2022", "2023", "2024"],
                "description": "Upload year-over-year data for the same months to fine-tune forecasts"
            },
            "data_upload_instructions": {
                "format": "Excel files with same column structure",
                "naming_convention": "Month_Year (e.g., Jan_2024, Feb_2024) or Year (e.g., 2023, 2022)",
                "required_columns": ["GP_Index_No", "Item_Name", "Net_Qty", "R_Amt", "Profit", "Closing_Stock"]
            },
            "forecast_accuracy_levels": {
                "basic_trend": {
                    "data_needed": "2-3 months",
                    "accuracy": "70-75%",
                    "best_for": "Short-term planning"
                },
                "statistical_seasonal": {
                    "data_needed": "6-12 months",
                    "accuracy": "80-85%",
                    "best_for": "Medium-term planning with seasonal adjustments"
                },
                "advanced_yearly": {
                    "data_needed": "2-3 years of same period data",
                    "accuracy": "85-90%",
                    "best_for": "Long-term strategic planning"
                }
            }
        }
        
        return requirements
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting forecast requirements: {str(e)}")

@api_router.post("/forecast-demand")
async def forecast_demand(request: ForecastRequest):
    """Forecast demand using different methods"""
    try:
        if request.method == "trend":
            return await simple_trend_forecast(request)
        elif request.method == "statistical":
            return await statistical_forecast(request)
        elif request.method == "ai":
            return await ai_forecast(request)
        else:
            raise HTTPException(status_code=400, detail="Invalid forecast method")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in demand forecasting: {str(e)}")

async def simple_trend_forecast(request: ForecastRequest):
    """Simple linear trend forecasting"""
    # Get historical data with product group
    pipeline = [
        {
            "$group": {
                "_id": {
                    "pluno": "$pluno", 
                    "item_name": "$item_name", 
                    "product_group": "$product_group",
                    "period": "$data_period"
                },
                "total_sold": {"$sum": "$net_qty"}
            }
        },
        {"$sort": {"_id.pluno": 1, "_id.period": 1}}
    ]
    
    historical_data = await db.sales_records.aggregate(pipeline).to_list(None)
    
    # Group by item and calculate trend
    forecasts = {}
    items_data = defaultdict(list)
    items_metadata = {}  # Store pluno, item_name, product_group
    
    for record in historical_data:
        item_key = record['_id']['pluno']
        items_data[item_key].append(record['total_sold'])
        
        # Store metadata (only once per item)
        if item_key not in items_metadata:
            items_metadata[item_key] = {
                "pluno": record['_id']['pluno'],
                "item_name": record['_id']['item_name'],
                "product_group": record['_id'].get('product_group') or extract_group_from_pluno(record['_id']['pluno'])
            }
    
    for item_key, sales_data in items_data.items():
        if len(sales_data) >= 2:
            # Simple linear regression
            X = np.array(range(len(sales_data))).reshape(-1, 1)
            y = np.array(sales_data)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Forecast next periods
            future_periods = range(len(sales_data), len(sales_data) + request.forecast_months)
            future_X = np.array(list(future_periods)).reshape(-1, 1)
            forecast = model.predict(future_X)
            
            metadata = items_metadata[item_key]
            forecasts[item_key] = {
                "pluno": metadata["pluno"],
                "item_name": metadata["item_name"],
                "product_group": metadata["product_group"],
                "method": "trend",
                "historical_sales": sales_data,
                "forecasted_sales": [max(0, int(f)) for f in forecast],
                "trend_direction": "increasing" if model.coef_[0] > 0 else "decreasing"
            }
    
    return {"forecasts": list(forecasts.values())}

async def statistical_forecast(request: ForecastRequest):
    """Statistical forecasting using moving averages"""
    pipeline = [
        {
            "$group": {
                "_id": {
                    "pluno": "$pluno", 
                    "item_name": "$item_name",
                    "product_group": "$product_group",
                    "period": "$data_period"
                },
                "total_sold": {"$sum": "$net_qty"}
            }
        },
        {"$sort": {"_id.pluno": 1, "_id.period": 1}}
    ]
    
    historical_data = await db.sales_records.aggregate(pipeline).to_list(None)
    
    forecasts = {}
    items_data = defaultdict(list)
    items_metadata = {}  # Store pluno, item_name, product_group
    
    for record in historical_data:
        item_key = record['_id']['pluno']
        items_data[item_key].append(record['total_sold'])
        
        # Store metadata (only once per item)
        if item_key not in items_metadata:
            items_metadata[item_key] = {
                "pluno": record['_id']['pluno'],
                "item_name": record['_id']['item_name'],
                "product_group": record['_id'].get('product_group') or extract_group_from_pluno(record['_id']['pluno'])
            }
    
    for item_key, sales_data in items_data.items():
        if len(sales_data) >= 3:
            # Moving average forecast
            window_size = min(3, len(sales_data))
            recent_avg = np.mean(sales_data[-window_size:])
            
            # Simple seasonal adjustment (if we have enough data)
            seasonal_factor = 1.0
            if len(sales_data) >= 6:
                first_half = np.mean(sales_data[:len(sales_data)//2])
                second_half = np.mean(sales_data[len(sales_data)//2:])
                seasonal_factor = second_half / first_half if first_half > 0 else 1.0
            
            forecast = [int(recent_avg * seasonal_factor) for _ in range(request.forecast_months)]
            
            metadata = items_metadata[item_key]
            forecasts[item_key] = {
                "pluno": metadata["pluno"],
                "item_name": metadata["item_name"],
                "product_group": metadata["product_group"],
                "method": "statistical",
                "historical_sales": sales_data,
                "forecasted_sales": forecast,
                "moving_average": recent_avg,
                "seasonal_factor": seasonal_factor
            }
    
    return {"forecasts": list(forecasts.values())}

async def ai_forecast(request: ForecastRequest):
    """AI-powered forecasting (placeholder for LLM integration)"""
    # This would integrate with LLM for advanced forecasting
    # For now, return enhanced statistical forecast
    return {
        "forecasts": [],
        "message": "AI forecasting requires additional setup. Please use trend or statistical methods for now.",
        "requirements": [
            "LLM API integration needed",
            "Advanced feature engineering required",
            "External market data integration"
        ]
    }

@api_router.delete("/clear-data")
async def clear_all_data():
    """Clear all sales data from database"""
    try:
        result = await db.sales_records.delete_many({})
        return {
            "message": f"Successfully deleted {result.deleted_count} records",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing data: {str(e)}")

@api_router.get("/daily-sales-trend")
async def get_daily_sales_trend(period: Optional[str] = Query(None)):
    """Get daily sales data for current quarter (3 months) or specific period"""
    try:
        from datetime import datetime, timedelta
        
        # Determine current quarter
        now = datetime.now()
        current_month = now.month
        
        # Calculate quarter start month (1=Jan-Mar, 4=Apr-Jun, 7=Jul-Sep, 10=Oct-Dec)
        quarter_start_month = ((current_month - 1) // 3) * 3 + 1
        quarter_start_date = datetime(now.year, quarter_start_month, 1)
        
        # Build query filter
        query_filter = {
            "upload_type": "daily",
            "status": "success",
            "data_date": {
                "$gte": quarter_start_date,
                "$lt": now + timedelta(days=1)  # Include today
            }
        }
        
        # If period is specified, filter by that period
        if period and period != "all":
            # Check for "Current Year" special case
            if "Current Year" in period:
                year = int(period.split(" ")[0])
                query_filter["data_date"] = {
                    "$gte": datetime(year, 1, 1),
                    "$lt": datetime(year + 1, 1, 1)
                }
            # Convert period to date range
            elif len(period) == 7 and '-' in period:  # Format: 2025-11
                year, month = period.split('-')
                period_start = datetime(int(year), int(month), 1)
                # Calculate last day of month
                if int(month) == 12:
                    period_end = datetime(int(year) + 1, 1, 1)
                else:
                    period_end = datetime(int(year), int(month) + 1, 1)
                query_filter["data_date"] = {"$gte": period_start, "$lt": period_end}
            elif len(period) == 4:  # Format: 2025 (full year)
                year = int(period)
                query_filter["data_date"] = {
                    "$gte": datetime(year, 1, 1),
                    "$lt": datetime(year + 1, 1, 1)
                }
        
        # Query upload_history for daily uploads
        daily_uploads = await db.upload_history.find(query_filter).sort("data_date", 1).to_list(None)
        
        # Format data by month
        monthly_data = {}
        for upload in daily_uploads:
            upload_date = upload.get('data_date')
            if upload_date:
                month_key = upload_date.strftime('%Y-%m')
                month_name = upload_date.strftime('%B')
                date_str = upload_date.strftime('%Y-%m-%d')
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'month_name': month_name,
                        'month_key': month_key,
                        'data': []
                    }
                
                # Get net amount (total sales for that day)
                net_amount = upload.get('net_amt', 0)
                
                monthly_data[month_key]['data'].append({
                    'date': date_str,
                    'sales': float(net_amount) if net_amount else 0,
                    'day': upload_date.day
                })
        
        # Convert to list and sort by month
        result = []
        for month_key in sorted(monthly_data.keys()):
            result.append(monthly_data[month_key])
        
        return {
            "quarter_start": quarter_start_date.strftime('%Y-%m-%d'),
            "current_date": now.strftime('%Y-%m-%d'),
            "months": result
        }
        
    except Exception as e:
        logger.error(f"Error fetching daily sales trend: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching daily sales trend: {str(e)}")

@api_router.get("/dashboard-summary")
async def get_dashboard_summary(period: Optional[str] = Query(None)):
    """Get overall dashboard summary statistics with averages"""
    try:
        # Base filter to exclude forecast data
        analytics_filter = {"upload_source": {"$ne": "forecast"}}
        
        # Add period filter if specified
        if period and period != "all":
            # Check if this is a "Current Year" request
            if "Current Year" in period:
                # Extract year from period (e.g., "2025 - Current Year" -> "2025")
                year = period.split(" ")[0]
                # Match all periods containing this year (both "2025" and "25" formats)
                analytics_filter["data_period"] = {
                    "$regex": f"({year}|{year[2:]})", 
                    "$options": "i"
                }
            else:
                analytics_filter["data_period"] = period
        
        # Total records
        total_records = await db.sales_records.count_documents(analytics_filter)
        
        # Get distinct years for average calculations
        distinct_periods = await db.sales_records.distinct("data_period", analytics_filter)
        years = set()
        for data_period in distinct_periods:
            if data_period:
                # Extract year from period (could be "2024", "2024-11", etc.)
                year_str = str(data_period).split('-')[0]
                try:
                    years.add(int(year_str))
                except:
                    pass
        num_years = len(years) if years else 1
        start_year = min(years) if years else datetime.now().year
        
        # Get the earliest month for start year
        earliest_period_query = await db.sales_records.find(
            analytics_filter
        ).sort("data_period", 1).limit(1).to_list(1)
        
        start_month = "Jan"
        if earliest_period_query:
            earliest_period = earliest_period_query[0].get("data_period", "")
            if earliest_period and '-' in str(earliest_period):
                # Format is "2022-01" or similar
                month_num = int(str(earliest_period).split('-')[1])
                months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                start_month = months[month_num - 1] if 1 <= month_num <= 12 else "Jan"
            elif earliest_period:
                start_month = "Jan"  # If only year, assume January
        
        # Total revenue, profit, and items sold
        # Build match conditions for revenue pipeline
        revenue_match_conditions = [
            {"upload_source": {"$ne": "forecast"}},
            {"r_amt": {"$ne": None, "$exists": True, "$gt": 0}},
            {"profit": {"$ne": None, "$exists": True}},
            {"net_qty": {"$ne": None, "$exists": True}}
        ]
        
        # Add period filter if specified
        if period and period != "all":
            if "Current Year" in period:
                year = period.split(" ")[0]
                revenue_match_conditions.append({
                    "data_period": {
                        "$regex": f"({year}|{year[2:]})", 
                        "$options": "i"
                    }
                })
            else:
                revenue_match_conditions.append({"data_period": period})
        
        revenue_pipeline = [
            {
                "$match": {
                    "$and": revenue_match_conditions
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$r_amt"},
                    "total_profit": {"$sum": "$profit"},
                    "total_items_sold": {"$sum": "$net_qty"}
                }
            }
        ]
        
        revenue_result = await db.sales_records.aggregate(revenue_pipeline).to_list(1)
        
        revenue_data = revenue_result[0] if revenue_result else {
            "total_revenue": 0,
            "total_profit": 0,
            "total_items_sold": 0
        }
        
        total_revenue = revenue_data.get("total_revenue", 0) or 0
        total_profit = revenue_data.get("total_profit", 0) or 0
        
        # Calculate average yearly values
        avg_yearly_revenue = total_revenue / num_years
        avg_yearly_profit = total_profit / num_years
        
        # Calculate profit margin and percentage
        if total_revenue > 0:
            profit_margin = (total_profit / total_revenue) * 100
        else:
            profit_margin = 0.0
        
        # Current Stock Value - Get from most recent financial report
        # This value is manually entered when generating daily financial reports
        latest_financial_report = await db.financial_data.find_one(
            {"current_stock_value": {"$ne": None, "$exists": True}},
            sort=[("date", -1)]
        )
        
        current_stock_value = 0
        if latest_financial_report:
            current_stock_value = latest_financial_report.get("current_stock_value", 0) or 0
        
        avg_yearly_stock_value = current_stock_value / num_years
        
        # C Category Stock Value (need ABC analysis first)
        # Get ABC analysis to identify C category items
        abc_match_conditions = [
            {"upload_source": {"$ne": "forecast"}},
            {"r_amt": {"$ne": None, "$exists": True}}
        ]
        
        # Add period filter if specified
        if period and period != "all":
            if "Current Year" in period:
                year = period.split(" ")[0]
                abc_match_conditions.append({
                    "data_period": {
                        "$regex": f"({year}|{year[2:]})", 
                        "$options": "i"
                    }
                })
            else:
                abc_match_conditions.append({"data_period": period})
        
        abc_pipeline = [
            {
                "$match": {
                    "$and": abc_match_conditions
                }
            },
            {
                "$group": {
                    "_id": "$pluno",
                    "item_name": {"$first": "$item_name"},
                    "total_revenue": {"$sum": "$r_amt"}
                }
            },
            {"$sort": {"total_revenue": -1}}
        ]
        
        abc_items = await db.sales_records.aggregate(abc_pipeline).to_list(None)
        
        # Calculate cumulative revenue
        total_abc_revenue = sum(item["total_revenue"] for item in abc_items)
        cumulative = 0
        c_category_plu_codes = []
        
        for item in abc_items:
            cumulative += item["total_revenue"]
            percentage = (cumulative / total_abc_revenue * 100) if total_abc_revenue > 0 else 0
            
            # C category: bottom 50% of items (>95% revenue)
            if percentage > 95:
                c_category_plu_codes.append(item["_id"])
        
        # Calculate C category stock value
        c_stock_match_conditions = [
            {"upload_source": {"$ne": "forecast"}},
            {"pluno": {"$in": c_category_plu_codes}},
            {"closing_stock": {"$ne": None, "$exists": True, "$gt": 0}},
            {"w_rate": {"$ne": None, "$exists": True}}
        ]
        
        # Add period filter if specified
        if period and period != "all":
            if "Current Year" in period:
                year = period.split(" ")[0]
                c_stock_match_conditions.append({
                    "data_period": {
                        "$regex": f"({year}|{year[2:]})", 
                        "$options": "i"
                    }
                })
            else:
                c_stock_match_conditions.append({"data_period": period})
        
        c_stock_pipeline = [
            {
                "$match": {
                    "$and": c_stock_match_conditions
                }
            },
            {
                "$sort": {"data_period": -1}
            },
            {
                "$group": {
                    "_id": "$pluno",
                    "latest_closing_stock": {"$first": "$closing_stock"},
                    "latest_w_rate": {"$first": "$w_rate"}
                }
            },
            {
                "$addFields": {
                    "stock_value": {
                        "$multiply": [
                            {"$ifNull": ["$latest_closing_stock", 0]},
                            {"$ifNull": ["$latest_w_rate", 0]}
                        ]
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_c_stock_value": {"$sum": "$stock_value"}
                }
            }
        ]
        
        c_stock_result = await db.sales_records.aggregate(c_stock_pipeline).to_list(1)
        c_category_stock_value = c_stock_result[0].get("total_c_stock_value", 0) if c_stock_result else 0
        avg_yearly_c_stock_value = c_category_stock_value / num_years
        
        # Group distribution
        group_pipeline = [
            {
                "$group": {
                    "_id": "$product_group",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        group_distribution = await db.sales_records.aggregate(group_pipeline).to_list(None)
            
        return {
            "total_records": total_records,
            "total_revenue": total_revenue,
            "avg_yearly_revenue": avg_yearly_revenue,
            "total_profit": total_profit,
            "avg_yearly_profit": avg_yearly_profit,
            "profit_margin": profit_margin,
            "profit_percentage": profit_margin,  # Same as profit_margin
            "total_items_sold": revenue_data.get("total_items_sold", 0) or 0,
            "current_stock_value": current_stock_value,
            "avg_yearly_stock_value": avg_yearly_stock_value,
            "c_category_stock_value": c_category_stock_value,
            "avg_yearly_c_stock_value": avg_yearly_c_stock_value,
            "num_years": num_years,
            "start_year": start_year,
            "start_month": start_month,
            "data_from": f"{start_month} {start_year}",
            "group_distribution": group_distribution
        }
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard summary: {str(e)}")

@api_router.get("/available-periods")
async def get_available_periods():
    """Get list of all unique data periods available in the database"""
    try:
        # Get distinct periods from sales_records, excluding forecast data
        periods = await db.sales_records.distinct(
            "data_period",
            {"upload_source": {"$ne": "forecast"}}
        )
        
        # Filter out None values and sort
        periods = [p for p in periods if p is not None]
        periods.sort(reverse=True)  # Most recent first
        
        # Check if there's any data for current year (2025)
        current_year = datetime.now().year
        has_current_year_data = any(
            str(current_year) in str(p) or str(current_year)[2:] in str(p) 
            for p in periods
        )
        
        # Add "Current Year" option at the beginning if current year data exists
        if has_current_year_data:
            periods.insert(0, f"{current_year} - Current Year")
        
        return periods
        
    except Exception as e:
        logger.error(f"Error getting available periods: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting available periods: {str(e)}")

# ============================================================================
# PHASE 1: UPLOAD HISTORY & DATABASE VIEW ENDPOINTS
# ============================================================================

@api_router.get("/upload-history")
async def get_upload_history(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None),
    period_filter: Optional[str] = Query(None),
    data_date: Optional[str] = Query(None)
):
    """Get upload history with optional filtering"""
    try:
        # Build filter
        filter_query = {}
        if status_filter and status_filter != "all":
            filter_query["status"] = status_filter
        if period_filter:
            filter_query["period_covered"] = {"$regex": period_filter, "$options": "i"}
        
        # Filter by specific data_date if provided
        if data_date:
            target_date = datetime.strptime(data_date, "%Y-%m-%d")
            filter_query["data_date"] = {
                "$gte": target_date,
                "$lt": target_date + timedelta(days=1)
            }
        
        # Get total count
        total = await db.upload_history.count_documents(filter_query)
        
        # Get paginated results
        history = await db.upload_history.find(filter_query, {"_id": 0})\
            .sort("upload_date", -1)\
            .skip(skip)\
            .limit(limit)\
            .to_list(limit)
        
        return {
            "total": total,
            "limit": limit,
            "skip": skip,
            "uploads": history,  # Also return as "uploads" for compatibility
            "results": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching upload history: {str(e)}")

@api_router.get("/available-data-periods")
async def get_available_data_periods():
    """Get list of all available data periods from sales records"""
    try:
        # Get unique data_period values from sales_records, sorted in descending order
        periods = await db.sales_records.distinct(
            "data_period",
            {"upload_source": {"$ne": "forecast"}, "data_period": {"$ne": None, "$exists": True}}
        )
        
        # Sort periods in descending order (newest first)
        # Assuming format like "2025-01", "2024-12", etc.
        periods_sorted = sorted(periods, reverse=True)
        
        # Also get upload info for context
        pipeline = [
            {
                "$match": {
                    "status": "success"
                }
            },
            {
                "$project": {
                    "upload_id": "$id",
                    "upload_type": 1,
                    "data_date": 1,
                    "period_covered": 1,
                    "data_type": 1,
                    "records_count": 1,
                    "upload_date": 1,
                    "filename": 1
                }
            },
            {
                "$sort": {"upload_date": -1}
            }
        ]
        
        uploads = await db.upload_history.aggregate(pipeline).to_list(None)
        
        # Organize by daily and historical
        daily_uploads = []
        historical_uploads = []
        
        for upload in uploads:
            if upload.get('upload_type') == 'daily' and upload.get('data_date'):
                daily_uploads.append({
                    "upload_id": upload['upload_id'],
                    "date": upload['data_date'],
                    "records_count": upload['records_count'],
                    "upload_date": upload['upload_date'],
                    "filename": upload['filename']
                })
            else:
                historical_uploads.append({
                    "upload_id": upload['upload_id'],
                    "period": upload.get('period_covered'),
                    "data_type": upload.get('data_type'),
                    "records_count": upload['records_count'],
                    "upload_date": upload['upload_date'],
                    "filename": upload['filename']
                })
        
        return {
            "periods": periods_sorted,  # NEW: List of unique period strings
            "daily_uploads": daily_uploads,
            "historical_uploads": historical_uploads,
            "total_daily": len(daily_uploads),
            "total_historical": len(historical_uploads),
            "total_periods": len(periods_sorted)
        }
        
    except Exception as e:
        logger.exception("Error fetching available data periods")
        raise HTTPException(status_code=500, detail=f"Error fetching data periods: {str(e)}")


@api_router.get("/database-view")
async def get_database_view(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    group_filter: Optional[str] = Query(None),
    period_filter: Optional[str] = Query(None),
    gp_index_no: Optional[str] = Query(None),
    aggregated: bool = Query(False),
    sort_by: str = Query("upload_date"),
    sort_order: int = Query(-1)
):
    """Get paginated view of sales database with filters and aggregation
    
    Args:
        limit: Maximum records per page
        skip: Number of records to skip
        search: Search in item names
        group_filter: Filter by product group
        period_filter: Filter by data_period
        gp_index_no: Filter by Gp_Index_No (supports partial match)
        aggregated: If True, aggregate by gp_index_no and sum quantities
        sort_by: Field to sort by
        sort_order: Sort order (1 for ascending, -1 for descending)
    """
    try:
        # Build filter query
        filter_query = {}
        
        if search:
            filter_query["item_name"] = {"$regex": search, "$options": "i"}
        
        if group_filter and group_filter != "all":
            filter_query["product_group"] = group_filter
        
        if period_filter:
            filter_query["data_period"] = {"$regex": period_filter, "$options": "i"}
        
        if gp_index_no:
            filter_query["gp_index_no"] = {"$regex": gp_index_no, "$options": "i"}
        
        if aggregated:
            # Aggregated view: group by gp_index_no and sum quantities
            pipeline = [
                {"$match": filter_query},
                {
                    "$group": {
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
                        "periods": {"$addToSet": "$data_period"},
                        "record_count": {"$sum": 1}
                    }
                },
                {"$sort": {(sort_by if sort_by in ["gp_index_no", "item_name", "product_group", "total_qty", "total_net_qty", "total_r_amt", "total_w_amt", "total_profit"] else "total_r_amt"): sort_order}},
                {"$skip": skip},
                {"$limit": limit}
            ]
            
            # Get total count for aggregated results
            count_pipeline = [
                {"$match": filter_query},
                {"$group": {"_id": "$gp_index_no"}},
                {"$count": "total"}
            ]
            count_result = await db.sales_records.aggregate(count_pipeline).to_list(1)
            total = count_result[0]["total"] if count_result else 0
            
            # Get aggregated records
            records = await db.sales_records.aggregate(pipeline).to_list(limit)
        else:
            # Regular view: get individual records
            total = await db.sales_records.count_documents(filter_query)
            
            records = await db.sales_records.find(filter_query, {"_id": 0})\
                .sort(sort_by, sort_order)\
                .skip(skip)\
                .limit(limit)\
                .to_list(limit)
        
        # Get unique periods in database
        periods_pipeline = [
            {"$group": {"_id": "$data_period"}},
            {"$sort": {"_id": -1}},
            {"$limit": 50}
        ]
        periods = await db.sales_records.aggregate(periods_pipeline).to_list(50)
        unique_periods = [p["_id"] for p in periods if p["_id"]]
        
        # Get groups
        groups_pipeline = [
            {"$group": {"_id": "$product_group"}},
            {"$sort": {"_id": 1}}
        ]
        groups = await db.sales_records.aggregate(groups_pipeline).to_list(10)
        unique_groups = [g["_id"] for g in groups if g["_id"]]
        
        # Summary statistics
        summary = {
            "total_records": total,
            "available_periods": unique_periods,
            "available_groups": unique_groups,
            "date_range": {
                "earliest": None,
                "latest": None
            }
        }
        
        # Get date range
        if total > 0:
            earliest = await db.sales_records.find_one(
                filter_query,
                sort=[("upload_date", 1)],
                projection={"upload_date": 1, "_id": 0}
            )
            latest = await db.sales_records.find_one(
                filter_query,
                sort=[("upload_date", -1)],
                projection={"upload_date": 1, "_id": 0}
            )
            if earliest and "upload_date" in earliest:
                summary["date_range"]["earliest"] = str(earliest["upload_date"])
            if latest and "upload_date" in latest:
                summary["date_range"]["latest"] = str(latest["upload_date"])
        
        return {
            "total": total,
            "limit": limit,
            "skip": skip,
            "records": records,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error in database view: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching database view: {str(e)}")

@api_router.post("/validate-forecast-date")
async def validate_forecast_date_endpoint(year: int, month: int):
    """Validate that forecast date is not in the past"""
    validation = validate_forecast_date(year, month)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    return {"valid": True, "message": f"Forecast for {month}/{year} is valid"}

@api_router.delete("/reset-all-data")
async def reset_all_data():
    """Clear entire database - use with caution!"""
    try:
        # Delete all sales records
        sales_result = await db.sales_records.delete_many({})
        
        # Delete all upload history
        history_result = await db.upload_history.delete_many({})
        
        logger.warning(f"DATABASE RESET: Deleted {sales_result.deleted_count} sales records and {history_result.deleted_count} upload history entries")
        
        return {
            "message": "Database reset successful",
            "sales_records_deleted": sales_result.deleted_count,
            "upload_history_deleted": history_result.deleted_count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error resetting database: {str(e)}")

@api_router.delete("/undo-upload/{upload_id}")
async def undo_upload(upload_id: str):
    """Undo a specific upload by deleting all records from that batch"""
    try:
        # First, verify the upload exists
        upload_record = await db.upload_history.find_one({"id": upload_id})
        if not upload_record:
            raise HTTPException(status_code=404, detail="Upload record not found")
        
        # Delete all sales records with this batch_id
        delete_result = await db.sales_records.delete_many({"upload_batch_id": upload_id})
        
        # Delete the upload history entry
        await db.upload_history.delete_one({"id": upload_id})
        
        logger.info(f"UNDO UPLOAD: Deleted {delete_result.deleted_count} records from upload {upload_id} ({upload_record.get('filename', 'unknown')})")
        
        return {
            "message": "Upload undone successfully",
            "deleted_count": delete_result.deleted_count,
            "filename": upload_record.get('filename'),
            "period": upload_record.get('period_covered'),
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error undoing upload {upload_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error undoing upload: {str(e)}")

@api_router.post("/check-data-availability")
async def check_data_availability(periods: List[str]):
    """Check which periods have data available in the database
    
    Handles both normalized (2025-09) and legacy formats (Sep 2025, 1 Sep to 30 2025)
    Excludes multi-month/yearly data (e.g., "JAN TO SEP 2025")
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
                    month = match.group(2)
                    month_int = int(month)
                    
                    month_names = {
                        1: ['jan', 'january'],
                        2: ['feb', 'february'],
                        3: ['mar', 'march'],
                        4: ['apr', 'april'],
                        5: ['may'],
                        6: ['jun', 'june'],
                        7: ['jul', 'july'],
                        8: ['aug', 'august'],
                        9: ['sep', 'sept', 'september'],
                        10: ['oct', 'october'],
                        11: ['nov', 'november'],
                        12: ['dec', 'december']
                    }
                    
                    target_month_names = month_names.get(month_int, [])
                    
                    if target_month_names:
                        # Get all records that might contain this month
                        all_records = await db.sales_records.find({
                            "data_period": {"$exists": True, "$ne": None}
                        }).to_list(None)
                        
                        # Filter to find ONLY single-month records for the target month
                        matching_records = []
                        for record in all_records:
                            data_period = record.get("data_period", "").lower()
                            
                            # Skip if empty
                            if not data_period:
                                continue
                            
                            # Check if it's the target year
                            if year not in data_period:
                                continue
                            
                            # Check if it contains the target month
                            has_target_month = any(month_name in data_period for month_name in target_month_names)
                            if not has_target_month:
                                continue
                            
                            # CRITICAL: Exclude multi-month patterns
                            is_multi_month = False
                            for other_month_int in range(1, 13):
                                if other_month_int != month_int:
                                    other_month_names = month_names.get(other_month_int, [])
                                    for other_month_name in other_month_names:
                                        if other_month_name in data_period:
                                            is_multi_month = True
                                            break
                                    if is_multi_month:
                                        break
                            
                            # If it's single-month, add to matches
                            if not is_multi_month:
                                matching_records.append(record)
                                if not found_period or found_period == period:
                                    found_period = record.get("data_period")
                        
                        count = len(matching_records)
            
            if count > 0:
                # Get upload info - try both formats
                upload_info = await db.upload_history.find_one(
                    {"period_covered": period, "status": "success"},
                    sort=[("upload_date", -1)]
                )
                
                # If not found with normalized period, search by actual period found
                if not upload_info and found_period and found_period != period:
                    # Try to find upload history by matching filename pattern
                    all_uploads = await db.upload_history.find(
                        {"status": "success"}
                    ).sort([("upload_date", -1)]).to_list(None)
                    
                    for upload in all_uploads:
                        filename = upload.get("filename", "").lower()
                        # Check if filename contains the same month pattern
                        has_month = any(month_name in filename for month_name in target_month_names)
                        if has_month and year in filename:
                            # Make sure it's not a multi-month file
                            is_multi = False
                            for other_month_int in range(1, 13):
                                if other_month_int != month_int:
                                    other_names = month_names.get(other_month_int, [])
                                    if any(name in filename for name in other_names):
                                        is_multi = True
                                        break
                            if not is_multi:
                                upload_info = upload
                                found_filename = upload.get("filename")
                                break
                
                availability[period] = {
                    "available": True,
                    "record_count": count,
                    "upload_date": upload_info.get("upload_date") if upload_info else None,
                    "filename": found_filename or (upload_info.get("filename") if upload_info else None),
                    "actual_period": found_period
                }
            else:
                availability[period] = {
                    "available": False,
                    "record_count": 0
                }
        
        return {
            "periods_checked": len(periods),
            "availability": availability
        }
    except Exception as e:
        logger.error(f"Error checking data availability: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error checking data availability: {str(e)}")


# ============================================================================
# Phase 2: Financial Health Tracking Endpoints
# ============================================================================

@api_router.post("/financial-data")
async def create_financial_data(
    date: str,  # Format: "YYYY-MM-DD"
    liquor_sales: float,
    previous_bank_amount: float,
    grocery_sales_override: Optional[float] = None,
    previous_stock_value: Optional[float] = None,
    current_stock_value: Optional[float] = None,
    notes: Optional[str] = None
):
    """Create or update financial data for a specific date"""
    try:
        # Parse date
        target_date = datetime.strptime(date, "%Y-%m-%d")
        
        # Calculate grocery sales from that day's upload OR use override from image
        grocery_sales = 0.0
        
        if grocery_sales_override is not None:
            # Use the override value from image extraction
            grocery_sales = grocery_sales_override
            logger.info(f"Using grocery sales from image: ₹{grocery_sales:,.2f}")
        else:
            # Original logic - get from uploaded data
            daily_upload = await db.upload_history.find_one({
                "upload_type": "daily",
                "data_date": {
                    "$gte": target_date,
                    "$lt": target_date + timedelta(days=1)
                },
                "status": "success"
            })
            
            if daily_upload:
                # Use net_amt from Summary Details if available, otherwise calculate from records
                if daily_upload.get("net_amt") is not None:
                    grocery_sales = float(daily_upload["net_amt"])
                    logger.info(f"Using Net Amt from Summary Details: ₹{grocery_sales:,.2f}")
                else:
                    # Fallback: Calculate from uploaded records (old method)
                    logger.warning("Net Amt not found in upload history, calculating from records")
                    pipeline = [
                        {
                            "$match": {
                                "upload_batch_id": daily_upload["id"]
                            }
                        },
                        {
                            "$group": {
                                "_id": None,
                                "total_sales": {"$sum": {"$ifNull": ["$r_amt", 0]}}
                            }
                        }
                    ]
                    result = await db.sales_records.aggregate(pipeline).to_list(1)
                    if result:
                        grocery_sales = float(result[0].get("total_sales", 0))
        
        # Calculate totals
        total_sales = grocery_sales + liquor_sales
        current_bank_amount = previous_bank_amount + total_sales
        
        # Check if financial data already exists for this date
        existing = await db.financial_data.find_one({
            "date": {
                "$gte": target_date,
                "$lt": target_date + timedelta(days=1)
            }
        })
        
        financial_record = FinancialData(
            id=existing["id"] if existing else str(uuid.uuid4()),
            date=target_date,
            grocery_sales=grocery_sales,
            liquor_sales=liquor_sales,
            total_sales=total_sales,
            previous_bank_amount=previous_bank_amount,
            current_bank_amount=current_bank_amount,
            previous_stock_value=previous_stock_value,
            current_stock_value=current_stock_value,
            notes=notes
        )
        
        if existing:
            # Update existing record
            await db.financial_data.update_one(
                {"id": existing["id"]},
                {"$set": financial_record.dict()}
            )
            message = "Financial data updated successfully"
        else:
            # Insert new record
            await db.financial_data.insert_one(financial_record.dict())
            message = "Financial data created successfully"
        
        logger.info(f"Financial data for {date}: Grocery=₹{grocery_sales:.2f}, Liquor=₹{liquor_sales:.2f}, Total=₹{total_sales:.2f}")
        
        return {
            "message": message,
            "financial_data": financial_record.dict(),
            "status": "success"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Error creating financial data")
        raise HTTPException(status_code=500, detail=f"Error creating financial data: {str(e)}")

@api_router.get("/financial-data/{date}")
async def get_financial_data(date: str):
    """Get financial data for a specific date"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        
        financial_data = await db.financial_data.find_one({
            "date": {
                "$gte": target_date,
                "$lt": target_date + timedelta(days=1)
            }
        })
        
        if not financial_data:
            # Return default/empty data if not found
            return {
                "date": date,
                "exists": False,
                "grocery_sales": 0.0,
                "liquor_sales": 0.0,
                "total_sales": 0.0,
                "previous_bank_amount": 0.0,
                "current_bank_amount": 0.0
            }
        
        return {
            "exists": True,
            **financial_data
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Error fetching financial data")
        raise HTTPException(status_code=500, detail=f"Error fetching financial data: {str(e)}")

@api_router.get("/financial-data-range")
async def get_financial_data_range(
    start_date: str,
    end_date: str,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get financial data for a date range"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        financial_records = await db.financial_data.find({
            "date": {
                "$gte": start,
                "$lte": end
            }
        }).sort("date", -1).limit(limit).to_list(limit)
        
        # Convert ObjectId to string
        for record in financial_records:
            if "_id" in record:
                record["_id"] = str(record["_id"])
            # Convert datetime to ISO string
            if "date" in record and isinstance(record["date"], datetime):
                record["date"] = record["date"].isoformat()
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "count": len(financial_records),
            "records": financial_records
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Error fetching financial data range")
        raise HTTPException(status_code=500, detail=f"Error fetching financial data range: {str(e)}")

@api_router.put("/financial-data/{record_id}")
async def update_financial_data(
    record_id: str,
    liquor_sales: float,
    previous_bank_amount: float,
    previous_stock_value: Optional[float] = None,
    current_stock_value: Optional[float] = None,
    notes: Optional[str] = None
):
    """Update an existing financial data record"""
    try:
        # Find the existing record
        existing = await db.financial_data.find_one({"id": record_id})
        
        if not existing:
            raise HTTPException(status_code=404, detail="Financial record not found")
        
        # Get the date from existing record
        target_date = existing["date"]
        
        # Recalculate grocery sales from that day's upload
        grocery_sales = 0.0
        daily_upload = await db.upload_history.find_one({
            "upload_type": "daily",
            "data_date": {
                "$gte": target_date,
                "$lt": target_date + timedelta(days=1)
            },
            "status": "success"
        })
        
        if daily_upload:
            if daily_upload.get("net_amt") is not None:
                grocery_sales = float(daily_upload["net_amt"])
            else:
                pipeline = [
                    {"$match": {"upload_batch_id": daily_upload["id"]}},
                    {"$group": {"_id": None, "total_sales": {"$sum": {"$ifNull": ["$r_amt", 0]}}}}
                ]
                result = await db.sales_records.aggregate(pipeline).to_list(1)
                if result:
                    grocery_sales = float(result[0].get("total_sales", 0))
        
        # Calculate totals
        total_sales = grocery_sales + liquor_sales
        current_bank_amount = previous_bank_amount + total_sales
        
        # Update the record
        update_data = {
            "grocery_sales": grocery_sales,
            "liquor_sales": liquor_sales,
            "total_sales": total_sales,
            "previous_bank_amount": previous_bank_amount,
            "current_bank_amount": current_bank_amount,
            "previous_stock_value": previous_stock_value,
            "current_stock_value": current_stock_value,
            "notes": notes,
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.financial_data.update_one(
            {"id": record_id},
            {"$set": update_data}
        )
        
        # Get updated record
        updated_record = await db.financial_data.find_one({"id": record_id}, {"_id": 0})
        
        logger.info(f"Updated financial data for {target_date.strftime('%Y-%m-%d')}")
        
        return {
            "message": "Financial data updated successfully",
            "financial_data": updated_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error updating financial data")
        raise HTTPException(status_code=500, detail=f"Error updating financial data: {str(e)}")

@api_router.delete("/financial-data/{record_id}")
async def delete_financial_data(record_id: str):
    """Delete a financial data record"""
    try:
        # Find the existing record
        existing = await db.financial_data.find_one({"id": record_id})
        
        if not existing:
            raise HTTPException(status_code=404, detail="Financial record not found")
        
        # Delete the record
        result = await db.financial_data.delete_one({"id": record_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Financial record not found")
        
        date_str = existing["date"].strftime("%Y-%m-%d")
        logger.info(f"Deleted financial data for {date_str}")
        
        return {
            "message": f"Financial data for {date_str} deleted successfully",
            "deleted_id": record_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error deleting financial data")
        raise HTTPException(status_code=500, detail=f"Error deleting financial data: {str(e)}")

@api_router.get("/previous-financial-data")
async def get_previous_financial_data(date: str):
    """Get the financial data from the previous day for form pre-fill"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        previous_date = target_date - timedelta(days=1)
        
        # Try to find financial data from previous day
        previous_financial = await db.financial_data.find_one({
            "date": {
                "$gte": previous_date,
                "$lt": target_date
            }
        }, sort=[("date", -1)])
        
        if previous_financial:
            # Return the calculated values from previous day's report
            # These become "previous" values for today's report
            previous_bank_amount = previous_financial.get("current_bank_amount")
            previous_stock_value = previous_financial.get("current_stock_value")
            
            return {
                "previous_date": previous_date.strftime("%Y-%m-%d"),
                "bank_amount": previous_bank_amount,
                "stock_value": previous_stock_value,
                "found": True
            }
        
        # If not found, return null/not found
        return {
            "previous_date": previous_date.strftime("%Y-%m-%d"),
            "bank_amount": None,
            "stock_value": None,
            "found": False
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Error fetching previous financial data")
        raise HTTPException(status_code=500, detail=f"Error fetching previous financial data: {str(e)}")

@api_router.get("/previous-bank-amount")
async def get_previous_bank_amount(date: str):
    """Get the bank amount from the previous day for form pre-fill (legacy endpoint)"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
        previous_date = target_date - timedelta(days=1)
        
        # Try to find financial data from previous day
        previous_financial = await db.financial_data.find_one({
            "date": {
                "$gte": previous_date,
                "$lt": target_date
            }
        })
        
        if previous_financial and "current_bank_amount" in previous_financial:
            return {
                "previous_date": previous_date.strftime("%Y-%m-%d"),
                "bank_amount": previous_financial["current_bank_amount"],
                "found": True
            }
        
        # If not found, return null/not found
        return {
            "previous_date": previous_date.strftime("%Y-%m-%d"),
            "bank_amount": None,
            "found": False
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Error fetching previous bank amount")
        raise HTTPException(status_code=500, detail=f"Error fetching previous bank amount: {str(e)}")

@api_router.post("/extract-canteen-summary")
async def extract_canteen_summary(file: UploadFile = File(...)):
    """Extract grocery and liquor sales from CSD canteen summary image"""
    try:
        import base64
        from openai import OpenAI
        
        logger.info(f"Received image upload: {file.filename}, type: {file.content_type}")
        
        # Read the uploaded image
        contents = await file.read()
        logger.info(f"Image size: {len(contents)} bytes")
        
        # Convert to base64 for AI processing
        base64_image = base64.b64encode(contents).decode('utf-8')
        
        # Get API key (try Emergent LLM key first, then fallback to OpenAI key)
        api_key = os.environ.get('EMERGENT_LLM_KEY') or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="API key not configured. Set EMERGENT_LLM_KEY or OPENAI_API_KEY environment variable.")
        
        # Determine base URL based on key type
        base_url = None
        if api_key.startswith('sk-emergent-'):
            # Emergent LLM key - use Emergent proxy
            base_url = "https://api.emergentagi.com/v1"
        
        prompt = """Analyze this Canteen Summary image and extract the following data:
1. Today's Bill Amount - Grocery (look for "Today's Bill Amount" row, Grocery column)
2. Today's Bill Amount - Liquor (look for "Today's Bill Amount" row, Liquor column)

Return ONLY a JSON object with these exact fields:
{
  "grocery_sales": <number>,
  "liquor_sales": <number>
}

Remove commas and currency symbols from numbers. Return only the JSON, nothing else."""

        logger.info("Calling OpenAI API with vision...")
        
        # Create OpenAI client
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        
        # Call GPT-4o with vision
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a data extraction assistant. Extract numerical data from images accurately."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{file.content_type or 'image/jpeg'};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1024
        )
        
        response_text = response.choices[0].message.content
        logger.info(f"Received response from LLM: {response_text[:200]}...")
        
        # Extract JSON from response
        import re
        json_match = re.search(r'\{[^}]+\}', response_text)
        if json_match:
            extracted_data = json.loads(json_match.group())
        else:
            extracted_data = json.loads(response_text)
        
        logger.info(f"✓ Successfully extracted canteen data: {extracted_data}")
        
        return {
            "success": True,
            "data": {
                "grocery_sales": float(extracted_data.get("grocery_sales", 0)),
                "liquor_sales": float(extracted_data.get("liquor_sales", 0))
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}, Response: {response_text}")
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        logger.error(f"Error extracting canteen summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extract data from image: {str(e)}")

@api_router.post("/generate-daily-report")
async def generate_daily_sales_report(
    date: str,
    liquor_sales: float,
    previous_bank_amount: float,
    grocery_sales: Optional[float] = None,
    previous_stock_value: Optional[float] = None,
    current_stock_value: Optional[float] = None,
    notes: Optional[str] = None
):
    """Generate PDF daily sales report"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        from io import BytesIO
        
        # Calculate current stock value before creating financial data
        report_date = datetime.strptime(date, "%Y-%m-%d")
        calculated_stock_value = None
        
        # Get today's W_Amt from upload history to calculate stock value
        todays_w_amt = 0.0
        daily_upload = await db.upload_history.find_one({
            "upload_type": "daily",
            "data_date": {
                "$gte": report_date,
                "$lt": report_date + timedelta(days=1)
            },
            "status": "success"
        })
        
        if daily_upload:
            # Use W_Amt from Report Total if available
            if daily_upload.get("w_amt") is not None:
                todays_w_amt = float(daily_upload["w_amt"])
                logger.info(f"Using W_Amt from Report Total for stock calculation: Rs. {todays_w_amt:,.2f}")
        
        # Calculate stock value: Previous Stock - Today's Cost
        logger.info(f"Stock calculation inputs - previous_stock_value: {previous_stock_value}, current_stock_value: {current_stock_value}, todays_w_amt: {todays_w_amt}")
        
        if current_stock_value is not None:
            # User provided value - use it directly
            calculated_stock_value = current_stock_value
            logger.info(f"Using user-provided current stock value: {calculated_stock_value}")
        elif previous_stock_value is not None and todays_w_amt > 0:
            # Calculate: Previous Stock - Today's Cost
            calculated_stock_value = previous_stock_value - todays_w_amt
            logger.info(f"✓ Calculated stock value: {previous_stock_value} - {todays_w_amt} = {calculated_stock_value}")
        else:
            logger.info(f"No stock calculation - previous_stock_value: {previous_stock_value}, todays_w_amt: {todays_w_amt}")
        
        # Create/update financial data with calculated stock value
        financial_response = await create_financial_data(
            date=date,
            liquor_sales=liquor_sales,
            previous_bank_amount=previous_bank_amount,
            grocery_sales_override=grocery_sales,  # Allow override from image
            previous_stock_value=previous_stock_value,
            current_stock_value=calculated_stock_value,  # Use calculated value
            notes=notes
        )
        
        financial_data = financial_response["financial_data"]
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Container for elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        # Title
        report_date = datetime.strptime(date, "%Y-%m-%d")
        title = Paragraph(f"Sale Summary for {report_date.strftime('%d %B %Y')}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        # Sales Data Table
        sales_heading = Paragraph("Daily Sales Breakdown", heading_style)
        elements.append(sales_heading)
        
        sales_data = [
            ['Description', 'Amount'],
            ['Grocery Sales for the day', format_indian_currency(financial_data['grocery_sales'])],
            ['Liquor Sales for the day', format_indian_currency(financial_data['liquor_sales'])],
            ['Total Sales for the day (D)', format_indian_currency(financial_data['total_sales'])],
        ]
        
        sales_table = Table(sales_data, colWidths=[4*inch, 2*inch])
        sales_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eff6ff')),
        ]))
        
        elements.append(sales_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Bank Data Table
        previous_date = (report_date - timedelta(days=1)).strftime('%d %B %Y')
        bank_heading = Paragraph("Bank Account Summary", heading_style)
        elements.append(bank_heading)
        
        bank_data = [
            ['Description', 'Amount'],
            [f'Amount in Bank as on {previous_date} (Y)', format_indian_currency(financial_data['previous_bank_amount'])],
            [f'Total Amount in Bank on {report_date.strftime("%d %B %Y")} (Y+D)', format_indian_currency(financial_data['current_bank_amount'])],
        ]
        
        bank_table = Table(bank_data, colWidths=[4*inch, 2*inch])
        bank_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
        ]))
        
        elements.append(bank_table)
        
        # Stock Data (if provided)
        if previous_stock_value is not None or current_stock_value is not None:
            elements.append(Spacer(1, 0.3*inch))
            stock_heading = Paragraph("Inventory Stock Valuation", heading_style)
            elements.append(stock_heading)
            
            stock_data = [
                ['Description', 'Value'],
            ]
            
            if previous_stock_value is not None:
                stock_data.append([f'Total Value of Grocery Stock on {previous_date}', format_indian_currency(previous_stock_value)])
            
            # Add Today's Cost line if we calculated stock value
            if todays_w_amt > 0 and calculated_stock_value is not None:
                stock_data.append([f"Today's Cost of Goods Sold (W_Amt)", format_indian_currency(todays_w_amt)])
            
            # Add calculated current stock value
            if calculated_stock_value is not None:
                stock_data.append([
                    f'Total Value of Grocery Stock on {report_date.strftime("%d %B %Y")}',
                    format_indian_currency(calculated_stock_value)
                ])
            
            stock_table = Table(stock_data, colWidths=[4*inch, 2*inch])
            stock_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
            ]))
            
            elements.append(stock_table)
        
        # Notes section
        if notes:
            elements.append(Spacer(1, 0.3*inch))
            notes_heading = Paragraph("Additional Notes", heading_style)
            elements.append(notes_heading)
            notes_para = Paragraph(notes, styles['Normal'])
            elements.append(notes_para)
        
        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        footer_text = f"Generated on {datetime.now().strftime('%d %B %Y at %I:%M %p')}"
        footer = Paragraph(footer_text, footer_style)
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Return PDF as response
        from fastapi.responses import Response
        filename = f"daily_sales_report_{date}.pdf"
        
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.exception("Error generating daily sales report PDF")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

        
        if previous_financial and "current_bank_amount" in previous_financial:
            return {
                "previous_date": previous_date.strftime("%Y-%m-%d"),
                "bank_amount": previous_financial["current_bank_amount"],
                "found": True
            }
        
        # If not found, return null/not found
        return {
            "previous_date": previous_date.strftime("%Y-%m-%d"),
            "bank_amount": None,
            "found": False
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.exception("Error fetching previous bank amount")
        raise HTTPException(status_code=500, detail=f"Error fetching previous bank amount: {str(e)}")


# Configure logging FIRST (before CORS setup uses it)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS Configuration - FIXED per security best practices
raw_cors = os.environ.get("CORS_ORIGINS", "")
if raw_cors.strip() == "":
    allow_origins = []
elif raw_cors.strip() == "*":
    allow_origins = ["*"]
else:
    allow_origins = [o.strip() for o in raw_cors.split(",") if o.strip()]

allow_credentials = os.environ.get("CORS_ALLOW_CREDENTIALS", "false").lower() in ("1", "true", "yes")

# Safety: cannot use wildcard origin with credentials (browsers reject this)
if allow_origins == ["*"] and allow_credentials:
    logger.warning("CORS: wildcard origin with credentials is not allowed; disabling credentials.")
    allow_credentials = False

logger.info("CORS Configuration - allow_origins=%s allow_credentials=%s", allow_origins, allow_credentials)

# Apply CORS middleware BEFORE including routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router in the main app AFTER CORS middleware
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
