from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from typing import NamedTuple

_request_id_var: ContextVar[str | None] = ContextVar("log_request_id", default=None)
_subject_var: ContextVar[str | None] = ContextVar("log_subject", default=None)
_method_var: ContextVar[str | None] = ContextVar("log_method", default=None)
_path_var: ContextVar[str | None] = ContextVar("log_path", default=None)
_client_ip_var: ContextVar[str | None] = ContextVar("log_client_ip", default=None)


class RequestContextTokens(NamedTuple):
    request_id: Token
    subject: Token
    method: Token
    path: Token
    client_ip: Token


def bind_request(
    *, request_id: str, method: str | None, path: str | None, client_ip: str | None,
) -> RequestContextTokens:
    return RequestContextTokens(
        request_id=_request_id_var.set(request_id),
        subject=_subject_var.set(None),
        method=_method_var.set(method),
        path=_path_var.set(path),
        client_ip=_client_ip_var.set(client_ip),
    )


def reset_request(tokens: RequestContextTokens) -> None:
    _request_id_var.reset(tokens.request_id)
    _subject_var.reset(tokens.subject)
    _method_var.reset(tokens.method)
    _path_var.reset(tokens.path)
    _client_ip_var.reset(tokens.client_ip)


def bind_subject(subject: str | None) -> None:
    _subject_var.set(subject)


def get_request_id() -> str | None:
    return _request_id_var.get()


def get_subject() -> str | None:
    return _subject_var.get()


def get_method() -> str | None:
    return _method_var.get()


def get_path() -> str | None:
    return _path_var.get()


def get_client_ip() -> str | None:
    return _client_ip_var.get()


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        if not hasattr(record, "subject"):
            record.subject = get_subject()
        if not hasattr(record, "method"):
            record.method = get_method()
        if not hasattr(record, "path"):
            record.path = get_path()
        if not hasattr(record, "client_ip"):
            record.client_ip = get_client_ip()
        return True
