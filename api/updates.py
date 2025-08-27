from flask import Blueprint, jsonify, request, url_for
from datetime import datetime, timedelta
import pytz

from models import Update
from extensions import db
from timezone_utils import UTC, now_utc, ensure_timezone, is_within_hours

import os
try:
    import redis as _redis
except Exception:
    _redis = None

_cached_redis = None

def get_redis_client():
    """Return a redis client if REDIS_URL configured, or None.

    Caches the client so repeated calls are cheap.
    Uses short timeouts to prevent performance issues.
    """
    global _cached_redis
    # If tests or other code injected a redis_client, prefer it
    if "redis_client" in globals() and globals().get("redis_client") is not None:
        injected = globals().get("redis_client")
        if _cached_redis is not injected:
            _cached_redis = injected
        return _cached_redis
    if _cached_redis is not None:
        return _cached_redis
    if not _redis:
        _cached_redis = None
        return None
    url = os.environ.get("REDIS_URL")
    if not url:
        _cached_redis = None
        return None
    try:
        # Use short timeouts to prevent blocking
        _cached_redis = _redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=1.0,  # 1 second timeout
            socket_connect_timeout=1.0,  # 1 second connection timeout
            health_check_interval=30  # Check health every 30 seconds
        )
    except Exception:
        _cached_redis = None
    return _cached_redis


# Rate limit defaults (can be overridden via env)
def _get_rate_config():
    try:
        limit = int(os.environ.get("API_RATE_LIMIT", "5"))
    except Exception:
        limit = 5
    try:
        window = int(os.environ.get("API_RATE_WINDOW", "60"))
    except Exception:
        window = 60
    return limit, window


def is_redis_healthy():
    """Quick probe to check if Redis is reachable.

    Returns True if a ping succeeds, otherwise False.
    Uses a very short timeout to avoid performance issues.
    """
    r = get_redis_client()
    if not r:
        return False
    try:
        # Set a very short timeout to avoid blocking
        r.ping()
        return True
    except Exception:
        return False

bp = Blueprint("api", __name__, url_prefix="/api")


def _serialize_update(upd, current_time):
    ts = upd.timestamp
    if ts is None:
        ts_iso = None
        is_new = False
    else:
        ts = ensure_timezone(ts, UTC)
        ts_iso = ts.isoformat()
        is_new = is_within_hours(ts, 24, current_time)

    return {
        "id": upd.id,
        "name": getattr(upd, "name", None),
        "process": getattr(upd, "process", None),
        "message": getattr(upd, "message", None),
        "timestamp": ts_iso,
        "is_new": is_new,
    }


@bp.route("/updates")
def get_updates():
    """List updates with pagination and optional process filter.

    Query params:
      - page (int, default 1)
      - per_page (int, default 25, max 100)
      - process (string, optional)
    """
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get("per_page", 25))
    except ValueError:
        per_page = 25
    per_page = max(1, min(per_page, 100))

    process_filter = request.args.get("process")

    q = Update.query
    if process_filter:
        q = q.filter(Update.process == process_filter)

    total = None
    try:
        total = q.count()
        rows = q.order_by(Update.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
    except Exception:
        # If DB isn't ready, return an empty paginated structure
        meta = {
            "page": page,
            "per_page": per_page,
            "total": 0,
            "next": None,
            "prev": None,
        }
        return jsonify({"items": [], "meta": meta})

    current_time = now_utc()
    items = [_serialize_update(u, current_time) for u in rows]

    # Build minimal pagination links
    def _link(p):
        return url_for("api.get_updates", page=p, per_page=per_page, process=process_filter, _external=False)

    meta = {
        "page": page,
        "per_page": per_page,
        "total": total,
        "next": _link(page + 1) if (page * per_page) < total else None,
        "prev": _link(page - 1) if page > 1 else None,
    }

    return jsonify({"items": items, "meta": meta})


@bp.route("/openapi.json")
def openapi():
    # Minimal machine-readable description for the API
    return jsonify({
        "openapi": "3.0.0",
        "info": {"title": "LoopIn API", "version": "0.1"},
        "paths": {
            "/api/updates": {
                "get": {
                    "summary": "List updates",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "process", "in": "query", "schema": {"type": "string"}},
                    ],
                }
            }
        }
    })


@bp.route('/health/redis')
def redis_health():
    """Return Redis connectivity status for health checks."""
    try:
        ok = is_redis_healthy()
        if ok:
            return jsonify({'redis': 'ok'}), 200
        return jsonify({'redis': 'unavailable'}), 503
    except Exception as e:
        return jsonify({'redis': 'error', 'details': str(e)}), 500



