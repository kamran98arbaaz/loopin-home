import os
import time
import uuid
import pytz
import re
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func, or_
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_migrate import Migrate
from read_logs import bp as read_logs_bp
from flask_login import LoginManager
from models import User, Update, ReadLog, SOPSummary, LessonLearned, ActivityLog, ArchivedUpdate, ArchivedSOPSummary, ArchivedLessonLearned
from extensions import db, socketio
from role_decorators import admin_required, editor_required, writer_required, delete_required, export_required, get_user_role_info
from timezone_utils import UTC, IST, now_utc, to_utc, to_ist, format_ist, ensure_timezone, is_within_hours, get_hours_ago
from io import BytesIO
import sys
import os
import subprocess
from pathlib import Path

# Add system Python site-packages to path if needed (for environments with path issues)
try:
    import site
    # Get all site-packages directories and add them to path if not already present
    site_packages_dirs = site.getsitepackages()
    for site_dir in site_packages_dirs:
        if site_dir not in sys.path and os.path.exists(site_dir):
            sys.path.insert(0, site_dir)
except Exception:
    # Fallback: try common site-packages locations
    import platform
    python_version = f"Python{sys.version_info.major}{sys.version_info.minor}"
    if platform.system() == "Windows":
        possible_paths = [
            os.path.join(os.path.dirname(sys.executable), "Lib", "site-packages"),
            os.path.expanduser(f"~\\AppData\\Local\\Programs\\Python\\{python_version}\\Lib\\site-packages"),
            os.path.expanduser(f"~\\AppData\\Roaming\\Python\\Python{sys.version_info.major}{sys.version_info.minor}\\site-packages")
        ]
        for path in possible_paths:
            if path not in sys.path and os.path.exists(path):
                sys.path.insert(0, path)
                break

# Import pandas and openpyxl with error handling
try:
    import pandas as pd
    import openpyxl
    EXCEL_EXPORT_AVAILABLE = True
except ImportError as e:
    # Only print warning in development mode
    if os.getenv('FLASK_ENV') == 'development':
        print(f"Warning: Excel export dependencies not available: {e}")
    EXCEL_EXPORT_AVAILABLE = False

# Load .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login'

# Process start timestamp for basic metrics
APP_START = time.time()

