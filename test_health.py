#!/usr/bin/env python3
"""
Test health endpoints locally
"""
import os
import sys
import time
import requests

def test_health_endpoints():
    """Test all health endpoints"""
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("/health", "Basic health check"),
        ("/health/db", "Database health check"),
        ("/ready", "Readiness probe"),
        ("/health/detailed", "Detailed health check")
    ]
    
    print("🧪 Testing health endpoints...")
    print("=" * 50)
    
    for endpoint, description in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n🔍 Testing {endpoint} - {description}")
        
        try:
            response = requests.get(url, timeout=5)
            print(f"   Status: {response.status_code}")
            
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                print(f"   Response: {data}")
            else:
                print(f"   Response: {response.text[:100]}...")
                
            if response.status_code == 200:
                print("   ✅ PASS")
            else:
                print("   ❌ FAIL")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ ERROR: {e}")
        except Exception as e:
            print(f"   ❌ UNEXPECTED ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Health endpoint testing completed")

if __name__ == "__main__":
    test_health_endpoints()