@bp.route("/updates", methods=["POST"])
def post_update():
    """Create a new update. Simple API key auth via X-API-KEY header.

    Body (json): {"id": "optional-id", "name": "", "process": "", "message": ""}
    """
    # Allow logged-in session users to post without API key
    api_key = request.headers.get("X-API-KEY")
    user_id = None
    try:
        user_id = request.environ.get('beaker.session') and request.environ['beaker.session'].get('user_id')
    except Exception:
        user_id = None

    # Fallback: Flask session uses session['user_id'] set in app.py
    from flask import session
    if not user_id and session.get("user_id"):
        user_id = session.get("user_id")

    expected = None
    try:
        import os

        expected = os.environ.get("API_WRITE_KEY")
    except Exception:
        expected = None

    # If not logged in, require API key
    if not user_id and (not expected or api_key != expected):
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}

    # Validation and sanitization
    from markupsafe import escape

    def _clean_text(v, maxlen=2000):
        if v is None:
            return None
        s = str(v).strip()
        if len(s) > maxlen:
            return s[:maxlen]
        return escape(s)

    # Try to use marshmallow for stronger validation when available
    try:
        from marshmallow import Schema, fields, validate, ValidationError

        class UpdateSchema(Schema):
            id = fields.Str(required=False)
            name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
            process = fields.Str(required=True, validate=validate.Length(min=1, max=64))
            message = fields.Str(required=True, validate=validate.Length(min=1, max=4000))

        def _validate_with_schema(data):
            try:
                s = UpdateSchema()
                return s.load(data)
            except ValidationError as e:
                return {"_errors": e.messages}
    except Exception:
        UpdateSchema = None
        def _validate_with_schema(data):
            return data

    # Validate payload using marshmallow when available
    validated = _validate_with_schema(data)
    if isinstance(validated, dict) and validated.get("_errors"):
        return jsonify({"error": "validation", "details": validated["_errors"]}), 400

    if UpdateSchema:
        id_val = validated.get("id")
        name = _clean_text(validated.get("name"))
        process = _clean_text(validated.get("process"), maxlen=64)
        message = _clean_text(validated.get("message"), maxlen=4000)
    else:
        id_val = data.get("id")
        name = _clean_text(data.get("name")) if data.get("name") else None
        process = _clean_text(data.get("process"), maxlen=64) if data.get("process") else None
        message = _clean_text(data.get("message"), maxlen=4000) if data.get("message") else None

    # If user is logged in, override name with display_name
    if user_id:
        try:
            from models import User

            # Use session.get to avoid SQLAlchemy Query.get deprecation
            from extensions import db as _db
            uobj = _db.session.get(User, user_id)
            if uobj:
                name = uobj.display_name
        except Exception:
            pass

    if not name or not process or not message:
        return jsonify({"error": "name, process and message are required"}), 400

    # Rate limiter: prefer Redis-backed sliding window when REDIS_URL is configured.
    # Fallback to simple in-memory window per-process store for tests / dev.
    from time import time

    key = f"user:{user_id}" if user_id else f"ip:{request.remote_addr}"
    limit, window = _get_rate_config()

    def _redis_allowed(rclient, key, window, limit):
        # Prefer to use a sliding-window Lua script for more accurate limits.
        # If that fails, fall back to fixed-window INCR+EXPIRE.
        now_ts = int(now_utc().timestamp())
        rk = f"rate:api_post:{key}"
        member = f"{now_ts}:{os.getpid()}:{int(now_ts * 1e6)}"

        lua_sha = globals().get("_rate_lua_sha")
        script = (
            "local rk=KEYS[1]\n"
            "local now=tonumber(ARGV[1])\n"
            "local window=tonumber(ARGV[2])\n"
            "local member=ARGV[3]\n"
            "redis.call('ZREMRANGEBYSCORE', rk, 0, now - window)\n"
            "redis.call('ZADD', rk, now, member)\n"
            "redis.call('EXPIRE', rk, window + 5)\n"
            "local cnt=redis.call('ZCARD', rk)\n"
            "return cnt\n"
        )
        try:
            # Try evalsha if we've cached it
            if lua_sha:
                try:
                    cnt = rclient.evalsha(lua_sha, 1, rk, now_ts, window, member)
                except Exception:
                    # Register script and retry eval
                    lua_sha = rclient.script_load(script)
                    globals()['_rate_lua_sha'] = lua_sha
                    cnt = rclient.evalsha(lua_sha, 1, rk, now_ts, window, member)
            else:
                # Either load script or run eval directly
                try:
                    lua_sha = rclient.script_load(script)
                    globals()['_rate_lua_sha'] = lua_sha
                    cnt = rclient.evalsha(lua_sha, 1, rk, now_ts, window, member)
                except Exception:
                    # Some redis clients (or fakeredis) may not support script_load; fallback to eval
                    cnt = rclient.eval(script, 1, rk, now_ts, window, member)

            return int(cnt) <= int(limit)
        except Exception:
            # Fallback to fixed-window behavior if Lua fails
            try:
                bucket = now_ts // int(window)
                fk = f"rate:api_post:{key}:{bucket}"
                cur = rclient.incr(fk)
                if int(cur) == 1:
                    rclient.expire(fk, int(window))
                return int(cur) <= int(limit)
            except Exception:
                # On Redis errors, deny by default
                return False

    allowed = None
    # Prefer an injected module-level redis_client for tests; otherwise use get_redis_client()
    rclient = globals().get("redis_client") if globals().get("redis_client") is not None else get_redis_client()
    if rclient:
        try:
            allowed = _redis_allowed(rclient, key, window, limit)
        except Exception:
            allowed = None

    if allowed is None:
        if rclient:
            # Redis is configured but the Redis check failed; fail-open to avoid
            # incorrectly applying per-process in-memory limits (safer for
            # transient Redis issues). This prevents cross-test interference in
            # the test suite as well.
            allowed = True
        else:
            # Fallback in-memory limiter
            if not hasattr(post_update, "_rate_store"):
                post_update._rate_store = {}
            store = post_update._rate_store
            rclient = globals().get("redis_client") if globals().get("redis_client") is not None else get_redis_client()
            if rclient:
                allowed = _redis_allowed(rclient, key, window, limit)
                if not allowed:
                    return jsonify({"error": "rate_limited"}), 429
            else:
                # Fallback in-memory limiter
                if not hasattr(post_update, "_rate_store"):
                    post_update._rate_store = {}
                store = post_update._rate_store
                now = time()
                hits = store.get(key, [])
                # prune
                hits = [t for t in hits if now - t < window]
                if len(hits) >= limit:
                    return jsonify({"error": "rate_limited"}), 429
                hits.append(now)
                store[key] = hits
    # create and persist the Update now that rate limiting passed
    from extensions import db
    # Use the imported Update model

    if not id_val:
        import uuid
        id_val = uuid.uuid4().hex

    u = Update(id=id_val, name=name, process=process, message=message, timestamp=now_utc())
    try:
        db.session.add(u)
        db.session.commit()
        
        # Broadcast the new update via Socket.IO
        try:
            from api.socketio import broadcast_update
            update_data = u.to_dict()
            broadcast_update(update_data, process)
        except Exception as e:
            # Socket.IO broadcasting failure shouldn't break the API
            print(f"Socket.IO broadcast failed: {e}")
            
    except Exception:
        db.session.rollback()
        return jsonify({"error": "db_error"}), 500

    return jsonify({"id": u.id}), 201


