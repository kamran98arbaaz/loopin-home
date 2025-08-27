#!/usr/bin/env python3
"""
Startup script for Railway deployment to ensure database is ready
"""
import os
import sys
import time
from sqlalchemy import create_engine, text

def wait_for_database(max_retries=60, delay=2):
    """Wait for database to be ready with longer timeout"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        sys.exit(1)

    print(f"🔍 Checking database connectivity...")

    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Database is ready!")

            # Additional check - ensure we can create tables
            try:
                from sqlalchemy import inspect
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                print(f"📊 Found {len(tables)} existing tables")
            except Exception as e:
                print(f"⚠️ Could not inspect tables: {e}")

            return True
        except Exception as e:
            print(f"⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
                # Exponential backoff with max delay of 10 seconds
                delay = min(delay * 1.1, 10)
            else:
                print("❌ Database failed to become ready")
                sys.exit(1)

    return False

if __name__ == "__main__":
    wait_for_database()
    print("🚀 Starting application...")
