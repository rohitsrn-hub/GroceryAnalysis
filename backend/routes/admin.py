"""
Admin routes — destructive operations that require authentication.
SEC-1 fix: All destructive endpoints protected by require_api_key.

Routes:
- DELETE /reset-all-data
- DELETE /clear-data
- DELETE /undo-upload/{upload_id}
- POST /fix-jan-sep-period
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone

from database import db
from config import logger
from middleware.auth import require_api_key

router = APIRouter(prefix="/api", tags=["admin"])


@router.delete("/reset-all-data", dependencies=[Depends(require_api_key)])
async def reset_all_data():
    """Reset all data - DESTRUCTIVE. Requires API key authentication."""
    try:
        sales_result = await db.sales_records.delete_many({})
        history_result = await db.upload_history.delete_many({})
        financial_result = await db.financial_data.delete_many({})
        summary_result = await db.monthly_summaries.delete_many({})
        chat_result = await db.chat_history.delete_many({})

        logger.warning(
            f"ALL DATA RESET: {sales_result.deleted_count} sales, "
            f"{history_result.deleted_count} history, "
            f"{financial_result.deleted_count} financial, "
            f"{summary_result.deleted_count} summaries, "
            f"{chat_result.deleted_count} chat records deleted"
        )

        return {
            "status": "success",
            "message": "All data has been reset",
            "deleted": {
                "sales_records": sales_result.deleted_count,
                "upload_history": history_result.deleted_count,
                "financial_data": financial_result.deleted_count,
                "monthly_summaries": summary_result.deleted_count,
                "chat_history": chat_result.deleted_count,
            }
        }
    except Exception as e:
        logger.exception("Error resetting all data")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-data", dependencies=[Depends(require_api_key)])
async def clear_data():
    """Clear all sales records and upload history. Requires API key."""
    try:
        sales_result = await db.sales_records.delete_many({})
        history_result = await db.upload_history.delete_many({})
        summary_result = await db.monthly_summaries.delete_many({})

        logger.warning(
            f"DATA CLEARED: {sales_result.deleted_count} sales, "
            f"{history_result.deleted_count} history, "
            f"{summary_result.deleted_count} summaries deleted"
        )

        return {
            "status": "success",
            "message": "Sales data and history cleared",
            "deleted": {
                "sales_records": sales_result.deleted_count,
                "upload_history": history_result.deleted_count,
                "monthly_summaries": summary_result.deleted_count,
            }
        }
    except Exception as e:
        logger.exception("Error clearing data")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/undo-upload/{upload_id}", dependencies=[Depends(require_api_key)])
async def undo_upload(upload_id: str):
    """Undo a specific upload by deleting its records. Requires API key."""
    try:
        # Find the upload history record
        upload_record = await db.upload_history.find_one({"id": upload_id})

        if not upload_record:
            raise HTTPException(status_code=404, detail="Upload record not found")

        # Delete sales records from this upload batch
        batch_id = upload_record.get("id")
        sales_result = await db.sales_records.delete_many({
            "upload_batch_id": batch_id
        })

        # Mark upload as undone
        await db.upload_history.update_one(
            {"id": upload_id},
            {
                "$set": {
                    "status": "undone",
                    "undone_at": datetime.now(timezone.utc)
                }
            }
        )

        logger.info(
            f"Undo upload {upload_id}: "
            f"{sales_result.deleted_count} records deleted"
        )

        return {
            "status": "success",
            "message": f"Upload undone: {sales_result.deleted_count} records deleted",
            "deleted_count": sales_result.deleted_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error undoing upload {upload_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-jan-sep-period", dependencies=[Depends(require_api_key)])
async def fix_jan_sep_period():
    """Fix data_period for records with Jan-Sep range format.
    
    Migrates records with legacy period formats to normalized YYYY-MM-MM format.
    """
    try:
        # Find records with non-standard period formats
        result = await db.sales_records.update_many(
            {
                "data_period": {"$regex": "jan.*sep", "$options": "i"}
            },
            [
                {
                    "$set": {
                        "data_period": {
                            "$cond": {
                                "if": {"$regexMatch": {"input": "$data_period", "regex": "2025"}},
                                "then": "2025-01-09",
                                "else": "$data_period"
                            }
                        }
                    }
                }
            ]
        )

        return {
            "status": "success",
            "message": f"Fixed {result.modified_count} records",
            "modified_count": result.modified_count
        }

    except Exception as e:
        logger.exception("Error fixing Jan-Sep period")
        raise HTTPException(status_code=500, detail=str(e))
