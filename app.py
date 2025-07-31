import os
import uuid
import pytz
from datetime import datetime
from urllib.parse import urlparse

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
from dotenv import load_dotenv
from sqlalchemy import text

# Load .env locally if present
load_dotenv()

# Timezone helpers
IST = pytz.timezone("Asia/Kolkata")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-with-a-secure-random-string")
app.config["APP_NAME"] = "LoopIn"

# ---------- DATABASE CONFIGURATION & VALIDATION ----------

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in environment.")

# Basic sanity check / parsing
try:
    parsed = urlparse(DATABASE_URL)
    if parsed.scheme not in ("postgresql", "postgres"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")
    if parsed.port is None:
        raise ValueError("No port parsed from DATABASE_URL.")
except Exception as e:
    raise RuntimeError(f"Invalid DATABASE_URL '{DATABASE_URL}': {e}")

# Support optional SSL mode (some managed Postgres require it)
sslmode = os.getenv("PG_SSLMODE")  # e.g., "require"
if sslmode:
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"sslmode": sslmode}
    }

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# ---------- MODEL ----------

class Update(db.Model):
    __tablename__ = "updates"
    id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)  # stored in UTC

    def to_dict(self):
        # convert to IST for display
        utc_ts = self.timestamp
        if utc_ts.tzinfo is None:
            utc_ts = utc_ts.replace(tzinfo=pytz.UTC)
        ist_ts = utc_ts.astimezone(IST)
        return {
            "id": self.id,
            "name": self.name,
            "message": self.message,
            "timestamp": ist_ts.strftime("%d/%m/%Y, %H:%M:%S"),
        }


# ---------- AUTHORIZED USERS ----------

authorized_users = ["Kamran Arbaz", "Drishya CM", "Abigail Das"]


# ---------- ROUTES ----------

@app.route("/health")
def health():
    try:
        # Explicitly wrap SQL string using text()
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
    current_user = session.get("username")
    return render_template(
        "show.html",
        app_name=app.config["APP_NAME"],
        updates=[u.to_dict() for u in updates],
        current_user=current_user,
    )


@app.route("/post", methods=["GET", "POST"])
def post_update():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            name = (data.get("name") or "").strip()
            message = (data.get("message") or "").strip()

            if not name or not message:
                return jsonify({"success": False, "error": "Missing name or message."}), 400

            if name not in authorized_users:
                return jsonify({"success": False, "error": "Unauthorized."}), 403

            new_update = Update(
                id=uuid.uuid4().hex,
                name=name,
                message=message,
                timestamp=datetime.utcnow().replace(tzinfo=pytz.UTC),
            )
            try:
                db.session.add(new_update)
                db.session.commit()
                return jsonify({"success": True, "update": new_update.to_dict()}), 201
            except Exception as e:
                db.session.rollback()
                return jsonify({"success": False, "error": str(e)}), 500

        name = request.form.get("name", "").strip()
        message = request.form.get("message", "").strip()

        if name not in authorized_users:
            flash("🚫 You are not authorized to post updates.")
            return redirect(url_for("post_update"))

        session["username"] = name

        new_update = Update(
            id=uuid.uuid4().hex,
            name=name,
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

    current_user = session.get("username")
    return render_template(
        "post.html",
        app_name=app.config["APP_NAME"],
        authorized_users=authorized_users,
        current_user=current_user,
    )


@app.route("/edit/<update_id>", methods=["GET", "POST"])
def edit_update(update_id):
    update = Update.query.get(update_id)
    if not update:
        flash("⚠️ Update not found.")
        return redirect(url_for("show_updates"))

    current_user = session.get("username")
    if update.name != current_user:
        flash("🚫 You can only edit your own updates.")
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
        "edit.html", app_name=app.config["APP_NAME"], update=update.to_dict()
    )


@app.route("/delete/<update_id>", methods=["POST"])
def delete_update(update_id):
    update = Update.query.get(update_id)
    if not update:
        flash("⚠️ Update not found.")
        return redirect(url_for("show_updates"))

    current_user = session.get("username")
    if update.name != current_user:
        flash("🚫 You can only delete your own updates.")
        return redirect(url_for("show_updates"))

    try:
        db.session.delete(update)
        db.session.commit()
        flash("🗑️ Update deleted.")
    except Exception:
        db.session.rollback()
        flash("⚠️ Failed to delete update.")
    return redirect(url_for("show_updates"))


# ---------- ENTRYPOINT ----------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # ensure schema exists on startup (used when running directly)
    try:
        with app.app_context():
            db.create_all()
    except Exception as e:
        print("Failed to create/ensure schema:", e)
        raise
    app.run(host="0.0.0.0", port=port)
