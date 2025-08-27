#!/usr/bin/env python3
"""
Simple Flask app runner for Railway deployment
"""
import os
import sys

def main():
    """Main function to run the Flask app"""
    try:
        # Import the app
        from app import create_app
        
        # Create app instance
        app = create_app()
        
        # Get port from environment
        port = int(os.getenv('PORT', 8000))
        
        print(f"🚀 Starting Flask app on port {port}")
        
        # Run the app
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
        
    except Exception as e:
        print(f"❌ Failed to start Flask app: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
