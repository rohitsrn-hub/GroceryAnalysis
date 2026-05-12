"""
Financial health service — CRUD operations and calculations.
Extracted from server.py L5085-5460.

Handles:
- Financial data creation, retrieval, update, deletion
- Previous bank amount lookup
- Date range queries
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from database import db
from config import logger
from models.financial import FinancialData


async def create_financial_record(data: FinancialData) -> Dict[str, Any]:
    """Create or update financial data for a given date."""
    try:
        record_dict = data.model_dump()

        # Calculate total_sales if not provided
        if record_dict.get('total_sales', 0) == 0:
            record_dict['total_sales'] = (
                record_dict.get('grocery_sales', 0) +
                record_dict.get('liquor_sales', 0)
            )

        # Check if record exists for this date
        existing = await db.financial_data.find_one({
            "date": record_dict['date']
        })

        if existing:
            # Update existing record
            await db.financial_data.update_one(
                {"date": record_dict['date']},
                {"$set": record_dict}
            )
            logger.info(f"Updated financial record for {record_dict['date']}")
            return {
                "status": "updated",
                "message": "Financial data updated",
                "id": existing.get('id', record_dict['id'])
            }
        else:
            await db.financial_data.insert_one(record_dict)
            logger.info(f"Created financial record for {record_dict['date']}")
            return {
                "status": "created",
                "message": "Financial data created",
                "id": record_dict['id']
            }

    except Exception as e:
        logger.error(f"Error saving financial data: {str(e)}")
        raise


async def get_financial_data_by_date(date_str: str) -> Optional[Dict]:
    """Get financial data for a specific date."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        record = await db.financial_data.find_one(
            {"date": date},
            {"_id": 0}
        )
        return record
    except ValueError:
        return None


async def get_financial_data_range(
    start_date: str,
    end_date: str,
    limit: int = 100
) -> List[Dict]:
    """Get financial data for a date range."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )

        records = await db.financial_data.find(
            {"date": {"$gte": start, "$lte": end}},
            {"_id": 0}
        ).sort("date", 1).to_list(limit)

        return records
    except ValueError:
        return []


async def update_financial_record(
    record_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update an existing financial record."""
    try:
        # Remove fields that shouldn't be updated
        update_data = {k: v for k, v in updates.items()
                       if k not in ('id', '_id', 'created_at')}

        result = await db.financial_data.update_one(
            {"id": record_id},
            {"$set": update_data}
        )

        if result.modified_count > 0:
            return {"status": "success", "message": "Financial data updated"}
        elif result.matched_count > 0:
            return {"status": "success", "message": "No changes made"}
        else:
            return {"status": "not_found", "message": "Record not found"}

    except Exception as e:
        logger.error(f"Error updating financial record: {str(e)}")
        raise


async def delete_financial_record(record_id: str) -> Dict[str, Any]:
    """Delete a financial record by ID."""
    result = await db.financial_data.delete_one({"id": record_id})
    if result.deleted_count > 0:
        return {"status": "success", "message": "Financial record deleted"}
    return {"status": "not_found", "message": "Record not found"}


async def get_previous_financial_data(date_str: str) -> Dict[str, Any]:
    """Get the most recent financial data BEFORE a given date.

    Correctly skips holidays/weekly offs by finding the last available record.
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )

        # Find the most recent record before this date
        previous_record = await db.financial_data.find_one(
            {"date": {"$lt": target_date}},
            {"_id": 0},
            sort=[("date", -1)]
        )

        if previous_record and "current_bank_amount" in previous_record:
            prev_date = previous_record.get("date")
            return {
                "previous_date": prev_date.strftime("%Y-%m-%d") if prev_date else None,
                "bank_amount": previous_record["current_bank_amount"],
                "stock_value": previous_record.get("current_stock_value"),
                "found": True
            }

        return {
            "previous_date": None,
            "bank_amount": None,
            "stock_value": None,
            "found": False
        }

    except ValueError as e:
        raise ValueError(f"Invalid date format: {str(e)}")


async def get_previous_bank_amount(date_str: str) -> Dict[str, Any]:
    """Get previous bank amount for a specific date.

    Alias for get_previous_financial_data with simplified response.
    """
    return await get_previous_financial_data(date_str)
