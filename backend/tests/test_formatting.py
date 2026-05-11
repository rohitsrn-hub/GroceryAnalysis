"""
Unit tests for formatting utilities.
Agent 4 Task A4-14.
"""
import pytest
from utils.formatting import (
    format_indian_number,
    format_indian_currency,
    extract_group_from_pluno,
    safe_float,
    safe_int,
)


class TestFormatIndianNumber:
    """Test Indian number formatting"""

    def test_zero(self):
        assert format_indian_number(0) == "0"
        assert format_indian_number(0, currency=True) == "₹0"
        assert format_indian_number(0, currency=True, use_rs_prefix=True) == "Rs 0"

    def test_small_numbers(self):
        assert format_indian_number(100) == "100.00"
        assert format_indian_number(999) == "999.00"

    def test_thousands(self):
        result = format_indian_number(1000)
        assert result == "1,000.00"

    def test_lakhs(self):
        result = format_indian_number(100000)
        assert result == "1,00,000.00"

    def test_crores(self):
        result = format_indian_number(10000000)
        assert result == "1,00,00,000.00"

    def test_negative_numbers(self):
        result = format_indian_number(-50000)
        assert result.startswith("-")
        assert "50,000" in result

    def test_currency_prefix(self):
        result = format_indian_number(1000, currency=True)
        assert result.startswith("₹")

    def test_rs_prefix(self):
        result = format_indian_number(1000, currency=True, use_rs_prefix=True)
        assert result.startswith("Rs ")

    def test_none_value(self):
        assert format_indian_number(None) == "0"
        assert format_indian_number(None, currency=True) == "₹0"


class TestFormatIndianCurrency:
    """Test the shorthand currency formatter"""

    def test_basic(self):
        result = format_indian_currency(1000)
        assert result.startswith("Rs ")


class TestExtractGroupFromPluno:
    """Test PLU group extraction"""

    def test_group_i(self):
        assert extract_group_from_pluno("I/001") == "Group I"
        assert extract_group_from_pluno("1/001") == "Group I"

    def test_group_ii(self):
        assert extract_group_from_pluno("II/002") == "Group II"
        assert extract_group_from_pluno("2/002") == "Group II"

    def test_group_iii(self):
        assert extract_group_from_pluno("III/003") == "Group III"
        assert extract_group_from_pluno("3/003") == "Group III"

    def test_group_iv(self):
        assert extract_group_from_pluno("IV/004") == "Group IV"
        assert extract_group_from_pluno("4/004") == "Group IV"

    def test_group_vi(self):
        assert extract_group_from_pluno("VI/006") == "Group VI"
        assert extract_group_from_pluno("6/006") == "Group VI"

    def test_unknown_format(self):
        assert extract_group_from_pluno("XYZ") == "Unknown"
        assert extract_group_from_pluno("") == "Unknown"
        assert extract_group_from_pluno(None) == "Unknown"


class TestSafeFloat:
    """Test safe float conversion"""

    def test_valid_numbers(self):
        assert safe_float(42) == 42.0
        assert safe_float("3.14") == 3.14
        assert safe_float("1,000.50") == 1000.50

    def test_invalid_values(self):
        assert safe_float(None) == 0.0
        assert safe_float("") == 0.0
        assert safe_float("-") == 0.0
        assert safe_float("not a number") == 0.0

    def test_custom_default(self):
        assert safe_float("bad", default=-1.0) == -1.0


class TestSafeInt:
    """Test safe int conversion"""

    def test_valid_numbers(self):
        assert safe_int(42) == 42
        assert safe_int("100") == 100
        assert safe_int("3.7") == 3  # Truncates

    def test_invalid_values(self):
        assert safe_int(None) == 0
        assert safe_int("") == 0
        assert safe_int("abc") == 0

    def test_commas(self):
        assert safe_int("1,000") == 1000
