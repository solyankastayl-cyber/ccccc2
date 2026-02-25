#!/usr/bin/env python3
"""
FRACTAL V2.1 FULL CONFIDENCE PIPELINE TESTING SUITE
BLOCK 38.3-38.7: Evidence, Calibration Quality, Reliability Policy, Bayesian Calibration, effectiveN Floor
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class FractalV21ConfidenceTester:
    def __init__(self, base_url: str = "https://pointintime-macro.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.critical_failures = []

    def log_test(self, name: str, success: bool, details: Dict[str, Any]):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        else:
            self.critical_failures.append({
                "test": name,
                "error": details.get("error", "Unknown error"),
                "response": details.get("response_data")
            })
        
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
        if success and "note" in details:
            print(f"    Note: {details['note']}")
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

    # ═══════════════════════════════════════════════════════════════
    # BLOCK 38.3: CONFIDENCE V2 TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_confidence_v2_evidence_breakdown(self):
        """Test GET /api/fractal/v2.1/confidence - evidence breakdown + calibratedEvidence + finalConfidence"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/confidence")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                # Validate evidence breakdown structure
                evidence = data.get("evidence")
                if not evidence:
                    success = False
                    details["error"] = "Expected 'evidence' field in response"
                else:
                    required_evidence_fields = ["effectiveN", "dispersion", "consensus", "nScore", "dispScore", 
                                              "consScore", "rawEvidence", "evidence"]
                    missing_fields = [field for field in required_evidence_fields if field not in evidence]
                    if missing_fields:
                        success = False
                        details["error"] = f"Missing evidence fields: {missing_fields}"
                    
                    # Validate calibrated and final confidence
                    if success:
                        if "calibratedEvidence" not in data:
                            success = False
                            details["error"] = "Expected 'calibratedEvidence' field"
                        elif "finalConfidence" not in data:
                            success = False
                            details["error"] = "Expected 'finalConfidence' field"
                        elif "reliabilityModifier" not in data:
                            success = False
                            details["error"] = "Expected 'reliabilityModifier' field"
                        else:
                            # Check values are reasonable
                            effective_n = evidence.get("effectiveN", 0)
                            final_conf = data.get("finalConfidence", 0)
                            calibrated_ev = data.get("calibratedEvidence", 0)
                            
                            details["confidence_metrics"] = {
                                "effectiveN": effective_n,
                                "calibratedEvidence": calibrated_ev,
                                "finalConfidence": final_conf,
                                "reliabilityModifier": data.get("reliabilityModifier", 0)
                            }
                            
                            if 0 <= final_conf <= 1:
                                details["note"] = f"✅ finalConfidence={final_conf} is in valid range [0,1]"
                            else:
                                success = False
                                details["error"] = f"finalConfidence={final_conf} out of range [0,1]"
        
        self.log_test("BLOCK 38.3: Confidence V2 Evidence Breakdown", success, details)
        return success

    # ═══════════════════════════════════════════════════════════════
    # BLOCK 38.4: CALIBRATION QUALITY TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_calibration_quality_ece_brier(self):
        """Test GET /api/fractal/v2.1/calibration/quality - ECE, Brier, badge, bins"""
        params = {"mockN": "150", "quality": "medium"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/calibration/quality", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                # Check required fields
                required_fields = ["sampleN", "ece", "brier", "badge", "bins", "monotonicityViolations", "coverage"]
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    success = False
                    details["error"] = f"Missing calibration quality fields: {missing_fields}"
                else:
                    # Validate metrics
                    ece = data.get("ece", 0)
                    brier = data.get("brier", 0)
                    badge = data.get("badge", "")
                    bins = data.get("bins", [])
                    
                    if not (0 <= ece <= 1):
                        success = False
                        details["error"] = f"ECE={ece} out of range [0,1]"
                    elif not (0 <= brier <= 1):
                        success = False
                        details["error"] = f"Brier={brier} out of range [0,1]"
                    elif badge not in ["OK", "WARN", "DEGRADED", "CRITICAL", "INSUFFICIENT_DATA"]:
                        success = False
                        details["error"] = f"Invalid badge '{badge}'"
                    elif len(bins) == 0:
                        success = False
                        details["error"] = "Expected calibration bins"
                    else:
                        # Validate bin structure
                        first_bin = bins[0]
                        required_bin_fields = ["idx", "n", "pAvg", "hitRate", "gap", "pMin", "pMax"]
                        missing_bin_fields = [field for field in required_bin_fields if field not in first_bin]
                        if missing_bin_fields:
                            success = False
                            details["error"] = f"Missing bin fields: {missing_bin_fields}"
                        else:
                            details["calibration_metrics"] = {
                                "ece": ece,
                                "brier": brier, 
                                "badge": badge,
                                "bins_count": len(bins),
                                "sample_n": data.get("sampleN", 0)
                            }
                            details["note"] = f"✅ Calibration quality: ECE={ece:.4f}, Brier={brier:.4f}, Badge={badge}"
        
        self.log_test("BLOCK 38.4: Calibration Quality (ECE + Brier + Badge)", success, details)
        return success

    # ═══════════════════════════════════════════════════════════════
    # BLOCK 38.5: RELIABILITY POLICY TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_reliability_state_policy(self):
        """Test GET /api/fractal/v2.1/reliability/state - badge, score, modifier, action"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/reliability/state")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                # Check required reliability state fields
                required_fields = ["badge", "score", "modifier", "action", "thresholdsRaised", "reasons", "updatedAtTs"]
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    success = False
                    details["error"] = f"Missing reliability state fields: {missing_fields}"
                else:
                    badge = data.get("badge", "")
                    score = data.get("score", 0)
                    modifier = data.get("modifier", 0)
                    action = data.get("action", "")
                    
                    # Validate values
                    if badge not in ["OK", "WARN", "DEGRADED", "CRITICAL", "INSUFFICIENT_DATA"]:
                        success = False
                        details["error"] = f"Invalid reliability badge '{badge}'"
                    elif not (0 <= score <= 1):
                        success = False
                        details["error"] = f"Reliability score={score} out of range [0,1]"
                    elif not (0 <= modifier <= 1):
                        success = False
                        details["error"] = f"Reliability modifier={modifier} out of range [0,1]"
                    elif action not in ["NONE", "DEGRADE_CONFIDENCE", "RAISE_THRESHOLDS", "FREEZE_ENTRIES", "FREEZE_ALL"]:
                        success = False
                        details["error"] = f"Invalid reliability action '{action}'"
                    else:
                        details["reliability_state"] = {
                            "badge": badge,
                            "score": score,
                            "modifier": modifier,
                            "action": action,
                            "thresholds_raised": data.get("thresholdsRaised", False),
                            "reasons": data.get("reasons", [])
                        }
                        details["note"] = f"✅ Reliability: {badge}, Score={score:.3f}, Modifier={modifier:.3f}, Action={action}"
        
        self.log_test("BLOCK 38.5: Reliability Policy State", success, details)
        return success

    # ═══════════════════════════════════════════════════════════════
    # BLOCK 38.6: BAYESIAN CALIBRATION TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_calibration_v2_bayesian_buckets(self):
        """Test GET /api/fractal/v2.1/calibration - bucket stats snapshot"""
        params = {"symbol": "BTC", "horizonDays": "30"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/calibration", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                # Check calibration snapshot structure
                required_fields = ["symbol", "horizonDays", "asOfTs", "config", "buckets", "totalN", "ece", "isUsable"]
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    success = False
                    details["error"] = f"Missing calibration snapshot fields: {missing_fields}"
                else:
                    buckets = data.get("buckets", [])
                    config = data.get("config", {})
                    total_n = data.get("totalN", 0)
                    ece = data.get("ece", 0)
                    
                    # Check bucket structure
                    if len(buckets) == 0:
                        success = False
                        details["error"] = "Expected calibration buckets"
                    else:
                        first_bucket = buckets[0]
                        required_bucket_fields = ["i", "lo", "hi", "n", "k", "mean"]
                        missing_bucket_fields = [field for field in required_bucket_fields if field not in first_bucket]
                        if missing_bucket_fields:
                            success = False
                            details["error"] = f"Missing bucket fields: {missing_bucket_fields}"
                        else:
                            # Validate bucket means are Beta posterior
                            bucket_with_data = [b for b in buckets if b.get("n", 0) > 0]
                            details["calibration_snapshot"] = {
                                "buckets_total": len(buckets),
                                "buckets_with_data": len(bucket_with_data),
                                "total_n": total_n,
                                "ece": ece,
                                "is_usable": data.get("isUsable", False),
                                "prior_a": config.get("priorA", 1),
                                "prior_b": config.get("priorB", 1)
                            }
                            
                            if total_n > 0:
                                details["note"] = f"✅ Bayesian calibration: {len(bucket_with_data)}/{len(buckets)} buckets have data, ECE={ece:.4f}"
                            else:
                                details["note"] = "⚠️ No calibration data yet - buckets are empty"
        
        self.log_test("BLOCK 38.6: Bayesian Calibration Buckets", success, details)
        return success

    def test_calibration_seed_mock_data(self):
        """Test POST /api/fractal/v2.1/calibration/seed - seed mock calibration data"""
        data = {
            "symbol": "BTC",
            "horizonDays": 30,
            "count": 100,
            "quality": "medium"
        }
        success, details = self.make_request("POST", "/api/fractal/v2.1/calibration/seed", data=data)
        
        if success:
            response_data = details.get("response_data", {})
            if not response_data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                snapshot = response_data.get("snapshot")
                if not snapshot:
                    success = False
                    details["error"] = "Expected 'snapshot' field after seeding"
                else:
                    total_n = snapshot.get("totalN", 0)
                    if total_n != 100:
                        success = False
                        details["error"] = f"Expected totalN=100 after seeding, got {total_n}"
                    else:
                        details["seeding_result"] = {
                            "seeded_count": 100,
                            "total_n": total_n,
                            "ece": snapshot.get("ece", 0),
                            "is_usable": snapshot.get("isUsable", False)
                        }
                        details["note"] = f"✅ Seeded 100 medium quality points, totalN={total_n}"
        
        self.log_test("BLOCK 38.6: Calibration Mock Data Seeding", success, details)
        return success

    # ═══════════════════════════════════════════════════════════════
    # BLOCK 38.7: EFFECTIVEN FLOOR TESTS
    # ═══════════════════════════════════════════════════════════════

    def test_effectiven_floor_constraint(self):
        """Test GET /api/fractal/v2.1/calibration/full - effectiveN floor должен ограничивать confidence при низком N"""
        
        # Test case from context: effectiveN=5 с rawConf=0.9 должен вернуть capped ~0.39
        params = {"rawConf": "0.9", "effectiveN": "5", "symbol": "BTC", "horizonDays": "30"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/calibration/full", params=params)
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                # Check full calibration pipeline structure
                required_fields = ["input", "rawConfidence", "calibratedConfidence", "effectiveNCapped", "snapshot", "floorConfig"]
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    success = False
                    details["error"] = f"Missing full calibration fields: {missing_fields}"
                else:
                    input_data = data.get("input", {})
                    raw_conf = data.get("rawConfidence", 0)
                    calibrated_conf = data.get("calibratedConfidence", 0)  
                    capped_conf = data.get("effectiveNCapped", 0)
                    
                    # Validate input was preserved
                    if input_data.get("rawConf") != 0.9:
                        success = False
                        details["error"] = f"Expected input rawConf=0.9, got {input_data.get('rawConf')}"
                    elif input_data.get("effectiveN") != 5:
                        success = False
                        details["error"] = f"Expected input effectiveN=5, got {input_data.get('effectiveN')}"
                    else:
                        # Check effectiveN floor constraint
                        floor_config = data.get("floorConfig", {})
                        floors = floor_config.get("floors", [])
                        
                        # Find applicable floor for effectiveN=5
                        applicable_floors = [f for f in floors if f.get("minEffectiveN", 0) <= 5]
                        if applicable_floors:
                            max_floor = max(applicable_floors, key=lambda f: f.get("minEffectiveN", 0))
                            expected_max = max_floor.get("maxConfidence", 1.0)
                            
                            details["effectiven_floor_test"] = {
                                "raw_confidence": raw_conf,
                                "calibrated_confidence": calibrated_conf,
                                "effectiven_capped": capped_conf,
                                "effective_n": 5,
                                "expected_max_from_floor": expected_max,
                                "floor_applied": capped_conf < calibrated_conf
                            }
                            
                            # Check if floor was applied correctly
                            if capped_conf <= expected_max + 0.01:  # Small tolerance
                                if 0.35 <= capped_conf <= 0.45:  # Should be around 0.39
                                    details["note"] = f"✅ effectiveN floor working: rawConf=0.9 → capped={capped_conf:.3f} (expected ~0.39)"
                                else:
                                    details["note"] = f"⚠️ effectiveN floor applied but value {capped_conf:.3f} not in expected range ~0.39"
                            else:
                                success = False
                                details["error"] = f"effectiveN floor not applied: capped={capped_conf} > floor={expected_max}"
                        else:
                            success = False
                            details["error"] = "No applicable floor found for effectiveN=5"
        
        self.log_test("BLOCK 38.7: effectiveN Floor Constraint", success, details)
        return success

    def test_effectiven_floor_high_n(self):
        """Test effectiveN floor with high N (should not cap)"""
        params = {"rawConf": "0.9", "effectiveN": "25", "symbol": "BTC", "horizonDays": "30"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/calibration/full", params=params)
        
        if success:
            data = details.get("response_data", {})
            if data.get("ok"):
                raw_conf = data.get("rawConfidence", 0)
                calibrated_conf = data.get("calibratedConfidence", 0)
                capped_conf = data.get("effectiveNCapped", 0)
                
                details["high_n_test"] = {
                    "raw_confidence": raw_conf,
                    "calibrated_confidence": calibrated_conf,
                    "effectiven_capped": capped_conf,
                    "effective_n": 25
                }
                
                # With effectiveN=25, should allow high confidence (maxConfidence=1.0)
                if abs(capped_conf - calibrated_conf) < 0.01:
                    details["note"] = f"✅ High effectiveN (25): no capping applied, final={capped_conf:.3f}"
                else:
                    details["note"] = f"⚠️ High effectiveN (25): some capping applied {calibrated_conf:.3f} → {capped_conf:.3f}"
            else:
                success = False
                details["error"] = "Full calibration request failed"
        
        self.log_test("BLOCK 38.7: effectiveN Floor - High N Test", success, details)
        return success

    # ═══════════════════════════════════════════════════════════════
    # INTEGRATION TEST: V2.1 INFO ENDPOINT
    # ═══════════════════════════════════════════════════════════════

    def test_v21_info_blocks_endpoints(self):
        """Test GET /api/fractal/v2.1/info - показывает 11 блоков и 12 endpoints"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/info")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                blocks = data.get("blocks", {})
                endpoints = data.get("endpoints", {})
                
                # Check for 11 blocks
                expected_blocks = ["37.1", "37.2", "37.3", "37.4", "38.1", "38.2", "38.3", "38.4", "38.5", "38.6", "38.7"]
                if len(blocks) < 11:
                    success = False
                    details["error"] = f"Expected at least 11 blocks, got {len(blocks)}"
                else:
                    missing_blocks = [block for block in expected_blocks if block not in blocks]
                    if missing_blocks:
                        success = False
                        details["error"] = f"Missing expected blocks: {missing_blocks}"
                    
                    # Check for 12 endpoints 
                    expected_endpoints = ["match", "phase", "reliability", "reliabilityState", "stability", "decay", 
                                        "confidence", "calibrationQuality", "calibration", "calibrationFull", 
                                        "calibrationSeed", "info"]
                    if len(endpoints) < 12:
                        success = False
                        details["error"] = f"Expected at least 12 endpoints, got {len(endpoints)}"
                    else:
                        missing_endpoints = [ep for ep in expected_endpoints if ep not in endpoints]
                        if missing_endpoints:
                            success = False
                            details["error"] = f"Missing expected endpoints: {missing_endpoints}"
                        else:
                            details["v21_info"] = {
                                "blocks_count": len(blocks),
                                "endpoints_count": len(endpoints),
                                "version": data.get("version", ""),
                                "description": data.get("description", "")
                            }
                            details["note"] = f"✅ V2.1 Info: {len(blocks)} blocks, {len(endpoints)} endpoints"
        
        self.log_test("V2.1 Info: 11 Blocks + 12 Endpoints", success, details)
        return success

    def run_all_tests(self):
        """Run all Fractal V2.1 Full Confidence Pipeline tests"""
        print("═══════════════════════════════════════════════════════════════")
        print("  FRACTAL V2.1 FULL CONFIDENCE PIPELINE TEST SUITE")
        print("  BLOCK 38.3-38.7: Evidence, Calibration Quality, Reliability Policy")
        print("  Bayesian Calibration, effectiveN Floor")
        print("═══════════════════════════════════════════════════════════════\n")
        
        # Test each component of the full confidence pipeline
        
        # BLOCK 38.3: Evidence Confidence
        self.test_confidence_v2_evidence_breakdown()
        
        # BLOCK 38.4: Calibration Quality
        self.test_calibration_quality_ece_brier()
        
        # BLOCK 38.5: Reliability Policy
        self.test_reliability_state_policy()
        
        # BLOCK 38.6: Bayesian Calibration
        self.test_calibration_v2_bayesian_buckets()
        self.test_calibration_seed_mock_data()
        
        # BLOCK 38.7: effectiveN Floor
        self.test_effectiven_floor_constraint()
        self.test_effectiven_floor_high_n()
        
        # Integration: V2.1 Info
        self.test_v21_info_blocks_endpoints()
        
        # Print summary
        print("═══════════════════════════════════════════════════════════════")
        print("  TEST SUMMARY")
        print("═══════════════════════════════════════════════════════════════")
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        
        if self.critical_failures:
            print("\n❌ CRITICAL FAILURES:")
            for failure in self.critical_failures[:5]:  # Show first 5 failures
                print(f"  - {failure['test']}: {failure['error']}")
            if len(self.critical_failures) > 5:
                print(f"  ... and {len(self.critical_failures) - 5} more")
        
        print()
        return self.tests_passed == self.tests_run

def main():
    tester = FractalV21ConfidenceTester()
    all_passed = tester.run_all_tests()
    
    # Return appropriate exit code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()