@bp.route("/updates/<update_id>", methods=["DELETE"])
def delete_update_api(update_id):
    """Delete an update via API. Requires authentication."""
    from flask import session
    from flask_login import current_user

    # Check if user is authenticated
    if not session.get("user_id") and not (hasattr(current_user, 'is_authenticated') and current_user.is_authenticated):
        return jsonify({"error": "Authentication required"}), 401

    try:
        # Get the update
        update = Update.query.get(update_id)
        if not update:
            return jsonify({"error": "Update not found"}), 404

        # Check if user owns the update or is admin
        user_id = session.get("user_id")
        if user_id:
            from models import User
            user = User.query.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 401

            # Check ownership or admin role
            if update.name.strip().lower() != user.display_name.strip().lower() and user.role != 'admin':
                return jsonify({"error": "Not authorized to delete this update"}), 403
        elif hasattr(current_user, 'display_name'):
            # Flask-Login user
            if update.name.strip().lower() != current_user.display_name.strip().lower() and getattr(current_user, 'role', None) != 'admin':
                return jsonify({"error": "Not authorized to delete this update"}), 403
        else:
            return jsonify({"error": "Authentication required"}), 401

        # Capture details before deletion
        entity_title = f"Update: {update.message[:50]}..."

        # Capture user info before deletion (while session is still available)
        current_user_id = session.get("user_id")

        # Get client IP address
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        # Get user agent
        user_agent = request.headers.get('User-Agent', 'Unknown')

        # Archive the update before deletion
        from models import ArchivedUpdate
        import pytz
        from datetime import datetime

        archived_update = ArchivedUpdate(
            id=update.id,
            name=update.name,
            process=update.process,
            message=update.message,
            timestamp=update.timestamp,
            archived_at=now_utc(),
            archived_by=current_user_id
        )
        db.session.add(archived_update)

        # Delete the update
        db.session.delete(update)
        db.session.commit()

        # Log activity after successful deletion
        try:
            from models import ActivityLog
            import pytz
            from datetime import datetime

            activity = ActivityLog(
                user_id=current_user_id,
                action='deleted',
                entity_type='update',
                entity_id=str(update_id),
                entity_title=entity_title,
                timestamp=now_utc(),
                ip_address=client_ip,
                user_agent=user_agent,
                details='Deleted via API'
            )

            db.session.add(activity)
            db.session.commit()
        except Exception as e:
            # Don't let activity logging break the API response
            print(f"Activity logging failed in API: {e}")

        return jsonify({"success": True, "message": "Update deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete update: {str(e)}"}), 500
