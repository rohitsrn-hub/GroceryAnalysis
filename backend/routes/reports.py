"""
Report routes — comprehensive report, daily report, canteen extract, export.
Extracted from server.py L2277-2750, L3228-3385, L5459-5916.

These endpoints have heavy dependencies (openpyxl, reportlab, OpenAI)
so imports are kept lazy to avoid startup failures.
"""
import io
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response, FileResponse

from config import logger
from database import db
from services.period_service import format_period_display_name
from services.analytics_service import (
    get_abc_analysis,
    get_capital_blocking_analysis,
    get_group_analysis,
    get_fastest_selling_items,
    get_inventory_analysis,
)
from services.dashboard_service import get_dashboard_summary
from utils.formatting import format_indian_number, format_indian_currency
from utils.charts import generate_trend_bars, generate_daily_sales_line_graph

import tempfile

router = APIRouter(prefix="/api", tags=["reports"])


# ─── Export Data to Excel ────────────────────────────────────────────

@router.get("/export-data/{analysis_type}")
async def export_data_to_excel(
    analysis_type: str,
    group: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
):
    """Export analysis data to Excel file with group and period filters."""
    import openpyxl

    try:
        workbook = openpyxl.Workbook()
        ws = workbook.active

        if analysis_type == "abc":
            response = await get_abc_analysis(group=group, period=period)
            ws.title = "ABC Analysis"
            ws.append(["Item Code", "Item Name", "Group", "Category", "Revenue", "Revenue %", "Qty Sold", "Profit", "Capital Blocked"])
            for cat_name, items in response["abc_categories"].items():
                for item in items:
                    ws.append([
                        item["pluno"], item["item_name"], item["group"],
                        f"Category {cat_name}", item["total_revenue"],
                        f"{item['revenue_percentage']:.2f}%", item["total_qty_sold"],
                        item["total_profit"], item["capital_blocked"],
                    ])

        elif analysis_type == "capital-blocking":
            response = await get_capital_blocking_analysis(group=group, period=period)
            ws.title = "Capital Blocking Analysis"
            ws.append(["Item Code", "Item Name", "Group", "Capital Blocked", "Days to Sell", "Monthly Sales", "Risk Level", "Recommendation"])
            for item in response["capital_blocking_items"]:
                rec = "Liquidate" if item["risk_level"] == "CRITICAL" else "Discount" if item["risk_level"] == "HIGH" else "Monitor"
                ws.append([
                    item["_id"]["pluno"], item["_id"]["item_name"], item["_id"]["group"],
                    item["capital_blocked"],
                    item["days_to_sell"] if item["days_to_sell"] != 9999 else "∞",
                    item["avg_monthly_sales"], item["risk_level"], rec,
                ])

        elif analysis_type == "fastest-selling":
            items = await get_fastest_selling_items(limit=50, group=group, period=period)
            ws.title = "Fastest Selling Items"
            ws.append(["Item Code", "Item Name", "Group", "Total Sold", "Avg Monthly Sales", "Total Revenue", "Rank"])
            for i, item in enumerate(items, 1):
                ws.append([
                    item["item_code"], item["item_name"], item["group"],
                    item["total_sold"], item["avg_monthly_sales"],
                    item["total_revenue"], i,
                ])

        elif analysis_type == "group-analysis":
            response = await get_group_analysis(period=period)
            ws.title = "Group Performance Analysis"
            ws.append(["Group", "Items Count", "Total Revenue", "Total Profit", "Profit Margin %", "Top Performer"])
            for grp in response:
                top = grp["top_performers"][0]["item_name"] if grp["top_performers"] else "N/A"
                ws.append([
                    grp["group"], grp["item_count"], grp["total_revenue"],
                    grp["total_profit"], f"{grp['profit_margin']:.2f}%", top,
                ])

        elif analysis_type == "inventory-health":
            response = await get_inventory_analysis(period=period)
            ws.title = "Inventory Health Analysis"
            ws.append(["Type", "Item Code", "Item Name", "Group", "Capital Blocked", "Closing Stock", "Avg Cost"])
            for item in response.get("dead_inventory", []):
                ws.append([
                    "Dead Inventory",
                    item["_id"].get("pluno", "N/A"), item["_id"].get("item_name", "N/A"),
                    item["_id"].get("group", "N/A"), item.get("capital_blocked", 0),
                    item.get("avg_closing_stock", 0), item.get("avg_cost", 0),
                ])
            for item in response.get("slow_moving", []):
                ws.append([
                    "Slow Moving",
                    item["_id"].get("pluno", "N/A"), item["_id"].get("item_name", "N/A"),
                    "N/A", 0, 0, item.get("avg_cost", 0),
                ])
            for item in response.get("high_cost_poor_performance", []):
                ws.append([
                    "High Cost Poor Performance",
                    item["_id"].get("pluno", "N/A"), item["_id"].get("item_name", "N/A"),
                    "N/A", 0, 0, item.get("avg_cost", 0),
                ])
        else:
            raise HTTPException(status_code=400, detail="Invalid analysis type")

        buf = io.BytesIO()
        workbook.save(buf)
        buf.seek(0)
        fname = f"{analysis_type}-analysis-{group if group else 'all'}.xlsx"

        return StreamingResponse(
            io.BytesIO(buf.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")


# ─── Extract Canteen Summary (GPT-4o Image) ─────────────────────────

@router.post("/extract-canteen-summary")
async def extract_canteen_summary(file: UploadFile = File(...)):
    """Extract grocery and liquor sales from CSD canteen summary image."""
    import base64

    try:
        logger.info(f"Received image upload: {file.filename}, type: {file.content_type}")
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')
        mime = file.content_type or 'image/jpeg'

        openai_key = os.environ.get('OPENAI_API_KEY')
        emergent_key = os.environ.get('EMERGENT_LLM_KEY')

        if not openai_key and not emergent_key:
            raise HTTPException(
                status_code=500,
                detail="API key not configured. Set OPENAI_API_KEY or EMERGENT_LLM_KEY.",
            )

        prompt = """Analyze this Canteen Summary image and extract the following data:
1. Today's Bill Amount - Grocery (look for "Today's Bill Amount" row, Grocery column)
2. Today's Bill Amount - Liquor (look for "Today's Bill Amount" row, Liquor column)

Return ONLY a JSON object with these exact fields:
{
  "grocery_sales": <number>,
  "liquor_sales": <number>
}

Remove commas and currency symbols from numbers. Return only the JSON, nothing else."""

        response_text = None

        if openai_key:
            from openai import OpenAI
            logger.info("Using direct OpenAI SDK for image extraction")
            client = OpenAI(api_key=openai_key)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract numerical data from images accurately."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64_image}"}},
                    ]},
                ],
                max_tokens=1024,
            )
            response_text = resp.choices[0].message.content
        else:
            import httpx
            logger.info("Using Emergent LLM proxy for image extraction")
            proxy_url = os.environ.get('INTEGRATION_PROXY_URL', 'https://integrations.emergentagent.com').rstrip('/')
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a data extraction assistant."},
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64_image}"}},
                    ]},
                ],
                "max_tokens": 1024,
            }
            try:
                async with httpx.AsyncClient(timeout=45.0) as hc:
                    resp = await hc.post(
                        f"{proxy_url}/llm/chat/completions",
                        json=payload,
                        headers={"Authorization": f"Bearer {emergent_key}"},
                    )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="AI extraction timed out.")
            except httpx.HTTPError as he:
                raise HTTPException(status_code=502, detail=f"AI proxy error: {str(he)[:200]}")

            if resp.status_code >= 400:
                body = resp.text or ""
                try:
                    ej = resp.json()
                    err_msg = ej.get("error", {}).get("message") if isinstance(ej.get("error"), dict) else ej.get("error") or body
                except Exception:
                    err_msg = body
                if resp.status_code == 400 and "budget" in str(err_msg).lower():
                    raise HTTPException(status_code=402, detail="Emergent Key out of credits.")
                if resp.status_code == 502:
                    raise HTTPException(status_code=502, detail="AI proxy 502 — likely budget exhaustion.")
                raise HTTPException(status_code=resp.status_code, detail=f"AI failed: {str(err_msg)[:300]}")

            try:
                response_text = resp.json()["choices"][0]["message"]["content"]
            except Exception as pe:
                raise HTTPException(status_code=500, detail=f"Malformed LLM response: {pe}")

        logger.info(f"LLM response: {str(response_text)[:200]}...")
        text = str(response_text).strip()
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        extracted = json.loads(json_match.group()) if json_match else json.loads(text)

        return {
            "success": True,
            "data": {
                "grocery_sales": float(extracted.get("grocery_sales", 0)),
                "liquor_sales": float(extracted.get("liquor_sales", 0)),
            },
        }
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {e}")
    except Exception as e:
        logger.error(f"Error extracting canteen summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to extract data: {str(e)}")


