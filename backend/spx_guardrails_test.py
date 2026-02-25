#!/usr/bin/env python3
"""
SPX Guardrails Backend Testing
Testing B6.7 SPX Guardrails implementation - institutional anti-harm guardrails
"""

import requests
import json
import sys
from datetime import datetime

class SPXGuardrailsTester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, test_name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": test_name,
            "passed": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")

    def test_health_endpoint(self):
        """Test GET /api/health"""
        url = f"{self.base_url}/api/health"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    "Health Endpoint", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return False
            
            data = response.json()
            
            # Check if response has ok: true
            if not data.get('ok'):
                self.log_test(
                    "Health Endpoint", 
                    False, 
                    f"Expected ok: true, got: {data.get('ok')}"
                )
                return False
            
            self.log_test(
                "Health Endpoint", 
                True, 
                f"Health check passed: {data}"
            )
            return True
            
        except Exception as e:
            self.log_test("Health Endpoint", False, f"Exception: {str(e)}")
            return False

    def test_guardrails_full_policy(self):
        """Test GET /api/spx/v2.1/guardrails - full policy with all 6 horizons"""
        url = f"{self.base_url}/api/spx/v2.1/guardrails"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    "Guardrails Full Policy", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return False
            
            data = response.json()
            
            # Check basic response structure
            if not data.get('ok'):
                self.log_test(
                    "Guardrails Full Policy", 
                    False, 
                    f"Expected ok: true, got: {data.get('ok')}"
                )
                return False
            
            policy = data.get('data')
            if not policy:
                self.log_test(
                    "Guardrails Full Policy", 
                    False, 
                    "No policy data in response"
                )
                return False
            
            # Check required policy fields
            required_fields = ['version', 'policyHash', 'computedAt', 'globalStatus', 
                             'allowedHorizons', 'blockedHorizons', 'cautionHorizons', 'decisions']
            
            for field in required_fields:
                if field not in policy:
                    self.log_test(
                        "Guardrails Full Policy", 
                        False, 
                        f"Missing required field: {field}"
                    )
                    return False
            
            # Check decisions for all 6 horizons
            decisions = policy.get('decisions', [])
            expected_horizons = ['7d', '14d', '30d', '90d', '180d', '365d']
            
            if len(decisions) != 6:
                self.log_test(
                    "Guardrails Full Policy", 
                    False, 
                    f"Expected 6 decisions, got {len(decisions)}"
                )
                return False
            
            decision_horizons = [d.get('horizon') for d in decisions]
            for horizon in expected_horizons:
                if horizon not in decision_horizons:
                    self.log_test(
                        "Guardrails Full Policy", 
                        False, 
                        f"Missing decision for horizon: {horizon}"
                    )
                    return False
            
            # Check decision structure
            for decision in decisions:
                required_decision_fields = ['horizon', 'status', 'reasons', 'caps', 'evidence']
                for field in required_decision_fields:
                    if field not in decision:
                        self.log_test(
                            "Guardrails Full Policy", 
                            False, 
                            f"Decision missing field: {field} for horizon {decision.get('horizon')}"
                        )
                        return False
                
                # Check status is valid
                if decision['status'] not in ['ALLOW', 'CAUTION', 'BLOCK']:
                    self.log_test(
                        "Guardrails Full Policy", 
                        False, 
                        f"Invalid status: {decision['status']} for horizon {decision.get('horizon')}"
                    )
                    return False
            
            # Check meta information
            meta = data.get('meta')
            if meta:
                meta_fields = ['version', 'policyHash', 'globalStatus', 'allowedCount', 'blockedCount', 'cautionCount']
                for field in meta_fields:
                    if field not in meta:
                        self.log_test(
                            "Guardrails Full Policy", 
                            False, 
                            f"Meta missing field: {field}"
                        )
                        return False
            
            self.log_test(
                "Guardrails Full Policy", 
                True, 
                f"Policy returned with {len(decisions)} decisions, global status: {policy['globalStatus']}"
            )
            return True
            
        except Exception as e:
            self.log_test("Guardrails Full Policy", False, f"Exception: {str(e)}")
            return False

    def test_guardrails_summary(self):
        """Test GET /api/spx/v2.1/guardrails/summary"""
        url = f"{self.base_url}/api/spx/v2.1/guardrails/summary"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    "Guardrails Summary", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return False
            
            data = response.json()
            
            if not data.get('ok'):
                self.log_test(
                    "Guardrails Summary", 
                    False, 
                    f"Expected ok: true, got: {data.get('ok')}"
                )
                return False
            
            summary = data.get('data')
            if not summary:
                self.log_test(
                    "Guardrails Summary", 
                    False, 
                    "No summary data in response"
                )
                return False
            
            # Check required summary fields
            required_fields = ['globalStatus', 'version', 'policyHash', 'allowed', 
                             'blocked', 'caution', 'edgeUnlocked', 'rulesMode']
            
            for field in required_fields:
                if field not in summary:
                    self.log_test(
                        "Guardrails Summary", 
                        False, 
                        f"Missing required field: {field}"
                    )
                    return False
            
            # Check globalStatus is valid
            if summary['globalStatus'] not in ['ALLOW', 'CAUTION', 'BLOCK']:
                self.log_test(
                    "Guardrails Summary", 
                    False, 
                    f"Invalid globalStatus: {summary['globalStatus']}"
                )
                return False
            
            # Check rulesMode is ON
            if summary['rulesMode'] != 'ON':
                self.log_test(
                    "Guardrails Summary", 
                    False, 
                    f"Expected rulesMode: ON, got: {summary['rulesMode']}"
                )
                return False
            
            self.log_test(
                "Guardrails Summary", 
                True, 
                f"Summary returned: global={summary['globalStatus']}, edge={summary['edgeUnlocked']}, rules={summary['rulesMode']}"
            )
            return True
            
        except Exception as e:
            self.log_test("Guardrails Summary", False, f"Exception: {str(e)}")
            return False

    def test_guardrails_specific_horizon(self, horizon="90d"):
        """Test GET /api/spx/v2.1/guardrails/:horizon"""
        url = f"{self.base_url}/api/spx/v2.1/guardrails/{horizon}"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Guardrails Horizon ({horizon})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return False
            
            data = response.json()
            
            if not data.get('ok'):
                self.log_test(
                    f"Guardrails Horizon ({horizon})", 
                    False, 
                    f"Expected ok: true, got: {data.get('ok')}"
                )
                return False
            
            decision = data.get('data')
            if not decision:
                self.log_test(
                    f"Guardrails Horizon ({horizon})", 
                    False, 
                    "No decision data in response"
                )
                return False
            
            # Check decision structure
            required_fields = ['horizon', 'status', 'reasons', 'caps', 'evidence']
            for field in required_fields:
                if field not in decision:
                    self.log_test(
                        f"Guardrails Horizon ({horizon})", 
                        False, 
                        f"Missing required field: {field}"
                    )
                    return False
            
            # Check horizon matches request
            if decision['horizon'] != horizon:
                self.log_test(
                    f"Guardrails Horizon ({horizon})", 
                    False, 
                    f"Expected horizon {horizon}, got {decision['horizon']}"
                )
                return False
            
            # Check status is valid
            if decision['status'] not in ['ALLOW', 'CAUTION', 'BLOCK']:
                self.log_test(
                    f"Guardrails Horizon ({horizon})", 
                    False, 
                    f"Invalid status: {decision['status']}"
                )
                return False
            
            # Check caps structure
            caps = decision.get('caps', {})
            required_caps = ['maxSizeMult', 'maxConfidence', 'allowedDirections']
            for field in required_caps:
                if field not in caps:
                    self.log_test(
                        f"Guardrails Horizon ({horizon})", 
                        False, 
                        f"Caps missing field: {field}"
                    )
                    return False
            
            # Check evidence structure
            evidence = decision.get('evidence', {})
            required_evidence = ['skill', 'hitRate', 'baselineRate', 'samples']
            for field in required_evidence:
                if field not in evidence:
                    self.log_test(
                        f"Guardrails Horizon ({horizon})", 
                        False, 
                        f"Evidence missing field: {field}"
                    )
                    return False
            
            self.log_test(
                f"Guardrails Horizon ({horizon})", 
                True, 
                f"Decision: status={decision['status']}, samples={evidence['samples']}, skill={evidence['skill']}"
            )
            return True
            
        except Exception as e:
            self.log_test(f"Guardrails Horizon ({horizon})", False, f"Exception: {str(e)}")
            return False

    def test_invalid_horizon(self):
        """Test GET /api/spx/v2.1/guardrails/invalid - should return 400"""
        url = f"{self.base_url}/api/spx/v2.1/guardrails/invalid"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 400:
                self.log_test(
                    "Invalid Horizon Validation", 
                    False, 
                    f"Expected status code 400, got {response.status_code}"
                )
                return False
            
            data = response.json()
            
            if data.get('ok') is not False:
                self.log_test(
                    "Invalid Horizon Validation", 
                    False, 
                    f"Expected ok: false, got: {data.get('ok')}"
                )
                return False
            
            if 'error' not in data:
                self.log_test(
                    "Invalid Horizon Validation", 
                    False, 
                    "Expected error message in response"
                )
                return False
            
            self.log_test(
                "Invalid Horizon Validation", 
                True, 
                f"Correctly rejected invalid horizon: {data['error']}"
            )
            return True
            
        except Exception as e:
            self.log_test("Invalid Horizon Validation", False, f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all guardrails tests"""
        print("🧪 Starting SPX Guardrails Backend Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test health endpoint first
        self.test_health_endpoint()
        
        # Test all guardrails endpoints
        self.test_guardrails_full_policy()
        self.test_guardrails_summary()
        
        # Test specific horizons
        horizons_to_test = ['7d', '30d', '90d', '365d']
        for horizon in horizons_to_test:
            self.test_guardrails_specific_horizon(horizon)
        
        # Test validation
        self.test_invalid_horizon()
        
        # Print summary
        print("=" * 60)
        print(f"📊 Tests completed: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
        
        # Save detailed results
        results_file = "/app/backend/spx_guardrails_test_results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": self.tests_run,
                    "passed_tests": self.tests_passed,
                    "success_rate": f"{(self.tests_passed/self.tests_run)*100:.1f}%" if self.tests_run > 0 else "0%",
                    "timestamp": datetime.now().isoformat()
                },
                "test_results": self.test_results
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: {results_file}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = SPXGuardrailsTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())