import os
import json
from app import create_app
from extensions import db
from models import Update, User


def test_post_update_session_user(tmp_path):
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        # create users and updates table
        Update.__table__.create(db.engine)
        User.__table__.create(db.engine)
        u = User(username="john", display_name="John Doe", password_hash="x")
        db.session.add(u)
        db.session.commit()
        user_id = u.id

    client = app.test_client()
    # set session by logging in via the app's session mechanism
    with client.session_transaction() as sess:
        sess["user_id"] = user_id

    resp = client.post("/api/updates", json={"process": "ABC", "message": "from session user", "name": "ignored"})
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert "id" in data


def test_rate_limiting(tmp_path):
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["API_WRITE_KEY"] = "rl-key"

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        Update.__table__.create(db.engine)

    client = app.test_client()
    headers = {"X-API-KEY": "rl-key"}
    # Reset in-memory rate limiter to avoid interference from other tests
    try:
        from api.updates import post_update

        post_update._rate_store = {}
    except Exception:
        pass
    # perform up to 10 posts and ensure we see rate limiting kick in
    statuses = []
    for i in range(10):
        resp = client.post("/api/updates", headers=headers, json={"name": f"n{i}", "process": "ABC", "message": "hi"})
        statuses.append(resp.status_code)

    success = sum(1 for s in statuses if s == 201)
    rate_limited = any(s == 429 for s in statuses)

    # Expect at most `limit` successes and at least one 429 when the limiter works.
    assert success <= 5
    assert rate_limited


def test_rate_limiting_with_redis(tmp_path):
    # Ensure the Redis-backed path is exercised using fakeredis
    try:
        import fakeredis
    except Exception:
        # If fakeredis isn't installed in the environment, skip this test
        import pytest

        pytest.skip("fakeredis not available")

    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["API_WRITE_KEY"] = "rl-key"

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        Update.__table__.create(db.engine)

    # Inject a fake redis client into the api module
    from api import updates as api_updates

    server = fakeredis.FakeServer()
    fake = fakeredis.FakeRedis(server=server, decode_responses=True)
    api_updates.redis_client = fake
    # Ensure the fake redis starts clean for this test run
    try:
        fake.flushdb()
    except Exception:
        pass

    client = app.test_client()
    headers = {"X-API-KEY": "rl-key"}

    # Make a single request and assert the fake redis was used (a rate key exists).
    resp = client.post("/api/updates", headers=headers, json={"name": "n1", "process": "ABC", "message": "hi"})
    assert resp.status_code in (201, 429)

    # Confirm redis got a rate key for this client
    keys = fake.keys("rate:api_post*")
    assert len(keys) >= 1
