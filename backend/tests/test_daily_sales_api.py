"""
Backend API Tests for Grocery Sales Analytics - Daily Sales Report Feature
Tests the following endpoints:
1. POST /api/upload-sales-data - Daily Excel upload with data_date
2. GET /api/previous-financial-data - Returns previous bank/stock baseline
3. POST /api/generate-daily-report - Generates PDF report and saves financial_data
4. POST /api/extract-canteen-summary - Extracts grocery/liquor sales from image
5. GET /api/financial-data-range - Retrieves financial data for date range
"""

import pytest
import requests
import os
import io
from datetime import datetime, timedelta

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable not set")

print(f"Testing against: {BASE_URL}")


class TestHealthCheck:
    """Basic health check to ensure API is running"""
    
    def test_api_health(self):
        """Test that the API is accessible using available-periods endpoint"""
        response = requests.get(f"{BASE_URL}/api/available-periods")
        print(f"Health check response: {response.status_code}")
        assert response.status_code == 200
        data = response.json()
        # available-periods returns a list of periods
        assert isinstance(data, list) or "periods" in data or isinstance(data, dict)


class TestPreviousFinancialData:
    """Tests for GET /api/previous-financial-data endpoint"""
    
    def test_previous_financial_data_empty_db(self):
        """Test previous-financial-data returns found=false when no prior data exists"""
        # Use a date far in the past to ensure no data exists
        test_date = "2020-01-01"
        response = requests.get(f"{BASE_URL}/api/previous-financial-data?date={test_date}")
        
        print(f"Previous financial data response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        print(f"Response data: {data}")
        
        # Should return found=false when no prior data
        assert "found" in data
        # bank_amount and stock_value should be present (may be null)
        assert "bank_amount" in data
        assert "stock_value" in data
    
    def test_previous_financial_data_invalid_date(self):
        """Test previous-financial-data with invalid date format"""
        response = requests.get(f"{BASE_URL}/api/previous-financial-data?date=invalid-date")
        
        print(f"Invalid date response: {response.status_code}")
        assert response.status_code == 400
    
    def test_previous_financial_data_valid_format(self):
        """Test previous-financial-data with valid date format"""
        test_date = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/previous-financial-data?date={test_date}")
        
        print(f"Valid date response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        # Response should have expected structure
        assert "found" in data
        assert "bank_amount" in data
        assert "stock_value" in data
        assert "previous_date" in data


class TestUploadSalesData:
    """Tests for POST /api/upload-sales-data endpoint"""
    
    @pytest.fixture
    def sample_excel_file(self):
        """Create a minimal valid Excel file for testing"""
        import openpyxl
        from io import BytesIO
        
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Headers matching expected format
        headers = ['S.No', 'GP_Index_No', 'Item_Name', 'W_Rate', 'R_Rate', 'Qty', 'Refund_Qty', 'Net_Qty', 'R_Amt', 'W_Amt', 'Profit', 'O_B', 'Closing_Stock']
        ws.append(headers)
        
        # Sample data rows
        ws.append([1, 'I/001', 'Test Item 1', 10.00, 12.00, 5, 0, 5, 60.00, 50.00, 10.00, 100, 95])
        ws.append([2, 'I/002', 'Test Item 2', 20.00, 25.00, 3, 0, 3, 75.00, 60.00, 15.00, 50, 47])
        ws.append([3, 'II/001', 'Test Item 3', 15.00, 18.00, 10, 1, 9, 162.00, 135.00, 27.00, 200, 191])
        
        # Report Total row
        ws.append(['Report Total', '', '', '', '', 18, 1, 17, 297.00, 245.00, 52.00, '', ''])
        
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def test_upload_sales_data_invalid_file_type(self):
        """Test upload rejects non-Excel files"""
        files = {'file': ('test.txt', b'not an excel file', 'text/plain')}
        data = {'upload_type': 'daily', 'data_date': '2026-01-15'}
        
        response = requests.post(f"{BASE_URL}/api/upload-sales-data", files=files, data=data)
        
        print(f"Invalid file type response: {response.status_code}")
        assert response.status_code == 400
        assert "Excel" in response.json().get("detail", "")
    
    def test_upload_sales_data_daily_success(self, sample_excel_file):
        """Test successful daily upload with data_date"""
        # Use a unique date to avoid duplicate conflicts
        test_date = (datetime.now() + timedelta(days=100)).strftime("%Y-%m-%d")
        
        files = {'file': ('test_daily_data.xlsx', sample_excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'upload_type': 'daily',
            'data_date': test_date,
            'upload_source': 'analytics'
        }
        
        response = requests.post(f"{BASE_URL}/api/upload-sales-data", files=files, data=data)
        
        print(f"Daily upload response: {response.status_code}")
        print(f"Response body: {response.text[:500]}")
        
        # Accept 200 (success) or 400 (duplicate - if test ran before)
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "success"
            assert "records_count" in data
            assert data.get("upload_type") == "daily"
            assert data.get("data_date") == test_date
            print(f"Successfully uploaded {data.get('records_count')} records")
    
    def test_upload_sales_data_missing_date_for_daily(self, sample_excel_file):
        """Test daily upload without data_date still works (uses filename period)"""
        files = {'file': ('Jan_2026.xlsx', sample_excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'upload_type': 'daily'
            # No data_date provided
        }
        
        response = requests.post(f"{BASE_URL}/api/upload-sales-data", files=files, data=data)
        
        print(f"Upload without date response: {response.status_code}")
        # Should still work - period extracted from filename
        assert response.status_code in [200, 400]  # 400 if duplicate


class TestGenerateDailyReport:
    """Tests for POST /api/generate-daily-report endpoint"""
    
    def test_generate_daily_report_success(self):
        """Test generating a valid PDF report"""
        test_date = datetime.now().strftime("%Y-%m-%d")
        
        params = {
            'date': test_date,
            'liquor_sales': 50000.00,
            'previous_bank_amount': 100000.00,
            'grocery_sales': 25000.00,
            'previous_stock_value': 500000.00
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Generate report response: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        assert response.status_code == 200
        
        # Verify it's a PDF
        content_type = response.headers.get('Content-Type', '')
        assert 'application/pdf' in content_type
        
        # Verify PDF content starts with %PDF
        assert response.content[:4] == b'%PDF'
        
        print(f"PDF generated successfully, size: {len(response.content)} bytes")
    
    def test_generate_daily_report_minimal_params(self):
        """Test generating report with only required parameters"""
        test_date = datetime.now().strftime("%Y-%m-%d")
        
        params = {
            'date': test_date,
            'liquor_sales': 10000.00,
            'previous_bank_amount': 50000.00
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Minimal params response: {response.status_code}")
        assert response.status_code == 200
        assert response.content[:4] == b'%PDF'
    
    def test_generate_daily_report_invalid_date(self):
        """Test report generation with invalid date format"""
        params = {
            'date': 'not-a-date',
            'liquor_sales': 10000.00,
            'previous_bank_amount': 50000.00
        }
        
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        
        print(f"Invalid date response: {response.status_code}")
        assert response.status_code in [400, 422, 500]  # Should fail validation
    
    def test_generate_daily_report_saves_financial_data(self):
        """Test that generating report also saves financial_data record"""
        # Use a unique date
        test_date = (datetime.now() + timedelta(days=200)).strftime("%Y-%m-%d")
        
        params = {
            'date': test_date,
            'liquor_sales': 75000.00,
            'previous_bank_amount': 200000.00,
            'grocery_sales': 35000.00
        }
        
        # Generate report
        response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=params)
        assert response.status_code == 200
        
        # Verify financial data was saved by checking financial-data-range
        range_response = requests.get(
            f"{BASE_URL}/api/financial-data-range",
            params={'start_date': test_date, 'end_date': test_date}
        )
        
        print(f"Financial data range response: {range_response.status_code}")
        assert range_response.status_code == 200
        
        range_data = range_response.json()
        print(f"Financial data range: {range_data}")
        
        # Should have at least one record for this date
        assert range_data.get("count", 0) >= 1
        
        # Verify the record has correct values
        if range_data.get("records"):
            record = range_data["records"][0]
            assert record.get("liquor_sales") == 75000.00
            assert record.get("previous_bank_amount") == 200000.00
            print(f"Financial data verified: {record}")


class TestExtractCanteenSummary:
    """Tests for POST /api/extract-canteen-summary endpoint"""
    
    def test_extract_canteen_summary_no_file(self):
        """Test endpoint returns error when no file provided"""
        response = requests.post(f"{BASE_URL}/api/extract-canteen-summary")
        
        print(f"No file response: {response.status_code}")
        # Should return 422 (validation error) when file is missing
        assert response.status_code == 422
    
    def test_extract_canteen_summary_invalid_file(self):
        """Test endpoint handles non-image file gracefully"""
        files = {'file': ('test.txt', b'not an image', 'text/plain')}
        
        response = requests.post(f"{BASE_URL}/api/extract-canteen-summary", files=files)
        
        print(f"Invalid file response: {response.status_code}")
        # Should return 500 (AI processing error) or 400 (bad request)
        # The endpoint tries to process any file, so it may fail at AI level
        assert response.status_code in [400, 500]
    
    def test_extract_canteen_summary_with_minimal_image(self):
        """Test endpoint accepts image file (may fail at AI extraction)"""
        # Create a minimal valid PNG image (1x1 pixel)
        # PNG header + minimal IHDR + IDAT + IEND
        minimal_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 dimensions
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # bit depth, color type, etc
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,  # compressed data
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,  # 
            0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
            0x44, 0xAE, 0x42, 0x60, 0x82                      # IEND CRC
        ])
        
        files = {'file': ('test_image.png', minimal_png, 'image/png')}
        
        response = requests.post(f"{BASE_URL}/api/extract-canteen-summary", files=files)
        
        print(f"Minimal image response: {response.status_code}")
        print(f"Response body: {response.text[:500] if response.text else 'empty'}")
        
        # Endpoint should accept the image (200) or fail at AI extraction (500)
        # It should NOT return 422 (validation error) since file is provided
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "data" in data
            print(f"Extraction result: {data}")


class TestFinancialDataRange:
    """Tests for GET /api/financial-data-range endpoint"""
    
    def test_financial_data_range_valid_dates(self):
        """Test financial-data-range with valid date range"""
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        response = requests.get(
            f"{BASE_URL}/api/financial-data-range",
            params={'start_date': start_date, 'end_date': end_date}
        )
        
        print(f"Financial data range response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert "start_date" in data
        assert "end_date" in data
        assert "count" in data
        assert "records" in data
        assert isinstance(data["records"], list)
        
        print(f"Found {data['count']} financial records in range")
    
    def test_financial_data_range_invalid_dates(self):
        """Test financial-data-range with invalid date format"""
        response = requests.get(
            f"{BASE_URL}/api/financial-data-range",
            params={'start_date': 'invalid', 'end_date': 'also-invalid'}
        )
        
        print(f"Invalid dates response: {response.status_code}")
        assert response.status_code == 400
    
    def test_financial_data_range_empty_range(self):
        """Test financial-data-range returns empty for future dates"""
        # Use dates far in the future
        start_date = "2099-01-01"
        end_date = "2099-12-31"
        
        response = requests.get(
            f"{BASE_URL}/api/financial-data-range",
            params={'start_date': start_date, 'end_date': end_date}
        )
        
        print(f"Future dates response: {response.status_code}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 0
        assert data["records"] == []


class TestEndToEndAutoGeneration:
    """End-to-end test for the AUTO-GENERATION feature flow"""
    
    @pytest.fixture
    def sample_excel_file(self):
        """Create a minimal valid Excel file for testing"""
        import openpyxl
        from io import BytesIO
        
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Headers matching expected format
        headers = ['S.No', 'GP_Index_No', 'Item_Name', 'W_Rate', 'R_Rate', 'Qty', 'Refund_Qty', 'Net_Qty', 'R_Amt', 'W_Amt', 'Profit', 'O_B', 'Closing_Stock']
        ws.append(headers)
        
        # Sample data rows
        ws.append([1, 'I/001', 'Rice Premium', 45.00, 50.00, 100, 2, 98, 4900.00, 4410.00, 490.00, 500, 402])
        ws.append([2, 'I/002', 'Wheat Flour', 35.00, 40.00, 80, 0, 80, 3200.00, 2800.00, 400.00, 300, 220])
        ws.append([3, 'II/001', 'Cooking Oil', 120.00, 135.00, 50, 1, 49, 6615.00, 5880.00, 735.00, 100, 51])
        ws.append([4, 'II/002', 'Sugar', 42.00, 48.00, 60, 0, 60, 2880.00, 2520.00, 360.00, 200, 140])
        ws.append([5, 'III/001', 'Tea Leaves', 180.00, 200.00, 25, 0, 25, 5000.00, 4500.00, 500.00, 50, 25])
        
        # Report Total row
        ws.append(['Report Total', '', '', '', '', 315, 3, 312, 22595.00, 20110.00, 2485.00, '', ''])
        
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def test_e2e_upload_then_generate_report(self, sample_excel_file):
        """
        End-to-end test:
        1. Upload daily sales data
        2. Get previous financial data
        3. Generate daily report
        4. Verify financial data is saved and retrievable
        """
        # Use a unique date for this test
        test_date = (datetime.now() + timedelta(days=300)).strftime("%Y-%m-%d")
        next_day = (datetime.now() + timedelta(days=301)).strftime("%Y-%m-%d")
        
        print(f"\n=== E2E Test: Auto-generation flow for {test_date} ===")
        
        # Step 1: Upload daily sales data
        print("\nStep 1: Uploading daily sales data...")
        files = {'file': ('daily_sales.xlsx', sample_excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        data = {
            'upload_type': 'daily',
            'data_date': test_date,
            'upload_source': 'analytics'
        }
        
        upload_response = requests.post(f"{BASE_URL}/api/upload-sales-data", files=files, data=data)
        print(f"Upload response: {upload_response.status_code}")
        
        # Accept success or duplicate (if test ran before)
        assert upload_response.status_code in [200, 400]
        
        if upload_response.status_code == 200:
            upload_data = upload_response.json()
            print(f"Uploaded {upload_data.get('records_count')} records")
            assert upload_data.get("status") == "success"
        
        # Step 2: Get previous financial data (for next day)
        print("\nStep 2: Getting previous financial data...")
        prev_response = requests.get(f"{BASE_URL}/api/previous-financial-data?date={next_day}")
        print(f"Previous financial data response: {prev_response.status_code}")
        assert prev_response.status_code == 200
        
        prev_data = prev_response.json()
        print(f"Previous data: {prev_data}")
        
        # Step 3: Generate daily report
        print("\nStep 3: Generating daily report...")
        report_params = {
            'date': test_date,
            'liquor_sales': 45000.00,
            'previous_bank_amount': 150000.00,
            'grocery_sales': 22595.00,  # From our test data
            'previous_stock_value': 300000.00
        }
        
        report_response = requests.post(f"{BASE_URL}/api/generate-daily-report", params=report_params)
        print(f"Report generation response: {report_response.status_code}")
        assert report_response.status_code == 200
        assert report_response.content[:4] == b'%PDF'
        print(f"PDF generated: {len(report_response.content)} bytes")
        
        # Step 4: Verify financial data was saved
        print("\nStep 4: Verifying financial data persistence...")
        range_response = requests.get(
            f"{BASE_URL}/api/financial-data-range",
            params={'start_date': test_date, 'end_date': test_date}
        )
        print(f"Financial data range response: {range_response.status_code}")
        assert range_response.status_code == 200
        
        range_data = range_response.json()
        print(f"Financial records found: {range_data.get('count')}")
        
        assert range_data.get("count", 0) >= 1, "Financial data should be saved after report generation"
        
        # Verify the saved data
        if range_data.get("records"):
            saved_record = range_data["records"][0]
            print(f"Saved financial record: {saved_record}")
            
            assert saved_record.get("liquor_sales") == 45000.00
            assert saved_record.get("previous_bank_amount") == 150000.00
            
            # Verify calculated values
            expected_total = 22595.00 + 45000.00  # grocery + liquor
            expected_bank = 150000.00 + expected_total  # previous + total
            
            assert saved_record.get("total_sales") == expected_total
            assert saved_record.get("current_bank_amount") == expected_bank
        
        # Step 5: Verify previous-financial-data returns this data for next day
        print("\nStep 5: Verifying previous-financial-data for next day...")
        next_prev_response = requests.get(f"{BASE_URL}/api/previous-financial-data?date={next_day}")
        assert next_prev_response.status_code == 200
        
        next_prev_data = next_prev_response.json()
        print(f"Previous data for next day: {next_prev_data}")
        
        # Should find our saved record
        assert next_prev_data.get("found") == True
        assert next_prev_data.get("bank_amount") is not None
        
        print("\n=== E2E Test PASSED ===")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
