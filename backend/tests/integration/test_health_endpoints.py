def test_health_is_liveness_alias(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"data": {"status": "ok", "database": None}}
    assert resp.headers["X-Request-Id"]


def test_health_live(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"data": {"status": "ok", "database": None}}
    assert resp.headers["X-Request-Id"]


def test_health_ready_reports_database_reachable(client):
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"data": {"status": "ok", "database": "reachable"}}
    assert resp.headers["X-Request-Id"]


def test_health_ready_returns_503_when_database_unreachable(client, monkeypatch):
    import app.main as main_module

    class _BrokenSession:
        def __enter__(self):
            raise RuntimeError("simulated database outage")

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(main_module, "SessionLocal", lambda: _BrokenSession())

    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert body["error"]["details"] == {"dependency": "database", "status": "unreachable"}
    assert body["error"]["requestId"] == resp.headers["X-Request-Id"]
