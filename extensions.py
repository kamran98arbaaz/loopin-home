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
    cors_allowed_origins="*",  # Allow all origins for Socket.IO compatibility
    logger=is_development,  # Only enable logging in development
    engineio_logger=is_development,  # Only enable engineio logging in development
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1000000,
    allow_upgrades=True,
    cookie=None,  # Disable cookies for Railway compatibility
    cors_credentials=False,  # Disable credentials to avoid CORS issues
    cors_methods=["GET", "POST", "OPTIONS"],
    cors_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Forwarded-For"],
    # Railway-specific configurations
    manage_session=False,  # Disable Flask session management for Railway
    message_queue=None,  # Use in-memory queue for single instance
    channel='socketio',  # Channel name for message queue
    # Additional Railway-compatible settings
    async_mode='threading',  # Force threading mode for Railway
    path='/socket.io',  # Explicit Socket.IO path
    transports=['polling', 'websocket'],  # Explicit transport order
)
