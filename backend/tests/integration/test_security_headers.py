from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.security_headers import API_CSP
from app.main import app
from app.models.enums import Role

_BASE_HEADER_NAMES = [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Content-Security-Policy",
]


def _assert_baseline_headers(resp, *, expected_csp: str | None = None):
    for name in _BASE_HEADER_NAMES:
        assert resp.headers.get(name), f"missing {name} on {resp.request.method} {resp.request.url.path}"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    if expected_csp is not None:
        assert resp.headers["Content-Security-Policy"] == expected_csp


def _assert_no_duplicate_headers(resp):
    raw_names = [name.lower() for name, _ in resp.headers.multi_items()]
    for name in _BASE_HEADER_NAMES:
        count = raw_names.count(name.lower())
        assert count == 1, f"{name} appears {count} times on {resp.request.method} {resp.request.url.path}"


class TestSuccessResponses:
    def test_health_has_security_headers(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)

    def test_authenticated_api_response_has_security_headers(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)


class TestErrorResponses:
    def test_404_unknown_route_has_security_headers(self, client):
        resp = client.get("/api/v1/this-route-does-not-exist")
        assert resp.status_code == 404
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)

    def test_422_validation_error_has_security_headers(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/trend?granularity=bogus", headers=auth_headers)
        assert resp.status_code == 422
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)

    def test_401_unauthenticated_has_security_headers(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)

    def test_403_forbidden_has_security_headers(self, client, auth_headers, role_assignment_factory):
        role_assignment_factory(role=Role.FOREMAN)
        resp = client.get("/api/v1/anomalies", headers=auth_headers)
        assert resp.status_code == 403
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)

    def test_503_service_unavailable_has_security_headers(self, client, monkeypatch):
        import app.main as main_module

        class _BrokenSession:
            def __enter__(self):
                raise RuntimeError("simulated database outage")

            def __exit__(self, *exc_info):
                return False

        monkeypatch.setattr(main_module, "SessionLocal", lambda: _BrokenSession())
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)


class TestUnhandledException:
    def test_500_from_unhandled_exception_has_security_headers(self):
        app.add_api_route("/__test_only/unhandled-exception", _raise_unexpected, methods=["GET"])
        route = app.router.routes[-1]
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/__test_only/unhandled-exception")
            assert resp.status_code == 500
            _assert_baseline_headers(resp, expected_csp=API_CSP)
            _assert_no_duplicate_headers(resp)
        finally:
            app.router.routes.remove(route)


def _raise_unexpected():
    raise RuntimeError("simulated unexpected failure for security-header regression test")


class TestCorsPreflight:
    def test_preflight_for_allowed_origin_has_cors_and_security_headers(self, client):
        allowed_origin = get_settings().cors_origins[0]
        resp = client.options(
            "/api/v1/dashboard/summary",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == allowed_origin
        _assert_baseline_headers(resp, expected_csp=API_CSP)
        _assert_no_duplicate_headers(resp)

    def test_preflight_for_disallowed_origin_stays_fail_closed(self, client):
        resp = client.options(
            "/api/v1/dashboard/summary",
            headers={
                "Origin": "https://not-an-allowed-origin.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in {k.lower() for k in resp.headers.keys()}
        _assert_no_duplicate_headers(resp)


class TestDocsScopedCsp:
    def test_swagger_ui_gets_scoped_csp(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
        csp = resp.headers["Content-Security-Policy"]
        assert csp != API_CSP
        assert "https://cdn.jsdelivr.net" in csp
        assert "'unsafe-inline'" not in csp
        assert "'unsafe-eval'" not in csp
        _assert_no_duplicate_headers(resp)

    def test_redoc_gets_scoped_csp(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200
        csp = resp.headers["Content-Security-Policy"]
        assert csp != API_CSP
        assert "fonts.googleapis.com" in csp
        assert "'unsafe-inline'" not in csp
        assert "'unsafe-eval'" not in csp
        _assert_no_duplicate_headers(resp)

    def test_openapi_json_keeps_strict_api_csp(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        _assert_baseline_headers(resp, expected_csp=API_CSP)
