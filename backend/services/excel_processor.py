"""
Excel processor service — parses uploaded Excel/XLS/CSV sales data.
Extracted from server.py L501-1614.

Handles:
- Multi-format Excel reading (openpyxl, xlrd, CSV/TSV fallback)
- Column name normalization across format variants
- Special row detection (Group Total, Report Total, Summary Details)
- Report Total amount extraction (R_Amt, W_Amt)
- Row validation and skip logic
- MongoDB-ready record preparation
"""
import re
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple

import pandas as pd
from fastapi import HTTPException

from config import logger
from utils.formatting import extract_group_from_pluno
from utils.mongo_helpers import prepare_for_mongo


# ─── Column Name Mappings ────────────────────────────────────────────
COLUMN_MAPPING = {
    # Serial Number
    'SNo': 's_no', 'S.No': 's_no', 'S No': 's_no',
    # GP Index / Product Code
    'GP_Index_No': 'gp_index_no', 'GP_Index': 'gp_index_no',
    'GP Index No': 'gp_index_no', 'GP Index': 'gp_index_no',
    'pluno': 'pluno',
    # Item Name
    'Item_Name': 'item_name', 'Item Name': 'item_name', 'ItemName': 'item_name',
    # Wholesale Rate
    'W_Rate': 'w_rate', 'W Rate': 'w_rate', 'WRate': 'w_rate',
    # Retail Rate
    'R_Rate': 'r_rate', 'R Rate': 'r_rate', 'RRate': 'r_rate',
    # Quantity
    'Qty': 'qty', 'Quantity': 'qty',
    # Refund Quantity
    'Refund_Qty': 'refund_qty', 'Refund Qty': 'refund_qty', 'RefundQty': 'refund_qty',
    # Net Quantity
    'Net_Qty': 'net_qty', 'Net Qty': 'net_qty', 'NetQty': 'net_qty',
    # Retail Amount
    'R_Amt': 'r_amt', 'R Amt': 'r_amt', 'RAmt': 'r_amt',
    # Wholesale Amount
    'W_Amt': 'w_amt', 'W Amt': 'w_amt', 'WAmt': 'w_amt',
    # Profit
    'Profit': 'profit',
    # Opening Balance
    'O_B': 'o_b', 'O B': 'o_b', 'OB': 'o_b',
    'Opening_Balance': 'o_b', 'Opening Balance': 'o_b',
    # Closing Stock
    'Closing_Stock': 'closing_stock', 'Closing Stock': 'closing_stock',
    'ClosingStock': 'closing_stock',
    # Net Tax
    'Net_Tax': 'net_tax', 'Net Tax': 'net_tax',
    'Net-Tax': 'net_tax', 'NetTax': 'net_tax',
}

NUMERIC_COLUMNS = [
    's_no', 'w_rate', 'r_rate', 'qty', 'refund_qty', 'net_qty',
    'r_amt', 'w_amt', 'profit', 'o_b', 'closing_stock', 'net_tax',
]


# ─── Excel Reading ───────────────────────────────────────────────────

def read_excel_file(file_content: bytes, filename: str) -> pd.DataFrame:
    """Read Excel file with multi-engine fallback chain.

    Tries: openpyxl → xlrd → TSV → CSV
    """
    ext = filename.lower().rsplit('.', 1)[-1]

    # Primary attempt based on extension
    try:
        if ext == 'xlsx':
            return pd.read_excel(BytesIO(file_content), engine='openpyxl')
        elif ext == 'xls':
            try:
                return pd.read_excel(BytesIO(file_content), engine='xlrd')
            except Exception as xlrd_err:
                logger.warning(f"xlrd failed, trying TSV: {xlrd_err}")
                try:
                    df = pd.read_csv(BytesIO(file_content), sep='\t', encoding='latin1')
                    logger.info("Successfully read as TSV file")
                    return df
                except Exception:
                    df = pd.read_csv(BytesIO(file_content), sep=',', encoding='latin1')
                    logger.info("Successfully read as CSV file")
                    return df
        else:
            return pd.read_excel(BytesIO(file_content))
    except Exception as e:
        # Last resort fallback
        logger.warning(f"Failed to read as Excel, trying CSV/TSV: {e}")
        try:
            df = pd.read_csv(BytesIO(file_content), sep='\t', encoding='latin1')
            logger.info("Successfully read as TSV file")
            return df
        except Exception:
            df = pd.read_csv(BytesIO(file_content), sep=',', encoding='latin1')
            logger.info("Successfully read as CSV file")
            return df


