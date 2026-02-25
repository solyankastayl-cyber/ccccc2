#!/usr/bin/env python3
"""
BLOCK 73.8 Testing Suite - Phase Grade Integration
Tests phase grade integration with confidence adjustment for live trading.
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class Block738Tester:
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

    def test_backend_health(self):
        """Test GET /api/health - backend health check"""
        success, details = self.make_request("GET", "/api/health")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
        
        self.log_test("Backend Health Check (/api/health)", success, details)
        return success

    def test_terminal_phase_grade_data(self):
        """Test GET /api/fractal/v2.1/terminal - phase grade data in sizing"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Check if terminal response has decisionKernel.sizing
            if "decisionKernel" not in data:
                success = False
                details["error"] = "Expected 'decisionKernel' field in response"
            elif "sizing" not in data["decisionKernel"]:
                success = False
                details["error"] = "Expected 'sizing' field in decisionKernel"
            else:
                sizing = data["decisionKernel"]["sizing"]
                
                # Check for phase grade fields
                expected_phase_fields = ["phaseGrade", "phaseSampleQuality", "phaseScore"]
                missing_fields = []
                
                for field in expected_phase_fields:
                    if field not in sizing:
                        missing_fields.append(field)
                
                if missing_fields:
                    success = False
                    details["error"] = f"Missing phase grade fields in sizing: {missing_fields}"
                else:
                    # Store phase grade data for validation
                    phase_data = {
                        "phaseGrade": sizing.get("phaseGrade"),
                        "phaseSampleQuality": sizing.get("phaseSampleQuality"), 
                        "phaseScore": sizing.get("phaseScore")
                    }
                    details["phase_data"] = phase_data
                    
                    # Validate grade is A-F if present
                    grade = sizing.get("phaseGrade")
                    if grade and grade not in ["A", "B", "C", "D", "F"]:
                        success = False
                        details["error"] = f"Invalid phaseGrade '{grade}', expected A-F or null"
                    
                    # Validate sample quality if present
                    sample_quality = sizing.get("phaseSampleQuality")
                    valid_qualities = ["OK", "LOW_SAMPLE", "VERY_LOW_SAMPLE"]
                    if sample_quality and sample_quality not in valid_qualities:
                        success = False
                        details["error"] = f"Invalid phaseSampleQuality '{sample_quality}'"
                    
                    # Validate score is number if present
                    score = sizing.get("phaseScore")
                    if score is not None and not isinstance(score, (int, float)):
                        success = False
                        details["error"] = f"phaseScore should be number, got {type(score)}"
                    
                    if success:
                        details["note"] = f"Phase Grade: {grade}, Quality: {sample_quality}, Score: {score}"
        
        self.log_test("Terminal API Phase Grade Data", success, details)
        return success

    def test_terminal_confidence_adjustment(self):
        """Test GET /api/fractal/v2.1/terminal - confidence adjustment data"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            sizing = data.get("decisionKernel", {}).get("sizing", {})
            
            # Check for confidence adjustment
            if "confidenceAdjustment" not in sizing:
                success = False
                details["error"] = "Expected 'confidenceAdjustment' field in sizing"
            else:
                conf_adj = sizing["confidenceAdjustment"]
                
                # Check required confidence adjustment fields
                required_fields = ["basePp", "adjustmentPp", "finalPp", "reason"]
                missing_fields = [f for f in required_fields if f not in conf_adj]
                
                if missing_fields:
                    success = False
                    details["error"] = f"Missing confidenceAdjustment fields: {missing_fields}"
                else:
                    # Validate field types
                    for field in ["basePp", "adjustmentPp", "finalPp"]:
                        value = conf_adj.get(field)
                        if not isinstance(value, (int, float)):
                            success = False
                            details["error"] = f"confidenceAdjustment.{field} should be number, got {type(value)}"
                            break
                    
                    # Validate reason is string
                    reason = conf_adj.get("reason")
                    if not isinstance(reason, str):
                        success = False
                        details["error"] = f"confidenceAdjustment.reason should be string, got {type(reason)}"
                    
                    if success:
                        conf_data = {
                            "basePp": conf_adj.get("basePp"),
                            "adjustmentPp": conf_adj.get("adjustmentPp"),
                            "finalPp": conf_adj.get("finalPp"),
                            "reason": conf_adj.get("reason")
                        }
                        details["confidence_adjustment"] = conf_data
                        
                        # Check if adjustment is working
                        base_pp = conf_adj.get("basePp", 0)
                        adjustment_pp = conf_adj.get("adjustmentPp", 0)
                        final_pp = conf_adj.get("finalPp", 0)
                        
                        expected_final = base_pp + adjustment_pp
                        if abs(final_pp - expected_final) > 0.01:  # Allow small floating point errors
                            details["note"] = f"⚠️ finalPp ({final_pp}) != basePp ({base_pp}) + adjustmentPp ({adjustment_pp})"
                        else:
                            details["note"] = f"✅ Confidence adjustment working: {base_pp:.3f} + {adjustment_pp:.3f} = {final_pp:.3f} ({reason})"
        
        self.log_test("Terminal API Confidence Adjustment", success, details)
        return success

    def test_terminal_phase_breakdown(self):
        """Test GET /api/fractal/v2.1/terminal - PHASE factor in breakdown"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params)
        
        if success:
            data = details.get("response_data", {})
            sizing = data.get("decisionKernel", {}).get("sizing", {})
            
            # Check for breakdown field
            if "breakdown" not in sizing:
                success = False
                details["error"] = "Expected 'breakdown' field in sizing"
            else:
                breakdown = sizing["breakdown"]
                
                if not isinstance(breakdown, list):
                    success = False
                    details["error"] = "Expected breakdown to be an array"
                else:
                    # Look for PHASE factor in breakdown
                    phase_factor = None
                    for item in breakdown:
                        if item.get("factor") == "PHASE":
                            phase_factor = item
                            break
                    
                    if phase_factor is None:
                        success = False
                        details["error"] = "Expected PHASE factor in breakdown array"
                    else:
                        # Validate PHASE factor structure
                        required_fields = ["factor", "multiplier", "note", "severity"]
                        missing_fields = [f for f in required_fields if f not in phase_factor]
                        
                        if missing_fields:
                            success = False
                            details["error"] = f"Missing PHASE factor fields: {missing_fields}"
                        else:
                            details["phase_factor"] = {
                                "multiplier": phase_factor.get("multiplier"),
                                "note": phase_factor.get("note"),
                                "severity": phase_factor.get("severity")
                            }
                            
                            # Validate note contains grade information
                            note = phase_factor.get("note", "")
                            if "Grade" not in note:
                                success = False
                                details["error"] = f"Expected PHASE factor note to contain 'Grade', got: '{note}'"
                            else:
                                details["note"] = f"✅ PHASE factor found: {note} (×{phase_factor.get('multiplier', 1):.2f})"
        
        self.log_test("Terminal API Phase Breakdown Factor", success, details)
        return success

    def test_phase_performance_api(self):
        """Test GET /api/fractal/v2.1/admin/phase-performance - phase performance data"""
        params = {"symbol": "BTC", "tier": "TACTICAL"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/phase-performance", params=params)
        
        if success:
            data = details.get("response_data", {})
            
            # Check basic structure
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true in phase performance response"
            elif "meta" not in data:
                success = False
                details["error"] = "Expected 'meta' field in response"
            elif "phases" not in data:
                success = False
                details["error"] = "Expected 'phases' field in response"
            else:
                phases = data["phases"]
                
                if not isinstance(phases, list):
                    success = False
                    details["error"] = "Expected phases to be an array"
                else:
                    details["phases_count"] = len(phases)
                    
                    if len(phases) > 0:
                        # Validate first phase has required fields
                        first_phase = phases[0]
                        required_fields = ["grade", "score", "sampleQuality", "phaseType"]
                        missing_fields = [f for f in required_fields if f not in first_phase]
                        
                        if missing_fields:
                            success = False
                            details["error"] = f"Missing phase fields: {missing_fields}"
                        else:
                            # Validate grade
                            grade = first_phase.get("grade")
                            if grade not in ["A", "B", "C", "D", "F"]:
                                success = False
                                details["error"] = f"Invalid phase grade '{grade}'"
                            
                            # Validate sample quality
                            sample_quality = first_phase.get("sampleQuality")
                            valid_qualities = ["OK", "LOW_SAMPLE", "VERY_LOW_SAMPLE"]
                            if sample_quality not in valid_qualities:
                                success = False
                                details["error"] = f"Invalid sampleQuality '{sample_quality}'"
                            
                            if success:
                                phase_data = {
                                    "phase": first_phase.get("phaseType"),
                                    "grade": first_phase.get("grade"),
                                    "score": first_phase.get("score"),
                                    "sampleQuality": first_phase.get("sampleQuality"),
                                    "samples": first_phase.get("samples", 0)
                                }
                                details["first_phase"] = phase_data
                                details["note"] = f"✅ Found {len(phases)} phases, first: {phase_data['phase']} Grade {phase_data['grade']} (score {phase_data['score']:.0f})"
                    else:
                        # Empty phases is acceptable in fallback mode
                        details["note"] = "No phases returned (fallback mode or insufficient data)"
        
        self.log_test("Phase Performance Admin API", success, details)
        return success

    def run_all_tests(self):
        """Run all BLOCK 73.8 tests"""
        print("🔬 BLOCK 73.8 Testing Suite - Phase Grade Integration")
        print("=" * 60)
        print()
        
        # Test backend health first
        if not self.test_backend_health():
            print("❌ Backend health check failed - aborting tests")
            return False
        
        # Test terminal API phase grade features
        self.test_terminal_phase_grade_data()
        self.test_terminal_confidence_adjustment()  
        self.test_terminal_phase_breakdown()
        
        # Test phase performance admin API
        self.test_phase_performance_api()
        
        # Summary
        print()
        print("=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("✅ All BLOCK 73.8 tests passed!")
        else:
            print("❌ Some tests failed - see details above")
        
        return self.tests_passed == self.tests_run

    def save_results(self, filename: str = "block_738_test_results.json"):
        """Save test results to JSON file"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "block": "73.8",
            "description": "Phase Grade Integration with Confidence Adjustment",
            "summary": {
                "total_tests": self.tests_run,
                "passed_tests": self.tests_passed,
                "failed_tests": self.tests_run - self.tests_passed,
                "success_rate": f"{(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0%"
            },
            "test_results": self.test_results
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Test results saved to {filename}")

def main():
    tester = Block738Tester()
    success = tester.run_all_tests()
    tester.save_results()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())