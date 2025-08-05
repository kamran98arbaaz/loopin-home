import os
import uuid
import pytz
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_migrate import Migrate
from read_logs import bp as read_logs_bp
from flask_login import LoginManager
from models import User, Update, ReadLog
from extensions import db

# Load .env
load_dotenv()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login'

IST = pytz.timezone("Asia/Kolkata")

def create_app(config_name=None):
    app = Flask(__name__)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(read_logs_bp)

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
    if parsed.scheme not in ("postgresql", "postgres"):
        raise RuntimeError(f"Unsupported DB scheme: {parsed.scheme}")
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    sslmode = os.getenv("PG_SSLMODE")
    if sslmode:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"sslmode": sslmode}}

    db.init_app(app)

    with app.app_context():
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

    # Routes    
    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ok", "db": "reachable"}), 200
        except Exception as e:
            return jsonify({"status": "error", "db": str(e)}), 500

    @app.route("/")
    def home():
        return render_template("home.html", app_name=app.config["APP_NAME"])

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
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
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
                timestamp=datetime.utcnow().replace(tzinfo=pytz.UTC),
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
            update.timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC)
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
        print("🔥 DELETE requested for ID:", update_id)
        
        update = Update.query.get(update_id)
        print("🔍 Found update object:", update)
        
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
            print("🧨 DB Error:", e)
            
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
    
        # [ ... API route for notifications ... ]

    @app.route('/api/latest-update-time')
    def latest_update_time():
        latest = Update.query.order_by(Update.timestamp.desc()).first()
        if latest:
            return jsonify({'latest_timestamp': latest.timestamp.isoformat()})
        return jsonify({'latest_timestamp': None})
        
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
