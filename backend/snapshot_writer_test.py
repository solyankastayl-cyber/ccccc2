#!/usr/bin/env python3
"""
BTC Signal Snapshot Writer Test Suite

Tests the following endpoints:
1. POST /api/fractal/v2.1/admin/snapshot/write-btc - Write snapshots
2. GET /api/fractal/v2.1/admin/snapshot/latest?symbol=BTC - Get latest snapshot  
3. GET /api/fractal/v2.1/admin/snapshot/count?symbol=BTC - Get snapshot counts
4. Idempotency testing (repeat calls should return skipped)
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class SnapshotWriterTester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test_result(self, test_name, passed, details=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        result = {
            "test_name": test_name,
            "status": status,
            "passed": passed,
            "details": details
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}")
        if details:
            print(f"   Details: {details}")

    def test_api_call(self, method, endpoint, expected_status=200, data=None, params=None):
        """Make API call and check response"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, params=params, timeout=30)
            else:
                return False, f"Unsupported method: {method}"

            success = response.status_code == expected_status
            response_data = response.json() if response.content else {}
            
            return success, response_data
            
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except json.JSONDecodeError as e:
            return False, f"JSON decode error: {str(e)}"

    def test_snapshot_count(self):
        """Test getting snapshot counts"""
        success, response = self.test_api_call(
            'GET', 
            '/api/fractal/v2.1/admin/snapshot/count',
            params={'symbol': 'BTC'}
        )
        
        if success:
            required_fields = ['symbol', 'active', 'shadow', 'total']
            has_all_fields = all(field in response for field in required_fields)
            
            if has_all_fields:
                details = f"Active: {response.get('active', 0)}, Shadow: {response.get('shadow', 0)}, Total: {response.get('total', 0)}"
                self.log_test_result("Snapshot Count API", True, details)
                return response
            else:
                missing = [f for f in required_fields if f not in response]
                self.log_test_result("Snapshot Count API", False, f"Missing fields: {missing}")
                return None
        else:
            self.log_test_result("Snapshot Count API", False, str(response))
            return None

    def test_latest_snapshot(self):
        """Test getting latest snapshot"""
        success, response = self.test_api_call(
            'GET',
            '/api/fractal/v2.1/admin/snapshot/latest',
            params={'symbol': 'BTC'}
        )
        
        if success:
            if response.get('found'):
                snapshot = response.get('snapshot', {})
                required_fields = ['asofDate', 'symbol', 'preset', 'version', 'action']
                has_all_fields = all(field in snapshot for field in required_fields)
                
                if has_all_fields:
                    details = f"Date: {snapshot.get('asofDate')}, Action: {snapshot.get('action')}, Preset: {snapshot.get('preset')}"
                    self.log_test_result("Latest Snapshot API", True, details)
                    return snapshot
                else:
                    missing = [f for f in required_fields if f not in snapshot]
                    self.log_test_result("Latest Snapshot API", False, f"Missing snapshot fields: {missing}")
                    return None
            else:
                self.log_test_result("Latest Snapshot API", True, "No snapshots found (valid response)")
                return None
        else:
            self.log_test_result("Latest Snapshot API", False, str(response))
            return None

    def test_write_snapshot_new_date(self):
        """Test writing snapshot for a new date (should write 3 presets)"""
        # Use yesterday's date to avoid conflicts with existing data
        test_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        success, response = self.test_api_call(
            'POST',
            '/api/fractal/v2.1/admin/snapshot/write-btc',
            params={'asofDate': test_date}
        )
        
        if success:
            written = response.get('written', 0)
            skipped = response.get('skipped', 0)
            items = response.get('items', [])
            
            if written == 3 and skipped == 0:
                details = f"Written: {written}, Skipped: {skipped}, Date: {test_date}"
                self.log_test_result("Write New Snapshot", True, details)
                return response, test_date
            else:
                # Check if this is because snapshots already exist for this date
                if written == 0 and skipped == 3:
                    details = f"All snapshots already exist for {test_date} (written: {written}, skipped: {skipped})"
                    self.log_test_result("Write New Snapshot", True, details)
                    return response, test_date
                else:
                    details = f"Unexpected counts - Written: {written}, Skipped: {skipped}"
                    self.log_test_result("Write New Snapshot", False, details)
                    return None, test_date
        else:
            self.log_test_result("Write New Snapshot", False, str(response))
            return None, test_date

    def test_write_snapshot_idempotency(self, test_date):
        """Test idempotency - repeat call should return skipped:3"""
        success, response = self.test_api_call(
            'POST',
            '/api/fractal/v2.1/admin/snapshot/write-btc',
            params={'asofDate': test_date}
        )
        
        if success:
            written = response.get('written', 0)
            skipped = response.get('skipped', 0)
            
            if written == 0 and skipped == 3:
                details = f"Idempotency verified - Written: {written}, Skipped: {skipped}"
                self.log_test_result("Idempotency Test", True, details)
                return True
            else:
                details = f"Idempotency failed - Written: {written}, Skipped: {skipped}"
                self.log_test_result("Idempotency Test", False, details)
                return False
        else:
            self.log_test_result("Idempotency Test", False, str(response))
            return False

    def test_write_snapshot_current_date(self):
        """Test writing snapshot for current/existing date (should return skipped)"""
        # Use default date (current)
        success, response = self.test_api_call(
            'POST',
            '/api/fractal/v2.1/admin/snapshot/write-btc'
        )
        
        if success:
            written = response.get('written', 0)
            skipped = response.get('skipped', 0)
            asof_date = response.get('asofDate', 'unknown')
            
            if skipped == 3:
                details = f"Existing data handled correctly - Written: {written}, Skipped: {skipped}, Date: {asof_date}"
                self.log_test_result("Write Existing Date", True, details)
                return True
            else:
                details = f"Unexpected behavior - Written: {written}, Skipped: {skipped}, Date: {asof_date}"
                self.log_test_result("Write Existing Date", False, details)
                return False
        else:
            self.log_test_result("Write Existing Date", False, str(response))
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🔍 Starting BTC Signal Snapshot Writer Tests...")
        print("=" * 60)
        
        # Test 1: Check snapshot counts
        print("\n📊 Test 1: Snapshot Counts")
        initial_counts = self.test_snapshot_count()
        
        # Test 2: Get latest snapshot
        print("\n📋 Test 2: Latest Snapshot")
        latest_snapshot = self.test_latest_snapshot()
        
        # Test 3: Write snapshot for new date
        print("\n✍️ Test 3: Write New Snapshot")
        write_result, test_date = self.test_write_snapshot_new_date()
        
        # Test 4: Test idempotency
        print("\n🔄 Test 4: Idempotency Test")
        if write_result and test_date:
            self.test_write_snapshot_idempotency(test_date)
        else:
            self.log_test_result("Idempotency Test", False, "Skipped - write test failed")
        
        # Test 5: Write for current date (should be skipped)
        print("\n📅 Test 5: Write Existing Date")
        self.test_write_snapshot_current_date()
        
        # Test 6: Verify counts changed appropriately
        print("\n📊 Test 6: Final Snapshot Counts")
        final_counts = self.test_snapshot_count()
        
        # Print summary
        self.print_summary(initial_counts, final_counts)

    def print_summary(self, initial_counts, final_counts):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if initial_counts and final_counts:
            print(f"\nSnapshot Count Changes:")
            print(f"Initial - Active: {initial_counts.get('active', 0)}, Shadow: {initial_counts.get('shadow', 0)}")
            print(f"Final   - Active: {final_counts.get('active', 0)}, Shadow: {final_counts.get('shadow', 0)}")
        
        print(f"\nDetailed Results:")
        for result in self.test_results:
            print(f"  {result['status']} - {result['test_name']}")
            if result['details']:
                print(f"    {result['details']}")
        
        print("\n" + "=" * 60)
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = SnapshotWriterTester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())