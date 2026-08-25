from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.error_handlers import register_exception_handlers
from app.core.errors import RateLimitExceededError
from app.core.rate_limit import SlidingWindowLimiter
from app.core.request_id import RequestIdMiddleware


def test_sliding_window_enforces_limit_per_identity():
    limiter = SlidingWindowLimiter()

    assert limiter.check("default:user-a", limit=2, window_seconds=60) == (True, 0)
    assert limiter.check("default:user-a", limit=2, window_seconds=60) == (True, 0)
    allowed, retry_after = limiter.check("default:user-a", limit=2, window_seconds=60)
    assert allowed is False
    assert retry_after >= 1

    assert limiter.check("default:user-b", limit=2, window_seconds=60) == (True, 0)


def test_rate_limit_error_has_retry_after_and_standard_envelope():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)

    @app.get("/limited")
    def limited():
        raise RateLimitExceededError("Limit aÅŸÄ±ldÄ±.", retry_after_seconds=17)

    response = TestClient(app).get("/limited", headers={"X-Request-Id": "rate-limit-request"})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "17"
    assert response.headers["X-Request-Id"] == "rate-limit-request"
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert response.json()["error"]["requestId"] == "rate-limit-request"
