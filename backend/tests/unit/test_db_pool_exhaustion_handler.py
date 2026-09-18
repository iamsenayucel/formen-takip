"""DB havuzu tükendiğinde (SQLAlchemy TimeoutError) 503 + DB_POOL_EXHAUSTED
dönüldüğünü doğrular — genel 500 INTERNAL_ERROR yerine ayrık bir sinyal.

Gerçek havuzu tüketmez; küçük, izole bir FastAPI app üzerinde route'un
doğrudan hatayı fırlatmasıyla handler'ı test eder (DB gerektirmez).
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as SATimeoutError

from app.core.error_handlers import register_exception_handlers


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise SATimeoutError("QueuePool limit of size 5 overflow 10 reached, connection timed out")

    return app


class TestDbPoolExhaustionHandler:
    def test_returns_503_with_dedicated_error_code(self):
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/boom")
        assert resp.status_code == 503
        body = resp.json()
        assert body["error"]["code"] == "DB_POOL_EXHAUSTED"

    def test_response_does_not_leak_connection_details(self):
        client = TestClient(_build_app(), raise_server_exceptions=False)
        resp = client.get("/boom")
        body = resp.json()
        assert "postgresql" not in body["error"]["message"].lower()
        assert "password" not in body["error"]["message"].lower()
