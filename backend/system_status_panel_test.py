#!/usr/bin/env python3
"""
System Status Panel Backend Testing
Testing /api/fractal/v2.1/terminal endpoint and phaseSnapshot data
"""

import requests
import json
import sys
from datetime import datetime

class SystemStatusPanelTester:
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

    def test_fractal_terminal_api(self, symbol="BTC", set_param="extended", focus="30d"):
        """Test GET /api/fractal/v2.1/terminal"""
        url = f"{self.base_url}/api/fractal/v2.1/terminal"
        params = {"symbol": symbol, "set": set_param, "focus": focus}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Fractal Terminal API ({symbol})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check for phaseSnapshot which is required for SystemStatusPanel
            if "phaseSnapshot" not in data:
                self.log_test(
                    f"Fractal Terminal API ({symbol})", 
                    False, 
                    "Missing phaseSnapshot field required for SystemStatusPanel"
                )
                return None
                
            phase_snapshot = data.get("phaseSnapshot")
            if not phase_snapshot or "phase" not in phase_snapshot:
                self.log_test(
                    f"Fractal Terminal API ({symbol})", 
                    False, 
                    "phaseSnapshot missing 'phase' field"
                )
                return None
                
            self.log_test(
                f"Fractal Terminal API ({symbol})", 
                True, 
                f"API returns phaseSnapshot with phase: {phase_snapshot.get('phase')}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Fractal Terminal API ({symbol})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_phase_snapshot_structure(self, data):
        """Test that phaseSnapshot contains required fields for Market State column"""
        if not data:
            return
            
        phase_snapshot = data.get("phaseSnapshot", {})
        
        # Required fields for Market State column in SystemStatusPanel
        required_fields = ["phase"]
        optional_fields = ["strengthIndex", "strength"]  # Either strengthIndex or strength
        
        missing_required = [f for f in required_fields if f not in phase_snapshot]
        
        if missing_required:
            self.log_test(
                "PhaseSnapshot Structure", 
                False, 
                f"Missing required fields: {missing_required}"
            )
            return
            
        # Check if at least one strength field exists
        has_strength = any(f in phase_snapshot for f in optional_fields)
        
        if not has_strength:
            self.log_test(
                "PhaseSnapshot Structure", 
                False, 
                f"Missing strength field (need either 'strengthIndex' or 'strength')"
            )
            return
            
        phase = phase_snapshot.get("phase")
        strength = phase_snapshot.get("strengthIndex") or phase_snapshot.get("strength", 0)
        
        self.log_test(
            "PhaseSnapshot Structure", 
            True, 
            f"Phase: {phase}, Strength: {strength}"
        )

    def test_consensus_pulse_api(self, symbol="BTC", days=7):
        """Test consensus pulse API endpoint for SystemStatusPanel"""
        url = f"{self.base_url}/api/fractal/v2.1/consensus-pulse"
        params = {"symbol": symbol, "days": days}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Consensus Pulse API ({symbol})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check for required fields for Market State column
            if "summary" not in data:
                self.log_test(
                    f"Consensus Pulse API ({symbol})", 
                    False, 
                    "Missing 'summary' field required for SystemStatusPanel"
                )
                return None
                
            summary = data.get("summary", {})
            required_summary_fields = ["current", "syncState"]
            missing_fields = [f for f in required_summary_fields if f not in summary]
            
            if missing_fields:
                self.log_test(
                    f"Consensus Pulse API ({symbol})", 
                    False, 
                    f"Missing summary fields: {missing_fields}"
                )
                return None
                
            self.log_test(
                f"Consensus Pulse API ({symbol})", 
                True, 
                f"Consensus: {summary.get('current')}, SyncState: {summary.get('syncState')}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Consensus Pulse API ({symbol})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_focus_pack_api(self, symbol="BTC", focus="30d"):
        """Test focus pack API for Projection Context data"""
        url = f"{self.base_url}/api/fractal/v2.1/focus-pack"
        params = {"symbol": symbol, "focus": focus}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                self.log_test(
                    f"Focus Pack API ({symbol}, {focus})", 
                    False, 
                    f"Status code {response.status_code}, expected 200"
                )
                return None
                
            data = response.json()
            
            # Check for meta data required for Projection Context
            if "meta" not in data:
                self.log_test(
                    f"Focus Pack API ({symbol}, {focus})", 
                    False, 
                    "Missing 'meta' field required for Projection Context"
                )
                return None
                
            meta = data.get("meta", {})
            required_meta_fields = ["focus", "tier", "windowLen", "aftermathDays"]
            missing_fields = [f for f in required_meta_fields if f not in meta]
            
            if missing_fields:
                self.log_test(
                    f"Focus Pack API ({symbol}, {focus})", 
                    False, 
                    f"Missing meta fields: {missing_fields}"
                )
                return None
                
            # Check for diagnostics and matchesCount for Data Status
            diagnostics = data.get("diagnostics", {})
            matches_count = data.get("matchesCount", 0)
            
            self.log_test(
                f"Focus Pack API ({symbol}, {focus})", 
                True, 
                f"Focus: {meta.get('focus')}, Tier: {meta.get('tier')}, Matches: {matches_count}"
            )
            
            return data
            
        except Exception as e:
            self.log_test(
                f"Focus Pack API ({symbol}, {focus})", 
                False, 
                f"Request failed: {str(e)}"
            )
            return None

    def test_system_status_panel_data_completeness(self, terminal_data, consensus_data, focus_data):
        """Test that all three columns of SystemStatusPanel have required data"""
        
        # Market State column completeness
        market_state_complete = True
        market_issues = []
        
        if not terminal_data or not terminal_data.get("phaseSnapshot"):
            market_state_complete = False
            market_issues.append("Missing phaseSnapshot")
            
        if not consensus_data or not consensus_data.get("summary"):
            market_state_complete = False  
            market_issues.append("Missing consensus summary")
            
        self.log_test(
            "Market State Data Completeness",
            market_state_complete,
            f"Issues: {market_issues}" if market_issues else "All required data present"
        )
        
        # Projection Context column completeness
        projection_context_complete = True
        projection_issues = []
        
        if not focus_data or not focus_data.get("meta"):
            projection_context_complete = False
            projection_issues.append("Missing focus meta")
            
        if not focus_data or not focus_data.get("matchesCount", 0):
            projection_context_complete = False
            projection_issues.append("Missing matchesCount")
            
        self.log_test(
            "Projection Context Data Completeness",
            projection_context_complete,
            f"Issues: {projection_issues}" if projection_issues else "All required data present"
        )
        
        # Data Status column completeness  
        data_status_complete = True
        data_issues = []
        
        if not focus_data or not focus_data.get("diagnostics"):
            data_status_complete = False
            data_issues.append("Missing diagnostics")
            
        matches_count = focus_data.get("matchesCount", 0) if focus_data else 0
        if matches_count == 0:
            data_issues.append("No historical matches available")
            
        self.log_test(
            "Data Status Column Completeness",
            data_status_complete,
            f"Issues: {data_issues}" if data_issues else f"Matches available: {matches_count}"
        )

    def test_different_horizons(self):
        """Test different focus horizons"""
        horizons = ["7d", "14d", "30d", "60d", "90d", "180d"]
        
        for horizon in horizons:
            focus_data = self.test_focus_pack_api("BTC", horizon)
            if focus_data:
                meta = focus_data.get("meta", {})
                tier = meta.get("tier", "UNKNOWN")
                matches = focus_data.get("matchesCount", 0)
                self.log_test(
                    f"Horizon {horizon} Data",
                    True,
                    f"Tier: {tier}, Matches: {matches}"
                )

    def run_all_tests(self):
        """Run all System Status Panel backend tests"""
        print("=" * 60)
        print("SYSTEM STATUS PANEL BACKEND TESTING")
        print("=" * 60)
        print(f"Base URL: {self.base_url}")
        print()
        
        # Test main terminal API
        terminal_data = self.test_fractal_terminal_api("BTC", "extended", "30d")
        if terminal_data:
            self.test_phase_snapshot_structure(terminal_data)
        
        # Test consensus pulse API
        consensus_data = self.test_consensus_pulse_api("BTC", 7)
        
        # Test focus pack API  
        focus_data = self.test_focus_pack_api("BTC", "30d")
        
        # Test data completeness for SystemStatusPanel
        self.test_system_status_panel_data_completeness(terminal_data, consensus_data, focus_data)
        
        # Test different horizons
        self.test_different_horizons()
        
        print()
        print("=" * 60)
        print(f"RESULTS: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 60)
        
        return self.tests_passed, self.tests_run, self.test_results

def main():
    """Main test execution"""
    tester = SystemStatusPanelTester()
    passed, total, results = tester.run_all_tests()
    
    # Save results
    with open('/app/test_reports/system_status_panel_backend_test_results.json', 'w') as f:
        json.dump({
            "summary": f"System Status Panel Backend Testing",
            "tests_passed": passed,
            "tests_total": total,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "timestamp": datetime.now().isoformat(),
            "test_details": results
        }, f, indent=2)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())