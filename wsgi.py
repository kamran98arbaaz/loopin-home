#!/usr/bin/env python3
"""
WSGI entry point for gunicorn
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from app import create_app
    
    # Create the application instance
    application = create_app()
    
    # Also create 'app' for compatibility
    app = application
    
    if __name__ == "__main__":
        port = int(os.getenv("PORT", 8000))
        application.run(host="0.0.0.0", port=port)
        
except Exception as e:
    print(f"❌ Failed to create Flask application: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
