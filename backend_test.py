import requests
import sys
import json
from datetime import datetime
import os

class SalesAnalyticsAPITester:
    def __init__(self, base_url="https://retail-metrics-app.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        if 'message' in response_data:
                            print(f"   Message: {response_data['message']}")
                        if 'records_count' in response_data:
                            print(f"   Records: {response_data['records_count']}")
                        if isinstance(response_data, list):
                            print(f"   Items returned: {len(response_data)}")
                        elif 'forecasts' in response_data:
                            print(f"   Forecasts: {len(response_data['forecasts'])}")
                except:
                    print(f"   Response length: {len(response.text)} chars")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   Raw response: {response.text[:200]}...")

            self.test_results.append({
                'name': name,
                'endpoint': endpoint,
                'method': method,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'success': success,
                'response_size': len(response.text) if response.text else 0
            })

            return success, response.json() if success and response.text else {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout (30s)")
            self.test_results.append({
                'name': name,
                'endpoint': endpoint,
                'method': method,
                'expected_status': expected_status,
                'actual_status': 'TIMEOUT',
                'success': False,
                'error': 'Request timeout'
            })
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                'name': name,
                'endpoint': endpoint,
                'method': method,
                'expected_status': expected_status,
                'actual_status': 'ERROR',
                'success': False,
                'error': str(e)
            })
            return False, {}

    def test_dashboard_summary(self):
        """Test dashboard summary endpoint"""
        return self.run_test(
            "Dashboard Summary",
            "GET",
            "dashboard-summary",
            200
        )

    def test_fastest_selling_items(self):
        """Test fastest selling items endpoint"""
        return self.run_test(
            "Fastest Selling Items",
            "GET",
            "fastest-selling-items?limit=10",
            200
        )

    def test_group_analysis(self):
        """Test group analysis endpoint"""
        return self.run_test(
            "Group Analysis",
            "GET",
            "group-analysis",
            200
        )

    def test_inventory_analysis(self):
        """Test inventory analysis endpoint"""
        return self.run_test(
            "Inventory Analysis",
            "GET",
            "inventory-analysis",
            200
        )

    def test_trend_forecast(self):
        """Test trend forecasting"""
        forecast_data = {
            "method": "trend",
            "forecast_months": 4,
            "additional_data": {
                "current_month": 12,
                "trend_analysis": True
            }
        }
        return self.run_test(
            "Trend Forecasting",
            "POST",
            "forecast-demand",
            200,
            data=forecast_data
        )

    def test_statistical_forecast(self):
        """Test statistical forecasting"""
        forecast_data = {
            "method": "statistical",
            "forecast_months": 4,
            "additional_data": {
                "current_month": 12,
                "seasonal_adjustments": True
            }
        }
        return self.run_test(
            "Statistical Forecasting",
            "POST",
            "forecast-demand",
            200,
            data=forecast_data
        )

    def test_ai_forecast(self):
        """Test AI forecasting (should return placeholder response)"""
        forecast_data = {
            "method": "ai",
            "forecast_months": 4,
            "additional_data": {
                "market_context": "Test market context for AI forecasting",
                "current_month": 12
            }
        }
        return self.run_test(
            "AI Forecasting",
            "POST",
            "forecast-demand",
            200,
            data=forecast_data
        )

    def test_abc_analysis_all_groups(self):
        """Test ABC analysis without group filter"""
        return self.run_test(
            "ABC Analysis - All Groups",
            "GET",
            "abc-analysis",
            200
        )

    def test_abc_analysis_group_iii(self):
        """Test ABC analysis for Group III specifically"""
        return self.run_test(
            "ABC Analysis - Group III",
            "GET",
            "abc-analysis?group=Group III",
            200
        )

    def test_abc_analysis_group_iv(self):
        """Test ABC analysis for Group IV specifically"""
        return self.run_test(
            "ABC Analysis - Group IV",
            "GET",
            "abc-analysis?group=Group IV",
            200
        )

    def test_capital_blocking_all_groups(self):
        """Test capital blocking analysis without group filter"""
        return self.run_test(
            "Capital Blocking Analysis - All Groups",
            "GET",
            "capital-blocking-analysis",
            200
        )

    def test_capital_blocking_group_iii(self):
        """Test capital blocking analysis for Group III"""
        return self.run_test(
            "Capital Blocking Analysis - Group III",
            "GET",
            "capital-blocking-analysis?group=Group III",
            200
        )

    def test_capital_blocking_group_iv(self):
        """Test capital blocking analysis for Group IV"""
        return self.run_test(
            "Capital Blocking Analysis - Group IV",
            "GET",
            "capital-blocking-analysis?group=Group IV",
            200
        )

    def test_fastest_selling_group_iii(self):
        """Test fastest selling items for Group III"""
        return self.run_test(
            "Fastest Selling Items - Group III",
            "GET",
            "fastest-selling-items?group=Group III&limit=10",
            200
        )

    def test_fastest_selling_group_iv(self):
        """Test fastest selling items for Group IV"""
        return self.run_test(
            "Fastest Selling Items - Group IV",
            "GET",
            "fastest-selling-items?group=Group IV&limit=10",
            200
        )

    def test_file_upload_validation(self):
        """Test file upload validation (without actual file)"""
        # This should fail with 422 due to missing file
        return self.run_test(
            "File Upload Validation",
            "POST",
            "upload-sales-data",
            422  # Expected to fail without file
        )

def main():
    print("🚀 Starting Sales Analytics API Testing...")
    print("=" * 60)
    
    # Setup
    tester = SalesAnalyticsAPITester()
    
    # Test all endpoints
    print("\n📊 Testing Dashboard & Analytics APIs...")
    tester.test_dashboard_summary()
    tester.test_fastest_selling_items()
    tester.test_group_analysis()
    tester.test_inventory_analysis()
    
    print("\n🔮 Testing Forecasting APIs...")
    tester.test_trend_forecast()
    tester.test_statistical_forecast()
    tester.test_ai_forecast()
    
    print("\n📁 Testing File Upload Validation...")
    tester.test_file_upload_validation()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 FINAL RESULTS:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for result in tester.test_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"   {status} - {result['name']} ({result['method']} {result['endpoint']})")
        if not result['success']:
            if 'error' in result:
                print(f"      Error: {result['error']}")
            else:
                print(f"      Expected: {result['expected_status']}, Got: {result['actual_status']}")
    
    # Check for critical failures
    critical_endpoints = ['dashboard-summary', 'fastest-selling-items', 'group-analysis', 'inventory-analysis']
    critical_failures = [r for r in tester.test_results if not r['success'] and any(ep in r['endpoint'] for ep in critical_endpoints)]
    
    if critical_failures:
        print(f"\n⚠️  CRITICAL ISSUES FOUND:")
        for failure in critical_failures:
            print(f"   - {failure['name']}: {failure.get('error', 'Status code mismatch')}")
        return 1
    
    if tester.tests_passed < tester.tests_run * 0.8:  # Less than 80% success
        print(f"\n⚠️  LOW SUCCESS RATE: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
        return 1
    
    print(f"\n🎉 Backend API testing completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())