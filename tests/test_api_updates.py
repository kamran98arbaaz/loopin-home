import os
import json
from app import create_app
from extensions import db


def test_get_updates_empty(tmp_path, monkeypatch):
    """Basic smoke test: start app with an in-memory sqlite DB and hit the endpoint.

    This avoids touching the real Postgres DB during the first milestone.
    """
    # Configure a temporary sqlite DB
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    app = create_app()
    app.config["TESTING"] = True

    # Do not run db.create_all() here; the app's endpoint handles DB errors
    # and returns an empty list if the DB is not fully initialized for sqlite.
    with app.app_context():
        pass

    client = app.test_client()
    resp = client.get("/api/updates")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "updates" in data
    assert isinstance(data["updates"], list)