# ─── Special Row Detection ───────────────────────────────────────────

def identify_special_rows(df: pd.DataFrame) -> Dict[str, Any]:
    """Identify Group Total, Report Total, Summary Details rows."""
    special_rows = {
        'group_totals': [],
        'report_total': None,
        'summary_start': None,
    }

    first_col = df.iloc[:, 0]
    for idx, value in enumerate(first_col):
        if pd.isna(value):
            continue
        value_str = str(value).strip().lower()

        if 'group total' in value_str and 'report' not in value_str:
            special_rows['group_totals'].append(idx)
        elif 'report total' in value_str:
            special_rows['report_total'] = idx
        elif 'summary details' in value_str or ('summary' in value_str and '*' in value_str):
            special_rows['summary_start'] = idx

    return special_rows


def extract_report_total_amounts(df: pd.DataFrame, report_total_idx: Optional[int]) -> Dict[str, Optional[float]]:
    """Extract R_Amt and W_Amt from the Report Total row."""
    result = {'r_amt': None, 'w_amt': None}
    if report_total_idx is None:
        return result

    try:
        r_amt_col_idx = None
        w_amt_col_idx = None

        for idx, col in enumerate(df.columns):
            col_lower = str(col).lower()
            if 'r_amt' in col_lower or 'r amt' in col_lower:
                r_amt_col_idx = idx
            elif 'w_amt' in col_lower or 'w amt' in col_lower:
                w_amt_col_idx = idx

        row = df.iloc[report_total_idx]

        if r_amt_col_idx is not None and pd.notna(row.iloc[r_amt_col_idx]):
            result['r_amt'] = float(row.iloc[r_amt_col_idx])
            logger.info(f"✓ Report Total R_Amt: Rs. {result['r_amt']:,.2f}")

        if w_amt_col_idx is not None and pd.notna(row.iloc[w_amt_col_idx]):
            result['w_amt'] = float(row.iloc[w_amt_col_idx])
            logger.info(f"✓ Report Total W_Amt: Rs. {result['w_amt']:,.2f}")

        return result
    except Exception as e:
        logger.error(f"Error extracting Report Total amounts: {e}")
        return result


def extract_report_total_from_embedded_text(df: pd.DataFrame) -> Optional[Dict[str, float]]:
    """Search for Report Total embedded in cell text (handles malformed Excel exports)."""
    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell_value = df.iloc[row_idx, col_idx]
            if pd.isna(cell_value):
                continue

            cell_str = str(cell_value)
            if 'report total' not in cell_str.lower():
                continue

            logger.info(f"Found 'Report Total' embedded in cell at row {row_idx}, col {col_idx}")

            lines = re.split(r'[\r\n]+|_x000D_', cell_str)
            for line in lines:
                if 'report total' not in line.lower():
                    continue

                parts = line.split('\t')
                numeric_values = []
                for i, part in enumerate(parts):
                    cleaned = part.replace(',', '').replace("'", '').replace('"', '').strip()
                    if cleaned and cleaned != '_x000D_':
                        try:
                            numeric_values.append((i, float(cleaned)))
                        except (ValueError, TypeError):
                            continue

                amount_values = [(idx, val) for idx, val in numeric_values if val > 10000]
                if amount_values:
                    r_amt = amount_values[0][1] if len(amount_values) >= 1 else None
                    w_amt = amount_values[1][1] if len(amount_values) >= 2 else None
                    logger.info(f"✓ Embedded text — R_Amt: {r_amt}, W_Amt: {w_amt}")
                    return {'r_amt': r_amt, 'w_amt': w_amt}

    return None


# ─── Row Validation ──────────────────────────────────────────────────

def _should_skip_row(item_name: str, pluno: str) -> Optional[str]:
    """Return skip reason if the row should be skipped, None otherwise."""
    if item_name == 'nan' and pluno == 'nan':
        return "Both pluno and item_name are empty"
    if item_name == 'nan' or pluno == 'nan':
        return "Item name or pluno is 'nan'"
    if len(item_name) > 100:
        return "Item name too long (>100 chars)"
    if '\t' in item_name or '_x000D_' in item_name:
        return "Item name contains invalid characters"
    if any(c in item_name for c in ['#', '$', '%']):
        return "Item name contains special characters"
    if len(item_name) < 3 and not item_name.isalpha():
        return "Item name too short"
    if 'round off' in item_name.lower() or 'roundoff' in item_name.lower():
        return "Round off entry"

    try:
        float(item_name)
        return "Item name is just a number"
    except ValueError:
        pass

    return None


