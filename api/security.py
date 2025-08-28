"""API security and rate limiting"""

import time
from functools import wraps
from flask import request, jsonify, current_app
from typing import Dict, Callable
import threading

class RateLimiter:
    """Simple in-memory rate limiter"""
    def __init__(self, limit: int = 100, window: int = 60):
        self.limit = limit  # requests per window
        self.window = window  # window in seconds
        self.tokens: Dict[str, list] = {}
        self.lock = threading.Lock()
        
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        with self.lock:
            now = time.time()
            # Initialize or cleanup old timestamps
            if key not in self.tokens:
                self.tokens[key] = []
            self.tokens[key] = [t for t in self.tokens[key] if t > now - self.window]
            
            # Check rate limit
            if len(self.tokens[key]) >= self.limit:
                return False
            
            # Add new timestamp
            self.tokens[key].append(now)
            return True

# Initialize rate limiter
rate_limiter = RateLimiter()

def require_api_key(f: Callable) -> Callable:
    """Decorator to require API key for access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != current_app.config.get('API_KEY'):
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(f: Callable) -> Callable:
    """Decorator to apply rate limiting to API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        key = f"{request.remote_addr}:{request.endpoint}"
        if not rate_limiter.is_allowed(key):
            return jsonify({"error": "Rate limit exceeded"}), 429
        return f(*args, **kwargs)
    return decorated_function
