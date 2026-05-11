"""
Unit tests for input validators.
Agent 4 Task A4-18 (partial).
"""
import pytest
from utils.validators import (
    sanitize_regex_input,
    validate_period_format,
    validate_date_string,
    validate_forecast_date,
    validate_upload_file,
    build_period_filter,
)


class TestSanitizeRegexInput:
    """Test regex sanitization for ReDoS prevention"""

    def test_normal_input_unchanged(self):
        assert sanitize_regex_input("hello") == "hello"
        assert sanitize_regex_input("item name") == "item\\ name"

    def test_special_chars_escaped(self):
        result = sanitize_regex_input("(a+)+$")
        assert "(" not in result or result.count("\\(") > 0
        assert "+" not in result or result.count("\\+") > 0

    def test_empty_input(self):
        assert sanitize_regex_input("") == ""
        assert sanitize_regex_input(None) == ""

    def test_regex_metacharacters(self):
        dangerous = ".*+?^${}()|[]\\"
        result = sanitize_regex_input(dangerous)
        # All metacharacters should be escaped
        assert result != dangerous


class TestValidatePeriodFormat:
    """Test period format validation"""

    def test_valid_monthly(self):
        valid, error = validate_period_format("2025-11")
        assert valid is True
        assert error == ""

    def test_valid_yearly(self):
        valid, error = validate_period_format("2025")
        assert valid is True

    def test_invalid_month(self):
        valid, error = validate_period_format("2025-13")
        assert valid is False
        assert "month" in error.lower()

    def test_empty_period(self):
        valid, error = validate_period_format("")
        assert valid is False

    def test_garbage_input(self):
        valid, error = validate_period_format("not-a-period")
        assert valid is False


class TestValidateDateString:
    """Test date string validation"""

    def test_valid_date(self):
        valid, dt = validate_date_string("2025-11-15")
        assert valid is True
        assert dt.year == 2025
        assert dt.month == 11
        assert dt.day == 15

    def test_invalid_date(self):
        valid, dt = validate_date_string("not-a-date")
        assert valid is False
        assert dt is None

    def test_invalid_format(self):
        valid, dt = validate_date_string("15/11/2025")
        assert valid is False


class TestValidateUploadFile:
    """Test upload file validation"""

    def test_xlsx_accepted(self):
        valid, error = validate_upload_file("data.xlsx")
        assert valid is True

    def test_xls_accepted(self):
        valid, error = validate_upload_file("data.xls")
        assert valid is True

    def test_csv_rejected(self):
        valid, error = validate_upload_file("data.csv")
        assert valid is False

    def test_empty_filename(self):
        valid, error = validate_upload_file("")
        assert valid is False


class TestBuildPeriodFilter:
    """Test period filter builder"""

    def test_specific_period(self):
        result = build_period_filter("2025-11")
        assert result == {"data_period": "2025-11"}

    def test_all_periods(self):
        assert build_period_filter("all") == {}
        assert build_period_filter("") == {}
        assert build_period_filter(None) == {}

    def test_current_year_format(self):
        result = build_period_filter("2025 - Current Year")
        assert "$regex" in result["data_period"]
        assert "2025" in result["data_period"]["$regex"]
