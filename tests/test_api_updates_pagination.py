import os
import json
from app import create_app
from extensions import db
from models import Update
from datetime import datetime
import pytz


def _make_update(id_suffix, process, message):
    return Update(
        id=f"u-{id_suffix}",
        name=f"user-{id_suffix}",
        process=process,
        message=message,
    timestamp=datetime.now(pytz.UTC),
    )


def test_pagination_and_filtering(tmp_path):
    db_file = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        # Create only the updates table (avoid creating Postgres-specific types)
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if "updates" not in inspector.get_table_names():
            Update.__table__.create(db.engine)

        db.session.add_all([
            _make_update(i, "ABC", f"msg {i}") for i in range(5)
        ] + [
            _make_update(i + 10, "XYZ", f"msg {i}") for i in range(3)
        ])
        db.session.commit()

    client = app.test_client()
    # default per_page 25 should return all
    resp = client.get("/api/updates")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "items" in data and "meta" in data
    assert data["meta"]["total"] == 8

    # filter by process
    resp2 = client.get("/api/updates?process=ABC")
    d2 = json.loads(resp2.data)
    assert d2["meta"]["total"] == 5

    # pagination per_page=3 page=1
    resp3 = client.get("/api/updates?page=1&per_page=3")
    d3 = json.loads(resp3.data)
    assert len(d3["items"]) == 3
    assert d3["meta"]["page"] == 1
