#!/usr/bin/env python3
"""
Test script to verify Flask app can be imported correctly
"""
import sys
import os

def test_app_import():
    """Test importing the Flask app"""
    print("🧪 Testing Flask app import...")
    
    try:
        # Test importing from app.py
        print("📦 Importing from app.py...")
        from app import app, create_app
        print(f"✅ Successfully imported app: {type(app)}")
        print(f"✅ Successfully imported create_app: {type(create_app)}")
        
        # Test importing from wsgi.py
        print("📦 Importing from wsgi.py...")
        from wsgi import application
        print(f"✅ Successfully imported application: {type(application)}")
        
        # Test app configuration
        print("🔧 Testing app configuration...")
        print(f"   App name: {app.name}")
        print(f"   Debug mode: {app.debug}")
        print(f"   Secret key set: {'Yes' if app.secret_key else 'No'}")
        
        # Test basic route
        print("🛣️ Testing basic routes...")
        with app.test_client() as client:
            response = client.get('/health')
            print(f"   Health endpoint status: {response.status_code}")
            
        print("✅ All import tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app_import()
    sys.exit(0 if success else 1)
