#!/usr/bin/env python3
"""
BLOCK 73.5.1 — Phase Hover Intelligence Test
Tests phase stats functionality in fractal chart API and phase tooltip integration

Key Features to Test:
1. Backend: /api/fractal/v2.1/chart returns phaseStats array with required fields
2. PhaseStats data correctness (durationDays, phaseReturnPct, volRegime, matchesCount)
3. Frontend integration (tested separately with browser automation)

Test Targets:
- GET /api/fractal/v2.1/chart?symbol=BTC&limit=365
- PhaseStats array structure and data validation
- Phase zones alignment with phase stats
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, List, Any

class PhaseHoverIntelligenceTest:
    def __init__(self, base_url_external="https://pointintime-macro.preview.emergentagent.com", 
                 base_url_local="http://localhost:8001"):
        # Agent notes mention using localhost:8001 due to external ingress issues
        self.base_url_external = base_url_external
        self.base_url_local = base_url_local
        self.current_base_url = None
        self.tests_run = 0
        self.tests_passed = 0
        self.phase_stats_data = None

    def log_test(self, name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name}")
        
        if details:
            print(f"   {details}")

    def test_chart_api_connectivity(self) -> bool:
        """Test API connectivity and choose working endpoint"""
        endpoints = [
            ("External", self.base_url_external),
            ("Local", self.base_url_local)
        ]
        
        for name, url in endpoints:
            try:
                response = requests.get(f"{url}/api/fractal/v2.1/chart?symbol=BTC&limit=10", timeout=10)
                if response.status_code == 200:
                    self.current_base_url = url
                    self.log_test(f"Chart API Connectivity ({name})", True, f"Status: {response.status_code}")
                    return True
                else:
                    print(f"❌ {name} endpoint failed: {response.status_code}")
            except Exception as e:
                print(f"❌ {name} endpoint error: {str(e)}")
        
        self.log_test("Chart API Connectivity", False, "All endpoints failed")
        return False

    def test_chart_api_response_structure(self) -> bool:
        """Test that chart API returns correct structure including phaseStats"""
        if not self.current_base_url:
            self.log_test("Chart API Response Structure", False, "No working base URL")
            return False
        
        try:
            response = requests.get(f"{self.current_base_url}/api/fractal/v2.1/chart?symbol=BTC&limit=365", timeout=30)
            
            if response.status_code != 200:
                self.log_test("Chart API Response Structure", False, f"Status: {response.status_code}")
                return False
            
            data = response.json()
            
            # Check basic structure
            required_fields = ['symbol', 'tf', 'asOf', 'count', 'candles', 'sma200', 'phaseZones']
            for field in required_fields:
                if field not in data:
                    self.log_test("Chart API Response Structure", False, f"Missing field: {field}")
                    return False
            
            # BLOCK 73.5.1: Check phaseStats field exists
            if 'phaseStats' not in data:
                self.log_test("Chart API Response Structure", False, "Missing phaseStats field")
                return False
            
            # Store data for further tests
            self.chart_data = data
            
            self.log_test("Chart API Response Structure", True, 
                         f"Got {len(data.get('candles', []))} candles, {len(data.get('phaseZones', []))} phases, {len(data.get('phaseStats', []))} phase stats")
            return True
            
        except Exception as e:
            self.log_test("Chart API Response Structure", False, f"Error: {str(e)}")
            return False

    def test_phase_stats_structure(self) -> bool:
        """Test phaseStats array structure and required fields"""
        if not hasattr(self, 'chart_data') or not self.chart_data.get('phaseStats'):
            self.log_test("Phase Stats Structure", False, "No phaseStats data available")
            return False
        
        phase_stats = self.chart_data['phaseStats']
        
        if not isinstance(phase_stats, list):
            self.log_test("Phase Stats Structure", False, "phaseStats is not an array")
            return False
        
        if len(phase_stats) == 0:
            self.log_test("Phase Stats Structure", False, "phaseStats array is empty")
            return False
        
        # Check structure of first phase stat
        required_fields = ['phaseId', 'phase', 'from', 'to', 'durationDays', 'phaseReturnPct', 'volRegime', 'matchesCount']
        sample_stat = phase_stats[0]
        
        for field in required_fields:
            if field not in sample_stat:
                self.log_test("Phase Stats Structure", False, f"Missing field in phaseStats: {field}")
                return False
        
        # Store for later tests
        self.phase_stats_data = phase_stats
        
        self.log_test("Phase Stats Structure", True, 
                     f"Found {len(phase_stats)} phase stats with all required fields")
        return True

    def test_phase_stats_data_validation(self) -> bool:
        """Validate phase stats data types and ranges"""
        if not self.phase_stats_data:
            self.log_test("Phase Stats Data Validation", False, "No phase stats data")
            return False
        
        validation_errors = []
        
        for i, stat in enumerate(self.phase_stats_data):
            # Test data types and ranges
            if not isinstance(stat.get('durationDays'), (int, float)) or stat['durationDays'] <= 0:
                validation_errors.append(f"Phase {i}: Invalid durationDays")
            
            if not isinstance(stat.get('phaseReturnPct'), (int, float)):
                validation_errors.append(f"Phase {i}: Invalid phaseReturnPct")
            
            valid_vol_regimes = ['LOW', 'NORMAL', 'HIGH', 'EXPANSION', 'CRISIS']
            if stat.get('volRegime') not in valid_vol_regimes:
                validation_errors.append(f"Phase {i}: Invalid volRegime: {stat.get('volRegime')}")
            
            if not isinstance(stat.get('matchesCount'), int) or stat['matchesCount'] < 0:
                validation_errors.append(f"Phase {i}: Invalid matchesCount")
            
            valid_phases = ['ACCUMULATION', 'DISTRIBUTION', 'MARKUP', 'MARKDOWN', 'RECOVERY', 'CAPITULATION', 'UNKNOWN']
            if stat.get('phase') not in valid_phases:
                validation_errors.append(f"Phase {i}: Invalid phase: {stat.get('phase')}")
        
        if validation_errors:
            self.log_test("Phase Stats Data Validation", False, "; ".join(validation_errors[:3]))
            return False
        
        # Sample some actual values for verification
        sample_stats = self.phase_stats_data[:3]  # First 3 phases
        sample_info = []
        for stat in sample_stats:
            sample_info.append(f"{stat['phase']}: {stat['durationDays']}d, {stat['phaseReturnPct']:.1f}%, {stat['volRegime']}, {stat['matchesCount']} matches")
        
        self.log_test("Phase Stats Data Validation", True, 
                     f"All data valid. Sample: {'; '.join(sample_info)}")
        return True

    def test_phase_zones_alignment(self) -> bool:
        """Test that phase zones and phase stats are properly aligned"""
        if not hasattr(self, 'chart_data'):
            self.log_test("Phase Zones Alignment", False, "No chart data")
            return False
        
        phase_zones = self.chart_data.get('phaseZones', [])
        phase_stats = self.phase_stats_data or []
        
        # There should be equal or similar number of zones and stats
        zone_count = len(phase_zones)
        stats_count = len(phase_stats)
        
        if abs(zone_count - stats_count) > 1:  # Allow 1 difference for edge cases
            self.log_test("Phase Zones Alignment", False, 
                         f"Mismatch: {zone_count} zones vs {stats_count} stats")
            return False
        
        # Check that phases match between zones and stats
        if zone_count > 0 and stats_count > 0:
            # Sample check: first phase should match
            first_zone = phase_zones[0]
            first_stat = phase_stats[0]
            
            if first_zone.get('phase') != first_stat.get('phase'):
                self.log_test("Phase Zones Alignment", False, 
                             f"Phase mismatch: zone='{first_zone.get('phase')}' vs stat='{first_stat.get('phase')}'")
                return False
        
        self.log_test("Phase Zones Alignment", True, 
                     f"Zones ({zone_count}) and stats ({stats_count}) properly aligned")
        return True

    def test_chart_data_completeness(self) -> bool:
        """Test that chart has sufficient data for meaningful phase analysis"""
        if not hasattr(self, 'chart_data'):
            self.log_test("Chart Data Completeness", False, "No chart data")
            return False
        
        candles = self.chart_data.get('candles', [])
        sma200 = self.chart_data.get('sma200', [])
        
        # Should have reasonable amount of data
        if len(candles) < 200:
            self.log_test("Chart Data Completeness", False, 
                         f"Insufficient candle data: {len(candles)} (need 200+ for SMA200)")
            return False
        
        if len(sma200) == 0:
            self.log_test("Chart Data Completeness", False, "No SMA200 data")
            return False
        
        # Check candle data structure
        sample_candle = candles[0]
        required_candle_fields = ['t', 'o', 'h', 'l', 'c']
        for field in required_candle_fields:
            if field not in sample_candle:
                self.log_test("Chart Data Completeness", False, f"Missing candle field: {field}")
                return False
        
        self.log_test("Chart Data Completeness", True, 
                     f"Complete data: {len(candles)} candles, {len(sma200)} SMA points")
        return True

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all phase hover intelligence tests"""
        print("🔍 BLOCK 73.5.1 — Phase Hover Intelligence Test Suite")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_chart_api_connectivity,
            self.test_chart_api_response_structure,
            self.test_phase_stats_structure,
            self.test_phase_stats_data_validation,
            self.test_phase_zones_alignment,
            self.test_chart_data_completeness
        ]
        
        for test in tests:
            test()
            print()
        
        # Summary
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed ({success_rate:.1f}%)")
        
        # Prepare result data
        result = {
            "test_suite": "BLOCK 73.5.1 Phase Hover Intelligence",
            "timestamp": datetime.now().isoformat(),
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "success_rate": success_rate,
            "working_endpoint": self.current_base_url,
            "phase_stats_count": len(self.phase_stats_data) if self.phase_stats_data else 0,
            "backend_ready": self.tests_passed >= 4  # Need at least basic functionality working
        }
        
        return result

def main():
    tester = PhaseHoverIntelligenceTest()
    result = tester.run_all_tests()
    
    # Save results
    with open('/app/backend/block_735_phase_stats_test_results.json', 'w') as f:
        json.dump(result, f, indent=2)
    
    return 0 if result["backend_ready"] else 1

if __name__ == "__main__":
    sys.exit(main())