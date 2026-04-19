"""
Backend API Tests for /api/generate-daily-report Fallback Behavior

Tests the hardened fallback logic:
1. previous_bank_amount OMITTED + no prior financial_data -> 400 with clear message
2. previous_bank_amount OMITTED + yesterday's report exists -> auto-fetch from yesterday
3. previous_bank_amount OMITTED + gap day (Day-2 exists, Day-1 missing) -> walk back to Day-2
4. previous_stock_value OMITTED + prior record has current_stock_value -> auto-fetch
5. Backward compatibility: previous_bank_amount EXPLICITLY provided -> use user value, NOT fallback
6. HTTPException (400) is not masked by outer Exception handler
7. /api/financial-data-range still returns correct records after fallback flow
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
from pymongo import MongoClient

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

# Get MongoDB connection for test setup/cleanup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')

print(f"Testing against: {BASE_URL}")
print(f"MongoDB: {MONGO_URL}, DB: {DB_NAME}")


@pytest.fixture(scope="module")
def mongo_client():
    """Create MongoDB client for test setup/cleanup"""
    client = MongoClient(MONGO_URL)
    yield client
    client.close()


@pytest.fixture(scope="module")
def db(mongo_client):
    """Get database reference"""
    return mongo_client[DB_NAME]


class TestFallbackNoPriorData:
    """Test Case 1: previous_bank_amount OMITTED + no prior financial_data records"""
    
    def test_no_prior_data_returns_400(self, db):
        """
        When previous_bank_amount is OMITTED and NO prior financial_data records exist,
        should return 400 with clear message about requiring previous_bank_amount.
        """
        # Use a date far in the past to ensure no prior data exists
        # First, clean up any test data for this specific date range
        test_date = "2019-01-15"
        
        # Delete any financial_data records before this date to ensure clean state
        db.financial_data.delete_many({"date": {"$lt": datetime(2019, 1, 16)}})
        
        # Call endpoint WITHOUT previous_bank_amount
        params = {
            'date': test_date,
            'liquor_sales': 50000.00
            # previous_bank_amount intentionally OMITTED
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should return 400 (not 500)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        
        # Verify error message is clear
        error_detail = response.json().get("detail", "")
        assert "previous_bank_amount is required" in error_detail, f"Expected clear error message, got: {error_detail}"
        assert "no prior financial report exists" in error_detail, f"Expected fallback explanation, got: {error_detail}"


class TestFallbackYesterdayExists:
    """Test Case 2: previous_bank_amount OMITTED + yesterday's report exists"""
    
    @pytest.fixture(autouse=True)
    def setup_yesterday_data(self, db):
        """Create a financial_data record for yesterday"""
        # Use unique dates for this test
        self.today = datetime(2025, 6, 15)
        self.yesterday = datetime(2025, 6, 14)
        
        # Clean up any existing test data
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
        
        # Insert yesterday's financial data
        yesterday_record = {
            "id": "TEST_fallback_yesterday",
            "date": self.yesterday,
            "grocery_sales": 20000.0,
            "liquor_sales": 40000.0,
            "total_sales": 60000.0,
            "previous_bank_amount": 100000.0,
            "current_bank_amount": 160000.0,  # This should be used as fallback
            "previous_stock_value": 500000.0,
            "current_stock_value": 480000.0,  # This should be used as fallback for stock
            "created_at": datetime.utcnow()
        }
        db.financial_data.insert_one(yesterday_record)
        
        yield
        
        # Cleanup after test
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
    
    def test_auto_fetch_from_yesterday(self, db):
        """
        When previous_bank_amount is OMITTED and yesterday's report exists,
        should auto-fetch from yesterday's current_bank_amount and succeed.
        """
        today_str = self.today.strftime("%Y-%m-%d")
        
        # Call endpoint WITHOUT previous_bank_amount
        params = {
            'date': today_str,
            'liquor_sales': 50000.00,
            'grocery_sales': 25000.00
            # previous_bank_amount intentionally OMITTED
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        # Should succeed with PDF
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text[:500]}"
        assert 'application/pdf' in response.headers.get('Content-Type', '')
        assert response.content[:4] == b'%PDF'
        
        # Verify financial data was saved with correct previous_bank_amount
        saved_record = db.financial_data.find_one({"date": self.today})
        assert saved_record is not None, "Financial data should be saved"
        
        # previous_bank_amount should be 160000 (yesterday's current_bank_amount)
        assert saved_record.get("previous_bank_amount") == 160000.0, \
            f"Expected previous_bank_amount=160000, got {saved_record.get('previous_bank_amount')}"
        
        print(f"✓ Auto-fetched previous_bank_amount: {saved_record.get('previous_bank_amount')}")


