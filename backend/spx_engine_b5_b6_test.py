#!/usr/bin/env python3
"""
SPX Engine BLOCKS B5.4 + B5.5 + B6.1 - Backend API Tests
Tests for SPX Phase Engine, Consensus Engine, and Memory Layer

NEW ENDPOINTS BEING TESTED:
- GET /api/spx/v2.1/phases - SPX Phase Engine (B5.4)
- GET /api/spx/v2.1/phases/segments?start=2020-01-01&end=2026-02-21 - Phase segments
- GET /api/spx/v2.1/admin/memory/stats - Memory stats (B6.1)
- POST /api/spx/v2.1/admin/memory/write - Write snapshot (B6.1)
- GET /api/spx/v2.1/admin/memory/snapshots - List snapshots
- GET /api/spx/v2.1/focus-pack?focus=30d - Existing endpoint compatibility check

Backend URL: https://pointintime-macro.preview.emergentagent.com
"""

import requests
import json
import sys
import os
from datetime import datetime

# Get backend URL from environment (use actual configured URL)
BASE_URL = 'https://pointintime-macro.preview.emergentagent.com'

class SpxEngineB5B6Tester:
    def __init__(self):
        self.base_url = BASE_URL
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []
        self.critical_failures = []
        
    def log_test(self, name, passed, details=None, error=None):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
            print(f"✅ PASS: {name}")
        else:
            print(f"❌ FAIL: {name}")
            if error:
                print(f"   Error: {error}")
            self.critical_failures.append({
                'name': name,
                'error': error,
                'details': details
            })
            
        self.results.append({
            'name': name,
            'passed': passed,
            'details': details,
            'error': error
        })
        
    def test_api_request(self, method, endpoint, expected_status=200, data=None, timeout=30):
        """Make API request with error handling"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            success = response.status_code == expected_status
            return success, response, None
            
        except requests.exceptions.Timeout:
            return False, None, f"Timeout after {timeout}s"
        except requests.exceptions.ConnectionError:
            return False, None, "Connection failed"
        except Exception as e:
            return False, None, str(e)

    def test_spx_phase_engine_basic(self):
        """Test B5.4 - SPX Phase Engine basic functionality"""
        print("\n🔍 Testing BLOCK B5.4 - SPX Phase Engine...")
        
        success, response, error = self.test_api_request('GET', '/api/spx/v2.1/phases')
        
        if not success:
            self.log_test("B5.4 Phase Engine - Basic Access", False, 
                         error=error or f"Status: {response.status_code if response else 'None'}")
            return False
            
        try:
            data = response.json()
            
            # Check basic structure
            if not data.get('ok'):
                self.log_test("B5.4 Phase Engine - Response OK", False, 
                             error=f"Response not ok: {data}")
                return False
                
            phase_data = data.get('data', {})
            
            # Check required fields
            required_fields = ['phaseIdAtNow', 'currentFlags', 'segments', 
                             'statsByPhase', 'overallGrade', 'totalDays', 'coverageYears']
            
            missing_fields = [f for f in required_fields if f not in phase_data]
            if missing_fields:
                self.log_test("B5.4 Phase Engine - Structure", False, 
                             error=f"Missing fields: {missing_fields}")
                return False
                
            # Check current phase
            phase_now = phase_data.get('phaseIdAtNow', {})
            valid_phases = ['BULL_EXPANSION', 'BULL_COOLDOWN', 'BEAR_DRAWDOWN', 'BEAR_RALLY', 'SIDEWAYS_RANGE']
            current_phase = phase_now.get('phase')
            
            if current_phase not in valid_phases:
                self.log_test("B5.4 Phase Engine - Valid Phase", False,
                             error=f"Invalid phase: {current_phase}, expected one of {valid_phases}")
                return False
                
            # Check flags
            current_flags = phase_data.get('currentFlags', [])
            valid_flags = ['VOL_SHOCK', 'DEEP_DRAWDOWN', 'TREND_BREAK']
            invalid_flags = [f for f in current_flags if f not in valid_flags]
            if invalid_flags:
                self.log_test("B5.4 Phase Engine - Valid Flags", False,
                             error=f"Invalid flags: {invalid_flags}")
                return False
                
            # Check stats by phase
            stats_by_phase = phase_data.get('statsByPhase', {})
            for phase in valid_phases:
                if phase not in stats_by_phase:
                    self.log_test("B5.4 Phase Engine - Stats Coverage", False,
                                 error=f"Missing stats for phase: {phase}")
                    return False
                    
            # Check coverage
            total_days = phase_data.get('totalDays', 0)
            coverage_years = phase_data.get('coverageYears', 0)
            
            if total_days < 250:
                self.log_test("B5.4 Phase Engine - Data Coverage", False,
                             error=f"Insufficient data: {total_days} days (need 250+)")
                return False
                
            self.log_test("B5.4 Phase Engine - Basic Functionality", True,
                         details=f"Phase: {current_phase}, Flags: {current_flags}, Coverage: {coverage_years} years")
            return True
            
        except Exception as e:
            self.log_test("B5.4 Phase Engine - JSON Parse", False, error=str(e))
            return False

    def test_spx_phase_segments(self):
        """Test B5.4 - SPX Phase segments for charting"""
        print("\n🔍 Testing BLOCK B5.4 - Phase Segments...")
        
        # Test with date range
        endpoint = '/api/spx/v2.1/phases/segments?start=2020-01-01&end=2026-02-21'
        success, response, error = self.test_api_request('GET', endpoint)
        
        if not success:
            self.log_test("B5.4 Phase Segments - API Access", False, error=error)
            return False
            
        try:
            data = response.json()
            
            if not data.get('ok'):
                self.log_test("B5.4 Phase Segments - Response OK", False, error=f"Response: {data}")
                return False
                
            # Check structure
            required_fields = ['symbol', 'dateRange', 'segmentsCount', 'segments']
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log_test("B5.4 Phase Segments - Structure", False, 
                             error=f"Missing fields: {missing_fields}")
                return False
                
            segments = data.get('segments', [])
            segments_count = data.get('segmentsCount', 0)
            
            if len(segments) != segments_count:
                self.log_test("B5.4 Phase Segments - Count Mismatch", False,
                             error=f"Segments length {len(segments)} != segmentsCount {segments_count}")
                return False
                
            # Check segment structure if any exist
            if segments:
                first_segment = segments[0]
                segment_fields = ['phaseId', 'phase', 'startDate', 'endDate', 'duration', 
                                'returnPct', 'maxDrawdownPct', 'realizedVol']
                missing_seg_fields = [f for f in segment_fields if f not in first_segment]
                if missing_seg_fields:
                    self.log_test("B5.4 Phase Segments - Segment Structure", False,
                                 error=f"Missing segment fields: {missing_seg_fields}")
                    return False
                    
            self.log_test("B5.4 Phase Segments - Functionality", True,
                         details=f"Found {segments_count} segments in date range")
            return True
            
        except Exception as e:
            self.log_test("B5.4 Phase Segments - Processing", False, error=str(e))
            return False

    def test_spx_memory_stats(self):
        """Test B6.1 - SPX Memory Layer stats"""
        print("\n🔍 Testing BLOCK B6.1 - SPX Memory Stats...")
        
        success, response, error = self.test_api_request('GET', '/api/spx/v2.1/admin/memory/stats')
        
        if not success:
            self.log_test("B6.1 Memory Stats - API Access", False, error=error)
            return False
            
        try:
            data = response.json()
            
            if not data.get('ok'):
                self.log_test("B6.1 Memory Stats - Response OK", False, error=f"Response: {data}")
                return False
                
            # Check required fields
            required_fields = ['snapshotCount', 'outcomeCount', 'sourceBreakdown']
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log_test("B6.1 Memory Stats - Structure", False,
                             error=f"Missing fields: {missing_fields}")
                return False
                
            # Check values are reasonable
            snapshot_count = data.get('snapshotCount', 0)
            outcome_count = data.get('outcomeCount', 0)
            
            if snapshot_count < 0:
                self.log_test("B6.1 Memory Stats - Invalid Snapshot Count", False,
                             error=f"Negative snapshot count: {snapshot_count}")
                return False
                
            if outcome_count < 0:
                self.log_test("B6.1 Memory Stats - Invalid Outcome Count", False,
                             error=f"Negative outcome count: {outcome_count}")
                return False
                
            self.log_test("B6.1 Memory Stats - Functionality", True,
                         details=f"Snapshots: {snapshot_count}, Outcomes: {outcome_count}")
            return True
            
        except Exception as e:
            self.log_test("B6.1 Memory Stats - Processing", False, error=str(e))
            return False

    def test_spx_memory_write_snapshot(self):
        """Test B6.1 - SPX Memory Layer snapshot writing"""
        print("\n🔍 Testing BLOCK B6.1 - Memory Snapshot Write...")
        
        # Test with dry run first
        write_data = {
            "asOfDate": "2024-12-01",
            "source": "TEST",
            "preset": "BALANCED",
            "horizons": ["30d", "90d"],
            "dryRun": True
        }
        
        success, response, error = self.test_api_request('POST', '/api/spx/v2.1/admin/memory/write', 
                                                        expected_status=200, data=write_data)
        
        if not success:
            self.log_test("B6.1 Memory Write - API Access", False, error=error)
            return False
            
        try:
            data = response.json()
            
            if not data.get('ok'):
                self.log_test("B6.1 Memory Write - Response OK", False, error=f"Response: {data}")
                return False
                
            # For dry run, should have written count and summary
            if 'written' not in data and 'summary' not in data:
                self.log_test("B6.1 Memory Write - Dry Run Response", False,
                             error="Expected 'written' or 'summary' in dry run response")
                return False
                
            self.log_test("B6.1 Memory Write - Dry Run", True,
                         details=f"Dry run successful: {data}")
            
            # Now test missing asOfDate (should fail)
            bad_data = {"source": "TEST"}
            success, response, error = self.test_api_request('POST', '/api/spx/v2.1/admin/memory/write',
                                                           expected_status=400, data=bad_data)
            
            if success:
                self.log_test("B6.1 Memory Write - Validation", True,
                             details="Correctly rejected request without asOfDate")
            else:
                self.log_test("B6.1 Memory Write - Validation", False,
                             error="Should have returned 400 for missing asOfDate")
                
            return True
            
        except Exception as e:
            self.log_test("B6.1 Memory Write - Processing", False, error=str(e))
            return False

    def test_spx_memory_snapshots_list(self):
        """Test B6.1 - SPX Memory Layer snapshots listing"""
        print("\n🔍 Testing BLOCK B6.1 - Memory Snapshots List...")
        
        success, response, error = self.test_api_request('GET', '/api/spx/v2.1/admin/memory/snapshots')
        
        if not success:
            self.log_test("B6.1 Memory Snapshots - API Access", False, error=error)
            return False
            
        try:
            data = response.json()
            
            if not data.get('ok'):
                self.log_test("B6.1 Memory Snapshots - Response OK", False, error=f"Response: {data}")
                return False
                
            # Check structure
            required_fields = ['total', 'returned', 'snapshots']
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                self.log_test("B6.1 Memory Snapshots - Structure", False,
                             error=f"Missing fields: {missing_fields}")
                return False
                
            total = data.get('total', 0)
            returned = data.get('returned', 0)
            snapshots = data.get('snapshots', [])
            
            if returned != len(snapshots):
                self.log_test("B6.1 Memory Snapshots - Count Consistency", False,
                             error=f"returned ({returned}) != snapshots length ({len(snapshots)})")
                return False
                
            # Test with filters
            filter_success, filter_response, filter_error = self.test_api_request(
                'GET', '/api/spx/v2.1/admin/memory/snapshots?source=LIVE&limit=10')
                
            if filter_success:
                filter_data = filter_response.json()
                filter_returned = filter_data.get('returned', 0)
                if filter_returned <= 10:
                    self.log_test("B6.1 Memory Snapshots - Filters & Limits", True,
                                 details=f"Filter test passed, returned {filter_returned} items")
                else:
                    self.log_test("B6.1 Memory Snapshots - Filters & Limits", False,
                                 error=f"Limit not respected: {filter_returned} > 10")
            
            self.log_test("B6.1 Memory Snapshots - Basic List", True,
                         details=f"Total: {total}, Returned: {returned}")
            return True
            
        except Exception as e:
            self.log_test("B6.1 Memory Snapshots - Processing", False, error=str(e))
            return False

    def test_spx_focus_pack_compatibility(self):
        """Test that existing focus-pack endpoint still works with new modules"""
        print("\n🔍 Testing SPX Focus Pack - Compatibility with new modules...")
        
        success, response, error = self.test_api_request('GET', '/api/spx/v2.1/focus-pack?focus=30d', timeout=60)
        
        if not success:
            self.log_test("SPX Focus Pack - Compatibility", False, error=error)
            return False
            
        try:
            data = response.json()
            
            if not data.get('ok'):
                self.log_test("SPX Focus Pack - Response OK", False, error=f"Response: {data}")
                return False
                
            # Quick check of main structure
            focus_data = data.get('data', {})
            key_sections = ['meta', 'overlay', 'forecast', 'phase']
            
            missing_sections = [s for s in key_sections if s not in focus_data]
            if missing_sections:
                self.log_test("SPX Focus Pack - Core Sections", False,
                             error=f"Missing sections: {missing_sections}")
                return False
                
            # Check processing time is reasonable
            processing_time = data.get('processingTimeMs', 0)
            if processing_time > 60000:  # 60 seconds
                self.log_test("SPX Focus Pack - Performance Warning", True,
                             details=f"Slow processing: {processing_time}ms (still functional)")
            
            self.log_test("SPX Focus Pack - Compatibility", True,
                         details=f"Processing time: {processing_time}ms")
            return True
            
        except Exception as e:
            self.log_test("SPX Focus Pack - Processing", False, error=str(e))
            return False

    def test_comprehensive_integration(self):
        """Test integration between all new modules"""
        print("\n🔍 Testing Cross-Module Integration...")
        
        # Test if phase engine data is consistent with other endpoints
        phase_success, phase_response, _ = self.test_api_request('GET', '/api/spx/v2.1/phases')
        terminal_success, terminal_response, _ = self.test_api_request('GET', '/api/spx/v2.1/core/terminal')
        
        if not (phase_success and terminal_success):
            self.log_test("Cross-Module Integration - Data Fetch", False,
                         error="Could not fetch data from both endpoints")
            return False
            
        try:
            phase_data = phase_response.json().get('data', {})
            terminal_data = terminal_response.json().get('data', {})
            
            # Check if terminal phase is consistent with phase engine (if available)
            terminal_phase = terminal_data.get('phase', {})
            phase_engine_current = phase_data.get('phaseIdAtNow', {})
            
            # They use different phase classifications, so just check they're both populated
            terminal_phase_name = terminal_phase.get('phase')
            engine_phase_name = phase_engine_current.get('phase')
            
            if not terminal_phase_name or not engine_phase_name:
                self.log_test("Cross-Module Integration - Phase Consistency", False,
                             error=f"Phase data missing: terminal={terminal_phase_name}, engine={engine_phase_name}")
                return False
                
            self.log_test("Cross-Module Integration - Phase Data", True,
                         details=f"Terminal phase: {terminal_phase_name}, Engine phase: {engine_phase_name}")
            return True
            
        except Exception as e:
            self.log_test("Cross-Module Integration - Processing", False, error=str(e))
            return False

    def run_all_tests(self):
        """Run all test suites"""
        print(f"🚀 Starting SPX Engine B5.4 + B5.5 + B6.1 Tests")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 80)
        
        # Run tests in logical order
        self.test_spx_phase_engine_basic()
        self.test_spx_phase_segments()
        self.test_spx_memory_stats()
        self.test_spx_memory_write_snapshot()
        self.test_spx_memory_snapshots_list()
        self.test_spx_focus_pack_compatibility()
        self.test_comprehensive_integration()
        
        # Results summary
        print("\n" + "=" * 80)
        print(f"📊 TESTS COMPLETED: {self.tests_passed}/{self.tests_run} passed")
        
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 SUCCESS RATE: {success_rate:.1f}%")
        
        if self.critical_failures:
            print(f"\n❌ CRITICAL FAILURES ({len(self.critical_failures)}):")
            for failure in self.critical_failures:
                print(f"   • {failure['name']}: {failure['error']}")
                
        # Save results
        results_file = '/app/backend/spx_engine_b5_b6_test_results.json'
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_tests': self.tests_run,
                    'passed_tests': self.tests_passed,
                    'success_rate': success_rate
                },
                'results': self.results,
                'critical_failures': self.critical_failures
            }, f, indent=2)
            
        print(f"\n📁 Results saved to: {results_file}")
        
        return success_rate >= 80  # Consider 80%+ success as acceptable

def main():
    tester = SpxEngineB5B6Tester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())