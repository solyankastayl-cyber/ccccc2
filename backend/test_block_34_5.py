#!/usr/bin/env python3
"""
BLOCK 34.5 Gate × Risk Combo Sweep Testing
Focused test for the specific functionality requested
"""

import requests
import json
import time
from datetime import datetime

class Block345Tester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def make_request(self, method, endpoint, data=None, timeout=60):
        """Make HTTP request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            return response.status_code == 200, response_data
            
        except Exception as e:
            return False, {"error": str(e)}

    def test_combo_sweep_post(self):
        """Test POST /api/fractal/admin/sim/combo-sweep"""
        print("🔍 Testing POST /api/fractal/admin/sim/combo-sweep...")
        
        data = {
            "symbol": "BTC",
            "from": "2023-06-01",
            "to": "2023-12-01",
            "gateConfig": {
                "minEnterConfidence": 0.30,
                "minFullSizeConfidence": 0.65,
                "minFlipConfidence": 0.45
            },
            "soft": [0.08, 0.10],
            "hard": [0.16, 0.18],
            "taper": [0.8, 1.0],
            "maxRuns": 8
        }
        
        success, response = self.make_request("POST", "/api/fractal/admin/sim/combo-sweep", data)
        
        self.tests_run += 1
        if success:
            if response.get("ok"):
                self.tests_passed += 1
                print("✅ POST combo-sweep: SUCCESS")
                print(f"   - Runs: {response.get('runs', 0)}")
                print(f"   - Gate config preserved: {response.get('gateConfig', {}).get('minEnterConfidence')}")
                
                # Check for gate telemetry in results
                top10 = response.get("top10", [])
                if top10:
                    first_result = top10[0]
                    gate_blocks = first_result.get("gateBlockEnter", 0)
                    avg_conf_scale = first_result.get("avgConfScale", 1)
                    print(f"   - Gate telemetry: {gate_blocks} blocks, {avg_conf_scale:.3f} avg scale")
                
                return True
            else:
                print(f"❌ POST combo-sweep: API returned ok=false")
                return False
        else:
            print(f"❌ POST combo-sweep: Request failed - {response.get('error', 'Unknown error')}")
            return False

    def test_combo_sweep_quick_get(self):
        """Test GET /api/fractal/admin/sim/combo-sweep/quick"""
        print("🔍 Testing GET /api/fractal/admin/sim/combo-sweep/quick...")
        
        success, response = self.make_request("GET", "/api/fractal/admin/sim/combo-sweep/quick")
        
        self.tests_run += 1
        if success:
            if response.get("ok"):
                self.tests_passed += 1
                print("✅ GET combo-sweep/quick: SUCCESS")
                print(f"   - Runs: {response.get('runs', 0)}")
                print(f"   - Duration: {response.get('duration', 0)}ms")
                
                # Check gate config
                gate_config = response.get("gateConfig", {})
                print(f"   - Gate config: enter={gate_config.get('minEnterConfidence')}, full={gate_config.get('minFullSizeConfidence')}")
                
                return True
            else:
                print(f"❌ GET combo-sweep/quick: API returned ok=false")
                return False
        else:
            print(f"❌ GET combo-sweep/quick: Request failed - {response.get('error', 'Unknown error')}")
            return False

    def test_gateRiskSweep_method(self):
        """Test the gateRiskSweep method via combo-sweep endpoint"""
        print("🔍 Testing gateRiskSweep method functionality...")
        
        # Test with specific gate configuration to verify the method works
        data = {
            "symbol": "BTC",
            "from": "2023-09-01",
            "to": "2023-11-01",
            "gateConfig": {
                "minEnterConfidence": 0.35,  # Higher threshold
                "minFullSizeConfidence": 0.70,
                "minFlipConfidence": 0.50
            },
            "soft": [0.08],
            "hard": [0.16],
            "taper": [0.8],
            "maxRuns": 1,
            "mode": "FROZEN"
        }
        
        success, response = self.make_request("POST", "/api/fractal/admin/sim/combo-sweep", data)
        
        self.tests_run += 1
        if success and response.get("ok"):
            # Verify gateRiskSweep method produced expected telemetry
            top10 = response.get("top10", [])
            if top10:
                result = top10[0]
                
                # Check for gate telemetry fields (specific to gateRiskSweep)
                has_gate_telemetry = (
                    "gateBlockEnter" in result and 
                    "avgConfScale" in result
                )
                
                if has_gate_telemetry:
                    self.tests_passed += 1
                    print("✅ gateRiskSweep method: SUCCESS")
                    print(f"   - Gate blocks: {result.get('gateBlockEnter', 0)}")
                    print(f"   - Avg conf scale: {result.get('avgConfScale', 1):.3f}")
                    print(f"   - Risk params: soft={result.get('soft')}, hard={result.get('hard')}, taper={result.get('taper')}")
                    return True
                else:
                    print("❌ gateRiskSweep method: Missing gate telemetry")
                    return False
            else:
                print("❌ gateRiskSweep method: No results returned")
                return False
        else:
            print(f"❌ gateRiskSweep method: Request failed - {response.get('error', 'Unknown error')}")
            return False

    def run_tests(self):
        """Run all BLOCK 34.5 tests"""
        print("🚀 BLOCK 34.5 Gate × Risk Combo Sweep Testing")
        print("=" * 60)
        print(f"Testing at: {self.base_url}")
        print(f"Started: {datetime.now().isoformat()}")
        print()
        
        # Run the three main tests
        test1 = self.test_combo_sweep_post()
        time.sleep(2)  # Brief pause between tests
        
        test2 = self.test_combo_sweep_quick_get()
        time.sleep(2)
        
        test3 = self.test_gateRiskSweep_method()
        
        # Summary
        print()
        print("=" * 60)
        print("📊 BLOCK 34.5 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All BLOCK 34.5 tests PASSED!")
            print("✅ Gate × Risk Combo Sweep functionality is working correctly")
            return True
        else:
            print(f"💥 {self.tests_run - self.tests_passed} test(s) failed")
            return False

if __name__ == "__main__":
    tester = Block345Tester()
    success = tester.run_tests()
    exit(0 if success else 1)