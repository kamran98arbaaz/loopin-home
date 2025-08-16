import os 
import time
import uuid
import pytz
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, current_app, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_migrate import Migrate
from read_logs import bp as read_logs_bp
from flask_login import LoginManager
from models import User, Update, ReadLog, SOPSummary, LessonLearned
from extensions import db

# Load .env
load_dotenv()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login'

IST = pytz.timezone("Asia/Kolkata")

# Process start timestamp for basic metrics
APP_START = time.time()

def create_app(config_name=None):
    app = Flask(__name__)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    app.register_blueprint(read_logs_bp)
    # Register new API blueprint (first milestone)
    try:
        from api.updates import bp as api_bp
        app.register_blueprint(api_bp)
    except Exception:
        # Blueprint registration should not break app startup if something is off
        pass

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-secure-random-string")
    app.config["APP_NAME"] = "LoopIn"

    # Database config
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set in environment.")
    parsed = urlparse(DATABASE_URL)
    # Support Postgres in production and sqlite for local testing
    if parsed.scheme in ("postgresql", "postgres", "sqlite", "sqlite3"):
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    else:
        raise RuntimeError(f"Unsupported DB scheme: {parsed.scheme}")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    sslmode = os.getenv("PG_SSLMODE")
    if sslmode and parsed.scheme in ("postgresql", "postgres"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"sslmode": sslmode}}

    db.init_app(app)

    with app.app_context():
        # Avoid running create_all for sqlite during tests because some
        # Postgres-specific column types (e.g. ARRAY) are not supported by sqlite
        if parsed.scheme not in ("sqlite", "sqlite3"):
            db.create_all()

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
        out = {"db": None, "redis": None}
        code = 200
        try:
            db.session.execute(text("SELECT 1"))
            out["db"] = "reachable"
        except Exception as e:
            out["db"] = str(e)
            code = 500

        # Try to import the Redis health helper from the API module if present
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
            out.pop("redis", None)

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
            try:
                from api.updates import is_redis_healthy
                g_redis.set(1 if is_redis_healthy() else 0)
            except Exception:
                g_redis.set(0)
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
            try:
                from api.updates import is_redis_healthy
                ok = is_redis_healthy()
                lines.append(f"redis_up {1 if ok else 0}")
            except Exception:
                lines.append("redis_up 0")
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
        results = {"updates": [], "sops": [], "lessons": []}

        if query:
            # Case-insensitive search
            query_filter = f"%{query}%"

            # Updates
            updates_rows = (
                Update.query.filter(Update.message.ilike(query_filter))
                .order_by(Update.timestamp.desc())
                .all()
            )
            for upd in updates_rows:
                results["updates"].append({
                    "id": upd.id,
                    "title": upd.message[:50] + ("..." if len(upd.message) > 50 else ""),
                    "timestamp": upd.timestamp,
                    "url": url_for("show_updates") + f"#update-{upd.id}"
                })

            # SOP Summaries
            sops_rows = (
                SOPSummary.query.filter(
                    (SOPSummary.title.ilike(query_filter)) |
                    (SOPSummary.summary_text.ilike(query_filter))
                ).order_by(SOPSummary.created_at.desc()).all()
            )
            for sop in sops_rows:
                results["sops"].append({
                    "id": sop.id,
                    "title": sop.title,
                    "url": url_for("view_sop_summary", summary_id=sop.id)
                })

            # Lessons Learned
            lessons_rows = (
                LessonLearned.query.filter(
                    (LessonLearned.title.ilike(query_filter)) |
                    (LessonLearned.content.ilike(query_filter))
                ).order_by(LessonLearned.created_at.desc()).all()
            )
            for lesson in lessons_rows:
                results["lessons"].append({
                    "id": lesson.id,
                    "title": lesson.title,
                    "url": url_for("view_lesson_learned", lesson_id=lesson.id)
                })

        return render_template("search_results.html", query=query, results=results)

    @app.route("/")
    def home():
        summaries = SOPSummary.query.order_by(SOPSummary.created_at.desc()).all()
        lessons = LessonLearned.query.order_by(LessonLearned.created_at.desc()).all()
        return render_template("home.html", app_name=app.config["APP_NAME"], summaries=summaries, lessons=lessons)

    @app.route("/updates")
    def show_updates():
        rows = (
            db.session.query(Update, func.count(ReadLog.id).label('read_count'))
            .outerjoin(ReadLog, ReadLog.update_id == Update.id)
            .group_by(Update.id)
            .order_by(Update.timestamp.desc())
            .all()
        )

        updates = []
        now_utc = datetime.now(pytz.UTC)
        for upd, count in rows:
            d = upd.to_dict()
            d['read_count'] = count

            # determine if it's within last 24 hours
            if upd.timestamp.tzinfo is None:
                ts_utc = upd.timestamp.replace(tzinfo=pytz.UTC)
            else:
                ts_utc = upd.timestamp.astimezone(pytz.UTC)
            d['is_new'] = (now_utc - ts_utc) <= timedelta(hours=24)

            updates.append(d)

        return render_template("show.html", app_name=app.config["APP_NAME"], updates=updates)

    @app.route("/post", methods=["GET", "POST"])
    @login_required
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
                timestamp=datetime.now(pytz.UTC),
            )
            try:
                db.session.add(new_update)
                db.session.commit()
                flash("✅ Update posted.")
            except Exception:
                db.session.rollback()
                flash("⚠️ Failed to post update.")
            return redirect(url_for("show_updates"))

        return render_template("post.html", app_name=app.config["APP_NAME"], processes=processes)

    @app.route("/edit/<update_id>", methods=["GET", "POST"])
    @login_required
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
            update.timestamp = datetime.now(pytz.UTC)
            try:
                db.session.commit()
                flash("✏️ Update edited successfully.")
            except Exception:
                db.session.rollback()
                flash("⚠️ Failed to edit update.")
            return redirect(url_for("show_updates"))

        return render_template(
            "edit.html",
            app_name=app.config["APP_NAME"],
            update=update.to_dict(),
        )

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
        
        try:
            db.session.delete(update)
            db.session.commit()
            flash("✅ Update deleted.")
        except Exception as e:
            db.session.rollback()
            flash("❌ Deletion failed.")
            print("DB Error:", e)
            
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
                return redirect(url_for("show_updates"))
            flash("🚫 Invalid credentials.")
            return redirect(url_for("login"))
        return render_template("login.html", app_name=app.config["APP_NAME"])

    @app.route("/logout")
    def logout():
        session.pop("user_id", None)
        flash("👋 You’ve been logged out.")
        return redirect(url_for("home"))
    
    # New routes for SOP Summaries
    @app.route("/sop_summaries")
    @login_required
    def list_sop_summaries():
        sops = SOPSummary.query.order_by(SOPSummary.created_at.desc()).all()
        return render_template("sop_summaries.html", sops=sops)

    @app.route("/sop_summaries/add", methods=["GET", "POST"])
    @login_required
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
                return redirect(url_for("list_sop_summaries"))
            except Exception as e:
                db.session.rollback()
                flash("Failed to add SOP Summary.")
                print("DB Error:", e)
                return redirect(url_for("add_sop_summary"))

        return render_template("add_sop_summary.html")

    @app.route("/sop_summaries/edit/<int:sop_id>", methods=["GET", "POST"])
    @login_required
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
                flash("SOP Summary updated successfully.")
            except Exception as e:
                db.session.rollback()
                flash("Failed to update SOP Summary.")
                print("DB Error:", e)
            return redirect(url_for("list_sop_summaries"))

        return render_template("edit_sop_summary.html", sop=sop)

    @app.route("/sop_summaries/delete/<int:sop_id>", methods=["POST"])
    @login_required
    def delete_sop_summary(sop_id):
        sop = SOPSummary.query.get(sop_id)
        if not sop:
            flash("⚠️ SOP Summary not found.")
            return redirect(url_for("list_sop_summaries"))
        try:
            db.session.delete(sop)
            db.session.commit()
            flash("✅ SOP Summary deleted.")
        except Exception as e:
            db.session.rollback()
            flash("❌ Failed to delete SOP Summary.")
            print("DB Error:", e)
        return redirect(url_for("list_sop_summaries"))

    # New routes for Lessons Learned
    @app.route("/lessons_learned")
    @login_required
    def list_lessons_learned():
        lessons = LessonLearned.query.order_by(LessonLearned.created_at.desc()).all()
        return render_template("lessons_learned.html", lessons=lessons)

    @app.route("/lessons_learned/add", methods=["GET", "POST"])
    @login_required
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
                return redirect(url_for("list_lessons_learned"))
            except Exception as e:
                db.session.rollback()
                flash("Failed to add Lesson Learned.")
                print("DB Error:", e)
                return redirect(url_for("add_lesson_learned"))

        return render_template("add_lesson_learned.html")

    @app.route("/lessons_learned/edit/<int:lesson_id>", methods=["GET", "POST"])
    @login_required
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
                flash("Lesson Learned updated successfully.")
            except Exception as e:
                db.session.rollback()
                flash("Failed to update Lesson Learned.")
                print("DB Error:", e)
            return redirect(url_for("list_lessons_learned"))

        return render_template("edit_lesson_learned.html", lesson=lesson)

    @app.route("/lessons_learned/delete/<int:lesson_id>", methods=["POST"])
    @login_required
    def delete_lesson_learned(lesson_id):
        lesson = LessonLearned.query.get(lesson_id)
        if not lesson:
            flash("Lesson Learned not found.")
            return redirect(url_for("list_lessons_learned"))
        try:
            db.session.delete(lesson)
            db.session.commit()
            flash("Lesson Learned deleted successfully.")
        except Exception as e:
            db.session.rollback()
            flash("Failed to delete Lesson Learned.")
        return redirect(url_for("list_lessons_learned"))
    
    @app.route('/api/latest-update-time')
    def latest_update_time():
        latest = Update.query.order_by(Update.timestamp.desc()).first()
        if latest:
            return jsonify({'latest_timestamp': latest.timestamp.isoformat()})
        return jsonify({'latest_timestamp': None})
        
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

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
