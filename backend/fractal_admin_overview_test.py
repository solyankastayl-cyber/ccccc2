#!/usr/bin/env python3
"""
BLOCK 49 & 50 Testing - Fractal Admin Overview Endpoint & UI
Tests the admin aggregator endpoint and admin dashboard UI functionality
"""

import requests
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

class FractalAdminOverviewTester:
    def __init__(self, base_url="https://pointintime-macro.preview.emergentagent.com"):
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

    def test_admin_overview_endpoint(self):
        """Test GET /api/fractal/v2.1/admin/overview - BLOCK 49"""
        print(f"\n{'='*60}")
        print("🔍 BLOCK 49 - Admin Overview Endpoint")
        print(f"{'='*60}")
        
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params={"symbol": "BTC"})
        
        if success:
            data = details.get("response_data", {})
            
            # Check for all required sections in payload
            required_sections = ['meta', 'governance', 'health', 'guard', 'telemetry', 
                               'model', 'performance', 'recommendation', 'recent']
            missing_sections = [section for section in required_sections if section not in data]
            
            if missing_sections:
                success = False
                details["error"] = f"Missing required sections: {missing_sections}"
            else:
                # Validate meta section
                meta = data.get('meta', {})
                if not meta.get('symbol') or not meta.get('version') or not meta.get('asOf'):
                    success = False
                    details["error"] = "Invalid meta section structure"
                
                # Validate governance section
                governance = data.get('governance', {})
                if governance.get('mode') not in ['NORMAL', 'PROTECTION_MODE', 'FROZEN_ONLY']:
                    success = False
                    details["error"] = f"Invalid governance mode: {governance.get('mode')}"
                
                # Validate health section
                health = data.get('health', {})
                if health.get('state') not in ['HEALTHY', 'WATCH', 'ALERT', 'CRITICAL']:
                    success = False
                    details["error"] = f"Invalid health state: {health.get('state')}"
                
                # Validate guard section
                guard = data.get('guard', {})
                if not isinstance(guard.get('degenerationScore'), (int, float)):
                    success = False
                    details["error"] = "Invalid guard degenerationScore"
                
                # Validate performance section
                performance = data.get('performance', {})
                if not performance.get('windows'):
                    success = False
                    details["error"] = "Missing performance windows"
                
                if success:
                    details["note"] = f"Complete payload received with {len(required_sections)} sections"
                    details["governance_mode"] = governance.get('mode')
                    details["health_state"] = health.get('state')
                    details["degeneration_score"] = guard.get('degenerationScore')
        
        self.log_test("Admin Overview Endpoint Structure", success, details)
        return success, details.get("response_data", {})

    def test_admin_overview_performance_data(self):
        """Test performance windows data structure"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params={"symbol": "BTC"})
        
        if success:
            data = details.get("response_data", {})
            performance = data.get('performance', {})
            windows = performance.get('windows', {})
            
            # Check for 30d, 60d, 90d windows
            required_windows = ['d30', 'd60', 'd90']
            missing_windows = [w for w in required_windows if w not in windows]
            
            if missing_windows:
                success = False
                details["error"] = f"Missing performance windows: {missing_windows}"
            else:
                # Check each window has required metrics
                for window in required_windows:
                    window_data = windows[window]
                    required_metrics = ['sharpe', 'maxDD', 'hitRate']
                    missing_metrics = [m for m in required_metrics if m not in window_data]
                    
                    if missing_metrics:
                        success = False
                        details["error"] = f"Missing metrics in {window}: {missing_metrics}"
                        break
                
                if success:
                    details["note"] = f"All 3 performance windows with required metrics present"
                    details["window_data"] = {
                        "d30_sharpe": windows['d30']['sharpe'],
                        "d60_sharpe": windows['d60']['sharpe'],
                        "d90_sharpe": windows['d90']['sharpe']
                    }
        
        self.log_test("Performance Windows Data Structure", success, details)
        return success

    def test_admin_overview_recommendation_data(self):
        """Test playbook recommendation data structure"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params={"symbol": "BTC"})
        
        if success:
            data = details.get("response_data", {})
            recommendation = data.get('recommendation', {})
            
            required_fields = ['playbook', 'priority', 'reasonCodes', 'suggestedActions', 'requiresConfirm']
            missing_fields = [f for f in required_fields if f not in recommendation]
            
            if missing_fields:
                success = False
                details["error"] = f"Missing recommendation fields: {missing_fields}"
            else:
                playbook_types = ['NO_ACTION', 'INVESTIGATION', 'RECALIBRATION', 'PROTECTION_ESCALATION', 'RECOVERY', 'FREEZE_ONLY']
                if recommendation.get('playbook') not in playbook_types:
                    success = False
                    details["error"] = f"Invalid playbook type: {recommendation.get('playbook')}"
                
                if not isinstance(recommendation.get('priority'), int) or recommendation.get('priority') < 1 or recommendation.get('priority') > 6:
                    success = False
                    details["error"] = f"Invalid priority: {recommendation.get('priority')}"
                
                if success:
                    details["note"] = f"Valid recommendation: {recommendation.get('playbook')} (P{recommendation.get('priority')})"
                    details["playbook"] = recommendation.get('playbook')
                    details["priority"] = recommendation.get('priority')
                    details["reason_count"] = len(recommendation.get('reasonCodes', []))
        
        self.log_test("Playbook Recommendation Data", success, details)
        return success

    def test_health_and_guard_integration(self):
        """Test health and guard data integration"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params={"symbol": "BTC"})
        
        if success:
            data = details.get("response_data", {})
            health = data.get('health', {})
            guard = data.get('guard', {})
            
            # Check health topRisks structure
            top_risks = health.get('topRisks', [])
            if not isinstance(top_risks, list):
                success = False
                details["error"] = "topRisks should be a list"
            else:
                for risk in top_risks:
                    required_risk_fields = ['key', 'severity', 'value', 'threshold']
                    missing_risk_fields = [f for f in required_risk_fields if f not in risk]
                    if missing_risk_fields:
                        success = False
                        details["error"] = f"Missing risk fields: {missing_risk_fields}"
                        break
                
                # Check guard subscores
                subscores = guard.get('subscores', {})
                required_subscores = ['reliability', 'drift', 'calibration', 'tailRisk', 'performance']
                missing_subscores = [s for s in required_subscores if s not in subscores]
                
                if missing_subscores:
                    success = False
                    details["error"] = f"Missing guard subscores: {missing_subscores}"
                
                if success:
                    details["note"] = f"Health has {len(top_risks)} risks, Guard has {len(subscores)} subscores"
                    details["health_score"] = health.get('score')
                    details["risk_keys"] = [r.get('key') for r in top_risks]
        
        self.log_test("Health & Guard Integration", success, details)
        return success

    def test_recent_snapshots_audit(self):
        """Test recent snapshots and audit data"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params={"symbol": "BTC"})
        
        if success:
            data = details.get("response_data", {})
            recent = data.get('recent', {})
            
            snapshots = recent.get('snapshots', [])
            audit = recent.get('audit', [])
            
            if not isinstance(snapshots, list) or not isinstance(audit, list):
                success = False
                details["error"] = "snapshots and audit should be lists"
            else:
                # Check snapshots structure (should have 7 days)
                if len(snapshots) != 7:
                    success = False
                    details["error"] = f"Expected 7 snapshots, got {len(snapshots)}"
                else:
                    # Check snapshot structure
                    first_snapshot = snapshots[0]
                    required_snapshot_fields = ['date', 'reliability', 'health']
                    missing_snapshot_fields = [f for f in required_snapshot_fields if f not in first_snapshot]
                    
                    if missing_snapshot_fields:
                        success = False
                        details["error"] = f"Missing snapshot fields: {missing_snapshot_fields}"
                
                # Check audit structure
                if success and len(audit) > 0:
                    first_audit = audit[0]
                    required_audit_fields = ['ts', 'actor', 'action', 'note']
                    missing_audit_fields = [f for f in required_audit_fields if f not in first_audit]
                    
                    if missing_audit_fields:
                        success = False
                        details["error"] = f"Missing audit fields: {missing_audit_fields}"
                
                if success:
                    details["note"] = f"{len(snapshots)} snapshots, {len(audit)} audit entries"
                    details["snapshot_count"] = len(snapshots)
                    details["audit_count"] = len(audit)
        
        self.log_test("Recent Snapshots & Audit Data", success, details)
        return success

    def get_summary_stats(self):
        """Get summary statistics from the last successful overview call"""
        success, details = self.make_request("GET", "/api/fractal/v2.1/admin/overview", params={"symbol": "BTC"})
        
        if success:
            data = details.get("response_data", {})
            return {
                "governance_mode": data.get('governance', {}).get('mode'),
                "health_state": data.get('health', {}).get('state'),
                "health_score": data.get('health', {}).get('score'),
                "degeneration_score": data.get('guard', {}).get('degenerationScore'),
                "playbook_recommendation": data.get('recommendation', {}).get('playbook'),
                "priority": data.get('recommendation', {}).get('priority'),
                "version": data.get('meta', {}).get('version'),
                "contract_frozen": data.get('governance', {}).get('freeze', {}).get('isFrozen')
            }
        return {}

