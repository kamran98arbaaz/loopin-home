#!/usr/bin/env python3
"""
Startup script for Railway deployment to ensure database is ready
"""
import os
import sys
import time
from sqlalchemy import create_engine, text

def wait_for_database(max_retries=30, delay=2):
    """Wait for database to be ready"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        sys.exit(1)
    
    print(f"🔍 Checking database connectivity...")
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Database is ready!")
            return True
        except Exception as e:
            print(f"⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                print("❌ Database failed to become ready")
                sys.exit(1)
    
    return False

if __name__ == "__main__":
    wait_for_database()
    print("🚀 Starting application...")
