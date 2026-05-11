"""
Test fixtures and configuration for the grocery analytics test suite.
Uses pytest-asyncio for async test support.
"""
import pytest
import sys
import os

# Add backend to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_period_formats():
    """Sample period strings in various formats for testing."""
    return {
        "normalized_monthly": "2025-11",
        "normalized_yearly": "2025",
        "range_format": "2025-01-09",
        "same_month_range": "2025-11-11",
        "legacy_month_year": "Nov 2025",
        "legacy_full_month": "November 2025",
        "legacy_range": "1 Nov to 30 2025",
    }


@pytest.fixture
def sample_sales_records():
    """Sample sales records for unit testing."""
    return [
        {
            "gp_index_no": "001",
            "pluno": "I/001",
            "item_name": "Test Item A",
            "net_qty": 10,
            "r_amt": 1000.0,
            "w_amt": 800.0,
            "profit": 200.0,
            "closing_stock": 50,
            "product_group": "Group I",
            "data_period": "2025-11",
        },
        {
            "gp_index_no": "002",
            "pluno": "II/002",
            "item_name": "Test Item B",
            "net_qty": 5,
            "r_amt": 500.0,
            "w_amt": 400.0,
            "profit": 100.0,
            "closing_stock": 20,
            "product_group": "Group II",
            "data_period": "2025-11",
        },
        {
            "gp_index_no": "003",
            "pluno": "VI/003",
            "item_name": "Test Item C",
            "net_qty": 0,
            "r_amt": 0.0,
            "w_amt": 0.0,
            "profit": 0.0,
            "closing_stock": 100,
            "product_group": "Group VI",
            "data_period": "2025-11",
        },
    ]
