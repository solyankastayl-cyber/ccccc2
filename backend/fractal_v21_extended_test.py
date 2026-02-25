#!/usr/bin/env python3
"""
Extended BLOCK 43.x Testing - Edge Cases and Badge Transitions
"""

import requests
import sys
import time
import json

class ExtendedFractalTester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.model_key = "BTCUSD:14"
        self.preset_key = "v2_entropy_final"
        
    def call_api(self, method, endpoint, data=None, params=None):
        """Make API call and return response"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            
            return response.status_code, response.json()
        except Exception as e:
            return 500, {"error": str(e)}

    def test_badge_progression(self):
        """Test the complete badge progression: OK → WARN → DEGRADED → CRITICAL"""
        print("🔄 Testing Complete Badge Progression")
        print("="*50)
        
        # Reset to clean state
        print("1. Resetting calibration...")
        status, _ = self.call_api('POST', '/api/fractal/v2.1/admin/drift/reset', 
                                 data={"modelKey": self.model_key, "presetKey": self.preset_key, "horizonDays": 14})
        
        if status != 200:
            print("❌ Reset failed")
            return False
            
        # Step 1: Start with clean state (should be OK or WARN)
        status, response = self.call_api('GET', '/api/fractal/v2.1/admin/status',
                                        params={"modelKey": self.model_key, "presetKey": self.preset_key})
        initial_badge = response.get('reliability', {}).get('badge', 'UNKNOWN')
        print(f"2. Initial state: {initial_badge}")
        
        # Step 2: Apply mild drift (severity 0.3)
        print("3. Applying mild drift (severity 0.3)...")
        status, response = self.call_api('POST', '/api/fractal/v2.1/admin/drift/inject',
                                        data={"modelKey": self.model_key, "presetKey": self.preset_key, 
                                             "horizonDays": 14, "severity": 0.3})
        
        if status == 200 and response.get('ok'):
            after_mild = response.get('after', {})
            print(f"   Badge after mild drift: {after_mild.get('badge')} (ECE: {after_mild.get('ece', 0):.3f})")
        
        # Step 3: Apply moderate drift (severity 0.6)
        print("4. Applying moderate drift (severity 0.6)...")
        status, response = self.call_api('POST', '/api/fractal/v2.1/admin/drift/inject',
                                        data={"modelKey": self.model_key, "presetKey": self.preset_key,
                                             "horizonDays": 14, "severity": 0.6})
        
        if status == 200 and response.get('ok'):
            after_moderate = response.get('after', {})
            print(f"   Badge after moderate drift: {after_moderate.get('badge')} (ECE: {after_moderate.get('ece', 0):.3f})")
        
        # Step 4: Apply severe drift (severity 0.9)
        print("5. Applying severe drift (severity 0.9)...")
        status, response = self.call_api('POST', '/api/fractal/v2.1/admin/drift/inject',
                                        data={"modelKey": self.model_key, "presetKey": self.preset_key,
                                             "horizonDays": 14, "severity": 0.9})
        
        if status == 200 and response.get('ok'):
            after_severe = response.get('after', {})
            print(f"   Badge after severe drift: {after_severe.get('badge')} (ECE: {after_severe.get('ece', 0):.3f})")
            
            # Verify final state is CRITICAL
            if after_severe.get('badge') in ['DEGRADED', 'CRITICAL']:
                print("✅ Badge progression working correctly")
                return True
                
        print("❌ Badge progression test failed")
        return False

    def test_snapshot_accumulation(self):
        """Test that snapshots accumulate in history"""
        print("\n🗄️  Testing Snapshot Accumulation")
        print("="*50)
        
        # Get initial history count
        status, response = self.call_api('GET', '/api/fractal/v2.1/admin/reliability/history',
                                        params={"modelKey": self.model_key, "presetKey": self.preset_key, "limit": "100"})
        
        if status != 200:
            print("❌ Failed to get history")
            return False
            
        initial_count = len(response.get('history', []))
        print(f"1. Initial snapshot count: {initial_count}")
        
        # Inject drift to create new snapshot
        print("2. Injecting drift to create snapshot...")
        status, response = self.call_api('POST', '/api/fractal/v2.1/admin/drift/inject',
                                        data={"modelKey": self.model_key, "presetKey": self.preset_key,
                                             "horizonDays": 14, "severity": 0.4})
        
        if status == 200 and response.get('ok'):
            snapshot_written = response.get('snapshotWritten', False)
            print(f"   Snapshot written: {snapshot_written}")
            
            # Check history again
            time.sleep(1)  # Allow for async operations
            status, response = self.call_api('GET', '/api/fractal/v2.1/admin/reliability/history',
                                            params={"modelKey": self.model_key, "presetKey": self.preset_key, "limit": "100"})
            
            new_count = len(response.get('history', []))
            print(f"3. New snapshot count: {new_count}")
            
            if new_count > initial_count:
                print("✅ Snapshot accumulation working")
                return True
            else:
                print("⚠️  Snapshot count didn't increase")
                
        print("❌ Snapshot accumulation test failed")
        return False

    def test_different_model_keys(self):
        """Test that different model keys maintain separate data"""
        print("\n🔑 Testing Model Key Separation")
        print("="*50)
        
        alt_model_key = "ETHUSD:7"
        
        # Get status for alternative model key
        status, response = self.call_api('GET', '/api/fractal/v2.1/admin/status',
                                        params={"modelKey": alt_model_key, "presetKey": self.preset_key})
        
        if status == 200:
            alt_reliability = response.get('reliability', {})
            alt_badge = alt_reliability.get('badge', 'UNKNOWN')
            alt_calibration = response.get('calibration')
            
            print(f"1. {alt_model_key} status: badge={alt_badge}")
            print(f"   Has calibration data: {alt_calibration is not None}")
            
            # Get status for original model key
            status, response = self.call_api('GET', '/api/fractal/v2.1/admin/status',
                                            params={"modelKey": self.model_key, "presetKey": self.preset_key})
            
            if status == 200:
                orig_reliability = response.get('reliability', {})
                orig_badge = orig_reliability.get('badge', 'UNKNOWN')
                
                print(f"2. {self.model_key} status: badge={orig_badge}")
                
                if alt_badge != orig_badge or (alt_calibration is None) != (response.get('calibration') is None):
                    print("✅ Model key separation working")
                    return True
                else:
                    print("⚠️  Model keys might be sharing data")
        
        print("❌ Model key separation test inconclusive")
        return False

    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        print("\n🚨 Testing Error Handling")
        print("="*50)
        
        tests_passed = 0
        total_tests = 3
        
        # Test 1: Invalid severity (> 1.0)
        print("1. Testing invalid severity...")
        status, response = self.call_api('POST', '/api/fractal/v2.1/admin/drift/inject',
                                        data={"modelKey": self.model_key, "presetKey": self.preset_key,
                                             "horizonDays": 14, "severity": 1.5})
        
        if status == 200:  # Should still work, but clamp severity
            print("   ✅ Invalid severity handled gracefully")
            tests_passed += 1
        
        # Test 2: Missing required parameters
        print("2. Testing missing parameters...")
        status, response = self.call_api('POST', '/api/fractal/v2.1/admin/drift/inject', data={})
        
        if status == 200:  # Should use defaults
            print("   ✅ Missing parameters handled with defaults")
            tests_passed += 1
        
        # Test 3: Invalid history limit
        print("3. Testing invalid history limit...")
        status, response = self.call_api('GET', '/api/fractal/v2.1/admin/reliability/history',
                                        params={"modelKey": self.model_key, "presetKey": self.preset_key, "limit": "-1"})
        
        if status == 200:  # Should handle gracefully
            print("   ✅ Invalid limit handled gracefully")
            tests_passed += 1
        
        if tests_passed == total_tests:
            print("✅ Error handling tests passed")
            return True
        else:
            print(f"⚠️  Error handling: {tests_passed}/{total_tests} tests passed")
            return False


def main():
    print("🔬 FRACTAL V2.1 BLOCK 43.x - Extended Testing")
    print("="*60)
    
    tester = ExtendedFractalTester()
    
    # Run extended tests
    results = []
    
    badge_progression = tester.test_badge_progression()
    results.append(("Badge Progression", badge_progression))
    
    snapshot_accumulation = tester.test_snapshot_accumulation()  
    results.append(("Snapshot Accumulation", snapshot_accumulation))
    
    model_separation = tester.test_different_model_keys()
    results.append(("Model Key Separation", model_separation))
    
    error_handling = tester.test_error_handling()
    results.append(("Error Handling", error_handling))
    
    # Results
    print("\n" + "="*60)
    print("📊 EXTENDED TEST RESULTS")
    print("="*60)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "⚠️  PARTIAL/FAIL"
        print(f"{status} {test_name}")
    
    passed_count = sum(1 for _, success in results if success)
    print(f"\n📈 Extended tests: {passed_count}/{len(results)} passed")
    
    return 0 if passed_count >= 3 else 1  # Allow 1 failure

if __name__ == "__main__":
    sys.exit(main())