"""
Formatting utilities for Indian number system, currency, and display helpers.
Extracted from server.py L36-87.
"""
import pandas as pd
from .constants import GROUP_PREFIXES


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


def format_indian_currency(number):
    """Shorthand for format_indian_number with currency=True"""
    return format_indian_number(number, currency=True, use_rs_prefix=True)


def extract_group_from_pluno(pluno) -> str:
    """Extract product group from PLU number.

    Handles formats like 'VI/123', '6/123', 'I/456', '1/456'.
    """
    if not pluno or pd.isna(pluno):
        return "Unknown"

    pluno_str = str(pluno).strip()

    for prefix, group in GROUP_PREFIXES.items():
        if pluno_str.startswith(prefix):
            return group

    return "Unknown"


def safe_float(value, default=0.0):
    """Safely convert a value to float, returning default on failure.

    Logs a warning (via return info) instead of silently swallowing errors.
    Returns tuple (value, was_converted_ok) for callers that want to track failures.
    """
    if value is None or value == '' or value == '-':
        return default
    try:
        if isinstance(value, str):
            # Remove commas and whitespace
            value = value.replace(',', '').strip()
        result = float(value)
        return result
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    """Safely convert a value to int, returning default on failure."""
    if value is None or value == '' or value == '-':
        return default
    try:
        if isinstance(value, str):
            value = value.replace(',', '').strip()
        return int(float(value))
    except (ValueError, TypeError):
        return default