def create_app(config_name=None):
    app = Flask(__name__)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    socketio.init_app(app)
    app.register_blueprint(read_logs_bp)
    # Register new API blueprint (first milestone)
    try:
        from api.updates import bp as api_bp
        app.register_blueprint(api_bp)
    except Exception:
        # Blueprint registration should not break app startup if something is off
        pass
    
    # Register Socket.IO blueprint for real-time updates
    try:
        from api.socketio import bp as socketio_bp, init_socketio
        app.register_blueprint(socketio_bp)
        init_socketio(socketio, app)
    except Exception:
        # Socket.IO registration should not break app startup if something is off
        pass
    
    # Register search API blueprint
    try:
        from api.search import bp as search_bp
        app.register_blueprint(search_bp)
    except Exception:
        # Search API registration should not break app startup if something is off
        pass

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-secure-random-string")
    app.config["APP_NAME"] = "LoopIn"

    # ✅ ENHANCED DATABASE CONFIG WITH TEST SEPARATION
    # Determine environment and set appropriate database
    flask_env = os.getenv("FLASK_ENV", "production").lower()
    testing_mode = os.getenv("TESTING", "false").lower() == "true"

    if testing_mode or flask_env == "testing":
        # Use separate test database
        TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
        if TEST_DATABASE_URL:
            DATABASE_URL = TEST_DATABASE_URL
            print("🧪 Using TEST database for testing environment")
        else:
            # Fallback to SQLite for tests if no test database specified
            DATABASE_URL = "sqlite:///test_loopin.db"
            print("🧪 Using SQLite test database (fallback)")
    else:
        # Use production database
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set in environment.")
        print("🚀 Using PRODUCTION database")

    parsed = urlparse(DATABASE_URL)

    # Support Postgres in production and sqlite for local testing
    if parsed.scheme in ("postgresql", "postgres", "sqlite", "sqlite3"):
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    else:
        raise RuntimeError(f"Unsupported DB scheme: {parsed.scheme}")

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configure database connection options for better Railway compatibility
    engine_options = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 20,
        "max_overflow": 0
    }

    sslmode = os.getenv("PG_SSLMODE")
    if sslmode and parsed.scheme in ("postgresql", "postgres"):
        engine_options["connect_args"] = {"sslmode": sslmode}

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    db.init_app(app)

    with app.app_context():
        # ✅ SAFE DATABASE INITIALIZATION
        # Only create tables if they don't exist and we're not in a risky environment
        if parsed.scheme not in ("sqlite", "sqlite3"):
            # For PostgreSQL, use migrations instead of create_all in production
            if testing_mode or flask_env in ["development", "testing"]:
                print("🔧 Creating database tables for development/testing")
                db.create_all()
            else:
                print("🏭 Production mode: Use 'flask db upgrade' for database setup")
        else:
            # For SQLite (test database), always create tables
            print("🔧 Creating SQLite database tables")
            db.create_all()

    # Activity Logging Helper
    def log_activity(action, entity_type, entity_id, entity_title=None, details=None):
        """Log user activity for audit trail"""
        try:
            user_id = session.get("user_id")

            # Get client IP address
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
            if ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()

            # Get user agent
            user_agent = request.headers.get('User-Agent', 'Unknown')

            activity = ActivityLog(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                entity_title=entity_title,
                timestamp=now_utc(),
                ip_address=client_ip,
                user_agent=user_agent,
                details=details
            )

            db.session.add(activity)
            db.session.commit()
        except Exception as e:
            # Don't let activity logging break the main functionality
            print(f"Activity logging failed: {e}")

    # Archive Helper Functions
    def archive_update(update):
        """Archive an update before deletion"""
        try:
            user_id = session.get("user_id")
            archived_update = ArchivedUpdate(
                id=update.id,
                name=update.name,
                process=update.process,
                message=update.message,
                timestamp=update.timestamp,
                archived_at=now_utc(),
                archived_by=user_id
            )
            db.session.add(archived_update)
            return True
        except Exception as e:
            print(f"Failed to archive update: {e}")
            return False

    def archive_sop(sop):
        """Archive a SOP before deletion"""
        try:
            user_id = session.get("user_id")
            archived_sop = ArchivedSOPSummary(
                id=sop.id,
                title=sop.title,
                summary_text=sop.summary_text,
                department=sop.department,
                tags=sop.tags,
                created_at=sop.created_at,
                archived_at=now_utc(),
                archived_by=user_id
            )
            db.session.add(archived_sop)
            return True
        except Exception as e:
            print(f"Failed to archive SOP: {e}")
            return False

    def archive_lesson(lesson):
        """Archive a lesson learned before deletion"""
        try:
            user_id = session.get("user_id")
            archived_lesson = ArchivedLessonLearned(
                id=lesson.id,
                title=lesson.title,
                content=lesson.content,
                summary=lesson.summary,
                author=lesson.author,
                department=lesson.department,
                tags=lesson.tags,
                created_at=lesson.created_at,
                archived_at=now_utc(),
                archived_by=user_id
            )
            db.session.add(archived_lesson)
            return True
        except Exception as e:
            print(f"Failed to archive lesson: {e}")
            return False

    # Auth Helpers
    def login_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("user_id"):
                flash("🔒 Please log in to continue.")
                return redirect(url_for("login", next=request.endpoint))
            return f(*args, **kwargs)
        return decorated

    @app.context_processor
    def inject_current_user():
        user = None
        if session.get("user_id"):
            user = User.query.get(session["user_id"])
        return dict(current_user=user)

    @app.context_processor
    def inject_user_role_info():
        """
        Inject user role information into templates for conditional rendering.
        """
        user = None
        if session.get("user_id"):
            user = User.query.get(session["user_id"])
        role_info = get_user_role_info(user)
        return dict(user_role=role_info)

    @app.template_filter('to_ist')
    def to_ist_filter(utc_datetime):
        """Convert UTC datetime to IST for display"""
        return format_ist(utc_datetime, '%Y-%m-%d %H:%M')

    @app.template_filter('format_datetime')
    def format_datetime_filter(dt, format='%Y-%m-%d %H:%M'):
        """Format datetime with timezone conversion"""
        return format_ist(dt, format)

    @app.template_filter('format_backup_timestamp')
    def format_backup_timestamp_filter(iso_string):
        """Convert ISO timestamp string to IST for backup display"""
        if not iso_string:
            return 'N/A'
        try:
            # Parse the ISO string to datetime
            from datetime import datetime
            # Handle different ISO formats
            if iso_string.endswith('Z'):
                iso_string = iso_string.replace('Z', '+00:00')
            elif '+' not in iso_string and 'T' in iso_string:
                # Assume UTC if no timezone info
                iso_string = iso_string + '+00:00'

            dt = datetime.fromisoformat(iso_string)
            # Convert to IST and format
            return format_ist(dt, '%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError, TypeError):
            # Fallback to original string manipulation if parsing fails
            try:
                return iso_string[:19].replace('T', ' ') + ' (UTC)'
            except:
                return str(iso_string)

    @app.context_processor
    def built_assets_available():
        """Expose a small flag to templates indicating whether built CSS exists.

        Templates can use `built_css` to prefer a local built stylesheet
        (e.g. `static/dist/styles.css`) when present, otherwise fall back
        to a CDN link. This keeps CI builds optional and safe for local dev.
        """
        try:
            static_path = os.path.join(app.root_path, "static", "dist", "styles.css")
            is_prod = str(app.config.get('ENV', '')).lower() == 'production' or os.getenv('FLASK_ENV', '').lower() == 'production' or os.getenv('ENV', '').lower() == 'production'
            return dict(built_css=os.path.exists(static_path), is_production=is_prod)
        except Exception:
            return dict(built_css=False, is_production=False)

    # Routes
    @app.route("/health")
    def health():
        """Ultra-simple health check endpoint for Railway deployment"""
        return jsonify({"status": "ok", "timestamp": now_utc().isoformat()}), 200

    @app.route("/health/db")
    def health_db():
        """Database-specific health check"""
        try:
            # Quick database connectivity check
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "db": "connected"}), 200
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return jsonify({"status": "error", "db": "disconnected", "error": str(e)}), 500

    @app.route("/ready")
    def ready():
        """Readiness probe - checks if app is ready to serve traffic"""
        try:
            # Check database connectivity
            db.session.execute(text("SELECT 1"))

            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if len(tables) > 0:
                return jsonify({
                    "status": "ready",
                    "db": "connected",
                    "tables": len(tables),
                    "timestamp": now_utc().isoformat()
                }), 200
            else:
                return jsonify({
                    "status": "not_ready",
                    "db": "connected",
                    "tables": 0,
                    "message": "Database tables not created yet"
                }), 503

        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return jsonify({
                "status": "not_ready",
                "db": "disconnected",
                "error": str(e)
            }), 503

    @app.route("/health/detailed")
    def health_detailed():
        """Detailed health check with Redis and other services"""
        out = {"db": None}
        code = 200
        try:
            db.session.execute(text("SELECT 1"))
            out["db"] = "reachable"
        except Exception as e:
            out["db"] = str(e)
            code = 500

        # Only check Redis if REDIS_URL is configured to avoid unnecessary delays
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                from api.updates import is_redis_healthy
                try:
                    out["redis"] = "ok" if is_redis_healthy() else "unavailable"
                    if out["redis"] != "ok":
                        code = max(code, 503)
                except Exception as re:
                    out["redis"] = f"error: {re}"
                    code = max(code, 500)
            except Exception:
                # If redis helper not available, just omit it
                out["redis"] = "not_configured"
        else:
            out["redis"] = "not_configured"

        status = "ok" if code == 200 else "error"
        out["status"] = status
        return jsonify(out), code

    try:
        from prometheus_client import CollectorRegistry, Gauge, generate_latest, CONTENT_TYPE_LATEST
        registry = CollectorRegistry()
        g_uptime = Gauge('app_uptime_seconds', 'App uptime in seconds', registry=registry)
        g_updates = Gauge('updates_total', 'Total updates', registry=registry)
        g_redis = Gauge('redis_up', 'Redis up (1/0)', registry=registry)

        @app.route('/metrics')
        def metrics():
            try:
                g_uptime.set(int(time.time() - APP_START))
            except Exception:
                g_uptime.set(0)
            try:
                g_updates.set(int(Update.query.count()))
            except Exception:
                g_updates.set(0)
            # Only check Redis if configured to avoid performance issues
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    from api.updates import is_redis_healthy
                    g_redis.set(1 if is_redis_healthy() else 0)
                except Exception:
                    g_redis.set(0)
            else:
                g_redis.set(0)  # Redis not configured
            data = generate_latest(registry)
            return (data, 200, {'Content-Type': CONTENT_TYPE_LATEST})
    except Exception:
        # If prometheus_client not available, keep the small plaintext /metrics
        @app.route('/metrics')
        def metrics_plain():
            lines = []
            try:
                uptime = time.time() - APP_START
                lines.append(f"app_uptime_seconds {int(uptime)}")
            except Exception:
                lines.append("app_uptime_seconds 0")
            try:
                total = Update.query.count()
                lines.append(f"updates_total {int(total)}")
            except Exception:
                lines.append("updates_total 0")
            # Only check Redis if configured to avoid performance issues
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                try:
                    from api.updates import is_redis_healthy
                    ok = is_redis_healthy()
                    lines.append(f"redis_up {1 if ok else 0}")
                except Exception:
                    lines.append("redis_up 0")
            else:
                lines.append("redis_up 0")  # Redis not configured
            return ("\n".join(lines), 200, {"Content-Type": "text/plain; version=0.0.4"})

    @app.route('/health/alert', methods=['POST'])
    def health_alert():
        """Trigger a POST to a configured alert webhook with current health status.

        Useful for manual or automated alerting during deployment checks.
        Configure `HEALTH_ALERT_URL` in the environment to enable.
        """
        url = os.getenv('HEALTH_ALERT_URL')
        if not url:
            return jsonify({'error': 'no_webhook_configured'}), 400
        try:
            import requests
            # Reuse /health to get current status
            with app.test_client() as c:
                resp = c.get('/health')
                payload = resp.get_json()
            r = requests.post(url, json=payload, timeout=5)
            return jsonify({'status': 'sent', 'response_code': r.status_code}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route("/lessons_learned/view/<int:lesson_id>")
    @login_required
    def view_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))
        return render_template("view_lesson_learned.html", lesson=lesson)

    @app.route("/search")
    def search():
        query = request.args.get("q", "").strip()
        results = []

        # Get filter parameters
        category = request.args.get("category", "")
        process = request.args.get("process", "")
        department = request.args.get("department", "")
        date_range = request.args.get("date_range", "")

        # Prepare filters for template
        filters = {
            "category": category,
            "process": process,
            "department": department,
            "date_range": date_range
        }

        # Available options for filters
        available_processes = ["ABC", "XYZ", "AB"]
        available_departments = ["ABC", "XYZ", "AB"]  # Fixed to match process options

        if query:
            # Case-insensitive search
            query_filter = f"%{query}%"

            # Search Updates (if no category filter or category is 'updates')
            if not category or category == "updates":
                updates_query = Update.query.filter(
                    or_(
                        Update.message.ilike(query_filter),
                        Update.name.ilike(query_filter),
                        Update.process.ilike(query_filter)
                    )
                )

                # Apply process filter
                if process:
                    updates_query = updates_query.filter(Update.process.ilike(f"%{process}%"))

                updates_rows = updates_query.order_by(Update.timestamp.desc()).all()

                for upd in updates_rows:
                    results.append({
                        "id": upd.id,
                        "title": f"{upd.process} - {upd.name}",
                        "content": upd.message[:200] + ("..." if len(upd.message) > 200 else ""),
                        "type": "update",
                        "url": url_for("view_update", update_id=upd.id),
                        "author": upd.name,
                        "created_at": upd.timestamp,
                        "process": upd.process
                    })

            # Search SOP Summaries (if no category filter or category is 'sops')
            if not category or category == "sops":
                sops_query = SOPSummary.query.filter(
                    or_(
                        SOPSummary.title.ilike(query_filter),
                        SOPSummary.summary_text.ilike(query_filter)
                    )
                )

                # Apply department filter
                if department:
                    sops_query = sops_query.filter(SOPSummary.department.ilike(f"%{department}%"))

                sops_rows = sops_query.order_by(SOPSummary.created_at.desc()).all()

                for sop in sops_rows:
                    results.append({
                        "id": sop.id,
                        "title": sop.title,
                        "content": sop.summary_text[:200] + ("..." if len(sop.summary_text) > 200 else ""),
                        "type": "sop",
                        "url": url_for("view_sop_summary", summary_id=sop.id),
                        "created_at": sop.created_at,
                        "tags": sop.tags or []
                    })

            # Search Lessons Learned (if no category filter or category is 'lessons')
            if not category or category == "lessons":
                lessons_query = LessonLearned.query.filter(
                    or_(
                        LessonLearned.title.ilike(query_filter),
                        LessonLearned.content.ilike(query_filter),
                        LessonLearned.summary.ilike(query_filter)
                    )
                )

                # Apply department filter
                if department:
                    lessons_query = lessons_query.filter(LessonLearned.department.ilike(f"%{department}%"))

                lessons_rows = lessons_query.order_by(LessonLearned.created_at.desc()).all()

                for lesson in lessons_rows:
                    results.append({
                        "id": lesson.id,
                        "title": lesson.title,
                        "content": (lesson.summary or lesson.content or "")[:200] + ("..." if len(lesson.summary or lesson.content or "") > 200 else ""),
                        "type": "lesson",
                        "url": url_for("view_lesson_learned", lesson_id=lesson.id),
                        "author": lesson.author,
                        "created_at": lesson.created_at,
                        "tags": lesson.tags or []
                    })

        return render_template("search_results.html",
                             query=query,
                             results=results,
                             filters=filters,
                             available_processes=available_processes,
                             available_departments=available_departments)



    @app.route("/")
    def home():
        try:
            summaries = SOPSummary.query.order_by(SOPSummary.created_at.desc()).all()
            lessons = LessonLearned.query.order_by(LessonLearned.created_at.desc()).all()
            
            # Get latest updates for the home page - simplified version
            latest_updates = Update.query.order_by(Update.timestamp.desc()).limit(5).all()
            updates_data = []
            
            for update in latest_updates:
                update_dict = update.to_dict()
                update_dict['read_count'] = 0  # Simplified for now
                update_dict['is_new'] = False  # Simplified for now
                updates_data.append(update_dict)
            
            return render_template("home.html", app_name=app.config["APP_NAME"],
                                 summaries=summaries, lessons=lessons, updates=updates_data,
                                 excel_export_available=EXCEL_EXPORT_AVAILABLE)
        except Exception as e:
            # Return a basic template without updates if there's an error
            return render_template("home.html", app_name=app.config["APP_NAME"],
                                 summaries=[], lessons=[], updates=[],
                                 excel_export_available=EXCEL_EXPORT_AVAILABLE)

    @app.route("/updates")
    def show_updates():
        # Get filter parameters from query string
        selected_process = request.args.get("process", "")
        selected_department = request.args.get("department", "")
        sort = request.args.get("sort", "newest")
        
        # Base query
        base_query = (
            db.session.query(Update, func.count(ReadLog.id).label('read_count'))
            .outerjoin(ReadLog, ReadLog.update_id == Update.id)
            .group_by(Update.id)
        )
        
        # Apply process filter if specified
        if selected_process:
            base_query = base_query.filter(Update.process == selected_process)
        
        # Apply sorting
        if sort == "oldest":
            base_query = base_query.order_by(Update.timestamp.asc())
        elif sort == "process":
            base_query = base_query.order_by(Update.process.asc(), Update.timestamp.desc())
        elif sort == "author":
            base_query = base_query.order_by(Update.name.asc(), Update.timestamp.desc())
        else:  # newest (default)
            base_query = base_query.order_by(Update.timestamp.desc())
        
        rows = base_query.all()

        updates = []
        current_time = now_utc()
        for upd, count in rows:
            d = upd.to_dict()
            d['read_count'] = count

            # determine if it's within last 24 hours
            d['is_new'] = is_within_hours(upd.timestamp, 24, current_time)

            # Add the original datetime object for isoformat() in template
            d['timestamp_obj'] = upd.timestamp

            updates.append(d)

        # Get additional data for template
        all_updates = Update.query.all()
        unique_authors = list(set([upd.name for upd in all_updates if upd.name]))
        processes = list(set([upd.process for upd in all_updates if upd.process]))
        
        # Calculate updates this week
        updates_this_week = 0
        for upd in all_updates:
            if upd.timestamp and is_within_hours(upd.timestamp, 24 * 7, current_time):
                updates_this_week += 1
        
        # Get unique departments (consistent with other forms)
        departments = ["ABC", "XYZ", "AB"]
        
        return render_template("show.html", 
                             app_name=app.config["APP_NAME"], 
                             updates=updates,
                             unique_authors=unique_authors,
                             processes=processes,
                             departments=departments,
                             updates_this_week=updates_this_week,
                             selected_process=selected_process,
                             selected_department=selected_department,
                             sort=sort)

    @app.route("/post", methods=["GET", "POST"])
    @writer_required
    def post_update():
        processes = ["ABC", "XYZ", "AB"]

        if request.method == "POST":
            message = request.form.get("message", "").strip()
            selected_process = request.form.get("process")
            name = inject_current_user()["current_user"].display_name

            if not message or not selected_process:
                flash("⚠️ Message and process are required.")
                return redirect(url_for("post_update"))

            new_update = Update(
                id=uuid.uuid4().hex,
                name=name,
                process=selected_process,
                message=message,
                timestamp=now_utc(),
            )
            try:
                db.session.add(new_update)
                db.session.commit()
                flash("✅ Update posted.")

                # Log activity
                log_activity('created', 'update', new_update.id, f"Update: {message[:50]}...")

                # Broadcast the new update via Socket.IO
                try:
                    from api.socketio import broadcast_update
                    update_data = {
                        'id': new_update.id,
                        'name': new_update.name,
                        'process': new_update.process,
                        'message': new_update.message,
                        'timestamp': new_update.timestamp.isoformat()
                    }
                    broadcast_update(update_data, selected_process)
                except Exception as e:
                    # Socket.IO broadcasting failure shouldn't break the posting
                    print(f"Socket.IO broadcast failed: {e}")

            except Exception:
                db.session.rollback()
                flash("⚠️ Failed to post update.")
            return redirect(url_for("show_updates"))

        return render_template("post.html", app_name=app.config["APP_NAME"], processes=processes)

    @app.route("/edit/<update_id>", methods=["GET", "POST"])
    @writer_required
    def edit_update(update_id):
        update = Update.query.get(update_id)
        current = inject_current_user()["current_user"]
        if not update or update.name != current.display_name:
            flash("🚫 Unauthorized or not found.")
            return redirect(url_for("show_updates"))

        if request.method == "POST":
            new_message = request.form.get("message", "").strip()
            if not new_message:
                flash("⚠️ Message cannot be empty.")
                return redirect(url_for("edit_update", update_id=update_id))
            update.message = new_message
            update.timestamp = now_utc()
            try:
                db.session.commit()
                flash("✏️ Update edited successfully.")

                # Log activity
                log_activity('edited', 'update', update.id, f"Update: {new_message[:50]}...")

            except Exception:
                db.session.rollback()
                flash("⚠️ Failed to edit update.")
            return redirect(url_for("show_updates"))

        return render_template("edit.html", app_name=app.config["APP_NAME"], update=update)

    @app.route("/view/<update_id>")
    def view_update(update_id):
        """View a specific update"""
        update = Update.query.get(update_id)
        if not update:
            flash("🚫 Update not found.")
            return redirect(url_for("show_updates"))
        
        # Get read count for this update
        read_count = db.session.query(func.count(ReadLog.id)).filter(
            ReadLog.update_id == update_id
        ).scalar()
        
        # Check if current user has read this update
        is_read = False
        if session.get("user_id"):
            read_log = ReadLog.query.filter_by(
                update_id=update_id,
                user_id=session["user_id"]
            ).first()
            is_read = read_log is not None
        
        return render_template("view_update.html", 
                             app_name=app.config["APP_NAME"], 
                             update=update, 
                             read_count=read_count,
                             is_read=is_read)

    @app.route("/delete/<update_id>", methods=["POST"])
    @login_required
    def delete_update(update_id):
        update = Update.query.get(update_id)
        current = inject_current_user()["current_user"]
        if not update:
            flash("⚠️ Update not found.")
            return redirect(url_for("show_updates"))

        if update.name.strip().lower() != current.display_name.strip().lower():
            flash("🚫 Not authorized to delete.")
            return redirect(url_for("show_updates"))

        # Capture details before deletion
        entity_title = f"Update: {update.message[:50]}..."

        try:
            # Archive the update before deletion
            if archive_update(update):
                db.session.delete(update)
                db.session.commit()
                flash("✅ Update deleted and archived.")

                # Log activity after successful deletion
                log_activity('deleted', 'update', update_id, entity_title)
            else:
                flash("⚠️ Failed to archive update. Deletion cancelled for safety.")

        except Exception as e:
            db.session.rollback()
            flash("❌ Deletion failed.")
            logger.error(f"Failed to delete update: {e}")

        return redirect(url_for("show_updates"))
            
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            display_name = request.form["display_name"].strip()
            username = request.form["username"].strip().replace(" ", "_").lower()
            password = request.form["password"]

            if not re.match("^[A-Za-z0-9_]+$", username):
                flash("🚫 Username can only contain letters, numbers, and underscores.")
                return redirect(url_for("register"))

            if not username or not display_name or not password:
                flash("⚠️ All fields required.")
                return redirect(url_for("register"))

            if User.query.filter_by(username=username).first():
                flash("🚫 Username taken.")
                return redirect(url_for("register"))

            new_user = User(username=username, display_name=display_name)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash("✅ Registered! Please log in.")
            return redirect(url_for("login"))

        return render_template("register.html", app_name=app.config["APP_NAME"])

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"].strip().replace(" ", "_").lower()
            password = request.form["password"]
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session["user_id"] = user.id
                flash(f"👋 Welcome back, {user.display_name}!")

                # Handle redirect logic
                next_page = request.form.get('next') or request.args.get('next')

                # If user came from home page login button, redirect to home
                if next_page == 'home':
                    return redirect(url_for("home"))
                # If there's a next page specified, redirect there
                elif next_page:
                    # Check if it's a full URL (from role decorators)
                    if next_page.startswith('http') or next_page.startswith('/'):
                        # Validate that it's a safe redirect within our app
                        from urllib.parse import urlparse
                        parsed = urlparse(next_page)
                        if not parsed.netloc or parsed.netloc == request.host:
                            return redirect(next_page)

                    # Map of valid endpoints to their URL functions
                    valid_endpoints = {
                        'show_updates': 'show_updates',
                        'post_update': 'post_update',
                        'list_sop_summaries': 'list_sop_summaries',
                        'list_lessons_learned': 'list_lessons_learned',
                        'search': 'search',
                        'add_sop_summary': 'add_sop_summary',
                        'add_lesson_learned': 'add_lesson_learned',
                        'export_readlogs': 'export_readlogs'
                    }

                    # Handle search result redirects for SOPs and Lessons
                    if next_page == 'view_sop_summary':
                        return redirect(url_for('list_sop_summaries'))
                    elif next_page == 'view_lesson_learned':
                        return redirect(url_for('list_lessons_learned'))
                    elif next_page in valid_endpoints:
                        return redirect(url_for(valid_endpoints[next_page]))

                # Default fallback to home page instead of show_updates
                return redirect(url_for("home"))

            flash("🚫 Invalid credentials.")
            return redirect(url_for("login"))

        # For GET requests, preserve the next parameter
        next_page = request.args.get('next')
        return render_template("login.html", app_name=app.config["APP_NAME"], next_page=next_page)

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash("👋 You’ve been logged out.")
        return redirect(url_for("home"))

    @app.route("/api/latest-update-time")
    def api_latest_update_time():
        """API endpoint to get the timestamp of the most recent update"""
        try:
            latest_update = Update.query.order_by(Update.timestamp.desc()).first()
            if latest_update:
                # Ensure timezone is properly handled
                timestamp = ensure_timezone(latest_update.timestamp, UTC)

                return jsonify({
                    "latest_timestamp": timestamp.isoformat(),
                    "success": True
                })
            else:
                return jsonify({
                    "latest_timestamp": None,
                    "success": True
                })
        except Exception as e:
            logger.error(f"Error getting latest update time: {e}")
            return jsonify({
                "latest_timestamp": None,
                "success": False,
                "error": str(e)
            }), 500
    
    # New routes for SOP Summaries
    @app.route("/sop_summaries")
    @login_required
    def list_sop_summaries():
        sops = SOPSummary.query.order_by(SOPSummary.created_at.desc()).all()
        return render_template("sop_summaries.html", sops=sops)

    @app.route("/sop_summaries/add", methods=["GET", "POST"])
    @writer_required
    def add_sop_summary():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            summary_text = request.form.get("summary_text", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not summary_text:
                flash("Title and Summary are required.")
                return redirect(url_for("add_sop_summary"))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            sop = SOPSummary(
                title=title,
                summary_text=summary_text,
                department=department or None,
                tags=tags_list or None,
            )
            try:
                db.session.add(sop)
                db.session.commit()
                flash("SOP Summary added successfully.")

                # Log activity
                log_activity('created', 'sop', sop.id, title)

                # Broadcast notification for new SOP
                try:
                    from api.socketio import broadcast_notification
                    broadcast_notification({
                        'type': 'new_sop',
                        'title': 'New SOP Added',
                        'message': f'**NEW SOP:** {title}',
                        'timestamp': now_utc().isoformat()
                    })
                except Exception as e:
                    print(f"Socket.IO broadcast failed: {e}")

                return redirect(url_for("list_sop_summaries"))
            except Exception as e:
                db.session.rollback()
                flash("Failed to add SOP Summary.")
                logger.error(f"Failed to add SOP Summary: {e}")
                return redirect(url_for("add_sop_summary"))

        return render_template("add_sop_summary.html")

    @app.route("/sop_summaries/edit/<int:sop_id>", methods=["GET", "POST"])
    @writer_required
    def edit_sop_summary(sop_id):
        sop = SOPSummary.query.get(sop_id)
        if not sop:
            flash("SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            summary_text = request.form.get("summary_text", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not summary_text:
                flash("Title and Summary are required.")
                return redirect(url_for("edit_sop_summary", sop_id=sop_id))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            sop.title = title
            sop.summary_text = summary_text
            sop.department = department or None
            sop.tags = tags_list or None
            try:
                db.session.commit()
                flash("✅ SOP Summary updated successfully.")

                # Log activity
                log_activity('edited', 'sop', sop.id, title)

            except Exception as e:
                db.session.rollback()
                flash("❌ Failed to update SOP Summary.")
                logger.error(f"Failed to update SOP Summary: {e}")

            # Check if user came from view page or list page
            referrer = request.form.get('referrer') or request.referrer
            if referrer and 'sop_summaries/' in referrer and str(sop_id) in referrer:
                return redirect(url_for("view_sop_summary", summary_id=sop_id))
            else:
                return redirect(url_for("list_sop_summaries"))

        return render_template("edit_sop_summary.html", sop=sop)

    @app.route("/sop_summaries/delete/<int:sop_id>", methods=["POST"])
    @delete_required
    def delete_sop_summary(sop_id):
        sop = SOPSummary.query.get(sop_id)
        if not sop:
            flash("⚠️ SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))

        # Capture details before deletion
        entity_title = sop.title

        try:
            # Archive the SOP before deletion
            if archive_sop(sop):
                db.session.delete(sop)
                db.session.commit()
                flash("✅ SOP Summary deleted and archived.")

                # Log activity after successful deletion
                log_activity('deleted', 'sop', sop_id, entity_title)
            else:
                flash("⚠️ Failed to archive SOP. Deletion cancelled for safety.")

        except Exception as e:
            db.session.rollback()
            flash("❌ Failed to delete SOP Summary.")
            logger.error(f"Failed to delete SOP Summary: {e}")

        # Always redirect to list page after deletion since the item no longer exists
        return redirect(url_for("list_sop_summaries"))

    # New routes for Lessons Learned
    @app.route("/lessons_learned")
    @login_required
    def list_lessons_learned():
        lessons = LessonLearned.query.order_by(LessonLearned.created_at.desc()).all()
        return render_template("lessons_learned.html", lessons=lessons)

    @app.route("/lessons_learned/add", methods=["GET", "POST"])
    @writer_required
    def add_lesson_learned():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            summary = request.form.get("summary", "").strip()
            author = request.form.get("author", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not content:
                flash("Title and Content are required.")
                return redirect(url_for("add_lesson_learned"))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            lesson = LessonLearned(
                title=title,
                content=content,
                summary=summary or None,
                author=author or None,
                department=department or None,
                tags=tags_list or None,
            )
            try:
                db.session.add(lesson)
                db.session.commit()
                flash("Lesson Learned added successfully.")

                # Log activity
                log_activity('created', 'lesson', lesson.id, title)

                # Broadcast notification for new Lesson Learned
                try:
                    from api.socketio import broadcast_notification
                    broadcast_notification({
                        'type': 'new_lesson',
                        'title': 'New Lesson Learned',
                        'message': f'**NEW LESSON:** {title}',
                        'timestamp': now_utc().isoformat()
                    })
                except Exception as e:
                    print(f"Socket.IO broadcast failed: {e}")

                return redirect(url_for("list_lessons_learned"))
            except Exception as e:
                db.session.rollback()
                flash("Failed to add Lesson Learned.")
                logger.error(f"Failed to add Lesson Learned: {e}")
                return redirect(url_for("add_lesson_learned"))

        return render_template("add_lesson_learned.html")

    @app.route("/lessons_learned/edit/<int:lesson_id>", methods=["GET", "POST"])
    @writer_required
    def edit_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            summary = request.form.get("summary", "").strip()
            author = request.form.get("author", "").strip()
            department = request.form.get("department", "").strip()
            tags = request.form.get("tags", "").strip()

            if not title or not content:
                flash("Title and Content are required.")
                return redirect(url_for("edit_lesson_learned", lesson_id=lesson_id))

            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            lesson.title = title
            lesson.content = content
            lesson.summary = summary or None
            lesson.author = author or None
            lesson.department = department or None
            lesson.tags = tags_list or None

            try:
                db.session.commit()
                flash("✅ Lesson Learned updated successfully.")

                # Log activity
                log_activity('edited', 'lesson', lesson.id, title)

            except Exception as e:
                db.session.rollback()
                flash("❌ Failed to update Lesson Learned.")
                logger.error(f"Failed to update Lesson Learned: {e}")

            # Check if user came from view page or list page
            referrer = request.form.get('referrer') or request.referrer
            if referrer and 'lessons_learned/view/' in referrer and str(lesson_id) in referrer:
                return redirect(url_for("view_lesson_learned", lesson_id=lesson_id))
            else:
                return redirect(url_for("list_lessons_learned"))

        return render_template("edit_lesson_learned.html", lesson=lesson)

    @app.route("/lessons_learned/delete/<int:lesson_id>", methods=["POST"])
    @delete_required
    def delete_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))

        # Capture details before deletion
        entity_title = lesson.title

        try:
            # Archive the lesson before deletion
            if archive_lesson(lesson):
                db.session.delete(lesson)
                db.session.commit()
                flash("✅ Lesson Learned deleted and archived.")

                # Log activity after successful deletion
                log_activity('deleted', 'lesson', lesson_id, entity_title)
            else:
                flash("⚠️ Failed to archive lesson. Deletion cancelled for safety.")

        except Exception as e:
            db.session.rollback()
            flash("❌ Failed to delete Lesson Learned.")

        # Always redirect to list page after deletion since the item no longer exists
        return redirect(url_for("list_lessons_learned"))
    

        
    @app.route("/sop_summaries/<int:summary_id>")
    @login_required
    def view_sop_summary(summary_id):
        summary = SOPSummary.query.get(summary_id)
        if not summary:
            flash("\u26a0\ufe0f SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))

        return render_template(
            "view_sop_summary.html",
            summary=summary,
            app_name=current_app.config["APP_NAME"]
        )



    @app.route("/api/recent-updates")
    def recent_updates():
        """Get updates from the past 24 hours for the bell icon banner."""
        try:
            # Calculate 24 hours ago
            twenty_four_hours_ago = get_hours_ago(24)

            # Query for recent updates
            recent_updates = Update.query.filter(
                Update.timestamp >= twenty_four_hours_ago
            ).order_by(Update.timestamp.desc()).limit(10).all()

            updates_data = []
            for update in recent_updates:
                # Ensure timezone is properly handled
                timestamp = ensure_timezone(update.timestamp, UTC)

                updates_data.append({
                    "id": update.id,
                    "name": update.name,
                    "process": update.process,
                    "message": update.message,
                    "timestamp": timestamp.isoformat()
                })

            return jsonify({
                "success": True,
                "updates": updates_data
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/export-readlogs")
    @export_required
    def export_readlogs():
        """Export read logs to Excel file with comprehensive analytics."""
        # Check if Excel export dependencies are available
        if not EXCEL_EXPORT_AVAILABLE:
            flash("❌ Excel export feature is not available. Please install pandas and openpyxl.", "error")
            return redirect(url_for('home'))

        # Check if this is a download request
        download = request.args.get('download', 'false').lower() == 'true'

        if not download:
            # Show export page with download button
            return render_template('export_readlogs.html', app_name=app.config["APP_NAME"])

        # If download=true, proceed with file generation and download
        try:
            # Query all read logs with related data
            read_logs_query = db.session.query(
                ReadLog.id,
                ReadLog.timestamp,
                ReadLog.guest_name,
                ReadLog.ip_address,
                ReadLog.user_agent,
                Update.id.label('update_id'),
                Update.message.label('update_message'),
                Update.name.label('update_author'),
                Update.process.label('update_process'),
                Update.timestamp.label('update_created'),
                User.display_name.label('reader_name'),
                User.username.label('reader_username')
            ).outerjoin(
                Update, ReadLog.update_id == Update.id
            ).outerjoin(
                User, ReadLog.user_id == User.id
            ).order_by(ReadLog.timestamp.desc())

            # Execute query and get results
            results = read_logs_query.all()

            # Prepare data for Excel
            data = []
            for row in results:
                # Determine reader name (user or guest)
                reader_name = row.reader_name if row.reader_name else (row.guest_name or "Anonymous")
                reader_type = "Registered User" if row.reader_name else "Guest"

                # Format timestamps
                read_time = row.timestamp.strftime('%Y-%m-%d %H:%M:%S') if row.timestamp else ""
                update_created_time = row.update_created.strftime('%Y-%m-%d %H:%M:%S') if row.update_created else ""

                # Truncate long messages for readability
                update_message = (row.update_message[:100] + "...") if row.update_message and len(row.update_message) > 100 else (row.update_message or "")

                data.append({
                    'Read Log ID': row.id,
                    'Reader Name': reader_name,
                    'Reader Type': reader_type,
                    'Reader Username': row.reader_username or "N/A",
                    'Read Timestamp': read_time,
                    'IP Address': row.ip_address or "N/A",
                    'Browser User-Agent': row.user_agent or "N/A",
                    'Update ID': row.update_id or "N/A",
                    'Update Message': update_message,
                    'Update Author': row.update_author or "N/A",
                    'Update Process': row.update_process or "N/A",
                    'Update Created': update_created_time,
                })

            # Create DataFrame
            df = pd.DataFrame(data)

            # Create summary statistics
            summary_data = []

            # Total reads
            total_reads = len(df)
            summary_data.append({'Metric': 'Total Reads', 'Value': total_reads})

            # Unique readers
            unique_readers = df['Reader Name'].nunique()
            summary_data.append({'Metric': 'Unique Readers', 'Value': unique_readers})

            # Registered vs Guest reads
            registered_reads = len(df[df['Reader Type'] == 'Registered User'])
            guest_reads = len(df[df['Reader Type'] == 'Guest'])
            summary_data.append({'Metric': 'Registered User Reads', 'Value': registered_reads})
            summary_data.append({'Metric': 'Guest Reads', 'Value': guest_reads})

            # Most active readers (top 10)
            top_readers = df['Reader Name'].value_counts().head(10)

            # Most read updates (top 10)
            most_read_updates = df.groupby(['Update ID', 'Update Message', 'Update Author']).size().reset_index(name='Read Count').sort_values('Read Count', ascending=False).head(10)

            # Create Excel file in memory
            output = BytesIO()

            # Query activity logs
            activity_logs_query = db.session.query(
                ActivityLog.id,
                ActivityLog.action,
                ActivityLog.entity_type,
                ActivityLog.entity_id,
                ActivityLog.entity_title,
                ActivityLog.timestamp,
                ActivityLog.ip_address,
                ActivityLog.user_agent,
                ActivityLog.details,
                User.display_name.label('user_name'),
                User.username.label('username')
            ).outerjoin(
                User, ActivityLog.user_id == User.id
            ).order_by(ActivityLog.timestamp.desc())

            activity_results = activity_logs_query.all()

            # Prepare activity logs data
            activity_data = []
            for row in activity_results:
                user_name = row.user_name if row.user_name else "System"
                activity_time = row.timestamp.strftime('%Y-%m-%d %H:%M:%S') if row.timestamp else ""

                activity_data.append({
                    'Activity ID': row.id,
                    'User Name': user_name,
                    'Username': row.username or "N/A",
                    'Action': row.action.title(),
                    'Entity Type': row.entity_type.upper(),
                    'Entity ID': row.entity_id,
                    'Entity Title': row.entity_title or "N/A",
                    'Timestamp': activity_time,
                    'IP Address': row.ip_address or "N/A",
                    'Browser User-Agent': row.user_agent or "N/A",
                    'Details': row.details or "N/A"
                })

            activity_df = pd.DataFrame(activity_data)

            # Query registered users for authority tracking
            users_query = db.session.query(
                User.id,
                User.username,
                User.display_name,
                User.email,
                User.role
            ).order_by(User.id)

            users_results = users_query.all()
            users_data = []
            for idx, user in enumerate(users_results, 1):
                users_data.append({
                    'Serial #': idx,
                    'User ID': user.id,
                    'Username': user.username,
                    'Display Name': user.display_name,
                    'Email': user.email or "N/A",
                    'Role': user.role.title()
                })

            users_df = pd.DataFrame(users_data)

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Main data sheet
                df.to_excel(writer, sheet_name='Read Logs', index=False)

                # Summary sheet
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Activity Logs sheet
                activity_df.to_excel(writer, sheet_name='Activity Logs', index=False)

                # Registered Users sheet
                users_df.to_excel(writer, sheet_name='Registered Users', index=False)

                # Top readers sheet
                top_readers_df = pd.DataFrame({
                    'Reader Name': top_readers.index,
                    'Total Reads': top_readers.values
                })
                top_readers_df.to_excel(writer, sheet_name='Top Readers', index=False)

                # Most read updates sheet
                most_read_updates.to_excel(writer, sheet_name='Most Read Updates', index=False)

                # Process-wise analytics
                if not df.empty and 'Update Process' in df.columns:
                    process_stats = df.groupby('Update Process').agg({
                        'Read Log ID': 'count',
                        'Reader Name': 'nunique'
                    }).rename(columns={
                        'Read Log ID': 'Total Reads',
                        'Reader Name': 'Unique Readers'
                    }).reset_index()
                    process_stats.to_excel(writer, sheet_name='Process Analytics', index=False)

                # Format the Excel sheets
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]

                    # Auto-adjust column widths
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter

                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass

                        adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            output.seek(0)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'readlogs_export_{timestamp}.xlsx'

            return send_file(
                output,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        except Exception as e:
            # Log the error
            current_app.logger.error(f"Error exporting read logs: {str(e)}")

            # Return error page or redirect with flash message
            flash(f"❌ Error exporting read logs: {str(e)}", "error")
            return redirect(url_for('home'))

    @app.route("/reset-activity-logs", methods=["POST"])
    @admin_required
    def reset_activity_logs():
        """Reset (delete all) activity logs with admin password verification."""
        try:
            # Get the admin password from the form
            admin_password = request.form.get('admin_password', '').strip()

            if not admin_password:
                flash("❌ Admin password is required to reset activity logs.", "error")
                return redirect(url_for('export_readlogs'))

            # Get the current admin user
            admin_user_id = session.get("user_id")
            if not admin_user_id:
                flash("❌ Authentication error. Please log in again.", "error")
                return redirect(url_for('login'))

            admin_user = User.query.get(admin_user_id)
            if not admin_user or admin_user.role != 'admin':
                flash("❌ Admin access required.", "error")
                return redirect(url_for('home'))

            # Verify the admin password
            if not admin_user.check_password(admin_password):
                flash("❌ Incorrect admin password. Activity logs were not reset.", "error")
                return redirect(url_for('export_readlogs'))

            # Count current activity logs before deletion
            activity_count = ActivityLog.query.count()

            # Delete all activity logs
            ActivityLog.query.delete()
            db.session.commit()

            flash(f"✅ Successfully reset activity logs. {activity_count} records were deleted.", "success")

            # Log this action (create a new activity log entry for the reset)
            log_activity('reset', 'activity_logs', 'all', f"Reset all activity logs ({activity_count} records)",
                        details=f"Admin {admin_user.display_name} reset all activity logs")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error resetting activity logs: {str(e)}", "error")

        return redirect(url_for('export_readlogs'))

    @app.route("/backup")
    @admin_required
    def backup_page():
        """Display backup management page."""
        try:
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()
            backups = backup_system.list_backups()
            return render_template('backup.html',
                                 app_name=app.config["APP_NAME"],
                                 backups=backups)
        except Exception as e:
            flash(f"❌ Error loading backup page: {str(e)}", "error")
            return redirect(url_for('home'))

    @app.route("/backup/create", methods=["POST"])
    @admin_required
    def create_backup():
        """Create a new database backup."""
        try:
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()

            backup_type = request.form.get('backup_type', 'manual')
            backup_path = backup_system.create_backup(backup_type)

            if backup_path:
                flash(f"✅ Backup created successfully: {backup_path.name}", "success")
            else:
                flash("❌ Failed to create backup. Check logs for details.", "error")

        except Exception as e:
            flash(f"❌ Error creating backup: {str(e)}", "error")

        return redirect(url_for('backup_page'))

    @app.route("/backup/restore", methods=["POST"])
    @admin_required
    def restore_backup():
        """Restore database from backup with improved error handling."""
        import threading
        import time

        try:
            backup_file = request.form.get('backup_file')
            if not backup_file:
                flash("❌ Please select a backup file to restore.", "error")
                return redirect(url_for('backup_page'))

            backup_path = Path("backups") / backup_file

            # Check if backup file exists
            if not backup_path.exists():
                flash(f"❌ Backup file not found: {backup_file}", "error")
                return redirect(url_for('backup_page'))

            # Quick verification
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()

            if not backup_system.verify_backup(backup_path):
                flash("❌ Backup file verification failed. Cannot restore.", "error")
                return redirect(url_for('backup_page'))

            # Perform restore with timeout protection
            def restore_with_timeout():
                try:
                    return backup_system.restore_backup(backup_path)
                except Exception as e:
                    logger.error(f"Restore error in thread: {e}")
                    return False

            # Start restore in background with timeout
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(restore_with_timeout)
                try:
                    # Wait up to 90 seconds for restore to complete (matching backend timeout)
                    result = future.result(timeout=90)
                    if result:
                        flash("✅ Database restored successfully from backup. Archived items have been restored to their original locations.", "success")
                        # Log the restore activity
                        log_activity('restored', 'database', backup_file, f"Database restored from {backup_file}")
                    else:
                        flash("❌ Failed to restore backup. Check logs for details.", "error")
                except concurrent.futures.TimeoutError:
                    flash("⚠️ Restore operation timed out after 90 seconds. Please check if restore completed successfully.", "warning")
                except Exception as e:
                    flash(f"❌ Restore operation failed: {str(e)}", "error")

        except Exception as e:
            flash(f"❌ Error during restore process: {str(e)}", "error")
            logger.error(f"Backup restore error: {e}")

        return redirect(url_for('backup_page'))

    @app.route("/backup/cleanup", methods=["POST"])
    @admin_required
    def cleanup_backups():
        """Clean up old backups."""
        try:
            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()
            backup_system.cleanup_old_backups()
            flash("✅ Old backups cleaned up successfully.", "success")
        except Exception as e:
            flash(f"❌ Error cleaning up backups: {str(e)}", "error")

        return redirect(url_for('backup_page'))

    @app.route("/backup/delete", methods=["POST"])
    @admin_required
    def delete_backup():
        """Delete a backup file permanently."""
        try:
            backup_filename = request.form.get('backup_file')
            if not backup_filename:
                flash("❌ No backup file specified.", "error")
                return redirect(url_for('backup_page'))

            from backup_system import DatabaseBackupSystem
            backup_system = DatabaseBackupSystem()

            # Get the backup file path
            backup_path = backup_system.backup_dir / backup_filename
            metadata_path = backup_path.with_suffix('.json')

            if not backup_path.exists():
                flash("❌ Backup file not found.", "error")
                return redirect(url_for('backup_page'))

            # Delete the backup file and its metadata
            backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

            flash(f"✅ Backup file '{backup_filename}' deleted successfully.", "success")

            # Log activity
            log_activity('deleted', 'backup_file', backup_filename, f"Backup: {backup_filename}")

        except Exception as e:
            flash(f"❌ Error deleting backup file: {str(e)}", "error")

        return redirect(url_for('backup_page'))

    @app.route("/archives")
    @admin_required
    def archives_page():
        """Display archived items management page."""
        try:
            # Get archived items with user info
            archived_updates = db.session.query(
                ArchivedUpdate,
                User.display_name.label('archived_by_name')
            ).outerjoin(
                User, ArchivedUpdate.archived_by == User.id
            ).order_by(ArchivedUpdate.archived_at.desc()).all()

            archived_sops = db.session.query(
                ArchivedSOPSummary,
                User.display_name.label('archived_by_name')
            ).outerjoin(
                User, ArchivedSOPSummary.archived_by == User.id
            ).order_by(ArchivedSOPSummary.archived_at.desc()).all()

            archived_lessons = db.session.query(
                ArchivedLessonLearned,
                User.display_name.label('archived_by_name')
            ).outerjoin(
                User, ArchivedLessonLearned.archived_by == User.id
            ).order_by(ArchivedLessonLearned.archived_at.desc()).all()

            return render_template('archives.html',
                                 app_name=app.config["APP_NAME"],
                                 archived_updates=archived_updates,
                                 archived_sops=archived_sops,
                                 archived_lessons=archived_lessons)
        except Exception as e:
            flash(f"❌ Error loading archives: {str(e)}", "error")
            return redirect(url_for('backup_page'))

    @app.route("/archives/restore/<item_type>/<item_id>", methods=["POST"])
    @admin_required
    def restore_archived_item(item_type, item_id):
        """Restore an archived item."""
        try:
            if item_type == 'update':
                # For updates, item_id is a string (UUID)
                archived_item = ArchivedUpdate.query.get(item_id)
                if archived_item:
                    # Create new update from archived data
                    restored_update = Update(
                        id=archived_item.id,
                        name=archived_item.name,
                        process=archived_item.process,
                        message=archived_item.message,
                        timestamp=archived_item.timestamp
                    )
                    db.session.add(restored_update)
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Update restored successfully.", "success")

                    # Log activity
                    log_activity('restored', 'update', archived_item.id, f"Update: {archived_item.message[:50]}...")

            elif item_type == 'sop':
                # For SOPs, item_id is an integer
                try:
                    sop_id = int(item_id)
                    archived_item = ArchivedSOPSummary.query.get(sop_id)
                except ValueError:
                    flash("❌ Invalid SOP ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    restored_sop = SOPSummary(
                        title=archived_item.title,
                        summary_text=archived_item.summary_text,
                        department=archived_item.department,
                        tags=archived_item.tags,
                        created_at=archived_item.created_at
                    )
                    db.session.add(restored_sop)
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ SOP restored successfully.", "success")

                    # Log activity
                    log_activity('restored', 'sop', restored_sop.id, archived_item.title)

            elif item_type == 'lesson':
                # For lessons, item_id is an integer
                try:
                    lesson_id = int(item_id)
                    archived_item = ArchivedLessonLearned.query.get(lesson_id)
                except ValueError:
                    flash("❌ Invalid Lesson ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    restored_lesson = LessonLearned(
                        title=archived_item.title,
                        content=archived_item.content,
                        summary=archived_item.summary,
                        author=archived_item.author,
                        department=archived_item.department,
                        tags=archived_item.tags,
                        created_at=archived_item.created_at
                    )
                    db.session.add(restored_lesson)
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Lesson Learned restored successfully.", "success")

                    # Log activity
                    log_activity('restored', 'lesson', restored_lesson.id, archived_item.title)

            else:
                flash("❌ Invalid item type.", "error")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error restoring item: {str(e)}", "error")

        return redirect(url_for('archives_page'))

    @app.route("/archives/delete/<item_type>/<item_id>", methods=["POST"])
    @admin_required
    def delete_archived_item(item_type, item_id):
        """Permanently delete an archived item."""
        try:
            if item_type == 'update':
                # For updates, item_id is a string (UUID)
                archived_item = ArchivedUpdate.query.get(item_id)
                if archived_item:
                    entity_title = f"Update: {archived_item.message[:50]}..."
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Archived update permanently deleted.", "success")

                    # Log activity
                    log_activity('permanently_deleted', 'archived_update', archived_item.id, entity_title)
                else:
                    flash("❌ Archived update not found.", "error")

            elif item_type == 'sop':
                # For SOPs, item_id is an integer
                try:
                    sop_id = int(item_id)
                    archived_item = ArchivedSOPSummary.query.get(sop_id)
                except ValueError:
                    flash("❌ Invalid SOP ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    entity_title = archived_item.title
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Archived SOP permanently deleted.", "success")

                    # Log activity
                    log_activity('permanently_deleted', 'archived_sop', str(sop_id), entity_title)
                else:
                    flash("❌ Archived SOP not found.", "error")

            elif item_type == 'lesson':
                # For lessons, item_id is an integer
                try:
                    lesson_id = int(item_id)
                    archived_item = ArchivedLessonLearned.query.get(lesson_id)
                except ValueError:
                    flash("❌ Invalid lesson ID format.", "error")
                    return redirect(url_for('archives_page'))

                if archived_item:
                    entity_title = archived_item.title
                    db.session.delete(archived_item)
                    db.session.commit()
                    flash("✅ Archived lesson permanently deleted.", "success")

                    # Log activity
                    log_activity('permanently_deleted', 'archived_lesson', str(lesson_id), entity_title)
                else:
                    flash("❌ Archived lesson not found.", "error")

            else:
                flash("❌ Invalid item type.", "error")

        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error deleting archived item: {str(e)}", "error")

        return redirect(url_for('archives_page'))

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    # Set debug based on environment variable
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    socketio.run(app, host="0.0.0.0", port=port, debug=debug_mode)
