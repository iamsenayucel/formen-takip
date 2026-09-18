from __future__ import annotations

import base64
import hashlib
import re
from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

if TYPE_CHECKING:
    from fastapi import FastAPI

_INLINE_SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.DOTALL)
_INLINE_STYLE_RE = re.compile(r"<style>(.*?)</style>", re.DOTALL)

_BASE_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}

API_CSP = "default-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'"

HSTS_VALUE = "max-age=31536000"


def _csp_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).digest()
    return f"sha256-{base64.b64encode(digest).decode('ascii')}"


def _build_docs_csp(app: "FastAPI") -> tuple[str | None, frozenset[str]]:
    if not app.openapi_url:
        return None, frozenset()

    doc_paths: set[str] = set()
    script_hashes: list[str] = []
    style_hashes: list[str] = []

    if app.docs_url:
        from fastapi.openapi.docs import get_swagger_ui_html

        doc_paths.add(app.docs_url)
        html = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            init_oauth=app.swagger_ui_init_oauth,
            swagger_ui_parameters=app.swagger_ui_parameters,
        ).body.decode("utf-8")
        script_hashes.extend(_csp_hash(m) for m in _INLINE_SCRIPT_RE.findall(html))
        if app.swagger_ui_oauth2_redirect_url:
            doc_paths.add(app.swagger_ui_oauth2_redirect_url)

    if app.redoc_url:
        from fastapi.openapi.docs import get_redoc_html

        doc_paths.add(app.redoc_url)
        html = get_redoc_html(openapi_url=app.openapi_url, title=f"{app.title} - ReDoc").body.decode("utf-8")
        style_hashes.extend(_csp_hash(m) for m in _INLINE_STYLE_RE.findall(html))

    if not doc_paths:
        return None, frozenset()

    script_src = " ".join(["'self'", "https://cdn.jsdelivr.net", *(f"'{h}'" for h in script_hashes)])
    style_src = " ".join(
        ["'self'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com", *(f"'{h}'" for h in style_hashes)]
    )
    csp = "; ".join(
        [
            "default-src 'self'",
            "base-uri 'none'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'none'",
            f"script-src {script_src}",
            f"style-src {style_src}",
            "img-src 'self' https://fastapi.tiangolo.com data:",
            "font-src 'self' https://fonts.gstatic.com",
            "connect-src 'self'",
        ]
    )
    return csp, frozenset(doc_paths)


def apply_baseline_security_headers(headers: MutableHeaders, *, environment: str) -> None:
    for name, value in _BASE_HEADERS.items():
        headers.setdefault(name, value)
    headers.setdefault("Content-Security-Policy", API_CSP)
    if environment == "production":
        headers.setdefault("Strict-Transport-Security", HSTS_VALUE)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, *, environment: str, docs_csp: str | None, docs_paths: frozenset[str]) -> None:
        self.app = app
        self._environment = environment
        self._docs_csp = docs_csp
        self._docs_paths = docs_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        csp = self._docs_csp if (self._docs_csp and path in self._docs_paths) else API_CSP
        environment = self._environment

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in _BASE_HEADERS.items():
                    headers.setdefault(name, value)
                headers.setdefault("Content-Security-Policy", csp)
                if environment == "production":
                    headers.setdefault("Strict-Transport-Security", HSTS_VALUE)
            await send(message)

        await self.app(scope, receive, send_wrapper)


def install_security_headers(app: "FastAPI", *, environment: str) -> None:
    docs_csp, docs_paths = _build_docs_csp(app)
    app.add_middleware(
        SecurityHeadersMiddleware,
        environment=environment,
        docs_csp=docs_csp,
        docs_paths=docs_paths,
    )
