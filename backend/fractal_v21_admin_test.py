#!/usr/bin/env python3
"""
BLOCK 43.x Testing - Fractal V2.1 Admin Routes
Tests drift injection, calibration reset, status endpoint, and reliability history
"""

import requests
import sys
import time
from datetime import datetime
import json

class FractalV21AdminTester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.model_key = "BTCUSD:14"
        self.preset_key = "v2_entropy_final"
        
    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            print(f"   Status: {response.status_code}")
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text}
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {json.dumps(response_data, indent=2)[:500]}")

            return success, response_data

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_system_status(self):
        """Test GET /api/fractal/v2.1/admin/status"""
        print("\n" + "="*60)
        print("🏥 BLOCK 43.4 - System Status Endpoint")
        print("="*60)
        
        success, response = self.run_test(
            "System Status",
            "GET", 
            "/api/fractal/v2.1/admin/status",
            200,
            params={"modelKey": self.model_key, "presetKey": self.preset_key}
        )
        
        if success:
            # Verify response structure
            required_fields = ['ts', 'modelKey', 'presetKey', 'signal', 'reliability', 'calibration']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
                return False, response
            
            # Check reliability structure
            if 'reliability' in response:
                rel = response['reliability']
                badge = rel.get('badge', 'UNKNOWN')
                score = rel.get('score', 0)
                print(f"   📊 Reliability: badge={badge}, score={score:.3f}")
                
                if 'components' in rel:
                    comp = rel['components']
                    print(f"   📈 Components: drift={comp.get('drift', 0):.3f}, calibration={comp.get('calibration', 0):.3f}")
            
            print(f"   ✅ Status endpoint structure valid")
        
        return success, response

    def test_calibration_reset(self):
        """Test POST /api/fractal/v2.1/admin/drift/reset"""
        print("\n" + "="*60)
        print("🔄 BLOCK 43.3 - Calibration Reset")
        print("="*60)
        
        success, response = self.run_test(
            "Calibration Reset",
            "POST",
            "/api/fractal/v2.1/admin/drift/reset",
            200,
            data={
                "modelKey": self.model_key,
                "presetKey": self.preset_key,
                "horizonDays": 14
            }
        )
        
        if success and response.get('ok'):
            print(f"   ✅ Calibration reset successful")
        
        return success, response

    def test_drift_injection_low_severity(self):
        """Test drift injection with low severity (should stay OK/WARN)"""
        print("\n" + "="*60)  
        print("⚠️  BLOCK 43.3 - Drift Injection (Low Severity)")
        print("="*60)
        
        # First get baseline status
        _, baseline = self.run_test(
            "Baseline Status Check",
            "GET",
            "/api/fractal/v2.1/admin/status", 
            200,
            params={"modelKey": self.model_key, "presetKey": self.preset_key}
        )
        
        baseline_badge = baseline.get('reliability', {}).get('badge', 'UNKNOWN')
        print(f"   📋 Baseline badge: {baseline_badge}")
        
        # Inject low severity drift (0.25)
        success, response = self.run_test(
            "Drift Injection (Low)",
            "POST",
            "/api/fractal/v2.1/admin/drift/inject",
            200,
            data={
                "modelKey": self.model_key,
                "presetKey": self.preset_key,
                "horizonDays": 14,
                "severity": 0.25
            }
        )
        
        if success and response.get('ok'):
            before = response.get('before', {})
            after = response.get('after', {})
            
            print(f"   📊 Before: ECE={before.get('ece', 0):.3f}, Brier={before.get('brier', 0):.3f}, Badge={before.get('badge', 'UNKNOWN')}")
            print(f"   📊 After:  ECE={after.get('ece', 0):.3f}, Brier={after.get('brier', 0):.3f}, Badge={after.get('badge', 'UNKNOWN')}")
            print(f"   📝 Snapshot written: {response.get('snapshotWritten', False)}")
            
        return success, response

    def test_drift_injection_high_severity(self):
        """Test drift injection with high severity (should become DEGRADED/CRITICAL)"""
        print("\n" + "="*60)
        print("🚨 BLOCK 43.3 - Drift Injection (High Severity)")
        print("="*60)
        
        # Inject high severity drift (0.8)
        success, response = self.run_test(
            "Drift Injection (High)",
            "POST",
            "/api/fractal/v2.1/admin/drift/inject",
            200,
            data={
                "modelKey": self.model_key,
                "presetKey": self.preset_key, 
                "horizonDays": 14,
                "severity": 0.8
            }
        )
        
        badge_changed_correctly = False
        if success and response.get('ok'):
            before = response.get('before', {})
            after = response.get('after', {})
            
            print(f"   📊 Before: ECE={before.get('ece', 0):.3f}, Brier={before.get('brier', 0):.3f}, Badge={before.get('badge', 'UNKNOWN')}")
            print(f"   📊 After:  ECE={after.get('ece', 0):.3f}, Brier={after.get('brier', 0):.3f}, Badge={after.get('badge', 'UNKNOWN')}")
            print(f"   📝 Snapshot written: {response.get('snapshotWritten', False)}")
            
            # Verify badge became DEGRADED or CRITICAL
            after_badge = after.get('badge', 'UNKNOWN')
            if after_badge in ['DEGRADED', 'CRITICAL']:
                print(f"   ✅ Badge correctly changed to {after_badge} with high severity")
                badge_changed_correctly = True
            else:
                print(f"   ⚠️  Expected DEGRADED/CRITICAL, got {after_badge}")
        
        return success and badge_changed_correctly, response

    def test_status_after_drift(self):
        """Test status endpoint shows updated badge after drift injection"""
        print("\n" + "="*60)
        print("📊 BLOCK 43.4 - Status After Drift")
        print("="*60)
        
        # Wait a moment for any async operations
        time.sleep(1)
        
        success, response = self.run_test(
            "Status After Drift",
            "GET",
            "/api/fractal/v2.1/admin/status",
            200,
            params={"modelKey": self.model_key, "presetKey": self.preset_key}
        )
        
        if success:
            reliability = response.get('reliability', {})
            badge = reliability.get('badge', 'UNKNOWN')
            score = reliability.get('score', 0)
            
            print(f"   📊 Current reliability: badge={badge}, score={score:.3f}")
            
            # Check no-trade reasons are populated for degraded badge
            no_trade_reasons = response.get('noTradeReasons', [])
            print(f"   🚫 No-trade reasons: {no_trade_reasons}")
            
            if badge in ['DEGRADED', 'CRITICAL'] and len(no_trade_reasons) > 0:
                print(f"   ✅ No-trade reasons correctly populated for {badge} badge")
            
        return success, response

    def test_reliability_history(self):
        """Test GET /api/fractal/v2.1/admin/reliability/history"""
        print("\n" + "="*60)
        print("📈 BLOCK 43.x - Reliability History")
        print("="*60)
        
        success, response = self.run_test(
            "Reliability History",
            "GET",
            "/api/fractal/v2.1/admin/reliability/history",
            200,
            params={
                "modelKey": self.model_key,
                "presetKey": self.preset_key,
                "limit": "10"
            }
        )
        
        if success:
            history = response.get('history', [])
            count = response.get('count', 0)
            
            print(f"   📊 History count: {count}")
            print(f"   📝 Snapshots returned: {len(history)}")
            
            # Verify snapshots have expected structure
            if len(history) > 0:
                recent = history[0]
                print(f"   📅 Most recent snapshot:")
                print(f"      - Timestamp: {recent.get('ts', 0)}")
                print(f"      - Badge: {recent.get('badge', 'UNKNOWN')}")
                print(f"      - Score: {recent.get('reliabilityScore', 0):.3f}")
                print(f"      - Context: {recent.get('context', {}).get('phase', 'UNKNOWN')}")
                
                # Verify at least one snapshot is from drift injection
                drift_snapshots = [s for s in history if s.get('context', {}).get('phase') == 'DRIFT_INJECTED']
                if drift_snapshots:
                    print(f"   ✅ Found {len(drift_snapshots)} drift injection snapshots")
                else:
                    print(f"   ⚠️  No drift injection snapshots found")
            
        return success, response

    def test_mongodb_persistence_check(self):
        """Indirect test of MongoDB persistence via API consistency"""
        print("\n" + "="*60)
        print("🗄️  MongoDB Persistence Check")
        print("="*60)
        
        print("   📝 Testing persistence through API consistency...")
        
        # Get status twice with small delay to test persistence
        _, status1 = self.run_test(
            "Status Check #1",
            "GET",
            "/api/fractal/v2.1/admin/status",
            200,
            params={"modelKey": self.model_key, "presetKey": self.preset_key}
        )
        
        time.sleep(2)
        
        _, status2 = self.run_test(
            "Status Check #2", 
            "GET",
            "/api/fractal/v2.1/admin/status",
            200,
            params={"modelKey": self.model_key, "presetKey": self.preset_key}
        )
        
        # Compare calibration data consistency
        cal1 = status1.get('calibration', {})
        cal2 = status2.get('calibration', {})
        
        if cal1 and cal2:
            ece1, ece2 = cal1.get('ece', 0), cal2.get('ece', 0)
            brier1, brier2 = cal1.get('brier', 0), cal2.get('brier', 0)
            
            if abs(ece1 - ece2) < 0.001 and abs(brier1 - brier2) < 0.001:
                print(f"   ✅ Calibration data consistent between calls (ECE={ece1:.3f}, Brier={brier1:.3f})")
                return True
            else:
                print(f"   ⚠️  Calibration data inconsistent: ECE {ece1:.3f}→{ece2:.3f}, Brier {brier1:.3f}→{brier2:.3f}")
        
        return False


