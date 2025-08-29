#!/usr/bin/env python3
"""
Test script for Socket.IO connection fixes
"""
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_socketio_setup():
    """Test Socket.IO setup and configuration"""
    print("Testing Socket.IO setup...")

    try:
        # Test imports
        from app import create_app
        from extensions import socketio
        print("OK: Imports successful")

        # Test app creation
        app = create_app()
        print("OK: App creation successful")

        # Test Socket.IO configuration
        print(f"INFO: Socket.IO async mode: {socketio.async_mode}")
        print(f"INFO: Socket.IO server options: {getattr(socketio, 'server_options', {})}")

        # Test with app context
        with app.app_context():
            print("OK: App context working")

            # Test database connection
            from extensions import db
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            print("OK: Database connection working")

        # Test Socket.IO initialization
        socketio.init_app(app)
        print("OK: Socket.IO initialization successful")

        print("SUCCESS: All Socket.IO setup tests passed!")
        return True

    except Exception as e:
        print(f"ERROR: Socket.IO setup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_health_endpoint():
    """Test health endpoint"""
    print("\nTesting health endpoint...")

    try:
        from app import create_app
        app = create_app()

        with app.test_client() as client:
            response = client.get('/health')
            if response.status_code == 200:
                data = response.get_json()
                print(f"OK: Health check passed: {data.get('status', 'unknown')}")
                return True
            else:
                print(f"ERROR: Health check failed: {response.status_code}")
                return False

    except Exception as e:
        print(f"ERROR: Health endpoint test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting Socket.IO connection tests...\n")

    # Test 1: Socket.IO setup
    setup_ok = test_socketio_setup()

    # Test 2: Health endpoint
    health_ok = test_health_endpoint()

    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)

    if setup_ok and health_ok:
        print("SUCCESS: ALL TESTS PASSED!")
        print("OK: Socket.IO setup: PASSED")
        print("OK: Health endpoint: PASSED")
        print("\nSocket.IO should be ready for client connections!")
        return 0
    else:
        print("ERROR: SOME TESTS FAILED!")
        print(f"Socket.IO setup: {'PASSED' if setup_ok else 'FAILED'}")
        print(f"Health endpoint: {'PASSED' if health_ok else 'FAILED'}")
        print("\nPlease check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())