# ─── Safe Converters (Excel-specific, handles quotes) ────────────────

def _safe_float_excel(value) -> Optional[float]:
    """Excel-specific safe float conversion (handles quoted strings)."""
    if pd.isna(value):
        return None
    try:
        if isinstance(value, str):
            cleaned = value.replace("'", "").replace('"', "").replace(",", "").strip()
        else:
            cleaned = str(value)
        if cleaned in ('', 'nan', 'None'):
            return None
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _safe_int_excel(value) -> Optional[int]:
    """Excel-specific safe int conversion."""
    if pd.isna(value):
        return None
    try:
        cleaned = str(value).replace("'", "").replace('"', "").strip()
        return int(float(cleaned)) if cleaned and cleaned != 'nan' else None
    except (ValueError, TypeError):
        return None


# ─── Main Processor ──────────────────────────────────────────────────

def process_excel_data(
    file_content: bytes,
    filename: str,
    period_info: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict], Optional[float], Optional[float]]:
    """Process uploaded Excel file and return structured data.

    Returns:
        (records, net_amt_r, net_amt_w) tuple
    """
    try:
        df = read_excel_file(file_content, filename)
        logger.info(f"Processing {filename}: {len(df)} rows, {len(df.columns)} columns")

        # Identify special rows
        special_rows = identify_special_rows(df)

        # Extract totals from Report Total row
        report_total = extract_report_total_amounts(df, special_rows['report_total'])
        net_r = report_total['r_amt']
        net_w = report_total['w_amt']

        # Fallback: search embedded text
        if net_r is None:
            embedded = extract_report_total_from_embedded_text(df)
            if embedded:
                net_r = embedded.get('r_amt')
                net_w = embedded.get('w_amt')

        # Normalize columns
        df = df.rename(columns=COLUMN_MAPPING)

        # Cross-populate gp_index_no / pluno
        if 'gp_index_no' in df.columns and 'pluno' not in df.columns:
            df['pluno'] = df['gp_index_no']
        elif 'pluno' in df.columns and 'gp_index_no' not in df.columns:
            df['gp_index_no'] = df['pluno']

        # Calculate net_qty if missing
        if 'net_qty' not in df.columns:
            if 'qty' in df.columns and 'refund_qty' in df.columns:
                df['net_qty'] = df['qty'] - df['refund_qty'].fillna(0)
            elif 'qty' in df.columns:
                df['net_qty'] = df['qty']

        # Convert numeric columns
        for col in NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Calculate profit
        if 'r_amt' in df.columns and 'w_amt' in df.columns:
            df['profit'] = df['r_amt'].fillna(0) - df['w_amt'].fillna(0)

        # Determine data_period
        if period_info and period_info.get('period'):
            data_period = period_info['period']
        else:
            data_period = filename.replace('.xlsx', '').replace('.xls', '')
            logger.warning(f"No period_info, using filename as period: {data_period}")

        # Build skip-index set
        skip_indices = set(special_rows['group_totals'])
        if special_rows['report_total'] is not None:
            skip_indices.add(special_rows['report_total'])
        if special_rows['summary_start'] is not None:
            for i in range(special_rows['summary_start'], len(df)):
                skip_indices.add(i)

        # Process rows
        records = []
        skipped_count = 0

        for idx, row in df.iterrows():
            if idx in skip_indices:
                skipped_count += 1
                continue

            item_name = str(row.get('item_name', '')).strip()
            gp_idx = str(row.get('gp_index_no', '')).strip()

            skip_reason = _should_skip_row(item_name, gp_idx)
            if skip_reason:
                skipped_count += 1
                continue

            record = {
                's_no': _safe_int_excel(row.get('s_no')),
                'gp_index_no': str(row.get('gp_index_no')) if not pd.isna(row.get('gp_index_no')) else None,
                'pluno': str(row.get('pluno')) if not pd.isna(row.get('pluno')) else None,
                'item_name': str(row.get('item_name')) if not pd.isna(row.get('item_name')) else None,
                'w_rate': _safe_float_excel(row.get('w_rate')),
                'r_rate': _safe_float_excel(row.get('r_rate')),
                'qty': _safe_int_excel(row.get('qty')),
                'refund_qty': _safe_int_excel(row.get('refund_qty')),
                'net_qty': _safe_int_excel(row.get('net_qty')),
                'r_amt': _safe_float_excel(row.get('r_amt')),
                'w_amt': _safe_float_excel(row.get('w_amt')),
                'profit': _safe_float_excel(row.get('profit')),
                'o_b': _safe_float_excel(row.get('o_b')),
                'closing_stock': _safe_float_excel(row.get('closing_stock')),
                'net_tax': _safe_float_excel(row.get('net_tax')),
                'data_period': data_period,
                'product_group': extract_group_from_pluno(
                    row.get('gp_index_no') or row.get('pluno')
                ),
            }

            record = prepare_for_mongo(record)
            records.append(record)

        logger.info(f"Processed {len(records)} valid records from {filename}, skipped {skipped_count}")

        if not records:
            raise HTTPException(
                status_code=400,
                detail=f"No valid records found. Rows: {len(df)}, Skipped: {skipped_count}."
            )

        # Fallback totals from record sums
        if net_r is None:
            net_r = sum(r.get('r_amt', 0) or 0 for r in records)
        if net_w is None:
            net_w = sum(r.get('w_amt', 0) or 0 for r in records)

        return records, net_r, net_w

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Excel file {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Error processing Excel file: {str(e)}")


def validate_excel_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate Excel file has minimum required columns."""
    required_cols = ['item_name', 'qty']
    recommended_cols = ['item_name', 'qty', 'closing_stock', 'w_rate', 'r_rate']

    df_cols_lower = [str(c).lower().replace(' ', '_').replace('.', '') for c in df.columns]

    missing_required = [c for c in required_cols if not any(c in col for col in df_cols_lower)]

    if missing_required:
        return {
            "valid": False,
            "error": f"Missing required columns: {', '.join(missing_required)}",
            "found_columns": list(df.columns),
        }

    missing_recommended = [c for c in recommended_cols if not any(c in col for col in df_cols_lower)]
    return {
        "valid": True,
        "missing_recommended": missing_recommended,
        "total_rows": len(df),
    }


def extract_period_from_filename(filename: str) -> Dict[str, Any]:
    """Extract period information from filename with smart date range detection.

    Examples:
    - "01 Jan to Sep 30 2025" -> Jan-Sep 2025
    - "01 to 30 Oct 25" -> Oct 2025
    - "YR 2024 C.xlsx" -> 2024
    """
    from utils.constants import MONTH_MAP, MONTH_NAMES_SHORT

    result = {
        "year": None, "month": None, "period": None,
        "data_type": None, "start_month": None, "end_month": None,
    }

    months = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2,
        'mar': 3, 'march': 3, 'apr': 4, 'april': 4,
        'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
    }

    filename_lower = filename.lower()

    # Extract year
    year_match = re.search(r'20\d{2}', filename)
    if year_match:
        result["year"] = int(year_match.group())
    else:
        year_2d = re.search(r'(?:^|\s|[a-z])(\d{2})(?:\s|\.|[)\]]|$)', filename_lower)
        if year_2d:
            y = int(year_2d.group(1))
            if 20 <= y <= 99:
                result["year"] = 1900 + y if y >= 50 else 2000 + y

    # Range with two months
    range_match = re.search(r'(\w+)\s+to\s+(\w+)', filename_lower)
    if range_match:
        start_m = end_m = None
        for name, num in months.items():
            if name in range_match.group(1):
                start_m = num
            if name in range_match.group(2):
                end_m = num
        if start_m and end_m and result["year"]:
            result.update({
                "start_month": start_m, "end_month": end_m,
                "data_type": "range",
                "period": f"{result['year']}-{start_m:02d}-{end_m:02d}",
                "display_name": f"{MONTH_NAMES_SHORT[start_m-1]}-{MONTH_NAMES_SHORT[end_m-1]} {result['year']}",
            })
            return result

    # Single month
    found = [num for name, num in months.items() if name in filename_lower]
    if found:
        result["month"] = found[0]
        result["data_type"] = "monthly"
        if result["year"]:
            result["period"] = f"{result['year']}-{result['month']:02d}"
            result["display_name"] = f"{MONTH_NAMES_SHORT[result['month']-1]} {result['year']}"
        return result

    # Yearly
    if result["year"]:
        result.update({
            "period": str(result["year"]),
            "data_type": "yearly",
            "display_name": str(result["year"]),
        })
    return result
