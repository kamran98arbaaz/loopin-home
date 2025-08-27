#!/usr/bin/env python3
"""
Simple deployment test script
"""
import os
import sys
import requests
from urllib.parse import urlparse

def test_deployment():
    """Test basic deployment functionality"""
    print("🧪 Testing deployment...")
    
    # Get the app URL (Railway provides this)
    app_url = os.getenv('RAILWAY_PUBLIC_DOMAIN')
    if not app_url:
        app_url = "http://localhost:8000"  # Fallback for local testing
    
    if not app_url.startswith('http'):
        app_url = f"https://{app_url}"
    
    print(f"🌐 Testing URL: {app_url}")
    
    try:
        # Test health endpoint
        print("🔍 Testing health endpoint...")
        response = requests.get(f"{app_url}/health", timeout=10)
        
        if response.status_code == 200:
            print("✅ Health check passed!")
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('db')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
        
        # Test main page
        print("🏠 Testing main page...")
        response = requests.get(app_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Main page accessible!")
        else:
            print(f"⚠️ Main page returned: {response.status_code}")
        
        print("🎉 Deployment test completed successfully!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

if __name__ == "__main__":
    success = test_deployment()
    sys.exit(0 if success else 1)
