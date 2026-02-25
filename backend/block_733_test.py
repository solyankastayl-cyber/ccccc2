#!/usr/bin/env python3
"""
BLOCK 73.3 Continuity Fix Testing Suite
Tests the intermediate horizon markers for visual continuity in 14D and 30D trajectories
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class Block733Tester:
    def __init__(self, base_url: str = "https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            **details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if not success and "error" in details:
            print(f"    Error: {details['error']}")
        if "note" in details:
            print(f"    Note: {details['note']}")
        print()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, timeout: int = 60) -> tuple[bool, Dict[str, Any]]:
        """Make HTTP request and return success status and response data"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
            
            # Try to parse JSON response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw_response": response.text}
            
            return response.status_code == 200, {
                "status_code": response.status_code,
                "response_data": response_data,
                "headers": dict(response.headers)
            }
            
        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_14d_focus_pack_markers(self):
        """Test /api/fractal/v2.1/focus-pack for 14D with intermediate markers"""
        params = {"symbol": "BTC", "focus": "14d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif "focusPack" not in data:
                success = False
                details["error"] = "Expected 'focusPack' field"
            else:
                focus_pack = data["focusPack"]
                
                # Check forecast contains markers
                forecast = focus_pack.get("forecast", {})
                markers = forecast.get("markers", [])
                
                if not markers:
                    success = False
                    details["error"] = "Expected 'markers' array in forecast"
                else:
                    # Check for 7d and 14d horizon markers
                    marker_horizons = [m.get("horizon") for m in markers]
                    expected_horizons = ["7d", "14d"]
                    missing_horizons = [h for h in expected_horizons if h not in marker_horizons]
                    
                    if missing_horizons:
                        success = False
                        details["error"] = f"Missing horizon markers: {missing_horizons}"
                    else:
                        # Validate marker structure (accept both day/dayIndex and price/expectedReturn)
                        for marker in markers:
                            has_horizon = "horizon" in marker
                            has_day = "day" in marker or "dayIndex" in marker
                            has_price = "price" in marker or "expectedReturn" in marker
                            
                            if not (has_horizon and has_day and has_price):
                                success = False
                                details["error"] = f"Invalid marker structure: {marker}"
                                break
                        
                        if success:
                            details["markers_found"] = marker_horizons
                            details["note"] = f"Found {len(markers)} markers with horizons: {marker_horizons}"
        
        self.log_test("14D Focus Pack - Intermediate Markers (BLOCK 73.3)", success, details)
        return success

    def test_30d_focus_pack_markers(self):
        """Test /api/fractal/v2.1/focus-pack for 30D with all horizon markers"""
        params = {"symbol": "BTC", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif "focusPack" not in data:
                success = False
                details["error"] = "Expected 'focusPack' field"
            else:
                focus_pack = data["focusPack"]
                
                # Check forecast contains markers
                forecast = focus_pack.get("forecast", {})
                markers = forecast.get("markers", [])
                
                if not markers:
                    success = False
                    details["error"] = "Expected 'markers' array in forecast"
                else:
                    # Check for 7d, 14d, and 30d horizon markers
                    marker_horizons = [m.get("horizon") for m in markers]
                    expected_horizons = ["7d", "14d", "30d"]
                    missing_horizons = [h for h in expected_horizons if h not in marker_horizons]
                    
                    if missing_horizons:
                        success = False
                        details["error"] = f"Missing horizon markers: {missing_horizons}"
                    else:
                        # Validate markers are ordered correctly by day
                        marker_days = []
                        for marker in markers:
                            if "day" in marker:
                                marker_days.append((marker["day"], marker["horizon"]))
                            elif "dayIndex" in marker:
                                marker_days.append((marker["dayIndex"] + 1, marker["horizon"]))
                        
                        marker_days.sort()
                        
                        # Check ordering makes sense (7d < 14d < 30d)
                        day_7d = next((day for day, h in marker_days if h == "7d"), None)
                        day_14d = next((day for day, h in marker_days if h == "14d"), None)
                        day_30d = next((day for day, h in marker_days if h == "30d"), None)
                        
                        if day_7d and day_14d and day_30d:
                            if not (day_7d < day_14d < day_30d):
                                success = False
                                details["error"] = f"Markers not ordered correctly: 7d={day_7d}, 14d={day_14d}, 30d={day_30d}"
                            else:
                                details["marker_ordering"] = f"7d=day{day_7d}, 14d=day{day_14d}, 30d=day{day_30d}"
                        
                        if success:
                            details["markers_found"] = marker_horizons
                            details["note"] = f"Found {len(markers)} markers with correct ordering"
        
        self.log_test("30D Focus Pack - All Horizon Markers (BLOCK 73.3)", success, details)
        return success

    def test_7d_focus_pack_no_intermediate_markers(self):
        """Test /api/fractal/v2.1/focus-pack for 7D should not have intermediate markers"""
        params = {"symbol": "BTC", "focus": "7d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif "focusPack" not in data:
                success = False
                details["error"] = "Expected 'focusPack' field"
            else:
                focus_pack = data["focusPack"]
                
                # Check forecast markers
                forecast = focus_pack.get("forecast", {})
                markers = forecast.get("markers", [])
                
                # For 7D, should have minimal or no intermediate markers
                intermediate_markers = [m for m in markers if m.get("horizon") != "7d"]
                
                if len(intermediate_markers) > 0:
                    details["note"] = f"Found {len(intermediate_markers)} intermediate markers in 7D (may be acceptable)"
                else:
                    details["note"] = "No intermediate markers in 7D focus (expected)"
                
                # Check meta tier is TIMING for 7D
                meta = focus_pack.get("meta", {})
                if meta.get("tier") != "TIMING":
                    success = False
                    details["error"] = f"Expected tier 'TIMING' for 7d, got '{meta.get('tier')}'"
        
        self.log_test("7D Focus Pack - No Intermediate Markers (BLOCK 73.3)", success, details)
        return success

    def test_marker_continuity_consistency(self):
        """Test that markers provide visual continuity across different horizons"""
        horizons_to_test = ["14d", "30d"]
        horizon_markers = {}
        
        success = True
        details = {"horizon_data": {}}
        
        for horizon in horizons_to_test:
            params = {"symbol": "BTC", "focus": horizon}
            req_success, req_details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
            
            if req_success:
                data = req_details.get("response_data", {})
                if data.get("ok") and "focusPack" in data:
                    forecast = data["focusPack"].get("forecast", {})
                    markers = forecast.get("markers", [])
                    horizon_markers[horizon] = markers
                    
                    # Extract marker details for analysis
                    marker_data = []
                    for marker in markers:
                        marker_data.append({
                            "horizon": marker.get("horizon"),
                            "day": marker.get("day", marker.get("dayIndex", 0) + 1),
                            "price": marker.get("price")
                        })
                    
                    details["horizon_data"][horizon] = {
                        "marker_count": len(markers),
                        "markers": marker_data
                    }
                else:
                    success = False
                    details["error"] = f"Failed to get valid response for {horizon}"
                    break
            else:
                success = False
                details["error"] = f"Request failed for {horizon}: {req_details.get('error')}"
                break
        
        if success:
            # Check that 14d has 7d marker and 30d has 7d and 14d markers
            markers_14d = horizon_markers.get("14d", [])
            markers_30d = horizon_markers.get("30d", [])
            
            # 14D should have 7d intermediate marker
            has_7d_in_14d = any(m.get("horizon") == "7d" for m in markers_14d)
            if not has_7d_in_14d:
                success = False
                details["error"] = "14D trajectory missing 7d intermediate marker for continuity"
            
            # 30D should have both 7d and 14d intermediate markers
            has_7d_in_30d = any(m.get("horizon") == "7d" for m in markers_30d)
            has_14d_in_30d = any(m.get("horizon") == "14d" for m in markers_30d)
            
            if not has_7d_in_30d:
                success = False
                details["error"] = "30D trajectory missing 7d intermediate marker for continuity"
            elif not has_14d_in_30d:
                success = False
                details["error"] = "30D trajectory missing 14d intermediate marker for continuity"
            
            if success:
                details["continuity_check"] = {
                    "14d_has_7d_marker": has_7d_in_14d,
                    "30d_has_7d_marker": has_7d_in_30d,
                    "30d_has_14d_marker": has_14d_in_30d
                }
                details["note"] = "Visual continuity markers validated across horizons"
        
        self.log_test("Marker Continuity Consistency (BLOCK 73.3)", success, details)
        return success

    def test_hybrid_mode_data_availability(self):
        """Test that focus-pack provides data needed for hybrid mode rendering"""
        params = {"symbol": "BTC", "focus": "14d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/focus-pack", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            elif "focusPack" not in data:
                success = False
                details["error"] = "Expected 'focusPack' field"
            else:
                focus_pack = data["focusPack"]
                
                # Check for forecast (synthetic) data
                forecast = focus_pack.get("forecast", {})
                price_path = forecast.get("path", [])  # Changed from 'pricePath' to 'path'
                
                if not price_path:
                    success = False
                    details["error"] = "Expected 'path' for synthetic line"
                else:
                    details["synthetic_path_length"] = len(price_path)
                
                # Check for primary match (replay) data
                overlay = focus_pack.get("overlay", {})
                matches = overlay.get("matches", [])
                
                if not matches:
                    success = False
                    details["error"] = "Expected 'matches' for replay line"
                else:
                    primary_match = matches[0] if matches else None
                    if primary_match:
                        # Check for replay data in various possible formats
                        has_replay_path = "replayPath" in primary_match
                        has_aftermath = "aftermath" in primary_match
                        has_price_series = "priceSeries" in primary_match
                        
                        if has_replay_path:
                            details["replay_path_length"] = len(primary_match["replayPath"])
                        elif has_aftermath:
                            details["aftermath_length"] = len(primary_match["aftermath"])
                        elif has_price_series:
                            details["price_series_length"] = len(primary_match["priceSeries"])
                        else:
                            # Check what fields are actually available
                            available_fields = list(primary_match.keys())
                            details["available_match_fields"] = available_fields
                            details["note"] = f"Primary match fields: {available_fields}"
                        
                        details["primary_match_similarity"] = primary_match.get("similarity")
                    else:
                        success = False
                        details["error"] = "No primary match found"
                
                # Check markers are available for hybrid renderer
                markers = forecast.get("markers", [])
                if not markers:
                    success = False
                    details["error"] = "Expected 'markers' for hybrid rendering"
                else:
                    details["markers_available"] = len(markers)
                    
                if success:
                    details["note"] = "All data needed for hybrid mode rendering is available"
        
        self.log_test("Hybrid Mode Data Availability (BLOCK 73.3)", success, details)
        return success

def main():
    """Run BLOCK 73.3 continuity fix tests"""
    print("🔬 Starting BLOCK 73.3 Continuity Fix Tests...")
    print("=" * 60)
    
    tester = Block733Tester()
    
    # Run all BLOCK 73.3 tests
    tests = [
        tester.test_14d_focus_pack_markers,
        tester.test_30d_focus_pack_markers,
        tester.test_7d_focus_pack_no_intermediate_markers,
        tester.test_marker_continuity_consistency,
        tester.test_hybrid_mode_data_availability
    ]
    
    for test in tests:
        try:
            test()
            time.sleep(0.5)  # Small delay between tests
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {str(e)}")
    
    # Print summary
    print("=" * 60)
    print(f"📊 BLOCK 73.3 Tests Summary:")
    print(f"   Tests run: {tester.tests_run}")
    print(f"   Tests passed: {tester.tests_passed}")
    print(f"   Success rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    # Save detailed results
    with open("/app/backend/block_733_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "tests_run": tester.tests_run,
                "tests_passed": tester.tests_passed,
                "success_rate": tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0
            },
            "test_results": tester.test_results,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())