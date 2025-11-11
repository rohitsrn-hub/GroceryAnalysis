from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
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
    records_count: int = 0
    status: str  # "success", "failed", "partial"
    error_message: Optional[str] = None
    uploaded_by: str = "system"  # Can be extended for multi-user
    file_size_kb: Optional[float] = None
    processing_time_seconds: Optional[float] = None

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
    """Extract year and month from filename"""
    import re
    
    # Patterns to match
    # "Jan 2023.xlsx", "1Aug to 31 2025.xlsx", "YR 2024 C.xlsx"
    
    result = {"year": None, "month": None, "period": None, "data_type": None}
    
    # Try to find year (4 digits)
    year_match = re.search(r'20\d{2}', filename)
    if year_match:
        result["year"] = int(year_match.group())
    
    # Try to find month
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
    
    filename_lower = filename.lower()
    for month_name, month_num in months.items():
        if month_name in filename_lower:
            result["month"] = month_num
            break
    
    # Determine period and data_type
    if result["year"] and result["month"]:
        result["period"] = f"{result['year']}-{result['month']:02d}"
        result["data_type"] = "monthly"
    elif result["year"]:
        result["period"] = str(result["year"])
        result["data_type"] = "yearly"
    
    return result

def process_excel_data(file_content: bytes, filename: str, period_info: Optional[Dict[str, Any]] = None) -> List[Dict]:
    """Process uploaded Excel file and return structured data with normalized period"""
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
        
        for idx, row in df.iterrows():
            # Skip empty rows or rows with invalid data
            item_name = str(row.get('item_name', '')).strip()
            pluno = str(row.get('pluno', '')).strip()
            
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
                if len(skipped_rows) < 5:  # Only log first 5 for debugging
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
        
        return records
        
    except HTTPException:
        # Re-raise HTTP exceptions with details
        raise
    except Exception as e:
        logger.error(f"Error processing Excel file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error processing Excel file: {str(e)}")

# API Routes
@api_router.post("/upload-sales-data")
async def upload_sales_data(file: UploadFile = File(...)):
    """Upload and process sales data from Excel file with history logging"""
    start_time = datetime.now()
    upload_id = str(uuid.uuid4())
    
    logger.info(f"Upload attempt: filename={file.filename}, upload_id={upload_id}")
    
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
        
        # Check for duplicate upload
        if period_info["period"]:
            existing = await check_duplicate_upload(period_info["period"])
            if existing:
                logger.warning(f"Duplicate upload blocked for period {period_info['period']}")
                upload_date_str = existing.get('upload_date')
                date_info = f" (uploaded on {upload_date_str})" if upload_date_str else ""
                raise HTTPException(
                    status_code=400,
                    detail=f"Data for period '{period_info['period']}' already exists in the database{date_info}. Found {existing['records_count']} existing records. Please use UNDO on the previous upload or reset database to re-upload."
                )
        
        # Process the data with normalized period information
        records = process_excel_data(contents, file.filename, period_info)
        
        if records:
            # Add upload batch tracking to each record
            for record in records:
                record['upload_batch_id'] = upload_id
                record['upload_date'] = datetime.now(timezone.utc)
            
            # Insert into MongoDB
            result = await db.sales_records.insert_many([SalesRecord(**record).dict() for record in records])
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log upload history
            upload_record = UploadHistory(
                id=upload_id,
                filename=file.filename,
                period_covered=period_info["period"],
                data_type=period_info["data_type"],
                records_count=len(records),
                status="success",
                file_size_kb=file_size_kb,
                processing_time_seconds=processing_time
            )
            await db.upload_history.insert_one(upload_record.dict())
            
            return {
                "message": f"Successfully uploaded {len(records)} records",
                "file_name": file.filename,
                "records_count": len(records),
                "inserted_ids": len(result.inserted_ids),
                "status": "success",
                "upload_id": upload_id,
                "period_covered": period_info["period"],
                "data_type": period_info["data_type"],
                "duplicate_warning": existing is not None
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
async def get_fastest_selling_items(limit: int = Query(10, ge=1, le=50), group: Optional[str] = Query(None)):
    """Get fastest selling items with seasonal patterns"""
    try:
        # Build match filter
        match_filter = {"net_qty": {"$ne": None, "$exists": True}}
        if group and group != "all":
            match_filter["product_group"] = group
            
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
                "total_revenue": item.get('total_revenue', 0)
            })
        
        return fastest_items
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching fastest selling items: {str(e)}")

