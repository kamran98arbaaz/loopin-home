#!/usr/bin/env python3
"""
Comprehensive deployment script for Railway
"""
import os
import sys
import time
import subprocess
from sqlalchemy import create_engine, text

def log(message):
    """Log with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_environment():
    """Check required environment variables"""
    log("🔍 Checking environment variables...")
    
    required_vars = ['DATABASE_URL', 'FLASK_SECRET_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        log(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    log("✅ All required environment variables are set")
    return True

def wait_for_database(max_retries=30):
    """Wait for database to be ready"""
    database_url = os.getenv('DATABASE_URL')
    log(f"🔍 Waiting for database to be ready...")
    
    for attempt in range(max_retries):
        try:
            engine = create_engine(database_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log("✅ Database is ready!")
            return True
        except Exception as e:
            log(f"⏳ Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    log("❌ Database failed to become ready")
    return False

def run_migrations():
    """Run database migrations"""
    log("🔄 Running database migrations...")
    try:
        result = subprocess.run(['flask', 'db', 'upgrade'], 
                              capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            log("✅ Database migrations completed successfully")
            return True
        else:
            log(f"❌ Migration failed: {result.stderr}")
            return False
    except Exception as e:
        log(f"❌ Migration error: {e}")
        return False

def start_application():
    """Start the application"""
    log("🚀 Starting application...")
    
    port = os.getenv('PORT', '8000')
    cmd = [
        'gunicorn', 
        'app:app',
        '--bind', f'0.0.0.0:{port}',
        '--workers', '1',
        '--timeout', '300',
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        '--preload'
    ]
    
    log(f"📝 Command: {' '.join(cmd)}")
    
    try:
        # Start gunicorn
        subprocess.run(cmd)
    except KeyboardInterrupt:
        log("🛑 Application stopped by user")
    except Exception as e:
        log(f"❌ Application failed to start: {e}")
        sys.exit(1)

def main():
    """Main deployment function"""
    log("🚀 Starting Railway deployment...")
    
    # Step 1: Check environment
    if not check_environment():
        sys.exit(1)
    
    # Step 2: Wait for database
    if not wait_for_database():
        sys.exit(1)
    
    # Step 3: Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Step 4: Start application
    start_application()

if __name__ == "__main__":
    main()
