#!/usr/bin/env python3
"""
Detailed Response Validation for Fractal Backend
Validates the actual response structures of each endpoint
"""

import requests
import sys
import json
from datetime import datetime

def test_endpoint_response(url, method="GET", data=None, params=None):
    """Test an endpoint and show detailed response structure"""
    try:
        if method.upper() == 'GET':
            response = requests.get(url, params=params, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, timeout=10)
            
        print(f"🔍 {method} {url}")
        print(f"   Status: {response.status_code}")
        
        try:
            json_data = response.json()
            if response.status_code == 200:
                print(f"   ✅ Response structure:")
                # Show top-level keys
                if isinstance(json_data, dict):
                    for key, value in json_data.items():
                        if isinstance(value, dict):
                            print(f"      {key}: {{...}} ({len(value)} keys)")
                        elif isinstance(value, list):
                            print(f"      {key}: [...] ({len(value)} items)")
                        else:
                            print(f"      {key}: {type(value).__name__} = {value}")
                else:
                    print(f"      Type: {type(json_data).__name__}")
            else:
                print(f"   ❌ Error: {json_data}")
        except:
            print(f"   Response: {response.text[:200]}")
        print()
            
    except Exception as e:
        print(f"🔍 {method} {url}")
        print(f"   ❌ Failed: {str(e)}")
        print()

def main():
    base_url = "https://pointintime-macro.preview.emergentagent.com"
    
    print("🧪 Detailed Fractal Backend Response Validation")
    print("="*60)
    
    # Test each required endpoint with response validation
    test_endpoint_response(f"{base_url}/api/health")
    test_endpoint_response(f"{base_url}/api/fractal/health")
    test_endpoint_response(f"{base_url}/api/fractal/signal", params={"symbol": "BTC"})
    test_endpoint_response(f"{base_url}/api/fractal/admin/autopilot/run", method="POST", data={})
    test_endpoint_response(f"{base_url}/api/fractal/admin/dataset")
    test_endpoint_response(f"{base_url}/api/fractal/match", method="POST", data={"symbol": "BTC"})

if __name__ == "__main__":
    main()