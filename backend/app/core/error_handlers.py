from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic.alias_generators import to_camel
from sqlalchemy.exc import TimeoutError as SATimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import clock
from app.core.config import get_settings
from app.core.errors import ApiException
from app.core.request_id import get_request_id
from app.core.security_headers import apply_baseline_security_headers
from app.db.session import engine as db_engine
from app.schemas.base import ApiError, ErrorEnvelope

logger = logging.getLogger("app.errors")

_STATUS_FALLBACK_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
}
_DEFAULT_FALLBACK_MESSAGE = "İstek işlenemedi."


def _error_response(
    request: Request, *, status_code: int, code: str, message: str, details: dict[str, Any] | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ApiError(
            code=code,
            message=message,
            request_id=get_request_id(request),
            timestamp=clock.now_utc(),
            details=details,
        )
    )
    response = JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json", by_alias=True))
    apply_baseline_security_headers(response.headers, environment=get_settings().environment)
    return response


def _validation_error_details(exc: RequestValidationError) -> dict[str, Any]:
    fields = []
    for err in exc.errors():
        loc = [to_camel(part) if isinstance(part, str) else str(part) for part in err.get("loc", ())]
        field = ".".join(loc[1:]) if len(loc) > 1 else (loc[0] if loc else "")
        fields.append({"field": field, "reason": err.get("msg", ""), "code": err.get("type", "invalid")})
    return {"fields": fields}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def handle_api_exception(request: Request, exc: ApiException) -> JSONResponse:
        response = _error_response(
            request, status_code=exc.status_code, code=exc.code, message=exc.message, details=exc.details,
        )
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            response.headers["Retry-After"] = str(getattr(exc, "retry_after_seconds", 60))
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            request, status_code=422, code="VALIDATION_ERROR",
            message="Girdi doğrulaması başarısız.", details=_validation_error_details(exc),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_FALLBACK_CODES.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) and exc.detail else _DEFAULT_FALLBACK_MESSAGE
        if exc.status_code == status.HTTP_404_NOT_FOUND and message == "Not Found":
            message = "Kaynak bulunamadı."
        return _error_response(request, status_code=exc.status_code, code=code, message=message)

    @app.exception_handler(SATimeoutError)
    async def handle_db_pool_timeout(request: Request, exc: SATimeoutError) -> JSONResponse:
        # SQLAlchemy pool_timeout süresinde boş/overflow bağlantı bulunamazsa fırlatılır.
        # Genel 500 yerine ayrık 503 + kod, kapasite sorununu uygulama hatasından ayırt
        # eder. Credential veya connection string loglanmaz; yalnızca pool durumu.
        pool = db_engine.pool
        logger.warning(
            "DB connection pool exhausted for %s %s (checked_out=%s, pool_size=%s, overflow=%s)",
            request.method,
            request.url.path,
            pool.checkedout(),
            pool.size(),
            pool.overflow(),
            extra={"subject": getattr(request.state, "subject", None), "status_code": 503},
        )
        return _error_response(
            request, status_code=503, code="DB_POOL_EXHAUSTED",
            message="Sistem şu anda yoğun; lütfen kısa süre sonra tekrar deneyin.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception while processing %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
            extra={"subject": getattr(request.state, "subject", None), "status_code": 500},
        )
        return _error_response(
            request, status_code=500, code="INTERNAL_ERROR", message="Beklenmeyen bir hata oluştu.",
        )
