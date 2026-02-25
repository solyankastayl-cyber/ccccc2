#!/usr/bin/env python3
"""
Fractal Telegram + Cron Integration Testing Suite
Tests the production Telegram bot integration and secured cron endpoints
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class TelegramCronTester:
    def __init__(self, base_url: str = "https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.cron_secret = "fractal_production_cron_secret_2024"

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
        if "response_data" in details:
            print(f"    Response: {json.dumps(details['response_data'], indent=2)}")
        print()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None, timeout: int = 30) -> tuple[bool, Dict[str, Any]]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        default_headers = {'Content-Type': 'application/json'}
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=default_headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=default_headers, json=data, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            return response.status_code in [200, 201], {
                "status_code": response.status_code,
                "response_data": response_data,
                "headers": dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_telegram_status(self):
        """Test GET /api/fractal/v2.1/admin/telegram/status - check Telegram configuration"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/telegram/status")
        
        if success:
            data = details.get("response_data", {})
            
            # Check required fields
            required_fields = ["enabled", "tokenConfigured", "chatIdConfigured"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing fields: {missing_fields}"
            elif not data.get("enabled"):
                success = False
                details["error"] = "Telegram not enabled - check TG_BOT_TOKEN and TG_ADMIN_CHAT_ID"
            elif not data.get("tokenConfigured"):
                success = False
                details["error"] = "TG_BOT_TOKEN not configured"
            elif not data.get("chatIdConfigured"):
                success = False
                details["error"] = "TG_ADMIN_CHAT_ID not configured"
            else:
                # Check if chatId is masked properly
                chat_id = data.get("chatId", "")
                if chat_id and not chat_id.startswith("***"):
                    details["note"] = "Warning: chatId not properly masked in response"
                else:
                    details["note"] = f"Telegram configured - chatId: {chat_id}"
        
        self.log_test("Telegram Status Check", success, details)
        return success

    def test_telegram_test_message(self):
        """Test POST /api/fractal/v2.1/admin/telegram/test - send test message"""
        # Send empty JSON object to avoid empty body error
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/telegram/test", data={})
        
        if success:
            data = details.get("response_data", {})
            
            if not data.get("success"):
                success = False
                details["error"] = "Expected 'success': true"
            elif "message" not in data:
                success = False
                details["error"] = "Expected 'message' field in response"
            else:
                details["note"] = f"Test message sent: {data.get('message')}"
        elif details.get("status_code") == 400:
            # Check if it's a configuration error
            data = details.get("response_data", {})
            if data.get("error") == "TELEGRAM_NOT_CONFIGURED":
                success = False
                details["error"] = "Telegram not configured - missing TG_BOT_TOKEN or TG_ADMIN_CHAT_ID"
            else:
                success = False
                details["error"] = f"Bad request: {data.get('message', 'Unknown error')}"
        elif details.get("status_code") == 500:
            # Check if it's a Telegram API error
            data = details.get("response_data", {})
            if data.get("error") == "TELEGRAM_SEND_FAILED":
                success = False
                details["error"] = f"Telegram send failed: {data.get('details', 'Unknown error')}"
        
        self.log_test("Telegram Test Message", success, details)
        return success

    def test_daily_run_tg_no_auth(self):
        """Test POST /api/fractal/v2.1/admin/jobs/daily-run-tg without auth - should return 401"""
        # Send empty JSON object to avoid empty body error
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/jobs/daily-run-tg", data={})
        
        # This should fail with 401 Unauthorized
        if details.get("status_code") == 401:
            success = True
            data = details.get("response_data", {})
            if "error" in data:
                details["note"] = f"Correctly rejected unauthorized request: {data['error']}"
            else:
                details["note"] = "Correctly returned 401 Unauthorized"
        elif success:
            success = False
            details["error"] = "Expected 401 Unauthorized, but request succeeded"
        else:
            success = False
            details["error"] = f"Expected 401, got {details.get('status_code')}"
        
        self.log_test("Daily Run TG - No Auth (should fail)", success, details)
        return success

    def test_daily_run_tg_with_auth(self):
        """Test POST /api/fractal/v2.1/admin/jobs/daily-run-tg with Bearer auth"""
        headers = {"Authorization": f"Bearer {self.cron_secret}"}
        data = {"symbol": "BTC"}
        
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/jobs/daily-run-tg", 
                                           data=data, headers=headers, timeout=60)
        
        if success:
            response_data = details.get("response_data", {})
            
            # Check required fields
            required_fields = ["success", "telegram", "notifications"]
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing fields: {missing_fields}"
            elif not response_data.get("success"):
                # Check if there's an error message
                error_msg = response_data.get("error", "Unknown error")
                success = False
                details["error"] = f"Daily job failed: {error_msg}"
            else:
                # Validate response structure
                telegram_enabled = response_data.get("telegram", False)
                notifications = response_data.get("notifications", [])
                daily_data = response_data.get("daily", {})
                
                details["job_result"] = {
                    "telegram_enabled": telegram_enabled,
                    "notifications_sent": notifications,
                    "daily_steps": daily_data.get("steps", {}),
                    "health_level": daily_data.get("health", {}).get("level", "UNKNOWN"),
                    "resolved_count": daily_data.get("resolvedCount", 0)
                }
                
                # Check if expected notifications were sent
                expected_notifications = ["DAILY_REPORT"]
                if daily_data.get("health", {}).get("level") in ["CRITICAL", "ALERT"]:
                    expected_notifications.append("CRITICAL_ALERT")
                if daily_data.get("resolvedCount", 0) >= 30:
                    expected_notifications.append("MILESTONE_30")
                
                missing_notifications = [n for n in expected_notifications if n not in notifications]
                if missing_notifications and telegram_enabled:
                    details["note"] = f"Missing expected notifications: {missing_notifications}"
                elif telegram_enabled:
                    details["note"] = f"All expected notifications sent: {notifications}"
                else:
                    details["note"] = "Telegram disabled - no notifications sent"
        
        self.log_test("Daily Run TG - With Auth", success, details)
        return success

    def test_daily_run_tg_open(self):
        """Test POST /api/fractal/v2.1/admin/jobs/daily-run-tg-open - no auth required"""
        data = {"symbol": "BTC"}
        
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/jobs/daily-run-tg-open", 
                                           data=data, timeout=60)
        
        if success:
            response_data = details.get("response_data", {})
            
            # Check required fields (same as secured endpoint)
            required_fields = ["success", "telegram", "notifications"]
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing fields: {missing_fields}"
            elif not response_data.get("success"):
                error_msg = response_data.get("error", "Unknown error")
                success = False
                details["error"] = f"Daily job failed: {error_msg}"
            else:
                # Validate daily job steps
                daily_data = response_data.get("daily", {})
                steps = daily_data.get("steps", {})
                
                expected_steps = ["write", "resolve", "rebuild", "audit"]
                step_results = {}
                
                for step in expected_steps:
                    step_data = steps.get(step, {})
                    step_results[step] = step_data.get("success", False)
                
                details["daily_job_steps"] = step_results
                
                # Check if all steps succeeded
                failed_steps = [step for step, success in step_results.items() if not success]
                if failed_steps:
                    details["note"] = f"Some steps failed: {failed_steps}"
                else:
                    details["note"] = "All daily job steps completed successfully"
                
                # Check notifications
                notifications = response_data.get("notifications", [])
                telegram_enabled = response_data.get("telegram", False)
                
                if telegram_enabled and "DAILY_REPORT" not in notifications:
                    details["note"] += " | Warning: Daily report notification not sent"
                elif telegram_enabled:
                    details["note"] += f" | Notifications sent: {notifications}"
        
        self.log_test("Daily Run TG Open - No Auth", success, details)
        return success

    def test_daily_job_workflow(self):
        """Test the complete daily job workflow: WRITE → RESOLVE → REBUILD → AUDIT"""
        data = {"symbol": "BTC"}
        
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/jobs/daily-run-tg-open", 
                                           data=data, timeout=90)
        
        if success:
            response_data = details.get("response_data", {})
            
            if response_data.get("success"):
                daily_data = response_data.get("daily", {})
                steps = daily_data.get("steps", {})
                
                # Validate each step in the workflow
                workflow_validation = {}
                
                # WRITE step
                write_step = steps.get("write", {})
                workflow_validation["WRITE"] = {
                    "success": write_step.get("success", False),
                    "written": write_step.get("written", 0),
                    "skipped": write_step.get("skipped", 0)
                }
                
                # RESOLVE step
                resolve_step = steps.get("resolve", {})
                workflow_validation["RESOLVE"] = {
                    "success": resolve_step.get("success", False),
                    "resolved": resolve_step.get("resolved", 0)
                }
                
                # REBUILD step
                rebuild_step = steps.get("rebuild", {})
                workflow_validation["REBUILD"] = {
                    "success": rebuild_step.get("success", False)
                }
                
                # AUDIT step
                audit_step = steps.get("audit", {})
                workflow_validation["AUDIT"] = {
                    "success": audit_step.get("success", False)
                }
                
                details["workflow_steps"] = workflow_validation
                
                # Check if all steps completed successfully
                failed_steps = [step for step, data in workflow_validation.items() 
                              if not data.get("success")]
                
                if failed_steps:
                    success = False
                    details["error"] = f"Workflow steps failed: {failed_steps}"
                else:
                    details["note"] = "Complete workflow executed successfully: WRITE → RESOLVE → REBUILD → AUDIT"
                    
                    # Additional validation
                    total_written = workflow_validation["WRITE"]["written"]
                    total_resolved = workflow_validation["RESOLVE"]["resolved"]
                    
                    if total_written > 0:
                        details["note"] += f" | Written: {total_written} signals"
                    if total_resolved > 0:
                        details["note"] += f" | Resolved: {total_resolved} signals"
            else:
                success = False
                details["error"] = f"Daily job failed: {response_data.get('error', 'Unknown error')}"
        
        self.log_test("Daily Job Workflow (4 steps)", success, details)
        return success

    def test_telegram_daily_report_format(self):
        """Test that Telegram daily report is sent with correct format after job"""
        data = {"symbol": "BTC"}
        
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/jobs/daily-run-tg-open", 
                                           data=data, timeout=60)
        
        if success:
            response_data = details.get("response_data", {})
            
            if response_data.get("success"):
                telegram_enabled = response_data.get("telegram", False)
                notifications = response_data.get("notifications", [])
                daily_data = response_data.get("daily", {})
                
                if not telegram_enabled:
                    success = False
                    details["error"] = "Telegram not enabled - cannot test report format"
                elif "DAILY_REPORT" not in notifications:
                    success = False
                    details["error"] = "Daily report notification not sent"
                else:
                    # Validate daily report data structure
                    report_validation = {}
                    
                    # Check required fields for report
                    required_report_fields = ["asofDate", "symbol", "steps", "health", "reliability"]
                    missing_report_fields = [field for field in required_report_fields 
                                           if field not in daily_data]
                    
                    if missing_report_fields:
                        success = False
                        details["error"] = f"Missing daily report fields: {missing_report_fields}"
                    else:
                        report_validation = {
                            "date": daily_data.get("asofDate"),
                            "symbol": daily_data.get("symbol"),
                            "health_level": daily_data.get("health", {}).get("level"),
                            "reliability_badge": daily_data.get("reliability", {}).get("badge"),
                            "reliability_score": daily_data.get("reliability", {}).get("score"),
                            "resolved_count": daily_data.get("resolvedCount", 0),
                            "governance_mode": daily_data.get("governanceMode", "NORMAL")
                        }
                        
                        details["daily_report_data"] = report_validation
                        
                        # Check if critical alert should be sent
                        health_level = daily_data.get("health", {}).get("level", "")
                        if health_level in ["CRITICAL", "ALERT", "HALT", "PROTECTION"]:
                            if "CRITICAL_ALERT" not in notifications:
                                details["note"] = f"Warning: Health level is {health_level} but no critical alert sent"
                            else:
                                details["note"] = f"Critical alert correctly sent for {health_level} health"
                        else:
                            details["note"] = f"Daily report sent for {health_level} health level"
                        
                        # Check milestone notification
                        resolved_count = daily_data.get("resolvedCount", 0)
                        if resolved_count >= 30:
                            if "MILESTONE_30" not in notifications:
                                details["note"] += f" | Warning: {resolved_count} resolved but no milestone notification"
                            else:
                                details["note"] += f" | Milestone notification sent for {resolved_count} resolved"
            else:
                success = False
                details["error"] = f"Daily job failed: {response_data.get('error', 'Unknown error')}"
        
        self.log_test("Telegram Daily Report Format", success, details)
        return success

    def test_cron_auth_validation(self):
        """Test cron authentication with various scenarios"""
        test_cases = [
            {
                "name": "Invalid Bearer token",
                "headers": {"Authorization": "Bearer invalid_token"},
                "expected_status": 401
            },
            {
                "name": "Missing Bearer prefix",
                "headers": {"Authorization": self.cron_secret},
                "expected_status": 401
            },
            {
                "name": "Empty Authorization header",
                "headers": {"Authorization": ""},
                "expected_status": 401
            },
            {
                "name": "Valid Bearer token",
                "headers": {"Authorization": f"Bearer {self.cron_secret}"},
                "expected_status": 200
            }
        ]
        
        all_passed = True
        auth_results = {}
        
        for case in test_cases:
            success, details = self.make_request("POST", "/api/fractal/v2.1/admin/jobs/daily-run-tg", 
                                               data={"symbol": "BTC"}, headers=case["headers"], timeout=30)
            
            actual_status = details.get("status_code", 0)
            expected_status = case["expected_status"]
            
            case_passed = (actual_status == expected_status)
            if not case_passed:
                all_passed = False
            
            auth_results[case["name"]] = {
                "passed": case_passed,
                "expected_status": expected_status,
                "actual_status": actual_status,
                "response": details.get("response_data", {})
            }
        
        details = {"auth_test_results": auth_results}
        if not all_passed:
            failed_cases = [name for name, result in auth_results.items() if not result["passed"]]
            details["error"] = f"Failed auth test cases: {failed_cases}"
        else:
            details["note"] = "All authentication scenarios tested successfully"
        
        self.log_test("Cron Authentication Validation", all_passed, details)
        return all_passed

    def run_all_tests(self):
        """Run all Telegram + Cron integration tests"""
        print("🚀 Starting Fractal Telegram + Cron Integration Tests")
        print(f"Base URL: {self.base_url}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_telegram_status,
            self.test_telegram_test_message,
            self.test_daily_run_tg_no_auth,
            self.test_cron_auth_validation,
            self.test_daily_run_tg_open,
            self.test_daily_job_workflow,
            self.test_telegram_daily_report_format,
            self.test_daily_run_tg_with_auth,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(f"{test.__name__} (EXCEPTION)", False, {"error": str(e)})
        
        # Summary
        print("=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1

    def save_results(self, filename: str = "telegram_cron_test_results.json"):
        """Save test results to JSON file"""
        results = {
            "summary": {
                "total_tests": self.tests_run,
                "passed_tests": self.tests_passed,
                "failed_tests": self.tests_run - self.tests_passed,
                "success_rate": (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Results saved to {filename}")

def main():
    # Use the frontend .env REACT_APP_BACKEND_URL for testing
    base_url = "https://pointintime-macro.preview.emergentagent.com"
    
    tester = TelegramCronTester(base_url)
    exit_code = tester.run_all_tests()
    tester.save_results()
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())