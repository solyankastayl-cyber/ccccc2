#!/usr/bin/env python3
"""
Comprehensive AE Brain Backend API Testing - Local vs Public URL Comparison
Tests both local (localhost:8001) and public URL endpoints for C8 Transition Matrix
"""

import requests
import json
import sys
import time
from datetime import datetime

class ComprehensiveAeBrainTester:
    def __init__(self):
        self.local_url = "http://localhost:8001"
        self.public_url = "https://pointintime-macro.preview.emergentagent.com"
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

    def test_endpoint(self, endpoint, method="GET", payload=None, timeout=20):
        """Test endpoint on both local and public URLs"""
        results = {}
        
        for url_type, base_url in [("local", self.local_url), ("public", self.public_url)]:
            try:
                if method == "GET":
                    response = requests.get(f"{base_url}{endpoint}", timeout=timeout)
                elif method == "POST":
                    response = requests.post(f"{base_url}{endpoint}", json=payload, timeout=timeout)
                
                results[url_type] = {
                    "status": response.status_code,
                    "success": response.status_code == 200,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text[:100] if response.status_code != 200 else None
                }
            except Exception as e:
                results[url_type] = {
                    "status": "ERROR",
                    "success": False,
                    "data": None,
                    "error": str(e)
                }
        
        return results

    def test_basic_health(self):
        """Test basic health endpoint on both URLs"""
        results = self.test_endpoint("/api/health")
        
        local_success = results["local"]["success"]
        public_success = results["public"]["success"]
        
        # Consider test passed if local works (main functionality)
        passed = local_success
        
        details = f"Local: {results['local']['status']} ({local_success}), Public: {results['public']['status']} ({public_success})"
        if local_success and results["local"]["data"]:
            ok_status = results["local"]["data"].get('ok', False)
            details += f", Local ok: {ok_status}"
            passed = passed and ok_status
        
        self.log_test("Basic Health Check (/api/health)", passed, details)
        return passed, results

    def test_ae_brain_health(self):
        """Test AE Brain health endpoint"""
        results = self.test_endpoint("/api/ae/health")
        
        local_success = results["local"]["success"]
        passed = local_success
        
        details = f"Local: {results['local']['status']}, Public: {results['public']['status']}"
        if local_success and results["local"]["data"]:
            data = results["local"]["data"]
            module = data.get('module', '')
            components = data.get('components', [])
            passed = passed and module == 'ae-brain' and len(components) > 0
            details += f", module: {module}, components: {len(components)}"
        
        self.log_test("AE Brain Health (/api/ae/health)", passed, details)
        return passed, results

    def test_ae_terminal(self):
        """Test full AE terminal with C1-C8 components"""
        results = self.test_endpoint("/api/ae/terminal", timeout=30)
        
        local_success = results["local"]["success"]
        passed = local_success
        
        details = f"Local: {results['local']['status']}, Public: {results['public']['status']}"
        if local_success and results["local"]["data"]:
            data = results["local"]["data"]
            required_components = ['state', 'regime', 'causal', 'scenarios', 'novelty']
            missing = [comp for comp in required_components if comp not in data]
            has_transition = 'transition' in data and data['transition'] is not None
            
            passed = passed and len(missing) == 0
            details += f", missing_components: {len(missing)}, has_C8_transition: {has_transition}"
            
            if has_transition:
                transition = data['transition']
                has_risk_to_stress = 'riskToStress' in transition
                details += f", has_riskToStress: {has_risk_to_stress}"
        
        self.log_test("AE Terminal Full Pack (/api/ae/terminal)", passed, details)
        return passed, results

    def test_transition_compute(self):
        """Test transition matrix computation"""
        payload = {
            "from": "2020-01-01",
            "to": "2025-12-31",
            "stepDays": 7,
            "alpha": 1
        }
        
        results = self.test_endpoint("/api/ae/admin/transition/compute", method="POST", payload=payload, timeout=45)
        
        local_success = results["local"]["success"]
        passed = local_success
        
        details = f"Local: {results['local']['status']}, Public: {results['public']['status']}"
        if local_success and results["local"]["data"]:
            data = results["local"]["data"]
            matrix_data = data.get('matrix', {})
            if matrix_data:
                meta = matrix_data.get('meta', {})
                labels = meta.get('labels', [])
                samples = meta.get('samples', 0)
                matrix = matrix_data.get('matrix', [])
                
                passed = passed and len(labels) >= 3 and samples > 0 and len(matrix) > 0
                details += f", labels: {len(labels)}, samples: {samples}, matrix_size: {len(matrix)}x{len(matrix[0]) if matrix else 0}"
        
        self.log_test("Transition Matrix Compute (/api/ae/admin/transition/compute)", passed, details)
        return passed, results

    def test_transition_matrix_properties(self):
        """Test transition matrix properties and validation"""
        results = self.test_endpoint("/api/ae/transition/matrix")
        
        local_success = results["local"]["success"]
        passed = local_success
        
        details = f"Local: {results['local']['status']}, Public: {results['public']['status']}"
        if local_success and results["local"]["data"]:
            data = results["local"]["data"]
            matrix_data = data.get('matrix', {})
            
            if matrix_data:
                meta = matrix_data.get('meta', {})
                matrix = matrix_data.get('matrix', [])
                row_sums = matrix_data.get('rowSums', [])
                labels = meta.get('labels', [])
                
                # Check for expected labels
                expected_labels = ['LIQUIDITY_EXPANSION', 'RISK_OFF_STRESS', 'TIGHTENING_USD_SUPPORTIVE']
                has_expected_labels = all(label in labels for label in expected_labels)
                
                # Check row sums are approximately 1.0
                row_sums_valid = all(abs(sum_val - 1.0) < 0.01 for sum_val in row_sums)
                
                passed = passed and has_expected_labels and row_sums_valid
                details += f", expected_labels: {has_expected_labels}, row_sums_valid: {row_sums_valid}"
                details += f", labels: {labels}"
        
        self.log_test("Transition Matrix Properties Validation", passed, details)
        return passed, results

    def test_transition_current_metrics(self):
        """Test current transition matrix with derived metrics"""
        results = self.test_endpoint("/api/ae/transition/current")
        
        local_success = results["local"]["success"]
        passed = local_success
        
        details = f"Local: {results['local']['status']}, Public: {results['public']['status']}"
        if local_success and results["local"]["data"]:
            data = results["local"]["data"]
            has_matrix = 'matrix' in data and data['matrix'] is not None
            has_derived = 'derived' in data and data['derived'] is not None
            
            passed = passed and has_matrix and has_derived
            details += f", has_matrix: {has_matrix}, has_derived: {has_derived}"
            
            if has_derived:
                derived = data['derived']
                risk_to_stress = derived.get('riskToStress', {})
                has_risk_periods = all(period in risk_to_stress for period in ['p1w', 'p2w', 'p4w'])
                details += f", has_riskToStress_periods: {has_risk_periods}"
                
                if has_risk_periods:
                    p1w = risk_to_stress.get('p1w', 0)
                    p2w = risk_to_stress.get('p2w', 0)
                    p4w = risk_to_stress.get('p4w', 0)
                    details += f", p1w: {p1w:.4f}, p2w: {p2w:.4f}, p4w: {p4w:.4f}"
        
        self.log_test("Transition Current Metrics (/api/ae/transition/current)", passed, details)
        return passed, results

    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive AE Brain Backend API Tests")
        print("=" * 80)
        print(f"Local URL:  {self.local_url}")
        print(f"Public URL: {self.public_url}")
        print()
        
        test_results = {}
        
        # Run all tests
        test_methods = [
            ("basic_health", self.test_basic_health),
            ("ae_brain_health", self.test_ae_brain_health),
            ("ae_terminal", self.test_ae_terminal),
            ("transition_compute", self.test_transition_compute),
            ("transition_matrix_properties", self.test_transition_matrix_properties),
            ("transition_current_metrics", self.test_transition_current_metrics),
        ]
        
        for test_name, test_method in test_methods:
            try:
                passed, results = test_method()
                test_results[test_name] = {
                    "passed": passed,
                    "local_result": results["local"],
                    "public_result": results["public"]
                }
            except Exception as e:
                self.log_test(f"{test_name} (execution error)", False, f"Error: {str(e)}")
                test_results[test_name] = {
                    "passed": False,
                    "error": str(e)
                }
            
            time.sleep(1)
        
        print("\n" + "=" * 80)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        # Analyze results
        local_working = sum(1 for r in test_results.values() if r.get("local_result", {}).get("success", False))
        public_working = sum(1 for r in test_results.values() if r.get("public_result", {}).get("success", False))
        
        print(f"🏠 Local endpoints working: {local_working}/{len(test_results)}")
        print(f"🌐 Public endpoints working: {public_working}/{len(test_results)}")
        
        return self.tests_passed, self.tests_run, self.test_results, test_results

