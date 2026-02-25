#!/usr/bin/env python3
"""
BLOCK B Module Isolation Testing Suite
Tests the module isolation implementation as requested in review
"""

import requests
import sys
import json
import subprocess
import time
from datetime import datetime
from typing import Dict, Any, Optional

class IsolationModuleTester:
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
        if "response_data" in details and details["response_data"]:
            print(f"    Response: {json.dumps(details['response_data'], indent=2)[:300]}...")
        print()

    def make_request(self, method: str, endpoint: str, timeout: int = 30) -> tuple[bool, Dict[str, Any]]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
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

    def run_shell_command(self, command: str, cwd: str = "/app/backend") -> tuple[bool, str]:
        """Run shell command and return success status and output"""
        try:
            result = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60)
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def test_backend_health(self):
        """Test GET /api/health should return {ok: true}"""
        success, details = self.make_request("GET", "/api/health")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                details["note"] = f"Health check passed with mode: {data.get('mode', 'unknown')}"
        
        self.log_test("Backend Health: GET /api/health", success, details)
        return success

    def test_fractal_health(self):
        """Test GET /api/fractal/health should return {ok: true, enabled: true}"""
        success, details = self.make_request("GET", "/api/fractal/health")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif not data.get("enabled"):
                success = False
                details["error"] = "Expected 'enabled': true"
            else:
                details["note"] = f"Fractal health check passed with {data.get('candleCount', 0)} candles"
        
        self.log_test("Fractal Health: GET /api/fractal/health", success, details)
        return success

    def test_freeze_status(self):
        """Test GET /api/fractal/v2.1/admin/freeze-status should return frozen: true"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/freeze-status")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("frozen"):
                success = False
                details["error"] = "Expected 'frozen': true"
            else:
                details["note"] = f"Contract frozen with version: {data.get('version', 'unknown')}"
        
        self.log_test("Freeze Status: GET /api/fractal/v2.1/admin/freeze-status", success, details)
        return success

    def test_isolation_linting_script(self):
        """Test isolation linting script: npx tsx scripts/check-fractal-isolation.ts"""
        success, output = self.run_shell_command("npx tsx scripts/check-fractal-isolation.ts")
        
        details = {"output": output}
        
        if success and "ISOLATION CHECK PASSED" in output:
            details["note"] = "Isolation linting passed with no violations"
        elif success and "ISOLATION CHECK FAILED" in output:
            success = False
            details["error"] = "Isolation linting found violations"
        elif not success:
            details["error"] = "Failed to run isolation linting script"
        
        self.log_test("Isolation Linting Script", success, details)
        return success

    def test_isolation_tests(self):
        """Test isolation tests: npx vitest run src/modules/fractal/isolation/__tests__/isolation.test.ts"""
        success, output = self.run_shell_command("npx vitest run src/modules/fractal/isolation/__tests__/isolation.test.ts")
        
        details = {"output": output}
        
        if success and "passed" in output.lower():
            # Extract test count from output
            lines = output.split('\n')
            for line in lines:
                if "Tests" in line and "passed" in line:
                    details["note"] = f"Isolation tests passed: {line.strip()}"
                    break
        else:
            details["error"] = "Isolation tests failed or could not be run"
        
        self.log_test("Isolation Tests (Vitest)", success, details)
        return success

    def test_frontend_accessibility(self):
        """Test if frontend is accessible (though testing type is 'backend only')"""
        # Note: Based on the review request, this is "backend only" testing
        # But let's check if frontend port is mentioned
        details = {"note": "Testing type is 'backend only' - skipping frontend accessibility test"}
        self.log_test("Frontend Accessibility (Skipped)", True, details)
        return True

    def run_all_tests(self):
        """Run all isolation module tests"""
        print("═══════════════════════════════════════════════════════════")
        print("        BLOCK B MODULE ISOLATION TEST SUITE")
        print("═══════════════════════════════════════════════════════════")
        print(f"Testing against: {self.base_url}")
        print()

        # Run tests in order
        tests = [
            self.test_backend_health,
            self.test_fractal_health,
            self.test_freeze_status,
            self.test_isolation_linting_script,
            self.test_isolation_tests,
            self.test_frontend_accessibility
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(f"ERROR in {test.__name__}", False, {"error": str(e)})

        # Print summary
        print("═══════════════════════════════════════════════════════════")
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("✅ ALL TESTS PASSED - BLOCK B MODULE ISOLATION WORKING")
        else:
            print("❌ SOME TESTS FAILED - Issues found in Module Isolation")

        return self.tests_passed == self.tests_run

def main():
    """Main test runner"""
    tester = IsolationModuleTester()
    success = tester.run_all_tests()
    
    # Save results to file
    with open("/app/backend/isolation_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "success_rate": tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": tester.test_results
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: /app/backend/isolation_test_results.json")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())