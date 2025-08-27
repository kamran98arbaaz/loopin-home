#!/usr/bin/env python3
"""
Test Configuration Helper
This script helps set up the environment for safe testing
"""

import os
import sys
from pathlib import Path

def setup_test_environment():
    """Set up environment variables for testing"""
    print("🧪 SETTING UP TEST ENVIRONMENT")
    print("=" * 35)
    
    # Set testing environment variables
    os.environ["TESTING"] = "true"
    os.environ["FLASK_ENV"] = "testing"
    
    # Check if test database URL is set
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        print("⚠️  TEST_DATABASE_URL not set, will use SQLite fallback")
        os.environ["TEST_DATABASE_URL"] = "sqlite:///test_loopin.db"
    else:
        print(f"✅ Using test database: {test_db_url}")
    
    print("✅ Test environment configured")
    print("🔒 Production database is protected")
    print()
    
    return True

def create_test_database():
    """Create test database if using PostgreSQL"""
    test_db_url = os.getenv("TEST_DATABASE_URL")
    
    if test_db_url and test_db_url.startswith("postgresql"):
        print("🔧 Creating PostgreSQL test database...")
        # Extract database name from URL
        from urllib.parse import urlparse
        parsed = urlparse(test_db_url)
        db_name = parsed.path.lstrip('/')
        
        print(f"📝 Test database name: {db_name}")
        print("💡 To create the test database, run:")
        print(f"   createdb {db_name}")
        print()
    
def run_tests():
    """Run tests with proper environment setup"""
    setup_test_environment()
    create_test_database()
    
    print("🚀 RUNNING TESTS")
    print("=" * 20)
    
    # Import and run tests
    try:
        import pytest
        # Run pytest with current environment
        exit_code = pytest.main(["-v", "--tb=short"])
        sys.exit(exit_code)
    except ImportError:
        print("❌ pytest not installed. Install with: pip install pytest")
        print("💡 Or run tests manually with your preferred test runner")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            setup_test_environment()
        elif command == "create-db":
            create_test_database()
        elif command == "run":
            run_tests()
        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        print_usage()

def print_usage():
    """Print usage information"""
    print("🧪 Test Configuration Helper")
    print("=" * 30)
    print("Usage: python test_config.py <command>")
    print()
    print("Commands:")
    print("  setup     - Set up test environment variables")
    print("  create-db - Show instructions for creating test database")
    print("  run       - Set up environment and run tests")
    print()
    print("Examples:")
    print("  python test_config.py setup")
    print("  python test_config.py run")

if __name__ == "__main__":
    main()
