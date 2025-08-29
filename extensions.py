# extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
import os

db = SQLAlchemy()
login_manager = LoginManager()

# Configure Socket.IO for Railway deployment
# Determine environment for conditional configuration
is_production = os.getenv("RAILWAY_ENVIRONMENT") == "production" or os.getenv("FLASK_ENV") == "production"
is_development = os.getenv("FLASK_ENV") == "development" or not is_production

socketio = SocketIO(
    cors_allowed_origins=[
        "https://loopin-home-production.up.railway.app",
        "https://*.up.railway.app",  # Allow all Railway subdomains
        # Only allow localhost in development
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ] if is_production else [
        "https://loopin-home-production.up.railway.app",
        "https://*.up.railway.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "*"  # Allow all in development only
    ],
    logger=is_development,  # Only enable logging in development
    engineio_logger=is_development,  # Only enable engineio logging in development
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    allow_upgrades=True,
    cookie=None,  # Disable cookies for Railway
    cors_credentials=True,  # Allow credentials
    cors_methods=["GET", "POST", "OPTIONS"],
    cors_headers=["Content-Type", "Authorization", "X-Requested-With"],
    # Railway-specific configurations
    manage_session=True,  # Enable Flask session management for better compatibility
    message_queue=os.getenv("REDIS_URL") if os.getenv("REDIS_URL") else None,  # Use Redis if available
    channel='socketio'  # Channel name for message queue
)