# ─── Generate Daily Report (PDF) ────────────────────────────────────

@router.post("/generate-daily-report")
async def generate_daily_sales_report(
    date: str,
    liquor_sales: float = 0.0,
    previous_bank_amount: Optional[float] = None,
    grocery_sales: Optional[float] = None,
    previous_stock_value: Optional[float] = None,
    current_stock_value: Optional[float] = None,
    notes: Optional[str] = None,
):
    """Generate PDF daily sales report with financial data creation."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
    from io import BytesIO

    try:
        report_date = datetime.strptime(date, "%Y-%m-%d")
        calculated_stock_value = None

        # Auto-fetch baseline values from last report if not supplied
        last_report = None
        if previous_bank_amount is None or previous_stock_value is None:
            last_report = await db.financial_data.find_one(
                {"date": {"$lt": report_date}},
                sort=[("date", -1)], projection={"_id": 0},
            )

        if previous_bank_amount is None:
            if last_report and last_report.get("current_bank_amount") is not None:
                previous_bank_amount = float(last_report["current_bank_amount"])
                logger.info(f"Auto-fetched previous_bank_amount from last report: ₹{previous_bank_amount:,.2f}")
            else:
                raise HTTPException(status_code=400, detail="previous_bank_amount required — no prior report exists.")

        if previous_stock_value is None and last_report and last_report.get("current_stock_value") is not None:
            previous_stock_value = float(last_report["current_stock_value"])

        # Get today's W_Amt for stock calculation
        todays_w_amt = 0.0
        daily_upload = await db.upload_history.find_one({
            "upload_type": "daily",
            "data_date": {"$gte": report_date, "$lt": report_date + timedelta(days=1)},
            "status": "success",
        })
        if daily_upload and daily_upload.get("w_amt") is not None:
            todays_w_amt = float(daily_upload["w_amt"])

        if current_stock_value is not None:
            calculated_stock_value = current_stock_value
        elif previous_stock_value is not None and todays_w_amt > 0:
            calculated_stock_value = previous_stock_value - todays_w_amt

        # Create financial data via inline logic (avoids circular import to server.py)
        grocery = grocery_sales or 0.0
        if grocery_sales is None and daily_upload:
            if daily_upload.get("net_amt") is not None:
                grocery = float(daily_upload["net_amt"])
            else:
                pipe = [
                    {"$match": {"upload_batch_id": daily_upload["id"]}},
                    {"$group": {"_id": None, "total_sales": {"$sum": {"$ifNull": ["$r_amt", 0]}}}},
                ]
                res = await db.sales_records.aggregate(pipe).to_list(1)
                if res:
                    grocery = float(res[0].get("total_sales", 0))

        total_sales = grocery + liquor_sales
        current_bank = previous_bank_amount + total_sales

        fin_id = str(uuid.uuid4())
        existing = await db.financial_data.find_one({
            "date": {"$gte": report_date, "$lt": report_date + timedelta(days=1)},
        })
        if existing:
            fin_id = existing.get("id", fin_id)

        fin_record = {
            "id": fin_id, "date": report_date,
            "grocery_sales": grocery, "liquor_sales": liquor_sales,
            "total_sales": total_sales,
            "previous_bank_amount": previous_bank_amount,
            "current_bank_amount": current_bank,
            "previous_stock_value": previous_stock_value,
            "current_stock_value": calculated_stock_value,
            "notes": notes,
        }

        if existing:
            await db.financial_data.update_one({"id": fin_id}, {"$set": fin_record})
        else:
            await db.financial_data.insert_one(fin_record)

        # Build PDF
        buf = BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20,
                                     textColor=colors.HexColor('#1e40af'), spaceAfter=30,
                                     alignment=TA_CENTER, fontName='Helvetica-Bold')
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14,
                                       textColor=colors.HexColor('#1e40af'), spaceAfter=12,
                                       spaceBefore=12, fontName='Helvetica-Bold')

        elements.append(Paragraph(f"Sale Summary for {report_date.strftime('%d %B %Y')}", title_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Sales table
        elements.append(Paragraph("Daily Sales Breakdown", heading_style))
        sales_data = [
            ['Description', 'Amount'],
            ['Grocery Sales for the day', format_indian_currency(grocery)],
            ['Liquor Sales for the day', format_indian_currency(liquor_sales)],
            ['Total Sales for the day (D)', format_indian_currency(total_sales)],
        ]
        st = Table(sales_data, colWidths=[4 * inch, 2 * inch])
        st.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eff6ff')),
        ]))
        elements.append(st)
        elements.append(Spacer(1, 0.3 * inch))

        # Bank table
        prev_date_str = (report_date - timedelta(days=1)).strftime('%d %B %Y')
        elements.append(Paragraph("Bank Account Summary", heading_style))
        bank_data = [
            ['Description', 'Amount'],
            [f'Amount in Bank as on {prev_date_str} (Y)', format_indian_currency(previous_bank_amount)],
            [f'Total Amount in Bank on {report_date.strftime("%d %B %Y")} (Y+D)', format_indian_currency(current_bank)],
        ]
        bt = Table(bank_data, colWidths=[4 * inch, 2 * inch])
        bt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
        ]))
        elements.append(bt)

        # Stock table (if applicable)
        if previous_stock_value is not None or calculated_stock_value is not None:
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph("Inventory Stock Valuation", heading_style))
            stock_rows = [['Description', 'Value']]
            if previous_stock_value is not None:
                stock_rows.append([f'Stock Value on {prev_date_str}', format_indian_currency(previous_stock_value)])
            if todays_w_amt > 0 and calculated_stock_value is not None:
                stock_rows.append(["Today's Cost of Goods Sold (W_Amt)", format_indian_currency(todays_w_amt)])
            if calculated_stock_value is not None:
                stock_rows.append([f'Stock Value on {report_date.strftime("%d %B %Y")}', format_indian_currency(calculated_stock_value)])
            svt = Table(stock_rows, colWidths=[4 * inch, 2 * inch])
            svt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef3c7')),
            ]))
            elements.append(svt)

        # Notes
        if notes:
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph("Additional Notes", heading_style))
            elements.append(Paragraph(notes, styles['Normal']))

        # Footer
        elements.append(Spacer(1, 0.5 * inch))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8,
                                       textColor=colors.grey, alignment=TA_CENTER)
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y at %I:%M %p')}", footer_style))

        doc.build(elements)
        pdf_data = buf.getvalue()
        buf.close()

        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=daily_sales_report_{date}.pdf"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating daily sales report PDF")
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


# ─── Comprehensive Business Report (Excel/PDF) ───────────────────────

@router.get("/comprehensive-report")
async def generate_comprehensive_report(
    format: str = Query("excel"),
    periods: Optional[str] = Query(None)  # Comma-separated list of periods
):
    """Generate comprehensive business analysis report using existing API calculations"""
    import openpyxl
    try:
        # Parse periods parameter
        period_list = []
        if periods:
            period_list = [p.strip() for p in periods.split(',') if p.strip()]
        
        # Determine period label for report title - format period values to display names
        if not period_list or len(period_list) == 0:
            period_label = " - All Periods"
        elif len(period_list) == 1:
            # Format single period
            formatted_period = format_period_display_name(period_list[0])
            period_label = f" - {formatted_period}"
        elif len(period_list) == 2:
            # Format two periods
            formatted_1 = format_period_display_name(period_list[0])
            formatted_2 = format_period_display_name(period_list[1])
            period_label = f" - {formatted_1} & {formatted_2}"
        elif len(period_list) <= 5:
            # Format multiple periods
            formatted_periods = []
            for p in period_list:
                formatted_periods.append(format_period_display_name(p))
            period_label = f" - {', '.join(formatted_periods)}"
        else:
            # Too many periods, show range or count with formatted names
            formatted_first = format_period_display_name(period_list[0])
            formatted_last = format_period_display_name(period_list[-1])
            period_label = f" - {formatted_first} to {formatted_last} ({len(period_list)} periods)"
        
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
        
        # ==========================================
        # MONTHLY INSIGHTS DATA (for enhanced reports)
        # ==========================================
        monthly_insights = {}
        
        # Only calculate monthly insights if specific period(s) selected
        if period_list and len(period_list) > 0:
            # Get the primary period (first one for single month view)
            primary_period = period_list[0]
            
            # Parse primary period to get date range
            if len(primary_period) == 7 and '-' in primary_period:  # Format YYYY-MM
                year, month = primary_period.split('-')
                year, month = int(year), int(month)
                period_start = datetime(year, month, 1)
                if month == 12:
                    period_end = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = datetime(year, month + 1, 1) - timedelta(days=1)
                
                # 1. Calculate average daily sale (from daily uploads in this period)
                daily_uploads = await db.upload_history.find({
                    "upload_type": "daily",
                    "status": "success",
                    "data_date": {"$gte": period_start, "$lte": period_end}
                }).to_list(None)
                
                daily_sales = [float(u.get('net_amt', 0) or 0) for u in daily_uploads]
                avg_daily_sale = sum(daily_sales) / len(daily_sales) if daily_sales else 0
                total_days = len(daily_sales)
                
                monthly_insights['avg_daily_sale'] = avg_daily_sale
                monthly_insights['total_days_data'] = total_days
                monthly_insights['daily_sales_data'] = [
                    {'day': u.get('data_date').day, 'sales': float(u.get('net_amt', 0) or 0), 'date': u.get('data_date').strftime('%Y-%m-%d')}
                    for u in daily_uploads if u.get('data_date')
                ]
                
                # 2. Get bank balance from financial_data on last day of month
                last_financial = await db.financial_data.find_one(
                    {"date": {"$gte": period_start, "$lte": period_end}},
                    sort=[("date", -1)]
                )
                if last_financial:
                    monthly_insights['bank_balance_last_day'] = last_financial.get('current_bank_amount', 0)
                    monthly_insights['bank_balance_date'] = last_financial.get('date').strftime('%Y-%m-%d') if last_financial.get('date') else None
                else:
                    monthly_insights['bank_balance_last_day'] = 0
                    monthly_insights['bank_balance_date'] = None
                
                # 3. Stock value reduction (first day vs last day)
                first_financial = await db.financial_data.find_one(
                    {"date": {"$gte": period_start, "$lte": period_end}},
                    sort=[("date", 1)]
                )
                if first_financial and last_financial:
                    first_stock = first_financial.get('current_stock_value', 0) or 0
                    last_stock = last_financial.get('current_stock_value', 0) or 0
                    monthly_insights['stock_value_first_day'] = first_stock
                    monthly_insights['stock_value_last_day'] = last_stock
                    monthly_insights['stock_value_reduction'] = first_stock - last_stock
                    monthly_insights['stock_first_date'] = first_financial.get('date').strftime('%Y-%m-%d') if first_financial.get('date') else None
                    monthly_insights['stock_last_date'] = last_financial.get('date').strftime('%Y-%m-%d') if last_financial.get('date') else None
                else:
                    monthly_insights['stock_value_first_day'] = 0
                    monthly_insights['stock_value_last_day'] = 0
                    monthly_insights['stock_value_reduction'] = 0
                
                # 4. Get last 3 months revenue/profit trend
                three_month_trend = []
                for i in range(3):
                    # Calculate month offset
                    trend_month = month - i
                    trend_year = year
                    if trend_month < 1:
                        trend_month += 12
                        trend_year -= 1
                    
                    trend_period = f"{trend_year}-{trend_month:02d}"
                    
                    # Get totals for this month
                    trend_pipeline = [
                        {"$match": {"data_period": trend_period, "upload_source": {"$ne": "forecast"}}},
                        {"$group": {
                            "_id": None,
                            "total_revenue": {"$sum": "$r_amt"},
                            "total_profit": {"$sum": "$profit"}
                        }}
                    ]
                    trend_result = await db.sales_records.aggregate(trend_pipeline).to_list(1)
                    
                    if trend_result:
                        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                        three_month_trend.insert(0, {
                            'period': trend_period,
                            'month_name': f"{month_names[trend_month-1]} {trend_year}",
                            'revenue': trend_result[0].get('total_revenue', 0) or 0,
                            'profit': trend_result[0].get('total_profit', 0) or 0
                        })
                
                monthly_insights['three_month_trend'] = three_month_trend
        
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
            
            # Add Monthly Insights if available
            if monthly_insights:
                ws_summary.append([""])
                ws_summary.append(["MONTHLY INSIGHTS"])
                if 'avg_daily_sale' in monthly_insights:
                    ws_summary.append(["Average Daily Sale", format_indian_number(monthly_insights['avg_daily_sale'], currency=True)])
                    ws_summary.append(["Days with Data", f"{monthly_insights.get('total_days_data', 0)}"])
                if monthly_insights.get('bank_balance_last_day'):
                    ws_summary.append(["Bank Balance (Last Day)", format_indian_number(monthly_insights['bank_balance_last_day'], currency=True)])
                    ws_summary.append(["Bank Balance Date", monthly_insights.get('bank_balance_date', 'N/A')])
                if monthly_insights.get('stock_value_first_day') or monthly_insights.get('stock_value_last_day'):
                    ws_summary.append(["Stock Value (First Day)", format_indian_number(monthly_insights.get('stock_value_first_day', 0), currency=True)])
                    ws_summary.append(["Stock Value (Last Day)", format_indian_number(monthly_insights.get('stock_value_last_day', 0), currency=True)])
                    reduction = monthly_insights.get('stock_value_reduction', 0)
                    ws_summary.append(["Stock Value Reduction", format_indian_number(reduction, currency=True) + (" (Increased)" if reduction < 0 else " (Decreased)")])
            
            # Add 3-Month Trend if available
            if monthly_insights.get('three_month_trend'):
                ws_summary.append([""])
                ws_summary.append(["3-MONTH REVENUE & PROFIT TREND"])
                ws_summary.append(["Month", "Revenue", "Profit"])
                for trend in monthly_insights['three_month_trend']:
                    ws_summary.append([
                        trend['month_name'],
                        format_indian_number(trend['revenue'], currency=True),
                        format_indian_number(trend['profit'], currency=True)
                    ])
            
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
            for item in capital_analysis.get('capital_blocking_items', [])[:50]:
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
                    <td>{format_indian_number(item['total_revenue'], currency=True)}</td>
                    <td>{format_indian_number(item['total_profit'], currency=True)}</td>
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
                    <td>{format_indian_number(group['total_revenue'], currency=True)}</td>
                    <td>{format_indian_number(group['total_profit'], currency=True)}</td>
                    <td>{group['profit_margin']:.2f}%</td>
                </tr>
                """
            
            # Build Monthly Insights HTML if available
            monthly_insights_html = ""
            if monthly_insights:
                # 3-month trend table rows
                trend_rows = ""
                for t in monthly_insights.get('three_month_trend', []):
                    margin = round(((t['profit'] / t['revenue']) * 100) if t['revenue'] > 0 else 0, 2)
                    trend_rows += f"""
                    <tr>
                        <td><strong>{t['month_name']}</strong></td>
                        <td>{format_indian_number(t['revenue'], currency=True)}</td>
                        <td>{format_indian_number(t['profit'], currency=True)}</td>
                        <td>{margin}%</td>
                    </tr>
                    """
                
                stock_change_color = '#28a745' if monthly_insights.get('stock_value_reduction', 0) > 0 else '#dc3545'
                stock_change_text = 'Decreased ✓' if monthly_insights.get('stock_value_reduction', 0) > 0 else 'Increased ↑'
                
                monthly_insights_html = f"""
                <div class="section">
                    <h2 class="section-title">📅 Monthly Insights</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px;">
                        <div class="metric">
                            <div>Average Daily Sale</div>
                            <div class="metric-value">{format_indian_number(monthly_insights.get('avg_daily_sale', 0), currency=True)}</div>
                        </div>
                        <div class="metric">
                            <div>Bank Balance (Last Day)</div>
                            <div class="metric-value">{format_indian_number(monthly_insights.get('bank_balance_last_day', 0), currency=True)}</div>
                        </div>
                        <div class="metric">
                            <div>Stock Value Change</div>
                            <div class="metric-value" style="color: {stock_change_color};">{format_indian_number(abs(monthly_insights.get('stock_value_reduction', 0)), currency=True)}</div>
                            <div style="font-size: 12px; color: #666;">{stock_change_text}</div>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2 class="section-title">📈 3-Month Trend</h2>
                    <table class="table">
                        <tr><th>Month</th><th>Revenue</th><th>Profit</th><th>Margin</th></tr>
                        {trend_rows}
                    </table>
                    <div style="margin-top: 20px;">
                        <svg viewBox="0 0 400 200" style="width: 100%; max-width: 600px; height: auto; margin: 0 auto; display: block;">
                            <rect width="400" height="200" fill="#f8f9fa"/>
                            {generate_trend_bars(monthly_insights.get('three_month_trend', []))}
                        </svg>
                    </div>
                </div>
                
                <div class="section">
                    <h2 class="section-title">📊 Daily Sales Trend</h2>
                    {generate_daily_sales_line_graph(monthly_insights.get('daily_sales_data', []))}
                </div>
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
                    .table th {{ background-color: #667eea; color: white; }}
                    .metric {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                    .recommendation {{ background-color: #fff3cd; padding: 12px; margin: 8px 0; border-left: 4px solid #ffc107; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏪 URC 101 Area - Comprehensive Sales Analysis Report{period_label}</h1>
                    <p>Generated on: {datetime.now().strftime("%d %B %Y, %H:%M:%S")}</p>
                </div>
                
                <div class="section">
                    <h2 class="section-title">📊 Executive Summary</h2>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="metric"><div>Total Revenue</div><div class="metric-value">{format_indian_number(dashboard_summary.get('total_revenue', 0), currency=True)}</div></div>
                        <div class="metric"><div>Total Profit</div><div class="metric-value">{format_indian_number(current_profit, currency=True)}</div></div>
                        <div class="metric"><div>Profit Margin</div><div class="metric-value">{current_margin:.2f}%</div></div>
                        <div class="metric"><div>Items Sold</div><div class="metric-value">{dashboard_summary.get('total_items_sold', 0):,}</div></div>
                    </div>
                </div>
                
                {monthly_insights_html}
                
                <div class="section">
                    <h2 class="section-title">📈 ABC Analysis</h2>
                    <table class="table">
                        <tr><th>Category</th><th>Items</th><th>% Items</th><th>Revenue</th><th>Strategy</th></tr>
                        <tr><td>Category A</td><td>{cat_a.get('item_count', 0)}</td><td>{cat_a.get('percentage_items', 0):.1f}%</td><td>{format_indian_number(cat_a.get('revenue', 0), currency=True)}</td><td>FOCUS: Ensure stock</td></tr>
                        <tr><td>Category B</td><td>{cat_b.get('item_count', 0)}</td><td>{cat_b.get('percentage_items', 0):.1f}%</td><td>{format_indian_number(cat_b.get('revenue', 0), currency=True)}</td><td>MONITOR: Balance levels</td></tr>
                        <tr><td>Category C</td><td>{cat_c.get('item_count', 0)}</td><td>{cat_c.get('percentage_items', 0):.1f}%</td><td>{format_indian_number(cat_c.get('revenue', 0), currency=True)}</td><td>REVIEW: Reduce stock</td></tr>
                    </table>
                </div>
                
                <div class="section">
                    <h2 class="section-title">⭐ Top Performers</h2>
                    <table class="table">
                        <tr><th>#</th><th>Code</th><th>Name</th><th>Sold</th><th>Revenue</th><th>Profit</th><th>Margin %</th></tr>
                        {top_performers_html}
                    </table>
                </div>
                
                <div class="section">
                    <h2 class="section-title">🏷️ Group Performance</h2>
                    <table class="table">
                        <tr><th>Group</th><th>Items</th><th>Revenue</th><th>Profit</th><th>Margin %</th></tr>
                        {group_html}
                    </table>
                </div>
                
                <div class="section">
                    <h2 class="section-title">💡 Recommendations</h2>
                    <div class="recommendation">
                        <strong>Capital Optimization:</strong> {critical_items} items blocking {format_indian_number(total_blocked, currency=True)}.<br>
                        <strong>Action:</strong> Liquidate slow-movers to recover est. {format_indian_number(total_blocked * 0.7, currency=True)}.
                    </div>
                    <div class="recommendation">
                        <strong>Profit Plan:</strong> Focus on Category A (80% revenue). Negotiate volume discounts for 5-7% profit boost.
                    </div>
                </div>
            </body>
            </html>
            """
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
            temp_file.write(html_content)
            temp_file.close()
            
            return FileResponse(
                temp_file.name,
                media_type='text/html',
                headers={"Content-Disposition": "attachment; filename=URC101-Comprehensive-Report.html"},
                filename="URC101-Comprehensive-Report.html"
            )
        else:
            return {"message": "Invalid format. Use 'excel' or 'pdf'."}
            
    except Exception as e:
        logger.exception("Error generating comprehensive report")
        raise HTTPException(status_code=500, detail=str(e))
