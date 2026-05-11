"""
Shared constants used across multiple modules.
Eliminates duplicated month maps, magic numbers, and hardcoded values.
"""

# ─── Month Name Mappings ─────────────────────────────────────────────
# Single source of truth — was previously defined independently in 4+ places
MONTH_MAP = {
    'january': '01', 'jan': '01',
    'february': '02', 'feb': '02',
    'march': '03', 'mar': '03',
    'april': '04', 'apr': '04',
    'may': '05',
    'june': '06', 'jun': '06',
    'july': '07', 'jul': '07',
    'august': '08', 'aug': '08',
    'september': '09', 'sep': '09', 'sept': '09',
    'october': '10', 'oct': '10',
    'november': '11', 'nov': '11',
    'december': '12', 'dec': '12',
}

MONTH_NAMES_FULL = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

MONTH_NAMES_SHORT = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
]

# Reverse lookup: "01" -> ["jan", "january"]
MONTH_NUM_TO_NAMES: dict[int, list[str]] = {
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
    12: ['dec', 'december'],
}

# ─── Product Group Mappings ──────────────────────────────────────────
GROUP_PREFIXES = {
    "VI/": "Group VI", "6/": "Group VI",
    "IV/": "Group IV", "4/": "Group IV",
    "III/": "Group III", "3/": "Group III",
    "II/": "Group II", "2/": "Group II",
    "I/": "Group I", "1/": "Group I",
}

# ─── Excel Column Names ─────────────────────────────────────────────
# Expected column headers for schema validation (case-insensitive matching)
REQUIRED_EXCEL_COLUMNS = [
    "GP_Index_No", "Item_Name", "Net_Qty", "R_Amt", "Profit", "Closing_Stock"
]

# ─── Chatbot Comparison Keywords ─────────────────────────────────────
COMPARISON_KEYWORDS = [
    'compare', 'comparison', 'vs', 'versus', 'between',
    'difference', 'differ', 'change', 'changed', 'growth',
    'increase', 'decrease', 'better', 'worse', 'more than',
    'less than', 'higher', 'lower', 'trend', 'month over month',
    'mom', 'yoy', 'year over year', 'previous', 'last month',
    'this month vs', 'compared to', 'against',
]
