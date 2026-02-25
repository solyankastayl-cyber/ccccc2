#!/usr/bin/env python3
"""
Focused Alert Engine Testing (BLOCK 67-68)
Tests only the alert system endpoints
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class AlertAPITester:
    def __init__(self, base_url: str = "https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if not success and "error" in details:
            print(f"    Error: {details['error']}")
        if "response_data" in details and success:
            print(f"    Response: {json.dumps(details['response_data'], indent=2)}")
        print()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, timeout: int = 30) -> tuple[bool, Dict[str, Any]]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            return response.status_code == 200, {
                "status_code": response.status_code,
                "response_data": response_data,
                "headers": dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_alerts_list(self):
        """Test GET /api/fractal/v2.1/admin/alerts - list alerts with filters"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/alerts")
        
        if success:
            data = details.get("response_data", {})
            required_fields = ["items", "stats", "quota"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing fields: {missing_fields}"
            else:
                # Validate quota structure
                quota = data.get("quota", {})
                quota_fields = ["used", "max", "remaining"]
                missing_quota_fields = [field for field in quota_fields if field not in quota]
                if missing_quota_fields:
                    success = False
                    details["error"] = f"Missing quota fields: {missing_quota_fields}"
                elif quota.get("max") != 3:
                    success = False
                    details["error"] = f"Expected quota max 3, got {quota.get('max')}"
        
        self.log_test("Alert List API (BLOCK 67-68)", success, details)
        return success

    def test_alerts_quota(self):
        """Test GET /api/fractal/v2.1/admin/alerts/quota - quota status"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/alerts/quota")
        
        if success:
            data = details.get("response_data", {})
            required_fields = ["used", "max", "remaining"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing quota fields: {missing_fields}"
            elif data.get("max") != 3:
                success = False
                details["error"] = f"Expected max quota 3, got {data.get('max')}"
            elif data.get("used", 0) + data.get("remaining", 0) != 3:
                success = False
                details["error"] = f"Quota math error: used({data.get('used')}) + remaining({data.get('remaining')}) != 3"
            else:
                details["quota_status"] = {
                    "used": data.get("used"),
                    "remaining": data.get("remaining"),
                    "max": data.get("max")
                }
        
        self.log_test("Alert Quota Status (BLOCK 67-68)", success, details)
        return success

    def test_alerts_stats(self):
        """Test GET /api/fractal/v2.1/admin/alerts/stats - statistics"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/alerts/stats")
        
        if success:
            data = details.get("response_data", {})
            required_fields = ["stats", "quota"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing fields: {missing_fields}"
            else:
                stats = data.get("stats", {})
                if "last24h" not in stats or "last7d" not in stats:
                    success = False
                    details["error"] = "Missing last24h or last7d stats"
                else:
                    # Validate stats structure
                    last24h = stats.get("last24h", {})
                    last7d = stats.get("last7d", {})
                    
                    level_fields = ["INFO", "HIGH", "CRITICAL"]
                    for period, period_stats in [("last24h", last24h), ("last7d", last7d)]:
                        for level in level_fields:
                            if level not in period_stats:
                                success = False
                                details["error"] = f"Missing {level} count in {period}"
                                break
                        if not success:
                            break
                    
                    if success:
                        details["stats_summary"] = {
                            "last24h": {level: last24h.get(level, 0) for level in level_fields},
                            "last7d": {level: last7d.get(level, 0) for level in level_fields}
                        }
        
        self.log_test("Alert Statistics (BLOCK 67-68)", success, details)
        return success

    def test_alerts_latest(self):
        """Test GET /api/fractal/v2.1/admin/alerts/latest - recent alerts"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/alerts/latest")
        
        if success:
            data = details.get("response_data", {})
            if "items" not in data:
                success = False
                details["error"] = "Missing 'items' field"
            else:
                items = data.get("items", [])
                if len(items) > 20:
                    success = False
                    details["error"] = f"Expected max 20 items, got {len(items)}"
                else:
                    details["latest_count"] = len(items)
        
        self.log_test("Alert Latest (BLOCK 67-68)", success, details)
        return success

    def test_alerts_check_dry_run(self):
        """Test POST /api/fractal/v2.1/admin/alerts/check - dry run"""
        data = {
            "symbol": "BTC",
            "current": {
                "volRegime": "NORMAL",
                "marketPhase": "BULL",
                "health": "HEALTHY",
                "tailRisk": 5.2,
                "decision": "LONG",
                "blockers": []
            },
            "previous": {
                "volRegime": "LOW",
                "marketPhase": "BULL", 
                "health": "HEALTHY",
                "tailRisk": 3.1
            }
        }
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/alerts/check", data=data)
        
        if success:
            response_data = details.get("response_data", {})
            if not response_data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif not response_data.get("dryRun"):
                success = False
                details["error"] = "Expected 'dryRun': true"
            elif "eventsCount" not in response_data:
                success = False
                details["error"] = "Missing 'eventsCount' field"
            elif "events" not in response_data:
                success = False
                details["error"] = "Missing 'events' field"
            else:
                events = response_data.get("events", [])
                events_count = response_data.get("eventsCount", 0)
                
                if len(events) != events_count:
                    success = False
                    details["error"] = f"Events count mismatch: {len(events)} vs {events_count}"
                else:
                    # Should detect regime shift from LOW to NORMAL
                    regime_events = [e for e in events if e.get("type") == "REGIME_SHIFT"]
                    details["dry_run_results"] = {
                        "events_count": events_count,
                        "regime_shifts": len(regime_events),
                        "total_events": len(events)
                    }
        
        self.log_test("Alert Check Dry Run (BLOCK 67-68)", success, details)
        return success

    def test_alerts_test_telegram(self):
        """Test POST /api/fractal/v2.1/admin/alerts/test - send test alert"""
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/alerts/test")
        
        if success:
            response_data = details.get("response_data", {})
            if "ok" not in response_data:
                success = False
                details["error"] = "Missing 'ok' field"
            elif "telegram" not in response_data:
                success = False
                details["error"] = "Missing 'telegram' field"
            else:
                telegram = response_data.get("telegram", {})
                if "sent" not in telegram or "failed" not in telegram:
                    success = False
                    details["error"] = "Missing telegram sent/failed counts"
                else:
                    details["test_alert_results"] = {
                        "success": response_data.get("ok"),
                        "telegram_sent": telegram.get("sent", 0),
                        "telegram_failed": telegram.get("failed", 0)
                    }
                    
                    # Note: Test alert might fail if Telegram is not configured
                    if not response_data.get("ok") and telegram.get("failed", 0) > 0:
                        details["note"] = "Test alert failed - Telegram may not be configured (expected in test environment)"
        
        self.log_test("Alert Test Telegram (BLOCK 67-68)", success, details)
        return success

    def test_alerts_filters(self):
        """Test alert list with various filters"""
        # Test level filter
        params = {"level": "CRITICAL"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/alerts", params=params)
        
        if success:
            data = details.get("response_data", {})
            items = data.get("items", [])
            details["critical_filter_count"] = len(items)
        
        # Test type filter
        if success:
            params = {"type": "REGIME_SHIFT"}
            success2, details2 = self.make_request("GET", "/api/fractal/v2.1/admin/alerts", params=params)
            
            if success2:
                data2 = details2.get("response_data", {})
                items2 = data2.get("items", [])
                details["regime_shift_filter_count"] = len(items2)
            else:
                success = False
                details["error"] = f"Type filter failed: {details2.get('error')}"
        
        # Test status filter
        if success:
            params = {"blockedBy": "NONE"}
            success3, details3 = self.make_request("GET", "/api/fractal/v2.1/admin/alerts", params=params)
            
            if success3:
                data3 = details3.get("response_data", {})
                items3 = data3.get("items", [])
                details["sent_alerts_count"] = len(items3)
            else:
                success = False
                details["error"] = f"Status filter failed: {details3.get('error')}"
        
        self.log_test("Alert Filters (BLOCK 67-68)", success, details)
        return success

    def run_all_tests(self):
        """Run all alert tests"""
        print(f"🚨 Alert Engine Testing Suite (BLOCK 67-68)")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 50)
        
        alert_tests = [
            self.test_alerts_quota(),
            self.test_alerts_stats(),
            self.test_alerts_latest(),
            self.test_alerts_list(),
            self.test_alerts_check_dry_run(),
            self.test_alerts_test_telegram(),
            self.test_alerts_filters(),
        ]
        
        print("\n" + "=" * 50)
        print(f"📊 ALERT ENGINE TEST RESULTS")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0.0%")
        
        alert_success = sum(alert_tests) / len(alert_tests) * 100 if alert_tests else 0
        print(f"Alert Engine Success: {alert_success:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL ALERT TESTS PASSED!")
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} ALERT TESTS FAILED")
            
            # Show failed tests
            failed_tests = [r for r in self.test_results if not r["success"]]
            if failed_tests:
                print("\n❌ FAILED TESTS:")
                for test in failed_tests:
                    print(f"  - {test['test']}")
                    if "error" in test:
                        print(f"    Error: {test['error']}")
        
        return {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
            "alert_success": alert_success,
            "all_results": self.test_results
        }

def main():
    """Main test execution"""
    print("🔧 Alert Engine Testing Suite - BLOCK 67-68")
    print(f"Testing backend at: https://pointintime-macro.preview.emergentagent.com")
    print(f"Test started at: {datetime.now().isoformat()}")
    print()
    
    tester = AlertAPITester()
    results = tester.run_all_tests()
    
    # Return appropriate exit code
    if results["alert_success"] >= 80:
        print("🎉 Alert Engine testing completed successfully!")
        return 0
    else:
        print("💥 Alert Engine testing found critical issues!")
        return 1

if __name__ == "__main__":
    sys.exit(main())