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
    o_b: Optional[str] = None  # Opening Balance
    closing_stock: Optional[str] = None
    net_tax: Optional[float] = None
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    
    pluno_str = str(pluno)
    if pluno_str.startswith("I/"):
        return "Group I"
    elif pluno_str.startswith("II/"):
        return "Group II"
    elif pluno_str.startswith("III/"):
        return "Group III"
    elif pluno_str.startswith("IV/"):
        return "Group IV"
    elif pluno_str.startswith("VI/"):
        return "Group VI"
    return "Unknown"

def process_excel_data(file_content: bytes, filename: str) -> List[Dict]:
    """Process uploaded Excel file and return structured data"""
    try:
        df = pd.read_excel(BytesIO(file_content))
        
        # Standardize column names
        column_mapping = {
            'SNo': 's_no',
            'S.No': 's_no', 
            'GP_Index_No': 'gp_index_no',
            'GP_Index': 'gp_index_no',
            'pluno': 'pluno',
            'Item_Name': 'item_name',
            'W_Rate': 'w_rate',
            'R_Rate': 'r_rate',
            'Qty': 'qty',
            'Refund_Qty': 'refund_qty',
            'Net_Qty': 'net_qty',
            'R_Amt': 'r_amt',
            'W_Amt': 'w_amt',
            'Profit': 'profit',
            'O_B': 'o_b',
            'Closing_Stock': 'closing_stock',
            'Net_Tax': 'net_tax',
            'Net-Tax': 'net_tax'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Extract data period from filename
        data_period = filename.replace('.xlsx', '').replace('.xls', '')
        
        records = []
        for _, row in df.iterrows():
            # Skip empty rows
            if pd.isna(row.get('pluno')) and pd.isna(row.get('item_name')):
                continue
                
            def safe_float(value):
                if pd.isna(value):
                    return None
                try:
                    # Handle string values with quotes or other formatting
                    str_val = str(value).replace("'", "").replace('"', "").strip()
                    return float(str_val) if str_val and str_val != 'nan' else None
                except (ValueError, TypeError):
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
                'o_b': str(row.get('o_b')) if not pd.isna(row.get('o_b')) else None,
                'closing_stock': str(row.get('closing_stock')) if not pd.isna(row.get('closing_stock')) else None,
                'net_tax': safe_float(row.get('net_tax')),
                'data_period': data_period,
                'product_group': extract_group_from_pluno(row.get('gp_index_no') or row.get('pluno'))
            }
            
            # Clean the record
            record = prepare_for_mongo(record)
            records.append(record)
        
        return records
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing Excel file: {str(e)}")

# API Routes
@api_router.post("/upload-sales-data")
async def upload_sales_data(file: UploadFile = File(...)):
    """Upload and process sales data from Excel file"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        records = process_excel_data(contents, file.filename)
        
        if records:
            # Insert into MongoDB
            result = await db.sales_records.insert_many([SalesRecord(**record).dict() for record in records])
            return {
                "message": f"Successfully uploaded {len(records)} records",
                "file_name": file.filename,
                "records_count": len(records),
                "inserted_ids": len(result.inserted_ids)
            }
        else:
            raise HTTPException(status_code=400, detail="No valid records found in the file")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@api_router.get("/fastest-selling-items")
async def get_fastest_selling_items(limit: int = Query(10, ge=1, le=50)):
    """Get fastest selling items with seasonal patterns"""
    try:
        pipeline = [
            {"$match": {"net_qty": {"$ne": None, "$exists": True}}},
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
        
        # Dead inventory (no sales)
        pipeline_dead = [
            {
                "$group": {
                    "_id": {"pluno": "$pluno", "item_name": "$item_name"},
                    "total_sold": {"$sum": "$net_qty"},
                    "avg_cost": {"$avg": "$w_rate"}
                }
            },
            {"$match": {"total_sold": {"$lte": 0}}},
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
    # Get historical data
    pipeline = [
        {
            "$group": {
                "_id": {"pluno": "$pluno", "item_name": "$item_name", "period": "$data_period"},
                "total_sold": {"$sum": "$net_qty"}
            }
        },
        {"$sort": {"_id.pluno": 1, "_id.period": 1}}
    ]
    
    historical_data = await db.sales_records.aggregate(pipeline).to_list(None)
    
    # Group by item and calculate trend
    forecasts = {}
    items_data = defaultdict(list)
    
    for record in historical_data:
        item_key = f"{record['_id']['pluno']}|{record['_id']['item_name']}"
        items_data[item_key].append(record['total_sold'])
    
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
            
            pluno, item_name = item_key.split('|', 1)
            forecasts[item_key] = {
                "pluno": pluno,
                "item_name": item_name,
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
                "_id": {"pluno": "$pluno", "item_name": "$item_name", "period": "$data_period"},
                "total_sold": {"$sum": "$net_qty"}
            }
        },
        {"$sort": {"_id.pluno": 1, "_id.period": 1}}
    ]
    
    historical_data = await db.sales_records.aggregate(pipeline).to_list(None)
    
    forecasts = {}
    items_data = defaultdict(list)
    
    for record in historical_data:
        item_key = f"{record['_id']['pluno']}|{record['_id']['item_name']}"
        items_data[item_key].append(record['total_sold'])
    
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
            
            pluno, item_name = item_key.split('|', 1)
            forecasts[item_key] = {
                "pluno": pluno,
                "item_name": item_name,
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

@api_router.get("/dashboard-summary")
async def get_dashboard_summary():
    """Get overall dashboard summary statistics"""
    try:
        # Total records
        total_records = await db.sales_records.count_documents({})
        
        # Total revenue and profit
        revenue_pipeline = [
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
            "total_revenue": revenue_data.get("total_revenue", 0) or 0,
            "total_profit": revenue_data.get("total_profit", 0) or 0,
            "total_items_sold": revenue_data.get("total_items_sold", 0) or 0,
            "group_distribution": group_distribution,
            "profit_margin": (
                (revenue_data.get("total_profit", 0) or 0) / 
                (revenue_data.get("total_revenue", 1) or 1)
            ) * 100
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard summary: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
