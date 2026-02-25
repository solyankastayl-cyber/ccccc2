#!/usr/bin/env python3
"""
Fractal Integration Test Suite
Tests all required Fractal endpoints for user and admin interfaces
"""

import requests
import sys
import json
from datetime import datetime

class FractalIntegrationTester:
    def __init__(self, base_url: str = "https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, endpoint, expected_status=200, method='GET', data=None):
        """Run a single test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
                
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                
                # Validate response content for key endpoints
                if response.content:
                    try:
                        response_data = response.json()
                        if endpoint == '/api/fractal/v2.1/admin/overview':
                            self.validate_admin_overview(response_data)
                        elif endpoint == '/api/fractal/v2.1/signal':
                            self.validate_signal_response(response_data)
                        elif endpoint == '/api/fractal/health':
                            self.validate_health_response(response_data)
                    except json.JSONDecodeError:
                        print(f"⚠️  Warning: Response not JSON")
                        
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    'name': name,
                    'endpoint': endpoint,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'error': response.text[:200]
                })
                
            return success, response.json() if response.content else {}
            
        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({
                'name': name,
                'endpoint': endpoint,
                'error': str(e)
            })
            return False, {}

    def validate_admin_overview(self, data):
        """Validate admin overview response structure"""
        required_fields = ['governance', 'health', 'guard', 'model', 'recommendation']
        for field in required_fields:
            if field not in data:
                print(f"⚠️  Warning: Missing field '{field}' in admin overview")
            else:
                print(f"✓ Found {field} section")

    def validate_signal_response(self, data):
        """Validate signal response structure"""
        required_fields = ['meta', 'signalsByHorizon', 'assembled', 'reliability']
        for field in required_fields:
            if field not in data:
                print(f"⚠️  Warning: Missing field '{field}' in signal response")
            else:
                print(f"✓ Found {field} section")
                
        # Check horizons
        if 'signalsByHorizon' in data:
            horizons = ['7d', '14d', '30d']
            for horizon in horizons:
                if horizon in data['signalsByHorizon']:
                    print(f"✓ Found {horizon} horizon data")

    def validate_health_response(self, data):
        """Validate health response structure"""
        required_fields = ['ok', 'enabled', 'bootstrapDone']
        for field in required_fields:
            if field not in data:
                print(f"⚠️  Warning: Missing field '{field}' in health response")
            else:
                print(f"✓ Found {field}: {data[field]}")

    def run_all_tests(self):
        """Run all required tests"""
        print("🔧 Fractal Integration Test Suite")
        print(f"🎯 Target: {self.base_url}")
        print("=" * 60)
        
        # Basic health checks
        print("\n📋 BASIC HEALTH CHECKS")
        print("-" * 30)
        self.run_test("Backend Health", "/api/health")
        self.run_test("Fractal Health", "/api/fractal/health")
        
        # User interface endpoints
        print("\n👤 USER INTERFACE ENDPOINTS")
        print("-" * 30)
        self.run_test("Fractal Signal (BTC)", "/api/fractal/v2.1/signal?symbol=BTC")
        self.run_test("Fractal Status", "/api/fractal/v2.1/admin/status?modelKey=BTC:14")
        
        # Admin interface endpoints  
        print("\n🏢 ADMIN INTERFACE ENDPOINTS")
        print("-" * 30)
        self.run_test("Admin Overview", "/api/fractal/v2.1/admin/overview")
        
        # Admin control endpoints
        print("\n⚙️ ADMIN CONTROL ENDPOINTS")
        print("-" * 30)
        self.run_test("Drift Inject", "/api/fractal/v2.1/admin/drift/inject", 
                     expected_status=200, method='POST', data={'severity': 0.1})
        self.run_test("Drift Reset", "/api/fractal/v2.1/admin/drift/reset", 
                     expected_status=200, method='POST', data={})

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"  - {test['name']}")
                if 'error' in test:
                    print(f"    Error: {test['error']}")
        else:
            print("\n✅ ALL TESTS PASSED!")

def main():
    tester = FractalIntegrationTester()
    tester.run_all_tests()
    tester.print_summary()
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())