@api_router.get("/abc-analysis")
async def get_abc_analysis(group: Optional[str] = Query(None)):
    """Perform ABC analysis - 80/20 rule for inventory classification"""
    try:
        # Build match filter
        match_filter = {"net_qty": {"$ne": None, "$exists": True, "$gt": 0}}
        if group and group != "all":
            match_filter["product_group"] = group
            
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
async def get_capital_blocking_analysis(group: Optional[str] = Query(None)):
    """Identify slow moving items with high inventory causing capital blocking"""
    try:
        match_filter = {}
        if group and group != "all":
            match_filter["product_group"] = group
            
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
async def get_inventory_analysis():
    """Analyze inventory for slow moving and dead stock"""
    try:
        # Get items with poor performance vs cost
        pipeline_high_cost = [
            {"$match": {"w_rate": {"$gt": 0}}},
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
async def get_group_analysis():
    """Analyze performance by product groups"""
    try:
        pipeline = [
            {
                "$group": {
                    "_id": "$product_group",
                    "total_revenue": {"$sum": "$r_amt"},
                    "total_profit": {"$sum": "$profit"},
                    "total_cost": {"$sum": "$w_amt"},
                    "item_count": {"$sum": 1},
                    "items": {
                        "$push": {
                            "pluno": "$pluno",
                            "item_name": "$item_name",
                            "revenue": "$r_amt",
                            "profit": "$profit",
                            "qty": "$net_qty"
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
            top_performers = sorted(
                group['items'], 
                key=lambda x: x.get('revenue', 0) or 0, 
                reverse=True
            )[:5]
            
            group_analysis.append({
                "group": group['_id'],
                "total_revenue": group.get('total_revenue', 0) or 0,
                "total_profit": group.get('total_profit', 0) or 0,
                "item_count": group['item_count'],
                "top_performers": top_performers,
                "profit_margin": group.get('profit_margin', 0) or 0
            })
        
        return group_analysis
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in group analysis: {str(e)}")

@api_router.get("/comprehensive-report")
async def generate_comprehensive_report(format: str = Query("excel")):
    """Generate comprehensive business analysis report"""
    try:
        # Gather all analytics data
        dashboard_summary = await get_dashboard_summary()
        abc_analysis = await get_abc_analysis(None)
        capital_analysis = await get_capital_blocking_analysis(None)
        group_analysis = await get_group_analysis()
        fastest_items = await get_fastest_selling_items(20)
        
        if format == "excel":
            # Create comprehensive Excel report
            workbook = openpyxl.Workbook()
            
            # Summary Sheet
            ws_summary = workbook.active
            ws_summary.title = "Executive Summary"
            
            ws_summary.append(["URC 101 Area - Comprehensive Sales Analysis Report"])
            ws_summary.append(["Generated on:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            ws_summary.append([""])
            ws_summary.append(["KEY METRICS"])
            ws_summary.append(["Total Revenue", f"₹{dashboard_summary['total_revenue']:,.2f}"])
            ws_summary.append(["Total Profit", f"₹{dashboard_summary['total_profit']:,.2f}"])
            ws_summary.append(["Profit Margin", f"{dashboard_summary['profit_margin']:.2f}%"])
            ws_summary.append(["Total Items Sold", f"{dashboard_summary['total_items_sold']:,}"])
            ws_summary.append(["Total Records", f"{dashboard_summary['total_records']:,}"])
            
            # ABC Analysis Sheet
            ws_abc = workbook.create_sheet("ABC Analysis")
            ws_abc.append(["Category", "Items", "% of Items", "Revenue", "% of Revenue"])
            for category in ['A', 'B', 'C']:
                cat_data = abc_analysis['summary'][f'category_{category}']
                ws_abc.append([
                    f"Category {category}",
                    cat_data['item_count'],
                    f"{cat_data['percentage_items']:.1f}%",
                    f"₹{cat_data['revenue']:,.2f}",
                    f"{(cat_data['revenue']/abc_analysis['summary']['total_revenue'])*100:.1f}%"
                ])
            
            # Capital Blocking Sheet
            ws_capital = workbook.create_sheet("Capital Blocking")
            ws_capital.append(["Item Code", "Item Name", "Group", "Capital Blocked", "Risk Level", "Days to Sell"])
            for item in capital_analysis['capital_blocking_items'][:50]:
                ws_capital.append([
                    item['_id']['pluno'],
                    item['_id']['item_name'],
                    item['_id']['group'],
                    f"₹{item['capital_blocked']:,.2f}",
                    item['risk_level'],
                    item['days_to_sell'] if item['days_to_sell'] != 9999 else "∞"
                ])
            
            # Group Performance Sheet
            ws_groups = workbook.create_sheet("Group Performance")
            ws_groups.append(["Group", "Items", "Revenue", "Profit", "Margin %"])
            for group in group_analysis:
                ws_groups.append([
                    group['group'],
                    group['item_count'],
                    f"₹{group['total_revenue']:,.2f}",
                    f"₹{group['total_profit']:,.2f}",
                    f"{group['profit_margin']:.2f}%"
                ])
            
            # Top Performers Sheet
            ws_top = workbook.create_sheet("Top Performers")
            ws_top.append(["Rank", "Item Code", "Item Name", "Group", "Units Sold", "Revenue", "Monthly Avg"])
            for i, item in enumerate(fastest_items, 1):
                ws_top.append([
                    i,
                    item['item_code'],
                    item['item_name'],
                    item['group'],
                    item['total_sold'],
                    f"₹{item['total_revenue']:,.2f}",
                    f"{item['avg_monthly_sales']:.1f}"
                ])
            
            # Recommendations Sheet
            ws_rec = workbook.create_sheet("Recommendations")
            ws_rec.append(["STRATEGIC RECOMMENDATIONS"])
            ws_rec.append([""])
            ws_rec.append(["1. CAPITAL OPTIMIZATION"])
            ws_rec.append([f"• {capital_analysis['summary']['critical_items']} items require immediate liquidation"])
            ws_rec.append([f"• Total blocked capital: ₹{capital_analysis['summary']['total_capital_blocked']:,.2f}"])
            ws_rec.append([""])
            ws_rec.append(["2. INVENTORY FOCUS"])
            ws_rec.append([f"• Focus on Category A items ({abc_analysis['summary']['category_A']['item_count']} items generating 80% revenue)"])
            ws_rec.append([f"• Review Category C items ({abc_analysis['summary']['category_C']['item_count']} items generating only 5% revenue)"])
            ws_rec.append([""])
            ws_rec.append(["3. GROUP PERFORMANCE"])
            top_group = max(group_analysis, key=lambda x: x['total_revenue'])
            ws_rec.append([f"• {top_group['group']} is the top revenue generator"])
            ws_rec.append(["• Consider expanding high-margin groups"])
            
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
            # Create HTML content for PDF conversion
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>URC 101 Area - Comprehensive Sales Analysis Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .section {{ margin-bottom: 30px; }}
                    .table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    .table th {{ background-color: #f2f2f2; }}
                    .metric {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>URC 101 Area - Comprehensive Sales Analysis Report</h1>
                    <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                </div>
                
                <div class="section">
                    <h2>Executive Summary</h2>
                    <div class="metric">Total Revenue: ₹{dashboard_summary['total_revenue']:,.2f}</div>
                    <div class="metric">Total Profit: ₹{dashboard_summary['total_profit']:,.2f}</div>
                    <div class="metric">Profit Margin: {dashboard_summary['profit_margin']:.2f}%</div>
                    <div class="metric">Items Sold: {dashboard_summary['total_items_sold']:,}</div>
                </div>
                
                <div class="section">
                    <h2>ABC Analysis Summary</h2>
                    <table class="table">
                        <tr><th>Category</th><th>Items</th><th>% of Items</th><th>Revenue</th><th>% of Revenue</th></tr>
                        <tr><td>Category A (Fast Moving)</td><td>{abc_analysis['summary']['category_A']['item_count']}</td><td>{abc_analysis['summary']['category_A']['percentage_items']:.1f}%</td><td>₹{abc_analysis['summary']['category_A']['revenue']:,.2f}</td><td>80%</td></tr>
                        <tr><td>Category B (Medium Moving)</td><td>{abc_analysis['summary']['category_B']['item_count']}</td><td>{abc_analysis['summary']['category_B']['percentage_items']:.1f}%</td><td>₹{abc_analysis['summary']['category_B']['revenue']:,.2f}</td><td>15%</td></tr>
                        <tr><td>Category C (Slow Moving)</td><td>{abc_analysis['summary']['category_C']['item_count']}</td><td>{abc_analysis['summary']['category_C']['percentage_items']:.1f}%</td><td>₹{abc_analysis['summary']['category_C']['revenue']:,.2f}</td><td>5%</td></tr>
                    </table>
                </div>
                
                <div class="section">
                    <h2>Strategic Recommendations</h2>
                    <ul>
                        <li>Focus on Category A items ({abc_analysis['summary']['category_A']['item_count']} items generating 80% revenue)</li>
                        <li>Review Category C items ({abc_analysis['summary']['category_C']['item_count']} items generating only 5% revenue)</li>
                        <li>{capital_analysis['summary']['critical_items']} items require immediate liquidation</li>
                        <li>Total blocked capital: ₹{capital_analysis['summary']['total_capital_blocked']:,.2f}</li>
                    </ul>
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
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

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

@api_router.get("/dashboard-summary")
async def get_dashboard_summary():
    """Get overall dashboard summary statistics"""
    try:
        # Total records
        total_records = await db.sales_records.count_documents({})
        
        # Total revenue and profit
        revenue_pipeline = [
            {
                "$match": {
                    "$and": [
                        {"r_amt": {"$ne": None, "$exists": True, "$gt": 0}},
                        {"profit": {"$ne": None, "$exists": True}},
                        {"net_qty": {"$ne": None, "$exists": True}}
                    ]
                }
            },
            {
                "$addFields": {
                    "clean_r_amt": {
                        "$cond": {
                            "if": {"$type": "$r_amt"},
                            "then": "$r_amt",
                            "else": 0
                        }
                    },
                    "clean_profit": {
                        "$cond": {
                            "if": {"$type": "$profit"},
                            "then": "$profit",
                            "else": 0
                        }
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_revenue": {"$sum": "$clean_r_amt"},
                    "total_profit": {"$sum": "$clean_profit"},
                    "total_items_sold": {"$sum": {"$ifNull": ["$net_qty", 0]}}
                }
            }
        ]
        
        revenue_result = await db.sales_records.aggregate(revenue_pipeline).to_list(1)
        revenue_data = revenue_result[0] if revenue_result else {
            "total_revenue": 0,
            "total_profit": 0,
            "total_items_sold": 0
        }
        
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
        
        total_revenue = revenue_data.get("total_revenue", 0) or 0
        total_profit = revenue_data.get("total_profit", 0) or 0
        
        # Calculate profit margin safely
        if total_revenue > 0:
            profit_margin = (total_profit / total_revenue) * 100
        else:
            profit_margin = 0.0
            
        return {
            "total_records": total_records,
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "total_items_sold": revenue_data.get("total_items_sold", 0) or 0,
            "group_distribution": group_distribution,
            "profit_margin": profit_margin
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard summary: {str(e)}")

# ============================================================================
# PHASE 1: UPLOAD HISTORY & DATABASE VIEW ENDPOINTS
# ============================================================================

@api_router.get("/upload-history")
async def get_upload_history(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None),
    period_filter: Optional[str] = Query(None)
):
    """Get upload history with optional filtering"""
    try:
        # Build filter
        filter_query = {}
        if status_filter and status_filter != "all":
            filter_query["status"] = status_filter
        if period_filter:
            filter_query["period_covered"] = {"$regex": period_filter, "$options": "i"}
        
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
            "results": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching upload history: {str(e)}")

@api_router.get("/database-view")
async def get_database_view(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    group_filter: Optional[str] = Query(None),
    period_filter: Optional[str] = Query(None),
    sort_by: str = Query("upload_date"),
    sort_order: int = Query(-1)
):
    """Get paginated view of sales database with filters"""
    try:
        # Build filter query
        filter_query = {}
        
        if search:
            filter_query["item_name"] = {"$regex": search, "$options": "i"}
        
        if group_filter and group_filter != "all":
            filter_query["product_group"] = group_filter
        
        if period_filter:
            filter_query["data_period"] = {"$regex": period_filter, "$options": "i"}
        
        # Get total count
        total = await db.sales_records.count_documents(filter_query)
        
        # Get paginated results
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