def main():
    print("🚀 FRACTAL ADMIN OVERVIEW TESTING - BLOCKS 49 & 50")
    print("="*80)
    
    tester = FractalAdminOverviewTester()
    
    # Test sequence for BLOCK 49 (Admin Overview Endpoint)
    test_results = []
    
    print("📋 Testing BLOCK 49: Admin Overview Endpoint")
    
    # 1. Main overview endpoint structure
    overview_success, overview_data = tester.test_admin_overview_endpoint()
    test_results.append(("Admin Overview Endpoint", overview_success))
    
    if overview_success:
        # 2. Performance windows validation
        performance_success = tester.test_admin_overview_performance_data()
        test_results.append(("Performance Windows Data", performance_success))
        
        # 3. Playbook recommendation validation
        recommendation_success = tester.test_admin_overview_recommendation_data()
        test_results.append(("Playbook Recommendation", recommendation_success))
        
        # 4. Health and guard integration
        integration_success = tester.test_health_and_guard_integration()
        test_results.append(("Health & Guard Integration", integration_success))
        
        # 5. Recent snapshots and audit
        recent_success = tester.test_recent_snapshots_audit()
        test_results.append(("Recent Snapshots & Audit", recent_success))
    
    # Final results
    print("\n" + "="*80)
    print("📊 BLOCK 49 BACKEND TEST RESULTS")
    print("="*80)
    
    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    passed_count = sum(r[1] for r in test_results)
    total_count = len(test_results)
    
    print(f"\n📈 Backend Tests: {passed_count}/{total_count} passed")
    
    # Get summary statistics
    if overview_success:
        print("\n📊 Current System State:")
        stats = tester.get_summary_stats()
        for key, value in stats.items():
            print(f"   {key}: {value}")
    
    # Return results for integration with main testing agent
    success_rate = passed_count / total_count if total_count > 0 else 0
    
    if success_rate >= 0.8:  # 80% or better
        print(f"\n🎯 BLOCK 49 Backend Tests: PASSED ({success_rate*100:.0f}%)")
        return 0
    else:
        print(f"\n🚨 BLOCK 49 Backend Tests: FAILED ({success_rate*100:.0f}%)")
        return 1

if __name__ == "__main__":
    sys.exit(main())