class TestFallbackGapDay:
    """Test Case 3: previous_bank_amount OMITTED + gap day (Day-2 exists, Day-1 missing)"""
    
    @pytest.fixture(autouse=True)
    def setup_gap_data(self, db):
        """Create a financial_data record for Day-2 (skip Day-1)"""
        # Use unique dates for this test
        self.today = datetime(2025, 7, 20)
        self.day_minus_1 = datetime(2025, 7, 19)  # No data for this day
        self.day_minus_2 = datetime(2025, 7, 18)  # Data exists here
        
        # Clean up any existing test data
        db.financial_data.delete_many({
            "date": {"$gte": self.day_minus_2, "$lte": self.today}
        })
        
        # Insert Day-2's financial data (skip Day-1)
        day_minus_2_record = {
            "id": "TEST_fallback_gap_day",
            "date": self.day_minus_2,
            "grocery_sales": 30000.0,
            "liquor_sales": 45000.0,
            "total_sales": 75000.0,
            "previous_bank_amount": 200000.0,
            "current_bank_amount": 275000.0,  # This should be used as fallback
            "previous_stock_value": 600000.0,
            "current_stock_value": 570000.0,  # This should be used as fallback
            "created_at": datetime.utcnow()
        }
        db.financial_data.insert_one(day_minus_2_record)
        
        yield
        
        # Cleanup after test
        db.financial_data.delete_many({
            "date": {"$gte": self.day_minus_2, "$lte": self.today}
        })
    
    def test_walk_back_to_day_minus_2(self, db):
        """
        When previous_bank_amount is OMITTED and Day-1 is missing but Day-2 exists,
        should walk back to Day-2 and use its current_bank_amount.
        """
        today_str = self.today.strftime("%Y-%m-%d")
        
        # Call endpoint WITHOUT previous_bank_amount
        params = {
            'date': today_str,
            'liquor_sales': 55000.00,
            'grocery_sales': 28000.00
            # previous_bank_amount intentionally OMITTED
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        
        # Should succeed with PDF
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text[:500]}"
        assert response.content[:4] == b'%PDF'
        
        # Verify financial data was saved with correct previous_bank_amount from Day-2
        saved_record = db.financial_data.find_one({"date": self.today})
        assert saved_record is not None, "Financial data should be saved"
        
        # previous_bank_amount should be 275000 (Day-2's current_bank_amount)
        assert saved_record.get("previous_bank_amount") == 275000.0, \
            f"Expected previous_bank_amount=275000 (from Day-2), got {saved_record.get('previous_bank_amount')}"
        
        print(f"✓ Walked back to Day-2 and fetched previous_bank_amount: {saved_record.get('previous_bank_amount')}")


class TestFallbackStockValue:
    """Test Case 4: previous_stock_value OMITTED + prior record has current_stock_value"""
    
    @pytest.fixture(autouse=True)
    def setup_stock_data(self, db):
        """Create a financial_data record with stock values"""
        self.today = datetime(2025, 8, 10)
        self.yesterday = datetime(2025, 8, 9)
        
        # Clean up any existing test data
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
        
        # Insert yesterday's financial data with stock values
        yesterday_record = {
            "id": "TEST_fallback_stock",
            "date": self.yesterday,
            "grocery_sales": 22000.0,
            "liquor_sales": 38000.0,
            "total_sales": 60000.0,
            "previous_bank_amount": 150000.0,
            "current_bank_amount": 210000.0,
            "previous_stock_value": 450000.0,
            "current_stock_value": 420000.0,  # This should be used as fallback for previous_stock_value
            "created_at": datetime.utcnow()
        }
        db.financial_data.insert_one(yesterday_record)
        
        yield
        
        # Cleanup after test
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
    
    def test_auto_fetch_stock_value(self, db):
        """
        When previous_stock_value is OMITTED and prior record has current_stock_value,
        should auto-fetch it.
        """
        today_str = self.today.strftime("%Y-%m-%d")
        
        # Call endpoint WITHOUT previous_stock_value (but WITH previous_bank_amount to isolate test)
        params = {
            'date': today_str,
            'liquor_sales': 42000.00,
            'grocery_sales': 23000.00
            # previous_bank_amount OMITTED - will fallback to 210000
            # previous_stock_value intentionally OMITTED - should fallback to 420000
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        
        # Should succeed with PDF
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text[:500]}"
        assert response.content[:4] == b'%PDF'
        
        # Verify financial data was saved with correct previous_stock_value
        saved_record = db.financial_data.find_one({"date": self.today})
        assert saved_record is not None, "Financial data should be saved"
        
        # previous_stock_value should be 420000 (yesterday's current_stock_value)
        assert saved_record.get("previous_stock_value") == 420000.0, \
            f"Expected previous_stock_value=420000, got {saved_record.get('previous_stock_value')}"
        
        print(f"✓ Auto-fetched previous_stock_value: {saved_record.get('previous_stock_value')}")


