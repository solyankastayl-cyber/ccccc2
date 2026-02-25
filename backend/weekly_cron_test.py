#!/usr/bin/env python3
"""
BLOCK 76.3 Weekly Cron Integration Testing Suite
Tests Weekly Cron API endpoints and protection logic
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class WeeklyCronTester:
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
        if "response_data" in details:
            print(f"    Response: {json.dumps(details['response_data'], indent=2)}")
        print()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, timeout: int = 60) -> tuple[bool, Dict[str, Any]]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                headers = {'Content-Type': 'application/json'}
                # For empty POST requests, send empty JSON object instead of None
                json_data = data if data is not None else {}
                response = requests.post(url, headers=headers, json=json_data, params=params, timeout=timeout)
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

    def test_weekly_cron_status(self):
        """Test GET /api/fractal/v2.1/admin/weekly-cron/status - returns enabled, running, config, nextRun, lastRun"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/weekly-cron/status")
        
        if success:
            data = details.get("response_data", {})
            
            # Check required status fields
            required_fields = ["enabled", "running", "config", "nextRun", "lastRun"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing fields: {missing_fields}"
            else:
                # Validate config structure
                config = data.get("config", {})
                expected_config_fields = ["dayOfWeek", "hour", "minute", "minSamples", "enabled"]
                missing_config = [field for field in expected_config_fields if field not in config]
                
                if missing_config:
                    success = False
                    details["error"] = f"Missing config fields: {missing_config}"
                else:
                    # Validate config values
                    if config["dayOfWeek"] != 0:  # 0 = Sunday
                        success = False
                        details["error"] = f"Expected dayOfWeek=0 (Sunday), got {config['dayOfWeek']}"
                    elif config["hour"] != 10:  # 10 UTC
                        success = False
                        details["error"] = f"Expected hour=10 UTC, got {config['hour']}"
                    elif config["minSamples"] != 30:  # Minimum 30 samples
                        success = False
                        details["error"] = f"Expected minSamples=30, got {config['minSamples']}"
                    
                    # Store status summary
                    details["status_summary"] = {
                        "enabled": data["enabled"],
                        "running": data["running"],
                        "schedule": f"Sunday {config['hour']:02d}:{config['minute']:02d} UTC",
                        "min_samples": config["minSamples"],
                        "next_run": data["nextRun"],
                        "last_run": data["lastRun"]
                    }
        
        self.log_test("Weekly Cron Status API", success, details)
        return success

    def test_weekly_cron_check_protections(self):
        """Test POST /api/fractal/v2.1/admin/weekly-cron/check - checks protections (canSend, reason)"""
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/weekly-cron/check")
        
        if success:
            data = details.get("response_data", {})
            
            # Check required protection fields
            required_fields = ["canSend", "reason"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing protection fields: {missing_fields}"
            else:
                can_send = data.get("canSend")
                reason = data.get("reason")
                modify_message = data.get("modifyMessage", False)
                
                # Validate canSend is boolean
                if not isinstance(can_send, bool):
                    success = False
                    details["error"] = f"Expected canSend to be boolean, got {type(can_send)}"
                else:
                    # Store protection summary
                    details["protection_result"] = {
                        "can_send": can_send,
                        "reason": reason,
                        "modify_message": modify_message
                    }
                    
                    # Check for expected protection reasons
                    if not can_send:
                        expected_reasons = [
                            "No resolved outcomes in memory",
                            "Insufficient samples:",
                            "Protection check error:"
                        ]
                        reason_match = any(expected in reason for expected in expected_reasons)
                        if not reason_match:
                            details["warning"] = f"Unexpected protection reason: {reason}"
                    elif can_send and modify_message:
                        # CRISIS regime case
                        if "CRISIS regime" not in reason:
                            details["warning"] = f"Expected CRISIS regime reason when modifyMessage=true, got: {reason}"
        
        self.log_test("Weekly Cron Protection Check", success, details)
        return success

    def test_weekly_cron_manual_trigger(self):
        """Test POST /api/fractal/v2.1/admin/weekly-cron/trigger - manual trigger with protections"""
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/weekly-cron/trigger")
        
        if success:
            data = details.get("response_data", {})
            
            # Check required trigger response fields
            required_fields = ["success", "protection"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing trigger response fields: {missing_fields}"
            else:
                trigger_success = data.get("success")
                protection = data.get("protection", {})
                result = data.get("result")
                
                # Validate protection object
                if not isinstance(protection, dict):
                    success = False
                    details["error"] = "Expected protection to be an object"
                elif "canSend" not in protection or "reason" not in protection:
                    success = False
                    details["error"] = "Protection object missing canSend or reason"
                else:
                    # Store trigger summary
                    details["trigger_result"] = {
                        "success": trigger_success,
                        "protection": {
                            "can_send": protection["canSend"],
                            "reason": protection["reason"],
                            "modify_message": protection.get("modifyMessage", False)
                        },
                        "result": result
                    }
                    
                    # If protection blocked, success should be False
                    if not protection["canSend"] and trigger_success:
                        success = False
                        details["error"] = "Expected success=false when protection.canSend=false"
                    
                    # If protection allowed and success=true, check result
                    if protection["canSend"] and trigger_success and result:
                        if not isinstance(result, dict):
                            success = False
                            details["error"] = "Expected result to be an object when digest sent"
                        elif "success" not in result or "message" not in result:
                            success = False
                            details["error"] = "Result object missing success or message fields"
        
        self.log_test("Weekly Cron Manual Trigger", success, details)
        return success

    def test_protection_logic_samples_threshold(self):
        """Test protection logic: blocks if samples < threshold (30)"""
        # First check current protection status
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/weekly-cron/check")
        
        if success:
            data = details.get("response_data", {})
            can_send = data.get("canSend")
            reason = data.get("reason", "")
            
            # Check if it's blocked due to insufficient samples
            if not can_send and "Insufficient samples" in reason:
                # Extract sample count from reason
                try:
                    # Reason format: "Insufficient samples: X < 30 required"
                    if "<" in reason:
                        sample_count_str = reason.split(":")[1].split("<")[0].strip()
                        sample_count = int(sample_count_str)
                        
                        if sample_count >= 30:
                            success = False
                            details["error"] = f"Expected sample count < 30 for blocking, got {sample_count}"
                        else:
                            details["protection_validation"] = {
                                "sample_count": sample_count,
                                "threshold": 30,
                                "blocked": True,
                                "reason": reason
                            }
                    else:
                        details["warning"] = f"Unexpected insufficient samples reason format: {reason}"
                except (ValueError, IndexError):
                    details["warning"] = f"Could not parse sample count from reason: {reason}"
            
            elif not can_send and "No resolved outcomes" in reason:
                # Blocked due to no resolved outcomes (sample count = 0)
                details["protection_validation"] = {
                    "sample_count": 0,
                    "threshold": 30,
                    "blocked": True,
                    "reason": "No resolved outcomes in memory"
                }
            
            elif can_send:
                # Not blocked - should have sufficient samples
                details["protection_validation"] = {
                    "blocked": False,
                    "reason": reason,
                    "note": "Protection passed - sufficient samples available"
                }
            
            else:
                # Other protection reason
                details["protection_validation"] = {
                    "blocked": True,
                    "reason": reason,
                    "note": "Blocked for other protection reason"
                }
        
        self.log_test("Protection Logic - Samples Threshold", success, details)
        return success

    def test_protection_logic_resolved_outcomes(self):
        """Test protection logic: blocks if no resolved outcomes"""
        # Check protection status specifically for resolved outcomes
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/weekly-cron/check")
        
        if success:
            data = details.get("response_data", {})
            can_send = data.get("canSend")
            reason = data.get("reason", "")
            
            # Analysis of protection result
            details["resolved_outcomes_check"] = {
                "can_send": can_send,
                "reason": reason
            }
            
            if not can_send:
                if "No resolved outcomes" in reason:
                    details["resolved_outcomes_check"]["status"] = "BLOCKED - No resolved outcomes (correct behavior)"
                elif "Insufficient samples" in reason:
                    details["resolved_outcomes_check"]["status"] = "BLOCKED - Insufficient samples (resolved outcomes exist but < 30)"
                else:
                    details["resolved_outcomes_check"]["status"] = f"BLOCKED - Other reason: {reason}"
            else:
                details["resolved_outcomes_check"]["status"] = "ALLOWED - Sufficient resolved outcomes and samples"
        
        self.log_test("Protection Logic - Resolved Outcomes", success, details)
        return success

    def test_crisis_regime_protection(self):
        """Test protection logic: CRISIS regime detection and message modification"""
        # Check if CRISIS regime affects protection
        success, details = self.make_request("POST", "/api/fractal/v2.1/admin/weekly-cron/check")
        
        if success:
            data = details.get("response_data", {})
            can_send = data.get("canSend")
            reason = data.get("reason", "")
            modify_message = data.get("modifyMessage", False)
            
            details["crisis_regime_check"] = {
                "can_send": can_send,
                "reason": reason,
                "modify_message": modify_message
            }
            
            if modify_message:
                # CRISIS regime detected
                if "CRISIS regime" not in reason:
                    success = False
                    details["error"] = f"Expected CRISIS regime in reason when modifyMessage=true, got: {reason}"
                elif not can_send:
                    success = False
                    details["error"] = "Expected canSend=true when CRISIS regime detected (should send with modified message)"
                else:
                    details["crisis_regime_check"]["status"] = "CRISIS regime detected - will send with modified message"
            
            elif can_send and not modify_message:
                details["crisis_regime_check"]["status"] = "Normal regime - no message modification needed"
            
            elif not can_send:
                details["crisis_regime_check"]["status"] = f"Blocked by other protection: {reason}"
        
        self.log_test("Protection Logic - CRISIS Regime", success, details)
        return success

    def test_cron_configuration_validation(self):
        """Test weekly cron configuration values"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/weekly-cron/status")
        
        if success:
            data = details.get("response_data", {})
            config = data.get("config", {})
            
            # Validate expected configuration values from weekly-cron.scheduler.ts
            expected_config = {
                "dayOfWeek": 0,      # Sunday
                "hour": 10,          # 10:00 UTC  
                "minute": 0,         # :00
                "minSamples": 30,    # Minimum 30 samples
                "enabled": True      # Should be enabled by default
            }
            
            config_validation = {}
            for key, expected_value in expected_config.items():
                actual_value = config.get(key)
                if actual_value != expected_value:
                    if key == "enabled":
                        # enabled could be false via WEEKLY_DIGEST_CRON env var
                        config_validation[key] = f"Expected {expected_value}, got {actual_value} (may be disabled via env)"
                    else:
                        success = False
                        details["error"] = f"Config {key}: expected {expected_value}, got {actual_value}"
                        break
                else:
                    config_validation[key] = f"✅ {actual_value}"
            
            if success:
                details["config_validation"] = config_validation
                
                # Validate nextRun format (should be ISO string)
                next_run = data.get("nextRun")
                if next_run:
                    try:
                        next_run_date = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                        details["next_run_validation"] = {
                            "next_run": next_run,
                            "parsed_date": next_run_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "day_of_week": next_run_date.weekday() + 1 if next_run_date.weekday() != 6 else 0  # Convert to Sunday=0
                        }
                        
                        # Should be a Sunday at 10:00 UTC
                        expected_day = 0  # Sunday
                        expected_hour = 10
                        actual_day = 0 if next_run_date.weekday() == 6 else next_run_date.weekday() + 1
                        actual_hour = next_run_date.hour
                        
                        if actual_day != expected_day:
                            success = False
                            details["error"] = f"Next run should be on Sunday (0), got day {actual_day}"
                        elif actual_hour != expected_hour:
                            success = False
                            details["error"] = f"Next run should be at hour 10, got hour {actual_hour}"
                    
                    except ValueError:
                        success = False
                        details["error"] = f"Invalid nextRun ISO format: {next_run}"
                else:
                    details["warning"] = "nextRun is null"
        
        self.log_test("Cron Configuration Validation", success, details)
        return success

    def test_cron_scheduler_running_status(self):
        """Test if cron scheduler is properly running"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/weekly-cron/status")
        
        if success:
            data = details.get("response_data", {})
            enabled = data.get("enabled")
            running = data.get("running")
            
            details["scheduler_status"] = {
                "enabled": enabled,
                "running": running
            }
            
            if enabled and not running:
                success = False
                details["error"] = "Cron scheduler is enabled but not running"
            elif not enabled and running:
                success = False
                details["error"] = "Cron scheduler is running but marked as disabled"
            elif enabled and running:
                details["scheduler_status"]["status"] = "✅ Scheduler enabled and running"
            elif not enabled and not running:
                details["scheduler_status"]["status"] = "⚠️ Scheduler disabled (check WEEKLY_DIGEST_CRON env var)"
        
        self.log_test("Cron Scheduler Running Status", success, details)
        return success

    def run_all_tests(self):
        """Run all weekly cron integration tests"""
        print("=" * 50)
        print("WEEKLY CRON INTEGRATION TEST SUITE")
        print("=" * 50)
        print()
        
        # Core API endpoints
        self.test_weekly_cron_status()
        self.test_weekly_cron_check_protections()
        self.test_weekly_cron_manual_trigger()
        
        # Protection logic validation
        self.test_protection_logic_samples_threshold()
        self.test_protection_logic_resolved_outcomes()
        self.test_crisis_regime_protection()
        
        # Configuration validation
        self.test_cron_configuration_validation()
        self.test_cron_scheduler_running_status()
        
        # Summary
        print("=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed < self.tests_run:
            print(f"\n❌ {self.tests_run - self.tests_passed} test(s) failed")
            return 1
        else:
            print(f"\n✅ All tests passed!")
            return 0

def main():
    tester = WeeklyCronTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())