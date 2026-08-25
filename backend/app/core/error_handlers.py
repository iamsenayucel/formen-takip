from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic.alias_generators import to_camel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import clock
from app.core.errors import ApiException
from app.core.request_id import get_request_id
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
    return JSONResponse(status_code=status_code, content=envelope.model_dump(mode="json", by_alias=True))


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

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path, exc_info=exc)
        return _error_response(
            request, status_code=500, code="INTERNAL_ERROR", message="Beklenmeyen bir hata oluştu.",
        )
