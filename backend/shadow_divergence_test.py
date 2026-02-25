#!/usr/bin/env python3
"""
Shadow Divergence API Testing Suite
Tests the Shadow Divergence endpoints for BLOCK 57.2
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class ShadowDivergenceAPITester:
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
        if "response_data" in details and not success:
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

    def test_shadow_divergence_api(self):
        """Test GET /api/fractal/v2.1/admin/shadow-divergence?symbol=BTC"""
        params = {"symbol": "BTC"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/shadow-divergence", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Check required top-level fields
            required_fields = ["meta", "recommendation", "summary", "divergenceLedger"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing required fields: {missing_fields}"
            else:
                # Validate meta structure
                meta = data.get("meta", {})
                meta_fields = ["symbol", "resolvedCount", "version"]
                missing_meta = [field for field in meta_fields if field not in meta]
                if missing_meta:
                    success = False
                    details["error"] = f"Missing meta fields: {missing_meta}"
                
                # Validate recommendation structure
                if success:
                    recommendation = data.get("recommendation", {})
                    rec_fields = ["verdict", "shadowScore", "reasoning"]
                    missing_rec = [field for field in rec_fields if field not in recommendation]
                    if missing_rec:
                        success = False
                        details["error"] = f"Missing recommendation fields: {missing_rec}"
                
                # Validate summary structure (3x3 matrix)
                if success:
                    summary = data.get("summary", {})
                    presets = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
                    horizons = ["7d", "14d", "30d"]
                    
                    for preset in presets:
                        if preset not in summary:
                            success = False
                            details["error"] = f"Missing preset '{preset}' in summary"
                            break
                        for horizon in horizons:
                            if horizon not in summary[preset]:
                                success = False
                                details["error"] = f"Missing horizon '{horizon}' in preset '{preset}'"
                                break
                
                # Validate divergenceLedger is a list
                if success:
                    ledger = data.get("divergenceLedger", [])
                    if not isinstance(ledger, list):
                        success = False
                        details["error"] = "Expected divergenceLedger to be a list"
                
                if success:
                    details["validation_summary"] = {
                        "resolved_count": meta.get("resolvedCount", 0),
                        "verdict": recommendation.get("verdict", "UNKNOWN"),
                        "shadow_score": recommendation.get("shadowScore", 0),
                        "ledger_entries": len(ledger),
                        "presets_available": len(summary.keys()),
                        "horizons_per_preset": len(summary.get("BALANCED", {}).keys()) if "BALANCED" in summary else 0
                    }
        
        self.log_test("Shadow Divergence API (/api/fractal/v2.1/admin/shadow-divergence)", success, details)
        return success

    def test_admin_overview_api(self):
        """Test GET /api/fractal/v2.1/admin/overview?symbol=BTC (for Overview tab)"""
        params = {"symbol": "BTC"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Check required fields for admin overview
            required_fields = ["meta", "governance", "health", "guard", "model", "performance", "recommendation", "recent"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing required fields: {missing_fields}"
            else:
                # Validate meta
                meta = data.get("meta", {})
                if not meta.get("symbol") or not meta.get("version"):
                    success = False
                    details["error"] = "Missing meta.symbol or meta.version"
                
                # Validate governance
                if success:
                    governance = data.get("governance", {})
                    if "status" not in governance:
                        success = False
                        details["error"] = "Missing governance.status"
                
                if success:
                    details["overview_summary"] = {
                        "symbol": meta.get("symbol"),
                        "version": meta.get("version"),
                        "governance_status": governance.get("status"),
                        "health_score": data.get("health", {}).get("score", 0),
                        "performance_sharpe": data.get("performance", {}).get("sharpe", 0)
                    }
        
        self.log_test("Admin Overview API (/api/fractal/v2.1/admin/overview)", success, details)
        return success

    def test_fractal_health(self):
        """Test /api/fractal/health endpoint"""
        success, details = self.make_request("GET", "/api/fractal/health")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif not data.get("enabled"):
                success = False
                details["error"] = "Expected 'enabled': true"
        
        self.log_test("Fractal Module Health Check", success, details)
        return success

    def run_all_tests(self):
        """Run all Shadow Divergence API tests"""
        print("🚀 Starting Shadow Divergence API Tests...")
        print(f"Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test basic health first
        self.test_fractal_health()
        
        # Test admin APIs
        self.test_admin_overview_api()
        self.test_shadow_divergence_api()
        
        # Print summary
        print("=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All Shadow Divergence API tests passed!")
            return True
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
            return False

def main():
    tester = ShadowDivergenceAPITester()
    success = tester.run_all_tests()
    
    # Save results
    with open("/app/backend/shadow_divergence_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "tests_run": tester.tests_run,
            "tests_passed": tester.tests_passed,
            "results": tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())