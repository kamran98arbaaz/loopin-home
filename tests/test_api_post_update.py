import os
import json
from app import create_app
from extensions import db
from models import Update
import pytz
from datetime import datetime


def test_post_update_success(tmp_path):
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    os.environ["API_WRITE_KEY"] = "secret-key"

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        # ensure updates table exists
        Update.__table__.create(db.engine)

    client = app.test_client()
    resp = client.post(
        "/api/updates",
        headers={"X-API-KEY": "secret-key"},
        json={"name": "tester", "process": "ABC", "message": "hello"},
    )
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert "id" in data

    # verify it shows up
    resp2 = client.get("/api/updates")
    d2 = json.loads(resp2.data)
    assert d2["meta"]["total"] >= 1


def test_post_update_unauthorized(tmp_path):
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    # no API_WRITE_KEY set

    app = create_app()
    app.config["TESTING"] = True

    client = app.test_client()
    resp = client.post(
        "/api/updates",
        headers={"X-API-KEY": "wrong"},
        json={"name": "tester", "process": "ABC", "message": "hello"},
    )
    assert resp.status_code == 401
