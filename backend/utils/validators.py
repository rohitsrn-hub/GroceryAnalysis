"""
Input validation and sanitization utilities.
Addresses SEC-2 (regex injection) and provides reusable validators.
"""
import re
from datetime import datetime
from typing import Optional


def sanitize_regex_input(user_input: str) -> str:
    """Escape special regex characters in user-provided search strings.

    Prevents ReDoS attacks when user input is used in MongoDB $regex queries.
    SEC-2 fix: replaces raw user input in $regex with escaped version.
    """
    if not user_input:
        return ""
    return re.escape(user_input)


def validate_period_format(period: str) -> tuple[bool, str]:
    """Validate period string format.

    Returns (is_valid, error_message).
    Accepted formats: 'YYYY-MM' (monthly), 'YYYY' (yearly)
    """
    if not period:
        return False, "Period is required"

    if len(period) == 7 and re.match(r'^\d{4}-\d{2}$', period):
        year, month = period.split('-')
        if 1 <= int(month) <= 12:
            return True, ""
        return False, f"Invalid month: {month}"

    if len(period) == 4 and re.match(r'^\d{4}$', period):
        return True, ""

    return False, "Period must be in format 'YYYY-MM' or 'YYYY'"


def validate_date_string(date_str: str) -> tuple[bool, Optional[datetime]]:
    """Validate and parse a YYYY-MM-DD date string.

    Returns (is_valid, parsed_datetime_or_None).
    """
    try:
        parsed = datetime.strptime(date_str, "%Y-%m-%d")
        return True, parsed
    except ValueError:
        return False, None


def validate_forecast_date(year: int, month: int) -> dict:
    """Validate that a forecast target date is not in the past.

    Returns dict with 'valid' bool and optional 'error' message.
    """
    now = datetime.now()
    if year < now.year or (year == now.year and month < now.month):
        return {
            "valid": False,
            "error": f"Forecast date {month}/{year} is in the past. "
                     f"Please select a future month."
        }
    return {"valid": True}


def validate_upload_file(filename: str) -> tuple[bool, str]:
    """Validate uploaded file is an accepted Excel format.

    Returns (is_valid, error_message).
    """
    if not filename:
        return False, "No filename provided"

    allowed_extensions = ('.xlsx', '.xls')
    if not filename.lower().endswith(allowed_extensions):
        return False, f"Only Excel files ({', '.join(allowed_extensions)}) are supported"

    return True, ""


def build_period_filter(period: str) -> dict:
    """Build a MongoDB filter dict for a given period string.

    Handles 'YYYY - Current Year' format, 'YYYY-MM', and 'YYYY'.
    Centralizes the duplicated period filter pattern used in 5+ endpoints.
    """
    if not period or period == "all":
        return {}

    if "Current Year" in period:
        year = period.split(" ")[0]
        return {
            "data_period": {
                "$regex": f"({year}|{year[2:]})",
                "$options": "i"
            }
        }

    return {"data_period": period}
