#!/usr/bin/env python3
"""
Database Configuration Checker
Shows current database configuration and environment status
"""

import os
from dotenv import load_dotenv
from urllib.parse import urlparse

def main():
    print("🔍 DATABASE CONFIGURATION CHECK")
    print("=" * 40)
    
    # Load environment
    load_dotenv()
    
    # Show current environment
    flask_env = os.getenv("FLASK_ENV", "production")
    testing_mode = os.getenv("TESTING", "false").lower() == "true"
    
    print(f"🌍 FLASK_ENV: {flask_env}")
    print(f"🧪 TESTING: {testing_mode}")
    print()
    
    # Show database URLs
    prod_url = os.getenv("DATABASE_URL")
    test_url = os.getenv("TEST_DATABASE_URL")
    
    print("📊 DATABASE URLS:")
    print("-" * 20)
    
    if prod_url:
        parsed_prod = urlparse(prod_url)
        print(f"🚀 Production: {parsed_prod.scheme}://{parsed_prod.hostname}:{parsed_prod.port}{parsed_prod.path}")
    else:
        print("❌ Production: DATABASE_URL not set")
    
    if test_url:
        parsed_test = urlparse(test_url)
        print(f"🧪 Test: {parsed_test.scheme}://{parsed_test.hostname}:{parsed_test.port}{parsed_test.path}")
    else:
        print("⚠️  Test: TEST_DATABASE_URL not set (will use SQLite fallback)")
    
    print()
    
    # Show which database would be used
    print("🎯 ACTIVE DATABASE:")
    print("-" * 20)
    
    if testing_mode or flask_env == "testing":
        active_url = test_url if test_url else "sqlite:///test_loopin.db"
        print(f"🧪 Currently using: TEST database")
        print(f"   URL: {active_url}")
        print("   ✅ Production data is PROTECTED")
    else:
        print(f"🚀 Currently using: PRODUCTION database")
        if prod_url:
            parsed = urlparse(prod_url)
            print(f"   URL: {parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}")
        print("   ⚠️  Tests could affect production data if run without TESTING=true")
    
    print()
    
    # Show backup directories
    print("🗂️  BACKUP DIRECTORIES:")
    print("-" * 25)
    
    if testing_mode or flask_env == "testing":
        print("🧪 Test backups: backups_test/")
        print("🚀 Production backups: backups/")
    else:
        print("🚀 Production backups: backups/")
        print("🧪 Test backups: backups_test/")
    
    print()
    
    # Show recommendations
    print("💡 RECOMMENDATIONS:")
    print("-" * 20)
    
    if not test_url:
        print("⚠️  Consider setting TEST_DATABASE_URL for better test isolation")
        print("   Example: TEST_DATABASE_URL=postgresql://user:pass@localhost/loopin_test")
    
    if not testing_mode and flask_env != "testing":
        print("🔒 To run tests safely:")
        print("   export TESTING=true")
        print("   python -m pytest")
        print("   # OR")
        print("   python test_config.py run")
    
    print()
    print("✅ Configuration check complete!")

if __name__ == "__main__":
    main()
