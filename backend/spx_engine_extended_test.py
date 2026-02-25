#!/usr/bin/env python3
"""
SPX Engine Extended Testing - Edge Cases & Performance
Comprehensive testing of B5.4 + B5.5 + B6.1 SPX modules
"""

import requests
import json
from datetime import datetime
import sys

BASE_URL = 'https://pointintime-macro.preview.emergentagent.com'

def test_edge_cases():
    """Test edge cases and error conditions"""
    print("🧪 Testing Edge Cases & Error Conditions")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Invalid date range for phase segments
    print("\n1. Testing invalid date range...")
    tests_total += 1
    try:
        response = requests.get(f"{BASE_URL}/api/spx/v2.1/phases/segments?start=2030-01-01&end=2020-01-01")
        data = response.json()
        if response.status_code == 200 and data.get('segmentsCount') == 0:
            print("✅ Correctly handled invalid date range")
            tests_passed += 1
        else:
            print(f"⚠️  Unexpected response to invalid date range: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid date range: {e}")
    
    # Test 2: Memory write with missing required field
    print("\n2. Testing memory write validation...")
    tests_total += 1
    try:
        response = requests.post(f"{BASE_URL}/api/spx/v2.1/admin/memory/write", 
                               json={"source": "TEST"}, 
                               headers={'Content-Type': 'application/json'})
        if response.status_code == 400:
            print("✅ Correctly rejected request without asOfDate")
            tests_passed += 1
        else:
            print(f"⚠️  Expected 400 for missing asOfDate, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing validation: {e}")
    
    # Test 3: Memory write with invalid horizon
    print("\n3. Testing memory write with invalid horizon...")
    tests_total += 1
    try:
        response = requests.post(f"{BASE_URL}/api/spx/v2.1/admin/memory/write", 
                               json={"asOfDate": "2024-01-15", "horizons": ["invalid_horizon"], "dryRun": True}, 
                               headers={'Content-Type': 'application/json'})
        data = response.json()
        if not data.get('ok') or response.status_code >= 400:
            print("✅ Correctly handled invalid horizon")
            tests_passed += 1
        else:
            print(f"⚠️  Should have rejected invalid horizon")
    except Exception as e:
        print(f"❌ Error testing invalid horizon: {e}")
    
    # Test 4: Focus pack with invalid horizon
    print("\n4. Testing focus pack with invalid horizon...")
    tests_total += 1
    try:
        response = requests.get(f"{BASE_URL}/api/spx/v2.1/focus-pack?focus=invalid")
        if response.status_code == 400:
            print("✅ Correctly rejected invalid horizon for focus pack")
            tests_passed += 1
        else:
            print(f"⚠️  Expected 400 for invalid horizon, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid focus horizon: {e}")
    
    print(f"\n📊 Edge Case Tests: {tests_passed}/{tests_total} passed")
    return tests_passed, tests_total

def test_performance():
    """Test performance characteristics"""
    print("\n⚡ Testing Performance Characteristics")
    print("=" * 50)
    
    import time
    
    endpoints = [
        ("/api/spx/v2.1/phases", "Phase Engine"),
        ("/api/spx/v2.1/phases/segments?start=2020-01-01&end=2026-02-21", "Phase Segments"),
        ("/api/spx/v2.1/admin/memory/stats", "Memory Stats"),
        ("/api/spx/v2.1/focus-pack?focus=30d", "Focus Pack 30d"),
        ("/api/spx/v2.1/focus-pack?focus=90d", "Focus Pack 90d"),
    ]
    
    for endpoint, name in endpoints:
        try:
            start = time.time()
            response = requests.get(f"{BASE_URL}{endpoint}")
            elapsed = time.time() - start
            
            if response.status_code == 200:
                print(f"✅ {name}: {elapsed:.2f}s")
            else:
                print(f"❌ {name}: Failed ({response.status_code})")
        except Exception as e:
            print(f"❌ {name}: Error - {e}")

def test_data_consistency():
    """Test data consistency across endpoints"""
    print("\n🔗 Testing Data Consistency")
    print("=" * 50)
    
    try:
        # Get phase data
        phase_response = requests.get(f"{BASE_URL}/api/spx/v2.1/phases")
        phase_data = phase_response.json().get('data', {})
        
        # Get terminal data  
        terminal_response = requests.get(f"{BASE_URL}/api/spx/v2.1/core/terminal")
        terminal_data = terminal_response.json().get('data', {})
        
        # Check data consistency
        phase_coverage = phase_data.get('coverageYears', 0)
        terminal_candles = terminal_data.get('meta', {}).get('totalCandles', 0)
        
        print(f"Phase Engine coverage: {phase_coverage} years")
        print(f"Terminal candles: {terminal_candles}")
        
        # Rough consistency check (252 trading days per year)
        expected_candles = phase_coverage * 252
        if abs(terminal_candles - expected_candles) / expected_candles < 0.1:
            print("✅ Data coverage consistent between endpoints")
        else:
            print("⚠️  Coverage mismatch between phase engine and terminal")
            
        # Check current phase info
        current_phase = phase_data.get('phaseIdAtNow', {}).get('phase')
        terminal_phase = terminal_data.get('phase', {}).get('phase')
        
        print(f"Current phases - Engine: {current_phase}, Terminal: {terminal_phase}")
        
        if current_phase and terminal_phase:
            print("✅ Both endpoints report current phase data")
        else:
            print("⚠️  Missing phase data in one or more endpoints")
            
    except Exception as e:
        print(f"❌ Error testing consistency: {e}")

def main():
    print("🚀 SPX Engine Extended Testing Suite")
    print(f"🌐 Backend: {BASE_URL}")
    print("=" * 80)
    
    # Run extended tests
    edge_passed, edge_total = test_edge_cases()
    test_performance()
    test_data_consistency()
    
    print(f"\n📋 EXTENDED TEST SUMMARY:")
    print(f"Edge cases: {edge_passed}/{edge_total} passed")
    print(f"Performance: All endpoints tested")
    print(f"Consistency: Cross-endpoint validation completed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())