class TestBackwardCompatibility:
    """Test Case 5: Backward compatibility - explicit value should NOT be overridden by fallback"""
    
    @pytest.fixture(autouse=True)
    def setup_prior_data(self, db):
        """Create a financial_data record that could be used for fallback"""
        self.today = datetime(2025, 9, 5)
        self.yesterday = datetime(2025, 9, 4)
        
        # Clean up any existing test data
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
        
        # Insert yesterday's financial data
        yesterday_record = {
            "id": "TEST_backward_compat",
            "date": self.yesterday,
            "grocery_sales": 25000.0,
            "liquor_sales": 50000.0,
            "total_sales": 75000.0,
            "previous_bank_amount": 180000.0,
            "current_bank_amount": 255000.0,  # Fallback would use this
            "previous_stock_value": 550000.0,
            "current_stock_value": 520000.0,  # Fallback would use this
            "created_at": datetime.utcnow()
        }
        db.financial_data.insert_one(yesterday_record)
        
        yield
        
        # Cleanup after test
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
    
    def test_explicit_value_not_overridden(self, db):
        """
        When previous_bank_amount is EXPLICITLY provided, should use user-provided value,
        NOT fall back to prior record, even if prior record exists.
        """
        today_str = self.today.strftime("%Y-%m-%d")
        
        # Call endpoint WITH explicit previous_bank_amount (different from fallback value)
        user_provided_bank = 300000.0  # Different from fallback (255000)
        user_provided_stock = 600000.0  # Different from fallback (520000)
        
        params = {
            'date': today_str,
            'liquor_sales': 48000.00,
            'grocery_sales': 27000.00,
            'previous_bank_amount': user_provided_bank,  # EXPLICITLY provided
            'previous_stock_value': user_provided_stock  # EXPLICITLY provided
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        
        # Should succeed with PDF
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text[:500]}"
        assert response.content[:4] == b'%PDF'
        
        # Verify financial data was saved with USER-PROVIDED values, NOT fallback
        saved_record = db.financial_data.find_one({"date": self.today})
        assert saved_record is not None, "Financial data should be saved"
        
        # Should use user-provided value (300000), NOT fallback (255000)
        assert saved_record.get("previous_bank_amount") == user_provided_bank, \
            f"Expected user-provided previous_bank_amount={user_provided_bank}, got {saved_record.get('previous_bank_amount')}"
        
        # Should use user-provided value (600000), NOT fallback (520000)
        assert saved_record.get("previous_stock_value") == user_provided_stock, \
            f"Expected user-provided previous_stock_value={user_provided_stock}, got {saved_record.get('previous_stock_value')}"
        
        print(f"✓ Used user-provided values: bank={saved_record.get('previous_bank_amount')}, stock={saved_record.get('previous_stock_value')}")


