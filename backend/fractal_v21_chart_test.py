#!/usr/bin/env python3
"""
Fractal v2.1 Chart & Overlay API Testing Suite
Tests the specific endpoints required for the Canvas Engine v1 implementation
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class FractalV21Tester:
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
        if "response_data" in details and not success:
            print(f"    Response: {json.dumps(details['response_data'], indent=2)}")
        print()

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None, timeout: int = 30) -> tuple[bool, Dict[str, Any]]:
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

    def test_fractal_chart_api(self):
        """Test GET /api/fractal/v2.1/chart?symbol=BTC&limit=365"""
        params = {"symbol": "BTC", "limit": 365}
        success, details = self.make_request("GET", "/api/fractal/v2.1/chart", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Check required fields for chart data
            required_fields = ["candles", "sma200", "phaseZones"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing required fields: {missing_fields}"
            else:
                # Validate candles structure
                candles = data.get("candles", [])
                if not isinstance(candles, list) or len(candles) == 0:
                    success = False
                    details["error"] = "Expected non-empty candles array"
                else:
                    # Check first candle structure
                    first_candle = candles[0]
                    candle_fields = ["t", "o", "h", "l", "c"]
                    missing_candle_fields = [field for field in candle_fields if field not in first_candle]
                    if missing_candle_fields:
                        success = False
                        details["error"] = f"Missing candle fields: {missing_candle_fields}"
                    else:
                        details["candles_count"] = len(candles)
                
                # Validate sma200 structure
                if success:
                    sma200 = data.get("sma200", [])
                    if not isinstance(sma200, list):
                        success = False
                        details["error"] = "Expected sma200 to be an array"
                    elif len(sma200) > 0:
                        first_sma = sma200[0]
                        sma_fields = ["t", "value"]
                        missing_sma_fields = [field for field in sma_fields if field not in first_sma]
                        if missing_sma_fields:
                            success = False
                            details["error"] = f"Missing SMA200 fields: {missing_sma_fields}"
                        else:
                            details["sma200_count"] = len(sma200)
                
                # Validate phaseZones structure
                if success:
                    phase_zones = data.get("phaseZones", [])
                    if not isinstance(phase_zones, list):
                        success = False
                        details["error"] = "Expected phaseZones to be an array"
                    elif len(phase_zones) > 0:
                        first_phase = phase_zones[0]
                        phase_fields = ["from", "to", "phase"]
                        missing_phase_fields = [field for field in phase_fields if field not in first_phase]
                        if missing_phase_fields:
                            success = False
                            details["error"] = f"Missing phase zone fields: {missing_phase_fields}"
                        else:
                            details["phase_zones_count"] = len(phase_zones)
        
        self.log_test("Fractal Chart API (v2.1) - BTC 365 days", success, details)
        return success

    def test_fractal_overlay_api(self):
        """Test GET /api/fractal/v2.1/overlay?symbol=BTC&windowLen=60&topK=10&aftermathDays=30"""
        params = {
            "symbol": "BTC",
            "windowLen": 60,
            "topK": 10,
            "aftermathDays": 30
        }
        success, details = self.make_request("GET", "/api/fractal/v2.1/overlay", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Check required fields for overlay data
            required_fields = ["currentWindow", "matches", "distribution"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing required fields: {missing_fields}"
            else:
                # Validate currentWindow structure
                current_window = data.get("currentWindow", {})
                if not isinstance(current_window, dict):
                    success = False
                    details["error"] = "Expected currentWindow to be an object"
                elif "normalized" not in current_window:
                    success = False
                    details["error"] = "Missing normalized field in currentWindow"
                else:
                    normalized = current_window.get("normalized", [])
                    if not isinstance(normalized, list) or len(normalized) == 0:
                        success = False
                        details["error"] = "Expected non-empty normalized array in currentWindow"
                    else:
                        details["current_window_length"] = len(normalized)
                
                # Validate matches structure
                if success:
                    matches = data.get("matches", [])
                    if not isinstance(matches, list):
                        success = False
                        details["error"] = "Expected matches to be an array"
                    elif len(matches) == 0:
                        success = False
                        details["error"] = "Expected non-empty matches array"
                    else:
                        # Check first match structure
                        first_match = matches[0]
                        match_fields = ["id", "similarity", "phase", "windowNormalized", "aftermathNormalized"]
                        missing_match_fields = [field for field in match_fields if field not in first_match]
                        if missing_match_fields:
                            success = False
                            details["error"] = f"Missing match fields: {missing_match_fields}"
                        else:
                            details["matches_count"] = len(matches)
                            details["first_match_similarity"] = first_match.get("similarity")
                            details["first_match_phase"] = first_match.get("phase")
                
                # Validate distribution structure
                if success:
                    distribution = data.get("distribution")
                    if distribution is not None:
                        if not isinstance(distribution, dict):
                            success = False
                            details["error"] = "Expected distribution to be an object"
                        else:
                            dist_fields = ["p10", "p90"]
                            missing_dist_fields = [field for field in dist_fields if field not in distribution]
                            if missing_dist_fields:
                                success = False
                                details["error"] = f"Missing distribution fields: {missing_dist_fields}"
                            else:
                                p10 = distribution.get("p10", [])
                                p90 = distribution.get("p90", [])
                                if not isinstance(p10, list) or not isinstance(p90, list):
                                    success = False
                                    details["error"] = "Expected p10 and p90 to be arrays"
                                else:
                                    details["distribution_p10_length"] = len(p10)
                                    details["distribution_p90_length"] = len(p90)
        
        self.log_test("Fractal Overlay API (v2.1) - BTC window=60", success, details)
        return success

    def test_fractal_signal_api(self):
        """Test GET /api/fractal/v2.1/signal?symbol=BTC (for forecast data)"""
        params = {"symbol": "BTC"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/signal", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Signal API might have different structure, check for basic fields
            if not isinstance(data, dict):
                success = False
                details["error"] = "Expected JSON object response"
            else:
                # Check for confidence field
                if "confidence" in data:
                    details["confidence"] = data.get("confidence")
                
                # Check for signalsByHorizon field (for forecast)
                if "signalsByHorizon" in data:
                    signals_by_horizon = data.get("signalsByHorizon", {})
                    if isinstance(signals_by_horizon, dict):
                        horizons = list(signals_by_horizon.keys())
                        details["available_horizons"] = horizons
                        
                        # Check for 7, 14, 30 day horizons
                        expected_horizons = ["7", "14", "30"]
                        found_horizons = [h for h in expected_horizons if h in signals_by_horizon]
                        details["forecast_horizons"] = found_horizons
                
                details["signal_fields"] = list(data.keys())
        
        self.log_test("Fractal Signal API (v2.1) - BTC forecast", success, details)
        return success

    def run_all_tests(self):
        """Run all fractal v2.1 tests"""
        print("🧪 Starting Fractal v2.1 Chart & Overlay API Tests")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test chart API
        self.test_fractal_chart_api()
        
        # Test overlay API  
        self.test_fractal_overlay_api()
        
        # Test signal API (for forecast)
        self.test_fractal_signal_api()
        
        # Print summary
        print("=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("❌ Some tests failed")
            return 1

def main():
    tester = FractalV21Tester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())