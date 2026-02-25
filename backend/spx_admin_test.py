#!/usr/bin/env python3
"""
SPX Admin Backend Testing for Russian Interface Updates
Testing the SPX admin API endpoints that feed the improved admin tabs
"""

import requests
import json
import sys
from datetime import datetime

class SPXAdminTester:
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

    def test_spx_regimes_summary(self):
        """Test SPX regimes summary API"""
        url = f"{self.base_url}/api/spx/v2.1/admin/regimes/summary?preset=BALANCED"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test("SPX Regimes Summary API", False, f"Status {response.status_code}")
                return None
                
            data = response.json()
            
            if not data.get("ok", False):
                self.log_test("SPX Regimes Summary API", False, f"API error: {data.get('error', 'Unknown')}")
                return None
                
            summary = data.get("data", {})
            total_days = summary.get("totalDays", 0)
            
            self.log_test(
                "SPX Regimes Summary API", 
                True, 
                f"Total days: {total_days}, Regimes: {len(summary.get('regimeDetails', []))}"
            )
            return data
            
        except Exception as e:
            self.log_test("SPX Regimes Summary API", False, f"Request failed: {str(e)}")
            return None

    def test_spx_regimes_matrix(self):
        """Test SPX regimes matrix API"""
        url = f"{self.base_url}/api/spx/v2.1/admin/regimes/matrix?preset=BALANCED"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test("SPX Regimes Matrix API", False, f"Status {response.status_code}")
                return None
                
            data = response.json()
            
            if not data.get("ok", False):
                self.log_test("SPX Regimes Matrix API", False, f"API error: {data.get('error', 'Unknown')}")
                return None
                
            matrix = data.get("data", {})
            cells = matrix.get("cells", [])
            regimes = matrix.get("regimes", [])
            
            self.log_test(
                "SPX Regimes Matrix API", 
                True, 
                f"Matrix cells: {len(cells)}, Regimes: {len(regimes)}"
            )
            return data
            
        except Exception as e:
            self.log_test("SPX Regimes Matrix API", False, f"Request failed: {str(e)}")
            return None

    def test_spx_constitution(self):
        """Test SPX constitution API"""
        url = f"{self.base_url}/api/spx/v2.1/admin/constitution"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test("SPX Constitution API", False, f"Status {response.status_code}")
                return None
                
            data = response.json()
            
            if not data.get("ok", False):
                self.log_test("SPX Constitution API", False, f"API error: {data.get('error', 'Unknown')}")
                return None
                
            constitution = data.get("data", {})
            policies = constitution.get("policies", [])
            
            self.log_test(
                "SPX Constitution API", 
                True, 
                f"Policies: {len(policies)}, Hash: {constitution.get('hash', 'N/A')[:8]}"
            )
            return data
            
        except Exception as e:
            self.log_test("SPX Constitution API", False, f"Request failed: {str(e)}")
            return None

    def test_spx_governance_versions(self):
        """Test SPX governance versions API"""
        url = f"{self.base_url}/api/spx/v2.1/admin/governance/versions?preset=BALANCED"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test("SPX Governance Versions API", False, f"Status {response.status_code}")
                return None
                
            data = response.json()
            
            if not data.get("ok", False):
                self.log_test("SPX Governance Versions API", False, f"API error: {data.get('error', 'Unknown')}")
                return None
                
            versions = data.get("data", [])
            
            self.log_test(
                "SPX Governance Versions API", 
                True, 
                f"Versions found: {len(versions)}"
            )
            return data
            
        except Exception as e:
            self.log_test("SPX Governance Versions API", False, f"Request failed: {str(e)}")
            return None

    def test_spx_backtest_full(self):
        """Test SPX backtest API"""
        url = f"{self.base_url}/api/spx/v2.1/admin/backtest/full?preset=BALANCED"
        
        try:
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.log_test("SPX Backtest API", False, f"Status {response.status_code}")
                return None
                
            data = response.json()
            
            if not data.get("ok", False):
                self.log_test("SPX Backtest API", False, f"API error: {data.get('error', 'Unknown')}")
                return None
                
            backtest = data.get("data", {})
            periods = backtest.get("periods", [])
            
            self.log_test(
                "SPX Backtest API", 
                True, 
                f"Backtest periods: {len(periods)}, Verdict: {backtest.get('overallVerdict', 'N/A')}"
            )
            return data
            
        except Exception as e:
            self.log_test("SPX Backtest API", False, f"Request failed: {str(e)}")
            return None

    def run_all_tests(self):
        """Run all SPX admin API tests"""
        print("=" * 60)
        print("SPX ADMIN BACKEND TESTING - Russian Interface Support")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test all SPX admin endpoints
        self.test_spx_regimes_summary()
        self.test_spx_regimes_matrix()
        self.test_spx_constitution()
        self.test_spx_governance_versions()
        self.test_spx_backtest_full()
        
        print()
        print("=" * 60)
        print(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 60)
        
        return self.tests_passed, self.tests_run, self.test_results

def main():
    """Main test execution"""
    tester = SPXAdminTester()
    passed, total, results = tester.run_all_tests()
    
    # Save results
    with open('/app/backend/spx_admin_test_results.json', 'w') as f:
        json.dump({
            "summary": f"SPX Admin Backend Testing for Russian Interface",
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "timestamp": datetime.now().isoformat(),
            "test_details": results
        }, f, indent=2)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())