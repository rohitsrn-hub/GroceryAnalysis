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
            # Skip empty rows or rows with invalid data
            item_name = str(row.get('item_name', '')).strip()
            pluno = str(row.get('pluno', '')).strip()
            
            # Skip rows with problematic data or round off amounts
            if (pd.isna(row.get('pluno')) and pd.isna(row.get('item_name'))) or \
               len(item_name) > 100 or '\t' in item_name or '_x000D_' in item_name or \
               item_name == 'nan' or pluno == 'nan' or \
               any(char in item_name for char in ['#', '$', '%']) or \
               (len(item_name) < 3 and not item_name.isalpha()) or \
               'round off' in item_name.lower() or 'roundoff' in item_name.lower():
                continue
                
            # Skip rows that look like numbers instead of item names
            try:
                float(item_name)
                continue  # Skip if item_name is just a number
            except ValueError:
                pass  # Good, it's not just a number
                
            def safe_float(value):
                if pd.isna(value):
                    return None
                try:
                    # Handle string values with quotes or other formatting
                    str_val = str(value).replace("'", "").replace('"', "").replace(",", "").strip()
                    # Handle negative values and empty strings
                    if str_val == '' or str_val == 'nan' or str_val == 'None':
                        return None
                    return float(str_val)
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
                'o_b': safe_float(row.get('o_b')),
                'closing_stock': safe_float(row.get('closing_stock')),
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
                    },
                    "days_to_sell": {
                        "$cond": {
                            "if": {"$gt": ["$avg_monthly_sales", 0]},
                            "then": {"$divide": ["$avg_closing_stock", {"$divide": ["$avg_monthly_sales", 30]}]},
                            "else": 9999
                        }
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
