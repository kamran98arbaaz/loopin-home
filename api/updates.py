from flask import Blueprint, jsonify
from datetime import datetime, timedelta
import pytz

from models import Update

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/updates")
def get_updates():
    """Return a small JSON list of recent updates.

    This endpoint is intentionally simple for the first milestone: it
    relies on the app's DB configuration and is safe to register.
    """
    try:
        rows = Update.query.order_by(Update.timestamp.desc()).all()
    except Exception:
        # If DB isn't configured yet, return an empty response rather than 500
        return jsonify({"updates": []})

    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
    out = []
    for upd in rows:
        ts = upd.timestamp
        if ts is None:
            ts_iso = None
            is_new = False
        else:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=pytz.UTC)
            ts_iso = ts.isoformat()
            is_new = (now_utc - ts) <= timedelta(hours=24)

        out.append({
            "id": upd.id,
            "name": getattr(upd, "name", None),
            "process": getattr(upd, "process", None),
            "message": getattr(upd, "message", None),
            "timestamp": ts_iso,
            "is_new": is_new,
        })

    return jsonify({"updates": out})