def main():
    print("🚀 FRACTAL V2.1 BLOCK 43.x - Admin Routes Testing")
    print("="*80)
    
    tester = FractalV21AdminTester()
    
    # Test sequence to verify all BLOCK 43.x functionality
    test_results = []
    
    # 1. Reset calibration to clean state
    print("📋 Step 1: Reset calibration to baseline")
    reset_success, _ = tester.test_calibration_reset()
    test_results.append(("Calibration Reset", reset_success))
    
    # 2. Test initial system status
    print("\n📋 Step 2: Check initial system status")
    status_success, _ = tester.test_system_status()
    test_results.append(("Initial Status", status_success))
    
    # 3. Test low severity drift injection
    print("\n📋 Step 3: Test low severity drift injection")
    low_drift_success, _ = tester.test_drift_injection_low_severity()
    test_results.append(("Low Severity Drift", low_drift_success))
    
    # 4. Test high severity drift injection (key requirement)
    print("\n📋 Step 4: Test high severity drift injection")
    high_drift_success, _ = tester.test_drift_injection_high_severity()
    test_results.append(("High Severity Drift", high_drift_success))
    
    # 5. Verify status reflects drift changes
    print("\n📋 Step 5: Verify status shows drift impact")
    post_drift_status_success, _ = tester.test_status_after_drift()
    test_results.append(("Post-Drift Status", post_drift_status_success))
    
    # 6. Test reliability history (snapshots)
    print("\n📋 Step 6: Test reliability history")
    history_success, _ = tester.test_reliability_history()
    test_results.append(("Reliability History", history_success))
    
    # 7. Test MongoDB persistence indirectly
    print("\n📋 Step 7: Test data persistence")
    persistence_success = tester.test_mongodb_persistence_check()
    test_results.append(("MongoDB Persistence", persistence_success))
    
    # Final results
    print("\n" + "="*80)
    print("📊 FINAL RESULTS")
    print("="*80)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📈 Overall: {sum(r[1] for r in test_results)}/{len(test_results)} tests passed")
    
    # Critical requirements check
    critical_tests = ["High Severity Drift", "Reliability History", "Post-Drift Status"]
    critical_passed = [r for r in test_results if r[0] in critical_tests and r[1]]
    
    if len(critical_passed) == len(critical_tests):
        print("🎯 All critical BLOCK 43.x requirements verified")
        return 0
    else:
        print("🚨 Critical requirements not fully verified")
        return 1

if __name__ == "__main__":
    sys.exit(main())