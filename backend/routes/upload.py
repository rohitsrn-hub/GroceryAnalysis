"""
Upload routes — file upload and history endpoints.
Extracted from server.py L1617-1805, L4589-4632.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form

from config import logger
from database import db
from models.sales import SalesRecord, UploadHistory
from services.excel_processor import process_excel_data, extract_period_from_filename

router = APIRouter(prefix="/api", tags=["upload"])


async def check_duplicate_upload(period: str):
    """Check if data for this period has already been uploaded."""
    return await db.upload_history.find_one({
        "period_covered": period,
        "status": "success",
    })


@router.post("/upload-sales-data")
async def upload_sales_data(
    file: UploadFile = File(...),
    upload_type: str = Form("historical"),
    data_date: Optional[str] = Form(None),
    upload_source: str = Form("analytics"),
):
    """Upload and process sales data from Excel file with history logging."""
    start_time = datetime.now()
    upload_id = str(uuid.uuid4())

    logger.info(
        f"Upload attempt: filename={file.filename}, upload_id={upload_id}, "
        f"type={upload_type}, data_date={data_date}, source={upload_source}"
    )

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Only Excel files (.xlsx or .xls) are supported.",
        )

    period_info = {}
    contents = b""

    try:
        contents = await file.read()
        file_size_kb = len(contents) / 1024

        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")

        # Extract period from filename
        period_info = extract_period_from_filename(file.filename)

        # Duplicate check
        existing = None
        if upload_type == "daily" and data_date:
            parsed = datetime.strptime(data_date, "%Y-%m-%d")
            existing = await db.upload_history.find_one({
                "upload_type": "daily",
                "data_date": {"$gte": parsed, "$lt": parsed + timedelta(days=1)},
                "status": "success",
            })
        elif upload_type == "historical" and period_info.get("period"):
            existing = await check_duplicate_upload(period_info["period"])

        if existing:
            date_info = ""
            if existing.get('upload_date'):
                date_info = f" (uploaded on {existing['upload_date']})"

            detail = (
                f"Data for date '{data_date}' has already been uploaded{date_info}."
                if upload_type == "daily" else
                f"Data for period '{period_info['period']}' already exists{date_info}."
            )
            raise HTTPException(status_code=400, detail=detail)

        # Process Excel data
        records, net_amt, w_amt = process_excel_data(contents, file.filename, period_info)

        if not records:
            raise HTTPException(
                status_code=400,
                detail="No valid records found. Check the data format.",
            )

        # Add upload metadata to each record
        for record in records:
            record['upload_batch_id'] = upload_id
            record['upload_date'] = datetime.now(timezone.utc)
            record['upload_source'] = upload_source

        # Insert into MongoDB
        result = await db.sales_records.insert_many(
            [SalesRecord(**r).dict() for r in records]
        )

        processing_time = (datetime.now() - start_time).total_seconds()

        # Parse data_date for upload history
        parsed_data_date = None
        if upload_type == "daily" and data_date:
            try:
                parsed_data_date = datetime.strptime(data_date, "%Y-%m-%d")
            except ValueError:
                logger.warning(f"Invalid data_date format: {data_date}")

        # Log upload history
        upload_record = UploadHistory(
            id=upload_id,
            filename=file.filename,
            period_covered=period_info.get("period"),
            data_type=period_info.get("data_type"),
            upload_type=upload_type,
            data_date=parsed_data_date,
            records_count=len(records),
            status="success",
            file_size_kb=file_size_kb,
            processing_time_seconds=processing_time,
            net_amt=net_amt,
            w_amt=w_amt,
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
            "period_covered": period_info.get("period"),
            "data_type": period_info.get("data_type"),
            "net_amt": net_amt,
        }

    except HTTPException as he:
        processing_time = (datetime.now() - start_time).total_seconds()
        try:
            rec = UploadHistory(
                id=upload_id,
                filename=file.filename,
                period_covered=period_info.get("period"),
                data_type=period_info.get("data_type"),
                records_count=0,
                status="failed",
                error_message=str(he.detail),
                file_size_kb=len(contents) / 1024 if contents else 0,
                processing_time_seconds=processing_time,
            )
            await db.upload_history.insert_one(rec.dict())
        except Exception as log_err:
            logger.error(f"Failed to log upload history: {log_err}")
        raise

    except Exception as e:
        logger.exception(f"Upload failed for file {file.filename}")
        error_message = str(e)

        if "Excel file format cannot be determined" in error_message:
            error_message = f"Cannot read Excel format for '{file.filename}'."
        elif "openpyxl" in error_message or "xlrd" in error_message:
            error_message = f"Excel library error: {error_message}"
        elif "authentication" in error_message.lower() or "mongo" in error_message.lower():
            error_message = "Database connection error. Please contact support."

        processing_time = (datetime.now() - start_time).total_seconds()
        try:
            rec = UploadHistory(
                id=upload_id,
                filename=file.filename,
                period_covered=period_info.get("period"),
                data_type=period_info.get("data_type"),
                records_count=0,
                status="failed",
                error_message=error_message,
                file_size_kb=len(contents) / 1024 if contents else 0,
                processing_time_seconds=processing_time,
            )
            await db.upload_history.insert_one(rec.dict())
        except Exception as log_err:
            logger.error(f"Failed to log upload history: {log_err}")

        raise HTTPException(
            status_code=400,
            detail=f"Failed to process file '{file.filename}': {error_message}",
        )


@router.get("/upload-history")
async def get_upload_history(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None),
    period_filter: Optional[str] = Query(None),
    data_date: Optional[str] = Query(None),
):
    """Get upload history with optional filtering."""
    try:
        filter_query = {}
        if status_filter and status_filter != "all":
            filter_query["status"] = status_filter
        if period_filter:
            filter_query["period_covered"] = {"$regex": period_filter, "$options": "i"}
        if data_date:
            target = datetime.strptime(data_date, "%Y-%m-%d")
            filter_query["data_date"] = {
                "$gte": target,
                "$lt": target + timedelta(days=1),
            }

        total = await db.upload_history.count_documents(filter_query)
        history = await db.upload_history.find(filter_query, {"_id": 0}) \
            .sort("upload_date", -1).skip(skip).limit(limit).to_list(limit)

        return {
            "total": total, "limit": limit, "skip": skip,
            "uploads": history, "results": history,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching upload history: {str(e)}",
        )
