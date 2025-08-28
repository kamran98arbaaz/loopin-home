# Gunicorn configuration for production
import multiprocessing

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1  # (2*CPU)+1 is a common formula
threads = 2
worker_class = 'eventlet'  # For WebSocket support
timeout = 120

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (if not handled by proxy)
# keyfile = 'ssl/private.key'
# certfile = 'ssl/cert.pem'

# Performance tuning
keepalive = 65
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
backlog = 2048
graceful_timeout = 30

# Process naming
proc_name = 'loopin'

def on_starting(server):
    """Log when the server starts."""
    server.log.info("Starting Loopin server")

def when_ready(server):
    """Log when the server is ready."""
    server.log.info("Loopin server is ready")

def worker_abort(worker):
    """Log when a worker is aborted."""
    worker.log.info("Worker aborted")
