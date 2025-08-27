#!/usr/bin/env python3
"""
Environment check script for Railway deployment debugging
"""
import os

def check_environment():
    """Check critical environment variables"""
    print("🔍 Environment Check:")
    print("=" * 50)
    
    # Critical variables
    critical_vars = [
        'DATABASE_URL',
        'PORT',
        'FLASK_SECRET_KEY'
    ]
    
    # Optional variables
    optional_vars = [
        'REDIS_URL',
        'FLASK_ENV',
        'TESTING'
    ]
    
    print("📋 Critical Variables:")
    for var in critical_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive data
            if 'URL' in var or 'KEY' in var:
                masked = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"  ✅ {var}: {masked}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ❌ {var}: NOT SET")
    
    print("\n📋 Optional Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            if 'URL' in var:
                masked = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"  ✅ {var}: {masked}")
            else:
                print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚪ {var}: not set")
    
    print("=" * 50)

if __name__ == "__main__":
    check_environment()
