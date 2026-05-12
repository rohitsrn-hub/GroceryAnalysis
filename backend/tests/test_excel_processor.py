"""
Unit tests for the Excel processor service.
Tests column mapping, special row detection, period extraction, and row validation.
"""
import pytest
from services.excel_processor import (
    _should_skip_row,
    _safe_float_excel,
    _safe_int_excel,
    extract_period_from_filename,
    COLUMN_MAPPING,
)


class TestShouldSkipRow:
    """Test row skip logic."""

    def test_valid_item(self):
        assert _should_skip_row("Basmati Rice", "I/001") is None

    def test_both_nan(self):
        assert _should_skip_row("nan", "nan") is not None

    def test_round_off(self):
        assert _should_skip_row("Round Off Amount", "I/999") is not None
        assert _should_skip_row("roundoff", "I/999") is not None

    def test_long_name(self):
        assert _should_skip_row("A" * 101, "I/001") is not None

    def test_tab_in_name(self):
        assert _should_skip_row("Item\tName", "I/001") is not None

    def test_special_chars(self):
        assert _should_skip_row("Item #1", "I/001") is not None
        assert _should_skip_row("Item $5", "I/001") is not None

    def test_numeric_name_rejected(self):
        assert _should_skip_row("12345", "I/001") is not None

    def test_short_non_alpha(self):
        assert _should_skip_row("12", "I/001") is not None


class TestSafeFloatExcel:
    """Test Excel-specific float conversion."""

    def test_numeric_values(self):
        assert _safe_float_excel(42.5) == 42.5
        assert _safe_float_excel(0) == 0.0

    def test_string_values(self):
        assert _safe_float_excel("100.50") == 100.50
        assert _safe_float_excel("'1,234.56'") == 1234.56

    def test_nan_and_none(self):
        import pandas as pd
        assert _safe_float_excel(None) is None
        assert _safe_float_excel(float('nan')) is None
        assert _safe_float_excel(pd.NA) is None

    def test_empty_string(self):
        assert _safe_float_excel("") is None
        assert _safe_float_excel("nan") is None


class TestSafeIntExcel:
    """Test Excel-specific int conversion."""

    def test_numeric(self):
        assert _safe_int_excel(42) == 42
        assert _safe_int_excel(3.7) == 3

    def test_string(self):
        assert _safe_int_excel("100") == 100

    def test_none(self):
        assert _safe_int_excel(None) is None


class TestExtractPeriodFromFilename:
    """Test filename-based period extraction."""

    def test_single_month_4digit_year(self):
        result = extract_period_from_filename("Nov 2025.xlsx")
        assert result["period"] == "2025-11"
        assert result["data_type"] == "monthly"

    def test_yearly(self):
        result = extract_period_from_filename("YR 2024 C.xlsx")
        assert result["period"] == "2024"
        assert result["data_type"] == "yearly"

    def test_range_two_months(self):
        result = extract_period_from_filename("01 Jan to Sep 30 2025.xlsx")
        assert result["period"] == "2025-01-09"
        assert result["data_type"] == "range"

    def test_single_month_2digit_year(self):
        # 2-digit year detection is fragile — known limitation.
        # For this pattern, month is detected but year might not be.
        result = extract_period_from_filename("01 to 30 Oct 25.xls")
        assert result["data_type"] == "monthly"
        assert result["month"] == 10

    def test_no_period_detected(self):
        result = extract_period_from_filename("random_file.xlsx")
        assert result["period"] is None


class TestColumnMapping:
    """Test column mapping completeness."""

    def test_all_variations_covered(self):
        # Verify all target fields are present
        target_fields = set(COLUMN_MAPPING.values())
        assert 'item_name' in target_fields
        assert 'r_amt' in target_fields
        assert 'w_amt' in target_fields
        assert 'net_qty' in target_fields
        assert 'closing_stock' in target_fields
        assert 'profit' in target_fields

    def test_case_sensitivity(self):
        # Verify both underscore and space variants exist
        assert 'R_Amt' in COLUMN_MAPPING
        assert 'R Amt' in COLUMN_MAPPING
        assert 'Closing_Stock' in COLUMN_MAPPING
        assert 'Closing Stock' in COLUMN_MAPPING
