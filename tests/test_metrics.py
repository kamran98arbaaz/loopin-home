from app import create_app


def test_metrics_endpoint(tmp_path):
    import os
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'db.sqlite'}"
    app = create_app()
    app.testing = True
    client = app.test_client()
    resp = client.get('/metrics')
    assert resp.status_code == 200
    assert resp.data
    # Content-Type may be prometheus or plain text depending on env
    assert 'text' in resp.content_type
