# app.py
import os
import uuid
import pytz
import re  # ✅ Added for username validation
from datetime import datetime
from urllib.parse import urlparse

from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_migrate import Migrate

# Load .env if present
load_dotenv()
IST = pytz.timezone("Asia/Kolkata")
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    migrate.init_app(app, db)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-secure-random-string")
    app.config["APP_NAME"] = "LoopIn"

    # Database Config
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

    #
    # Models
    #
    class Update(db.Model):
        __tablename__ = "updates"
        id = db.Column(db.String(32), primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        message = db.Column(db.Text, nullable=False)
        process = db.Column(db.String(32), nullable=False)
        timestamp = db.Column(db.DateTime, nullable=False)

        def to_dict(self):
            utc_ts = self.timestamp.replace(tzinfo=pytz.UTC)
            ist_ts = utc_ts.astimezone(IST)
            return {
                "id": self.id,
                "name": self.name,
                "process": self.process,
                "message": self.message,
                "timestamp": ist_ts.strftime("%d/%m/%Y, %H:%M:%S"),
            }

    class User(db.Model):
        __tablename__ = "users"
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(50), unique=True, nullable=False)
        display_name = db.Column(db.String(80), nullable=False)
        password_hash = db.Column(db.String(128), nullable=False)

        def set_password(self, raw_password):
            self.password_hash = generate_password_hash(raw_password)

        def check_password(self, raw_password):
            return check_password_hash(self.password_hash, raw_password)

    #
    # Auth Helpers
    #
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

    #
    # Routes
    #
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
        updates = Update.query.order_by(Update.timestamp.desc()).all()
        return render_template(
            "show.html",
            app_name=app.config["APP_NAME"],
            updates=[u.to_dict() for u in updates],
        )

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
        update = Update.query.get(update_id)
        current = inject_current_user()["current_user"]
        if not update or update.name != current.display_name:
            flash("🚫 Unauthorized or not found.")
            return redirect(url_for("show_updates"))

        try:
            db.session.delete(update)
            db.session.commit()
            flash("🗑️ Update deleted.")
        except Exception:
            db.session.rollback()
            flash("⚠️ Failed to delete update.")
        return redirect(url_for("show_updates"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            display_name = request.form["display_name"].strip()
            username = request.form["username"].strip().replace(" ", "_").lower()
            password = request.form["password"]

            # ✅ Validate characters in username
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

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
