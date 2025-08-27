#!/usr/bin/env python3
"""
Minimal Flask app for Railway deployment testing
"""
import os
from flask import Flask, jsonify

# Create Flask app
app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')

@app.route('/')
def home():
    """Home page"""
    return jsonify({
        "message": "LoopIn is running!",
        "status": "ok",
        "environment": os.getenv('FLASK_ENV', 'development')
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "message": "Application is healthy"
    }), 200

@app.route('/test')
def test():
    """Test endpoint"""
    return jsonify({
        "test": "success",
        "port": os.getenv('PORT', 'not set'),
        "database_url": "configured" if os.getenv('DATABASE_URL') else "not configured"
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