class TestHTTPExceptionNotMasked:
    """Test Case 6: HTTPException (400) is not masked by outer Exception handler"""
    
    def test_400_not_masked_as_500(self, db):
        """
        Verify that HTTPException(400) raised for missing previous_bank_amount
        is NOT caught by the outer Exception handler and converted to 500.
        """
        # Use a date with no prior data
        test_date = "2018-01-01"
        
        # Ensure no prior data exists
        db.financial_data.delete_many({"date": {"$lt": datetime(2018, 1, 2)}})
        
        # Call endpoint WITHOUT previous_bank_amount
        params = {
            'date': test_date,
            'liquor_sales': 30000.00
            # previous_bank_amount intentionally OMITTED
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        # Should return 400 (NOT 500)
        assert response.status_code == 400, \
            f"HTTPException(400) should not be masked as 500. Got {response.status_code}"
        
        # Verify it's the expected error message
        error_detail = response.json().get("detail", "")
        assert "previous_bank_amount is required" in error_detail
        
        print(f"✓ HTTPException(400) correctly propagated, not masked as 500")


class TestFinancialDataRangeAfterFallback:
    """Test Case 7: /api/financial-data-range returns correct records after fallback flow"""
    
    @pytest.fixture(autouse=True)
    def setup_and_generate(self, db):
        """Setup prior data and generate report using fallback"""
        self.day1 = datetime(2025, 10, 1)
        self.day2 = datetime(2025, 10, 2)
        self.day3 = datetime(2025, 10, 3)
        
        # Clean up any existing test data
        db.financial_data.delete_many({
            "date": {"$gte": self.day1, "$lte": self.day3}
        })
        
        # Insert Day 1's financial data
        day1_record = {
            "id": "TEST_range_day1",
            "date": self.day1,
            "grocery_sales": 20000.0,
            "liquor_sales": 35000.0,
            "total_sales": 55000.0,
            "previous_bank_amount": 100000.0,
            "current_bank_amount": 155000.0,
            "previous_stock_value": 400000.0,
            "current_stock_value": 380000.0,
            "created_at": datetime.utcnow()
        }
        db.financial_data.insert_one(day1_record)
        
        yield
        
        # Cleanup after test
        db.financial_data.delete_many({
            "date": {"$gte": self.day1, "$lte": self.day3}
        })
    
    def test_financial_data_range_after_fallback(self, db):
        """
        After generating reports using fallback, /api/financial-data-range
        should return all records correctly.
        """
        # Generate report for Day 2 using fallback
        day2_str = self.day2.strftime("%Y-%m-%d")
        params = {
            'date': day2_str,
            'liquor_sales': 40000.00,
            'grocery_sales': 22000.00
            # previous_bank_amount OMITTED - will fallback to Day 1's current_bank_amount (155000)
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        assert response.status_code == 200, f"Day 2 report generation failed: {response.text[:500]}"
        
        # Generate report for Day 3 using fallback
        day3_str = self.day3.strftime("%Y-%m-%d")
        params = {
            'date': day3_str,
            'liquor_sales': 38000.00,
            'grocery_sales': 24000.00
            # previous_bank_amount OMITTED - will fallback to Day 2's current_bank_amount
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        assert response.status_code == 200, f"Day 3 report generation failed: {response.text[:500]}"
        
        # Now verify /api/financial-data-range returns all 3 records
        start_date = self.day1.strftime("%Y-%m-%d")
        end_date = self.day3.strftime("%Y-%m-%d")
        
        range_response = requests.get(
            f"{BASE_URL}/api/financial-data-range",
            params={'start_date': start_date, 'end_date': end_date}
        )
        
        print(f"Financial data range response: {range_response.status_code}")
        assert range_response.status_code == 200
        
        range_data = range_response.json()
        print(f"Records found: {range_data.get('count')}")
        print(f"Records: {range_data.get('records')}")
        
        # Should have 3 records (Day 1, Day 2, Day 3)
        assert range_data.get("count") == 3, \
            f"Expected 3 records, got {range_data.get('count')}"
        
        # Verify the chain of previous_bank_amount values
        records = sorted(range_data.get("records", []), key=lambda x: x.get("date", ""))
        
        # Day 1: previous_bank_amount = 100000 (original)
        # Day 2: previous_bank_amount = 155000 (Day 1's current_bank_amount via fallback)
        # Day 3: previous_bank_amount = Day 2's current_bank_amount via fallback
        
        if len(records) >= 2:
            day2_record = records[1]
            assert day2_record.get("previous_bank_amount") == 155000.0, \
                f"Day 2 should have previous_bank_amount=155000 (from Day 1 fallback), got {day2_record.get('previous_bank_amount')}"
        
        print(f"✓ Financial data range correctly returns all records after fallback flow")


class TestLiquorSalesDefaultsToZero:
    """Test that liquor_sales defaults to 0.0 when not provided"""
    
    @pytest.fixture(autouse=True)
    def setup_prior_data(self, db):
        """Create a financial_data record for fallback"""
        self.today = datetime(2025, 11, 15)
        self.yesterday = datetime(2025, 11, 14)
        
        # Clean up any existing test data
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
        
        # Insert yesterday's financial data
        yesterday_record = {
            "id": "TEST_liquor_default",
            "date": self.yesterday,
            "grocery_sales": 18000.0,
            "liquor_sales": 32000.0,
            "total_sales": 50000.0,
            "previous_bank_amount": 120000.0,
            "current_bank_amount": 170000.0,
            "previous_stock_value": 350000.0,
            "current_stock_value": 330000.0,
            "created_at": datetime.utcnow()
        }
        db.financial_data.insert_one(yesterday_record)
        
        yield
        
        # Cleanup after test
        db.financial_data.delete_many({
            "date": {"$gte": self.yesterday, "$lte": self.today}
        })
    
    def test_liquor_sales_defaults_to_zero(self, db):
        """
        When liquor_sales is not provided, it should default to 0.0
        """
        today_str = self.today.strftime("%Y-%m-%d")
        
        # Call endpoint WITHOUT liquor_sales
        params = {
            'date': today_str,
            'grocery_sales': 20000.00
            # liquor_sales intentionally OMITTED - should default to 0.0
            # previous_bank_amount OMITTED - will fallback
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Response status: {response.status_code}")
        
        # Should succeed
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Body: {response.text[:500]}"
        
        # Verify financial data was saved with liquor_sales = 0.0
        saved_record = db.financial_data.find_one({"date": self.today})
        assert saved_record is not None, "Financial data should be saved"
        
        assert saved_record.get("liquor_sales") == 0.0, \
            f"Expected liquor_sales=0.0 (default), got {saved_record.get('liquor_sales')}"
        
        print(f"✓ liquor_sales correctly defaulted to 0.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
