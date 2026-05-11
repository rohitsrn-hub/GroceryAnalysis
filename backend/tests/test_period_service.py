"""
Unit tests for the period service.
Tests period formatting, normalization, and chatbot period detection.
Agent 4 Task A4-13.
"""
import pytest
from services.period_service import (
    format_period_display_name,
    format_periods_batch,
    normalize_period,
    detect_period_from_query,
    detect_multiple_periods_from_query,
    is_comparison_query,
    is_single_month_period,
)


class TestFormatPeriodDisplayName:
    """Test format_period_display_name()"""

    def test_yearly_format(self):
        assert format_period_display_name("2024") == "2024"
        assert format_period_display_name("2025") == "2025"

    def test_monthly_format(self):
        assert format_period_display_name("2025-01") == "Jan 2025"
        assert format_period_display_name("2025-11") == "Nov 2025"
        assert format_period_display_name("2024-06") == "Jun 2024"
        assert format_period_display_name("2025-12") in [
            "Dec 2025",
            "Current Period (Dec 2025)"
        ]

    def test_range_format(self):
        assert format_period_display_name("2025-01-09") == "Jan-Sep 2025"
        assert format_period_display_name("2025-03-06") == "Mar-Jun 2025"

    def test_same_month_range(self):
        # Same start and end month should display as single month
        result = format_period_display_name("2024-05-05")
        assert result == "May 2024"

    def test_empty_and_unknown(self):
        assert format_period_display_name("") == "Unknown"
        assert format_period_display_name("garbage") == "garbage"

    def test_none_handling(self):
        assert format_period_display_name(None) == "Unknown"


class TestFormatPeriodsBatch:
    """Test batch period formatting"""

    def test_batch_formatting(self):
        periods = ["2025-11", "2025-10", "2024"]
        result = format_periods_batch(periods)
        assert len(result) == 3
        assert result[0]["value"] == "2025-11"
        assert result[0]["label"] == "Nov 2025"
        assert result[2]["value"] == "2024"
        assert result[2]["label"] == "2024"

    def test_empty_batch(self):
        assert format_periods_batch([]) == []


class TestNormalizePeriod:
    """Test period normalization"""

    def test_already_normalized(self):
        assert normalize_period("2025-11") == "2025-11"
        assert normalize_period("2024") == "2024"

    def test_month_year_format(self):
        assert normalize_period("Nov 2025") == "2025-11"
        assert normalize_period("November 2025") == "2025-11"
        assert normalize_period("jan 2024") == "2024-01"

    def test_range_format_preserved(self):
        assert normalize_period("2025-01-09") == "2025-01-09"

    def test_invalid_period(self):
        assert normalize_period("") is None
        assert normalize_period("garbage") is None
        assert normalize_period(None) is None


class TestDetectPeriodFromQuery:
    """Test chatbot period detection"""

    def test_detect_month_year(self):
        available = ["2025-11", "2025-10", "2024"]
        assert detect_period_from_query("Show me November 2025 data", available) == "2025-11"
        assert detect_period_from_query("What about Oct 2025?", available) == "2025-10"

    def test_detect_year_only(self):
        available = ["2025-11", "2024"]
        assert detect_period_from_query("Show me 2024 data", available) == "2024"

    def test_no_match(self):
        available = ["2025-11"]
        assert detect_period_from_query("Hello world", available) is None

    def test_period_not_in_available(self):
        available = ["2025-11"]
        assert detect_period_from_query("Show me December 2025", available) is None


class TestIsComparisonQuery:
    """Test comparison query detection"""

    def test_comparison_keywords(self):
        assert is_comparison_query("Compare Nov and Oct 2025") is True
        assert is_comparison_query("Nov 2025 vs Oct 2025") is True
        assert is_comparison_query("What's the difference between months?") is True
        assert is_comparison_query("Show me growth trends") is True

    def test_non_comparison_queries(self):
        assert is_comparison_query("What are top selling items?") is False
        assert is_comparison_query("Show revenue") is False


class TestIsSingleMonthPeriod:
    """Test single month period detection for data availability checks"""

    def test_single_month_match(self):
        assert is_single_month_period("Nov 2025", "2025", 11) is True
        assert is_single_month_period("november 2025", "2025", 11) is True

    def test_multi_month_rejected(self):
        assert is_single_month_period("Jan to Sep 2025", "2025", 1) is False
        assert is_single_month_period("JAN TO SEP 2025", "2025", 9) is False

    def test_wrong_year(self):
        assert is_single_month_period("Nov 2024", "2025", 11) is False

    def test_empty_period(self):
        assert is_single_month_period("", "2025", 11) is False
        assert is_single_month_period(None, "2025", 11) is False
