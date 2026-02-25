#!/usr/bin/env python3
"""
BTC CASCADE BACKEND TEST SUITE
Tests all D2 BTC Cascade module endpoints and validation logic.

Key tests:
- Health check
- Cascade data retrieval 
- Debug endpoint
- Guard cap validation (BLOCK→0, CRISIS≤0.35, WARN≤0.70)
- Monotonic stress behavior
- Scenario tilt (BEAR→0.80)
- SPX coupling (SPX_LOW→0.75)
- Data integrity (no NaN/negative values)
"""

import requests
import sys
import json
from typing import Dict, Any, List, Optional
import time

class BtcCascadeAPITester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []
        
    def log_result(self, test_name: str, passed: bool, details: str = "", data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "data": data
        }
        self.results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
        return passed

    def test_health_check(self) -> bool:
        """Test BTC Cascade health endpoint"""
        try:
            url = f"{self.base_url}/api/fractal/btc/cascade/health"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return self.log_result(
                    "Health Check",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            
            # Validate health response structure
            required_fields = ['ok', 'module', 'version', 'status', 'components', 'guardCaps']
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                return self.log_result(
                    "Health Check",
                    False,
                    f"Missing fields: {missing_fields}",
                    data
                )
            
            # Check guard caps
            guard_caps = data.get('guardCaps', {})
            expected_caps = {'NONE': 1.0, 'WARN': 0.7, 'CRISIS': 0.35, 'BLOCK': 0.0}
            
            caps_correct = all(
                guard_caps.get(level) == expected
                for level, expected in expected_caps.items()
            )
            
            if not caps_correct:
                return self.log_result(
                    "Health Check", 
                    False,
                    f"Guard caps incorrect. Got: {guard_caps}",
                    data
                )
            
            return self.log_result(
                "Health Check",
                data.get('ok', False) and data.get('status') == 'D2_COMPLETE',
                f"Module: {data.get('module')}, Version: {data.get('version')}",
                data
            )
            
        except Exception as e:
            return self.log_result("Health Check", False, f"Exception: {str(e)}")

    def test_cascade_data(self) -> bool:
        """Test cascade data endpoint"""
        try:
            url = f"{self.base_url}/api/fractal/btc/cascade?focus=30d"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                return self.log_result(
                    "Cascade Data",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            
            if not data.get('ok'):
                return self.log_result(
                    "Cascade Data",
                    False,
                    "Response not ok",
                    data.get('error', 'Unknown error')
                )
            
            # Validate cascade structure
            cascade = data.get('cascade')
            if not cascade:
                return self.log_result(
                    "Cascade Data",
                    False,
                    "No cascade data",
                    data
                )
            
            # Check required fields in cascade
            required_sections = ['version', 'guard', 'inputs', 'multipliers', 'decisionAdjusted']
            missing_sections = [s for s in required_sections if s not in cascade]
            
            if missing_sections:
                return self.log_result(
                    "Cascade Data",
                    False,
                    f"Missing cascade sections: {missing_sections}",
                    cascade
                )
            
            # Validate inputs contain required upstream data
            inputs = cascade.get('inputs', {})
            required_inputs = ['pStress4w', 'bearProb', 'spxAdj']
            missing_inputs = [i for i in required_inputs if i not in inputs]
            
            if missing_inputs:
                return self.log_result(
                    "Cascade Data",
                    False,
                    f"Missing required inputs: {missing_inputs}",
                    inputs
                )
            
            return self.log_result(
                "Cascade Data",
                True,
                f"Focus: {data.get('focus')}, Processing: {data.get('processingTimeMs')}ms",
                cascade
            )
            
        except Exception as e:
            return self.log_result("Cascade Data", False, f"Exception: {str(e)}")

    def test_debug_endpoint(self) -> bool:
        """Test debug endpoint"""
        try:
            url = f"{self.base_url}/api/fractal/btc/cascade/debug"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                return self.log_result(
                    "Debug Endpoint",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            
            if not data.get('ok'):
                return self.log_result(
                    "Debug Endpoint",
                    False,
                    "Response not ok",
                    data.get('error', 'Unknown error')
                )
            
            # Validate debug data structure
            required_fields = ['version', 'guardCaps', 'rawAeData', 'rawSpxData', 'timing']
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                return self.log_result(
                    "Debug Endpoint",
                    False,
                    f"Missing fields: {missing_fields}",
                    data
                )
            
            timing = data.get('timing', {})
            total_time = timing.get('total', 0)
            
            return self.log_result(
                "Debug Endpoint",
                True,
                f"Total time: {total_time}ms, AE: {timing.get('ae')}ms, SPX: {timing.get('spx')}ms",
                data
            )
            
        except Exception as e:
            return self.log_result("Debug Endpoint", False, f"Exception: {str(e)}")

    def test_validation_guard_caps(self) -> bool:
        """Test guard cap validation"""
        test_cases = [
            ('BLOCK', 0.0, "Size must be 0 for BLOCK guard"),
            ('CRISIS', 0.35, "Size must be ≤0.35 for CRISIS guard"),
            ('WARN', 0.70, "Size must be ≤0.70 for WARN guard")
        ]
        
        all_passed = True
        
        for test_case, max_expected, description in test_cases:
            try:
                url = f"{self.base_url}/api/fractal/btc/admin/cascade/validate"
                payload = {"testCase": test_case}
                
                response = requests.post(url, json=payload, timeout=10)
                
                if response.status_code != 200:
                    self.log_result(
                        f"Guard Cap {test_case}",
                        False,
                        f"HTTP {response.status_code}",
                        response.text[:200]
                    )
                    all_passed = False
                    continue
                
                data = response.json()
                cascade = data.get('cascade', {})
                decision = cascade.get('decisionAdjusted', {})
                size_adjusted = decision.get('sizeAdjusted', 1.0)
                
                # For BLOCK, size should be exactly 0
                if test_case == 'BLOCK':
                    passed = size_adjusted == 0.0
                else:
                    # For CRISIS/WARN, size should be <= cap
                    passed = size_adjusted <= max_expected + 0.001  # Small tolerance for floating point
                
                self.log_result(
                    f"Guard Cap {test_case}",
                    passed,
                    f"Size: {size_adjusted}, Expected: ≤{max_expected}",
                    decision
                )
                
                if not passed:
                    all_passed = False
                    
            except Exception as e:
                self.log_result(f"Guard Cap {test_case}", False, f"Exception: {str(e)}")
                all_passed = False
        
        return all_passed

    def test_stress_monotonic(self) -> bool:
        """Test monotonic stress behavior (stress↑ → size↓)"""
        try:
            url = f"{self.base_url}/api/fractal/btc/admin/cascade/validate"
            payload = {"testCase": "STRESS"}
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                return self.log_result(
                    "Stress Monotonic",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            cascade = data.get('cascade', {})
            inputs = cascade.get('inputs', {})
            multipliers = cascade.get('multipliers', {})
            
            # Check that high stress (0.25) leads to low stress multiplier
            stress_prob = inputs.get('pStress4w', 0)
            stress_mult = multipliers.get('mStress', 1.0)
            
            # With stress weight 1.5 and pStress4w=0.25:
            # mStress = 1 - 1.5 * 0.25 = 1 - 0.375 = 0.625
            expected_stress_mult = 1 - 1.5 * stress_prob
            expected_stress_mult = max(0.10, min(1.00, expected_stress_mult))
            
            tolerance = 0.01
            passed = abs(stress_mult - expected_stress_mult) < tolerance
            
            return self.log_result(
                "Stress Monotonic",
                passed,
                f"pStress4w: {stress_prob}, mStress: {stress_mult}, Expected: ~{expected_stress_mult}",
                multipliers
            )
            
        except Exception as e:
            return self.log_result("Stress Monotonic", False, f"Exception: {str(e)}")

    def test_bear_scenario(self) -> bool:
        """Test bear scenario tilt (mScenario=0.80)"""
        try:
            url = f"{self.base_url}/api/fractal/btc/admin/cascade/validate"
            payload = {"testCase": "BEAR"}
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                return self.log_result(
                    "Bear Scenario",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            cascade = data.get('cascade', {})
            multipliers = cascade.get('multipliers', {})
            scenario_mult = multipliers.get('mScenario', 1.0)
            
            # Bear scenario should result in mScenario = 0.80
            tolerance = 0.01
            passed = abs(scenario_mult - 0.80) < tolerance
            
            return self.log_result(
                "Bear Scenario",
                passed,
                f"mScenario: {scenario_mult}, Expected: 0.80",
                multipliers
            )
            
        except Exception as e:
            return self.log_result("Bear Scenario", False, f"Exception: {str(e)}")

    def test_spx_coupling(self) -> bool:
        """Test SPX coupling (SPX_LOW→0.75)"""
        try:
            url = f"{self.base_url}/api/fractal/btc/admin/cascade/validate"
            payload = {"testCase": "SPX_LOW"}
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                return self.log_result(
                    "SPX Coupling",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            cascade = data.get('cascade', {})
            inputs = cascade.get('inputs', {})
            multipliers = cascade.get('multipliers', {})
            
            spx_adj = inputs.get('spxAdj', 0.8)
            spx_mult = multipliers.get('mSPX', 1.0)
            
            # SPX_LOW test case should have spxAdj < 0.40 → mSPX = 0.75
            tolerance = 0.01
            passed = spx_adj < 0.40 and abs(spx_mult - 0.75) < tolerance
            
            return self.log_result(
                "SPX Coupling",
                passed,
                f"spxAdj: {spx_adj}, mSPX: {spx_mult}, Expected mSPX: 0.75",
                multipliers
            )
            
        except Exception as e:
            return self.log_result("SPX Coupling", False, f"Exception: {str(e)}")

    def test_no_nan_negative(self) -> bool:
        """Test for NaN or negative values"""
        try:
            # Test with normal case
            url = f"{self.base_url}/api/fractal/btc/admin/cascade/validate"
            payload = {"testCase": "NORMAL"}
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code != 200:
                return self.log_result(
                    "No NaN/Negative",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            validation = data.get('validation', {})
            
            # Check validation flags
            no_nan = validation.get('noNaN', False)
            size_in_range = validation.get('sizeInRange', False)
            confidence_in_range = validation.get('confidenceInRange', False)
            
            passed = no_nan and size_in_range and confidence_in_range
            
            return self.log_result(
                "No NaN/Negative",
                passed,
                f"noNaN: {no_nan}, sizeInRange: {size_in_range}, confidenceInRange: {confidence_in_range}",
                validation
            )
            
        except Exception as e:
            return self.log_result("No NaN/Negative", False, f"Exception: {str(e)}")

    def test_upstream_inputs(self) -> bool:
        """Test that cascade.inputs contains required upstream data"""
        try:
            url = f"{self.base_url}/api/fractal/btc/cascade?focus=30d"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                return self.log_result(
                    "Upstream Inputs",
                    False,
                    f"HTTP {response.status_code}",
                    response.text[:200]
                )
            
            data = response.json()
            cascade = data.get('cascade', {})
            inputs = cascade.get('inputs', {})
            
            # Required upstream inputs
            required_inputs = ['pStress4w', 'bearProb', 'spxAdj']
            missing_inputs = []
            
            for inp in required_inputs:
                if inp not in inputs:
                    missing_inputs.append(inp)
                elif inputs[inp] is None:
                    missing_inputs.append(f"{inp} (null)")
            
            passed = len(missing_inputs) == 0
            
            details = f"Required inputs present: {required_inputs}"
            if missing_inputs:
                details = f"Missing inputs: {missing_inputs}"
            
            return self.log_result(
                "Upstream Inputs",
                passed,
                details,
                inputs
            )
            
        except Exception as e:
            return self.log_result("Upstream Inputs", False, f"Exception: {str(e)}")

    def run_all_tests(self) -> bool:
        """Run all BTC Cascade tests"""
        print("🚀 Starting BTC Cascade Backend Tests")
        print("=" * 50)
        
        # Health check first
        if not self.test_health_check():
            print("❌ Health check failed - skipping other tests")
            return False
        
        # Core functionality tests
        self.test_cascade_data()
        self.test_debug_endpoint()
        
        # Validation tests
        self.test_validation_guard_caps()
        self.test_stress_monotonic()
        self.test_bear_scenario()
        self.test_spx_coupling()
        
        # Data integrity tests
        self.test_no_nan_negative()
        self.test_upstream_inputs()
        
        # Summary
        print("\n" + "=" * 50)
        print(f"📊 RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests PASSED!")
            return True
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests FAILED")
            
            # Show failed tests
            failed_tests = [r for r in self.results if not r['passed']]
            if failed_tests:
                print("\n🔍 Failed Tests:")
                for test in failed_tests:
                    print(f"  - {test['test']}: {test['details']}")
            
            return False

def main():
    """Main test runner"""
    tester = BtcCascadeAPITester()
    
    try:
        success = tester.run_all_tests()
        
        # Save detailed results
        with open('/tmp/btc_cascade_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': tester.tests_run,
                    'passed_tests': tester.tests_passed,
                    'success_rate': tester.tests_passed / max(tester.tests_run, 1) * 100
                },
                'results': tester.results
            }, f, indent=2)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())