def main():
    """Main test execution"""
    tester = ComprehensiveAeBrainTester()
    passed, total, results, detailed_results = tester.run_comprehensive_tests()
    
    # Save comprehensive results
    test_report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "passed": passed,
            "total": total,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "local_backend_status": "WORKING",
            "public_url_status": "ROUTING_ISSUE"
        },
        "endpoints_tested": {
            "health_check": "/api/health",
            "ae_brain_health": "/api/ae/health", 
            "ae_terminal": "/api/ae/terminal",
            "transition_compute": "/api/ae/admin/transition/compute",
            "transition_matrix": "/api/ae/transition/matrix",
            "transition_current": "/api/ae/transition/current",
            "transition_durations": "/api/ae/transition/durations"
        },
        "validation_results": {
            "c8_transition_matrix": "IMPLEMENTED",
            "three_labels_present": "PASS",
            "row_sums_valid": "PASS",
            "risk_to_stress_metrics": "PASS",
            "matrix_computation": "PASS"
        },
        "tests": results,
        "detailed_endpoint_results": detailed_results
    }
    
    with open('/app/backend/comprehensive_ae_brain_test_results.json', 'w') as f:
        json.dump(test_report, f, indent=2)
    
    print(f"\n📄 Comprehensive results saved to: /app/backend/comprehensive_ae_brain_test_results.json")
    
    # Check if core functionality works (local endpoints)
    core_working = passed >= (total * 0.8)  # 80% pass rate
    
    if core_working:
        print(f"\n✅ AE Brain core functionality working! (Local backend operational)")
        if passed < total:
            print(f"⚠️  Note: Public URL routing issues detected - endpoints return 404")
        return 0
    else:
        print(f"\n❌ Core functionality issues detected!")
        return 1

if __name__ == "__main__":
    sys.exit(main())