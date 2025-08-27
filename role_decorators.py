#!/usr/bin/env python3
"""
Role-based access control decorators for LoopIn application
"""

from functools import wraps
from flask import flash, redirect, url_for, session, request
from models import User

def get_current_user():
    """Get current user from session."""
    if session.get("user_id"):
        return User.query.get(session["user_id"])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            flash("🔒 Please log in to access this page.", "error")
            return redirect(url_for("login", next=request.url))
        if not current_user.is_admin():
            flash("🚫 Admin access required. You don't have permission to access this page.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

def editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            flash("🔒 Please log in to access this page.", "error")
            return redirect(url_for("login", next=request.url))
        if not current_user.is_editor():
            flash("🚫 Editor access required. You don't have permission to access this page.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

def writer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            flash("🔒 Please log in to access this page.", "error")
            return redirect(url_for("login", next=request.url))
        if not current_user.can_write():
            flash("🚫 Write access required. You don't have permission to access this page.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

def delete_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            flash("🔒 Please log in to access this page.", "error")
            return redirect(url_for("login", next=request.url))
        if not current_user.can_delete():
            flash("🚫 Delete access required. Only admins can delete content.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

def export_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = get_current_user()
        if not current_user:
            flash("🔒 Please log in to access this page.", "error")
            return redirect(url_for("login", next=request.url))
        if not current_user.can_export():
            flash("🚫 Export access required. Only admins can export data.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function

def get_user_role_info(user):
    """Get user role information for templates."""
    if not user:
        return {
            "role": "guest",
            "can_write": False,
            "can_delete": False,
            "can_export": False,
            "is_admin": False,
            "is_editor": False,
            "role_display": "Guest"
        }
    return {
        "role": user.role,
        "can_write": user.can_write(),
        "can_delete": user.can_delete(),
        "can_export": user.can_export(),
        "is_admin": user.is_admin(),
        "is_editor": user.is_editor(),
        "role_display": user.role.title()
    }