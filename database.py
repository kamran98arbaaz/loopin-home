"""Database session management and utilities"""

from contextlib import contextmanager
from typing import Generator
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from extensions import db

@contextmanager
def db_session() -> Generator:
    """Provide a transactional scope around a series of operations."""
    try:
        yield db.session
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.session.close()

def init_db(app):
    """Initialize database with app context."""
    with app.app_context():
        try:
            db.create_all()
            current_app.logger.info("Database tables created successfully")
        except SQLAlchemyError as e:
            current_app.logger.error(f"Failed to initialize database: {str(e)}")
            raise

def cleanup_db():
    """Clean up database connections."""
    try:
        db.session.remove()
    except Exception as e:
        current_app.logger.error(f"Error cleaning up database session: {str(e)}")

def health_check() -> bool:
    """Check database connectivity."""
    try:
        db.session.execute("SELECT 1")
        return True
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database health check failed: {str(e)}")
        return False
