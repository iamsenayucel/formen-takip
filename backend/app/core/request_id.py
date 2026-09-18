from __future__ import annotations

import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core import log_context
from app.core.client_ip import get_client_ip

REQUEST_ID_HEADER = "X-Request-Id"

_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

_access_logger = logging.getLogger("app.access")


def _generate_request_id() -> str:
    return str(uuid.uuid4())


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming and _VALID_REQUEST_ID.match(incoming) else _generate_request_id()
        request.state.request_id = request_id

        tokens = log_context.bind_request(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=get_client_ip(request),
        )
        started = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                _access_logger.exception(
                    "%s %s failed after %.2fms",
                    request.method,
                    request.url.path,
                    duration_ms,
                    extra={
                        "subject": getattr(request.state, "subject", None),
                        "status_code": 500,
                        "duration_ms": duration_ms,
                    },
                )
                raise
            else:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                response.headers[REQUEST_ID_HEADER] = request_id
                status_code = response.status_code
                if status_code >= 500:
                    level = logging.ERROR
                elif status_code >= 400:
                    level = logging.WARNING
                else:
                    level = logging.INFO
                _access_logger.log(
                    level,
                    "%s %s %s %.2fms",
                    request.method,
                    request.url.path,
                    status_code,
                    duration_ms,
                    extra={
                        "subject": getattr(request.state, "subject", None),
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                    },
                )
                return response
        finally:
            log_context.reset_request(tokens)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", None) or _generate_request_id()
