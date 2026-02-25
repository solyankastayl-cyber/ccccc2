#!/usr/bin/env python3
"""
BLOCK 59.2 Decision Kernel Testing Suite
Tests P1.1 (Consensus Index), P1.2 (Conflict Policy), P1.3 (Sizing Policy)
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class DecisionKernelTester:
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
        if success and "note" in details:
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

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        success, details = self.make_request("GET", "/api/health")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Expected 'ok': true"
            else:
                details["note"] = f"Health status: {data.get('status', 'unknown')}"
        
        self.log_test("API Health Check (/api/health)", success, details)
        return success

    def test_decision_kernel_structure(self):
        """Test /api/fractal/v2.1/terminal decisionKernel structure - BLOCK 59.2"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params, timeout=90)
        
        if success:
            data = details.get("response_data", {})
            decision_kernel = data.get("decisionKernel")
            
            if not decision_kernel:
                success = False
                details["error"] = "Missing 'decisionKernel' in response"
            else:
                # Test P1.1: Consensus structure
                consensus = decision_kernel.get("consensus", {})
                required_consensus_fields = ["score", "dir", "dispersion", "multiplier", "weights", "votes"]
                missing_consensus = [f for f in required_consensus_fields if f not in consensus]
                
                if missing_consensus:
                    success = False
                    details["error"] = f"Missing consensus fields: {missing_consensus}"
                else:
                    # Validate weights structure
                    weights = consensus.get("weights", {})
                    required_weights = ["buy", "sell", "hold"]
                    missing_weights = [w for w in required_weights if w not in weights]
                    
                    if missing_weights:
                        success = False
                        details["error"] = f"Missing consensus weights: {missing_weights}"
                    else:
                        # Validate votes structure
                        votes = consensus.get("votes", [])
                        if not votes:
                            success = False
                            details["error"] = "Expected consensus votes array"
                        else:
                            vote = votes[0]
                            required_vote_fields = ["horizon", "tier", "direction", "rawConfidence", "effectiveWeight", "penalties", "contribution"]
                            missing_vote_fields = [f for f in required_vote_fields if f not in vote]
                            
                            if missing_vote_fields:
                                success = False
                                details["error"] = f"Missing vote fields: {missing_vote_fields}"
                            else:
                                details["note"] = f"P1.1 Consensus: score={consensus['score']:.3f}, dir={consensus['dir']}, votes={len(votes)}"
        
        self.log_test("BLOCK 59.2 P1.1: Consensus Index Structure", success, details)
        return success

    def test_conflict_policy_structure(self):
        """Test BLOCK 59.2 P1.2: Conflict Policy structure"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params, timeout=90)
        
        if success:
            data = details.get("response_data", {})
            decision_kernel = data.get("decisionKernel", {})
            conflict = decision_kernel.get("conflict", {})
            
            if not conflict:
                success = False
                details["error"] = "Missing 'conflict' in decisionKernel"
            else:
                # Validate conflict structure
                required_conflict_fields = ["level", "mode", "sizingPenalty", "sizingMultiplier", 
                                          "structureVsTiming", "tiers", "explain", "recommendation"]
                missing_conflict = [f for f in required_conflict_fields if f not in conflict]
                
                if missing_conflict:
                    success = False
                    details["error"] = f"Missing conflict fields: {missing_conflict}"
                else:
                    # Validate structureVsTiming
                    structure_vs_timing = conflict.get("structureVsTiming", {})
                    required_svt_fields = ["aligned", "structureDir", "timingDir", "divergenceScore"]
                    missing_svt = [f for f in required_svt_fields if f not in structure_vs_timing]
                    
                    if missing_svt:
                        success = False
                        details["error"] = f"Missing structureVsTiming fields: {missing_svt}"
                    else:
                        # Validate tiers structure
                        tiers = conflict.get("tiers", {})
                        required_tier_names = ["structure", "tactical", "timing"]
                        missing_tiers = [t for t in required_tier_names if t not in tiers]
                        
                        if missing_tiers:
                            success = False
                            details["error"] = f"Missing tier analysis: {missing_tiers}"
                        else:
                            # Validate each tier has required fields
                            for tier_name in required_tier_names:
                                tier = tiers[tier_name]
                                required_tier_fields = ["dir", "strength"]
                                missing_tier_fields = [f for f in required_tier_fields if f not in tier]
                                
                                if missing_tier_fields:
                                    success = False
                                    details["error"] = f"Missing {tier_name} tier fields: {missing_tier_fields}"
                                    break
                            
                            if success:
                                details["note"] = f"P1.2 Conflict: level={conflict['level']}, mode={conflict['mode']}, aligned={structure_vs_timing['aligned']}"
        
        self.log_test("BLOCK 59.2 P1.2: Conflict Policy Structure", success, details)
        return success

    def test_sizing_policy_structure(self):
        """Test BLOCK 59.2 P1.3: Sizing Policy structure"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params, timeout=90)
        
        if success:
            data = details.get("response_data", {})
            decision_kernel = data.get("decisionKernel", {})
            sizing = decision_kernel.get("sizing", {})
            
            if not sizing:
                success = False
                details["error"] = "Missing 'sizing' in decisionKernel"
            else:
                # Validate sizing structure
                required_sizing_fields = ["mode", "preset", "baseSize", "consensusMultiplier", 
                                        "conflictMultiplier", "riskMultiplier", "finalSize", 
                                        "sizeLabel", "blockers", "explain"]
                missing_sizing = [f for f in required_sizing_fields if f not in sizing]
                
                if missing_sizing:
                    success = False
                    details["error"] = f"Missing sizing fields: {missing_sizing}"
                else:
                    # Validate sizing values are reasonable
                    base_size = sizing.get("baseSize", 0)
                    final_size = sizing.get("finalSize", 0)
                    consensus_mult = sizing.get("consensusMultiplier", 0)
                    conflict_mult = sizing.get("conflictMultiplier", 0)
                    risk_mult = sizing.get("riskMultiplier", 0)
                    
                    if not (0 <= base_size <= 1):
                        success = False
                        details["error"] = f"baseSize {base_size} not in [0,1] range"
                    elif not (0 <= final_size <= 1):
                        success = False
                        details["error"] = f"finalSize {final_size} not in [0,1] range"
                    elif not (0 <= consensus_mult <= 1):
                        success = False
                        details["error"] = f"consensusMultiplier {consensus_mult} not in [0,1] range"
                    elif not (0 <= conflict_mult <= 1):
                        success = False
                        details["error"] = f"conflictMultiplier {conflict_mult} not in [0,1] range"
                    elif not (0 <= risk_mult <= 1):
                        success = False
                        details["error"] = f"riskMultiplier {risk_mult} not in [0,1] range"
                    else:
                        # Validate mode is valid
                        valid_modes = ["TREND_FOLLOW", "COUNTER_TREND", "NO_TRADE"]
                        mode = sizing.get("mode")
                        if mode not in valid_modes:
                            success = False
                            details["error"] = f"Invalid sizing mode '{mode}', expected one of {valid_modes}"
                        else:
                            # Validate preset is valid
                            valid_presets = ["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]
                            preset = sizing.get("preset")
                            if preset not in valid_presets:
                                success = False
                                details["error"] = f"Invalid preset '{preset}', expected one of {valid_presets}"
                            else:
                                details["note"] = f"P1.3 Sizing: mode={mode}, preset={preset}, finalSize={final_size:.3f}, sizeLabel={sizing.get('sizeLabel')}"
        
        self.log_test("BLOCK 59.2 P1.3: Sizing Policy Structure", success, details)
        return success

    def test_decision_kernel_values(self):
        """Test BLOCK 59.2: Decision Kernel value consistency"""
        params = {"symbol": "BTC", "set": "extended", "focus": "30d"}
        success, details = self.make_request("GET", "/api/fractal/v2.1/terminal", params=params, timeout=90)
        
        if success:
            data = details.get("response_data", {})
            decision_kernel = data.get("decisionKernel", {})
            
            consensus = decision_kernel.get("consensus", {})
            conflict = decision_kernel.get("conflict", {})
            sizing = decision_kernel.get("sizing", {})
            
            if not (consensus and conflict and sizing):
                success = False
                details["error"] = "Missing decisionKernel components"
            else:
                # Check consensus score vs dispersion consistency
                score = consensus.get("score", 0)
                dispersion = consensus.get("dispersion", 0)
                expected_dispersion = 1 - score
                
                if abs(dispersion - expected_dispersion) > 0.001:
                    success = False
                    details["error"] = f"Consensus dispersion inconsistent: {dispersion} != 1 - {score}"
                else:
                    # Check sizing multiplier consistency
                    consensus_mult = sizing.get("consensusMultiplier", 0)
                    conflict_mult = sizing.get("conflictMultiplier", 0)
                    risk_mult = sizing.get("riskMultiplier", 0)
                    base_size = sizing.get("baseSize", 0)
                    final_size = sizing.get("finalSize", 0)
                    
                    expected_final = base_size * consensus_mult * conflict_mult * risk_mult
                    
                    if abs(final_size - expected_final) > 0.001:
                        success = False
                        details["error"] = f"Sizing calculation inconsistent: {final_size} != {base_size} * {consensus_mult} * {conflict_mult} * {risk_mult}"
                    else:
                        # Check conflict level vs sizing penalty consistency
                        conflict_level = conflict.get("level", "NONE")
                        sizing_penalty = conflict.get("sizingPenalty", 0)
                        
                        # Expected penalties by level
                        expected_penalties = {
                            "NONE": 0,
                            "MINOR": 0.10,
                            "MODERATE": 0.25,
                            "MAJOR": 0.50,
                            "SEVERE": 0.75
                        }
                        
                        expected_penalty = expected_penalties.get(conflict_level, 0)
                        if abs(sizing_penalty - expected_penalty) > 0.01:
                            success = False
                            details["error"] = f"Conflict penalty inconsistent: level={conflict_level} has penalty={sizing_penalty}, expected ~{expected_penalty}"
                        else:
                            details["note"] = f"Value consistency OK: consensus={score:.3f}, conflict={conflict_level}, finalSize={final_size:.3f}"
        
        self.log_test("BLOCK 59.2: Decision Kernel Value Consistency", success, details)
        return success

    def test_mongodb_connection(self):
        """Test MongoDB connection via fractal health endpoint"""
        success, details = self.make_request("GET", "/api/fractal/health")
        
        if success:
            data = details.get("response_data", {})
            if not data.get("ok"):
                success = False
                details["error"] = "Fractal health check failed"
            elif not data.get("enabled"):
                success = False
                details["error"] = "Fractal module not enabled"
            else:
                details["note"] = f"MongoDB connection via fractal: {data.get('status', 'unknown')}"
        
        self.log_test("MongoDB Connection Test", success, details)
        return success

def main():
    print("🧪 BLOCK 59.2 Decision Kernel Testing Suite")
    print("=" * 50)
    
    tester = DecisionKernelTester()
    
    # Test sequence
    tests = [
        tester.test_health_endpoint,
        tester.test_mongodb_connection,
        tester.test_decision_kernel_structure,
        tester.test_conflict_policy_structure,
        tester.test_sizing_policy_structure,
        tester.test_decision_kernel_values,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {str(e)}")
            tester.tests_run += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All Decision Kernel tests PASSED!")
        return 0
    else:
        print("⚠️  Some tests FAILED - see details above")
        return 1

if __name__ == "__main__":
    sys.exit(main())