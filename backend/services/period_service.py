"""
Period normalization and formatting service.
Centralizes ALL period-related logic that was scattered across 6+ locations in server.py.

Key improvements:
- Single source of truth for period formatting
- Batch formatting to eliminate N+1 query patterns
- Pure functions (no DB calls) for display name formatting
"""
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from utils.constants import MONTH_MAP, MONTH_NAMES_SHORT, MONTH_NUM_TO_NAMES


def format_period_display_name(period: str) -> str:
    """Format period name intelligently based on stored period format.

    This is a PURE FUNCTION (no DB calls) — safe to call in loops.

    Examples:
    - Full year: "2024" -> "2024"
    - Single month: "2025-11" -> "Nov 2025"
    - Current month: "2025-12" -> "Current Period (Dec 2025)"
    - Range: "2025-01-09" -> "Jan-Sep 2025"
    """
    if not period:
        return "Unknown"

    # If it's already a year (4 digits), return as is
    if re.match(r'^\d{4}$', period):
        return period

    # Check for range format: YYYY-MM-MM (start month to end month)
    range_match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', period)
    if range_match:
        year = range_match.group(1)
        start_month = int(range_match.group(2))
        end_month = int(range_match.group(3))

        if 1 <= start_month <= 12 and 1 <= end_month <= 12:
            # If start and end are the same, treat as single month
            if start_month == end_month:
                current_date = datetime.now()
                if int(year) == current_date.year and start_month == current_date.month:
                    return f"Current Period ({MONTH_NAMES_SHORT[start_month - 1]} {year})"
                return f"{MONTH_NAMES_SHORT[start_month - 1]} {year}"

            # Range format
            return f"{MONTH_NAMES_SHORT[start_month - 1]}-{MONTH_NAMES_SHORT[end_month - 1]} {year}"

    # Single month format: YYYY-MM
    month_match = re.match(r'^(\d{4})-(\d{2})$', period)
    if month_match:
        year = month_match.group(1)
        month = int(month_match.group(2))

        if 1 <= month <= 12:
            # Check if this is current month
            current_date = datetime.now()
            if int(year) == current_date.year and month == current_date.month:
                return f"Current Period ({MONTH_NAMES_SHORT[month - 1]} {year})"

            return f"{MONTH_NAMES_SHORT[month - 1]} {year}"

    # Fallback: return as is
    return period


def format_periods_batch(periods: List[str]) -> List[Dict[str, str]]:
    """Format multiple periods at once — eliminates N+1 pattern.

    Returns list of {"value": raw_period, "label": formatted_name}.
    """
    return [
        {"value": p, "label": format_period_display_name(p)}
        for p in periods
    ]


def normalize_period(raw_period: str) -> Optional[str]:
    """Normalize any period format to YYYY-MM or YYYY.

    Handles:
    - "Nov 2025", "November 2025" -> "2025-11"
    - "1 Nov to 30 2025" -> "2025-11"
    - "2025-11" -> "2025-11" (already normalized)
    - "2025" -> "2025"

    Returns None if the period cannot be parsed.
    """
    if not raw_period:
        return None

    raw = raw_period.strip()

    # Already normalized: YYYY-MM
    if re.match(r'^\d{4}-\d{2}$', raw):
        return raw

    # Already normalized: YYYY
    if re.match(r'^\d{4}$', raw):
        return raw

    # Range format YYYY-MM-MM — keep as-is (special format)
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw

    raw_lower = raw.lower().strip()

    # Try "Month Year" format (e.g., "Nov 2025", "November 2025")
    for month_name, month_num in MONTH_MAP.items():
        if month_name in raw_lower:
            year_match = re.search(r'20\d{2}', raw)
            if year_match:
                return f"{year_match.group()}-{month_num}"

    return None


def detect_period_from_query(query: str, available_periods: List[str]) -> Optional[str]:
    """Detect if user is asking about a specific period in a chatbot query.

    Returns the matching data_period value or None.
    """
    query_lower = query.lower()

    # Try to find month + year pattern (e.g., "November 2025", "Nov 2025")
    for month_name, month_num in MONTH_MAP.items():
        if month_name in query_lower:
            year_match = re.search(r'20\d{2}', query)
            if year_match:
                year = year_match.group()
                target_period = f"{year}-{month_num}"
                if target_period in available_periods:
                    return target_period

    # Try to find just year (e.g., "2024", "year 2024")
    year_match = re.search(r'\b(20\d{2})\b', query)
    if year_match:
        year = year_match.group(1)
        if year in available_periods:
            return year

    return None


def detect_multiple_periods_from_query(
    query: str, available_periods: List[str]
) -> List[str]:
    """Detect multiple periods mentioned in a comparison query.

    Returns list of matching data_period values.
    """
    query_lower = query.lower()
    detected_periods: List[str] = []

    # Find all years in query
    years_found = re.findall(r'20\d{2}', query)

    # Find all month-year combinations
    for month_name, month_num in MONTH_MAP.items():
        if month_name in query_lower:
            for year in years_found:
                target_period = f"{year}-{month_num}"
                if target_period in available_periods and target_period not in detected_periods:
                    detected_periods.append(target_period)

            # If only one year found, use it for this month
            if len(years_found) == 1:
                target_period = f"{years_found[0]}-{month_num}"
                if target_period in available_periods and target_period not in detected_periods:
                    detected_periods.append(target_period)

    # Also check for standalone years
    for year in years_found:
        if year in available_periods and year not in detected_periods:
            detected_periods.append(year)

    return detected_periods


def is_comparison_query(query: str) -> bool:
    """Detect if user is asking for a comparison between periods."""
    from utils.constants import COMPARISON_KEYWORDS

    query_lower = query.lower()
    return any(keyword in query_lower for keyword in COMPARISON_KEYWORDS)


def is_single_month_period(data_period: str, target_year: str, target_month_int: int) -> bool:
    """Check if a data_period value represents a single specific month.

    Used to filter out multi-month ranges when looking for specific months.
    This replaces the expensive full-table-scan logic in check_data_availability.
    """
    if not data_period:
        return False

    data_period_lower = data_period.lower()

    # Check if it contains the target year
    if target_year not in data_period_lower:
        return False

    target_month_names = MONTH_NUM_TO_NAMES.get(target_month_int, [])

    # Check if it contains the target month
    has_target_month = any(name in data_period_lower for name in target_month_names)
    if not has_target_month:
        return False

    # Check it's NOT a multi-month range (doesn't contain OTHER month names)
    for other_month_int in range(1, 13):
        if other_month_int != target_month_int:
            other_names = MONTH_NUM_TO_NAMES.get(other_month_int, [])
            if any(name in data_period_lower for name in other_names):
                return False  # Contains another month = multi-month range

    return True
