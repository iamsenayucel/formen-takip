import asyncio
import json
import logging
import sys

import pytest

from app.core import log_context
from app.core.log_context import RequestContextFilter
from app.core.logging_config import JsonLogFormatter, build_logging_config, configure_logging


@pytest.fixture(autouse=True)
def _clean_log_context():
    tokens = log_context.bind_request(request_id=None, method=None, path=None, client_ip=None)
    yield
    log_context.reset_request(tokens)


def _record(logger_name="app.test", level=logging.INFO, msg="hello", args=(), exc_info=None):
    return logging.LogRecord(logger_name, level, __file__, 1, msg, args, exc_info)


class TestJsonLogFormatter:
    def test_includes_required_fields(self):
        record = _record(msg="hello %s", args=("world",))
        record.request_id = "rid-1"
        record.subject = "sub-1"
        record.method = "GET"
        record.path = "/api/v1/x"
        record.client_ip = "203.0.113.5"

        data = json.loads(JsonLogFormatter().format(record))

        assert data["message"] == "hello world"
        assert data["level"] == "INFO"
        assert data["logger"] == "app.test"
        assert data["request_id"] == "rid-1"
        assert data["subject"] == "sub-1"
        assert data["method"] == "GET"
        assert data["path"] == "/api/v1/x"
        assert data["client_ip"] == "203.0.113.5"
        assert "timestamp" in data

    def test_missing_context_fields_default_to_null(self):
        record = _record()
        data = json.loads(JsonLogFormatter().format(record))
        assert data["request_id"] is None
        assert data["subject"] is None

    def test_extra_fields_pass_through(self):
        record = _record(logger_name="app.access", msg="GET /x 200")
        record.status_code = 200
        record.duration_ms = 12.5
        data = json.loads(JsonLogFormatter().format(record))
        assert data["status_code"] == 200
        assert data["duration_ms"] == 12.5

    def test_exception_traceback_included(self):
        try:
            raise ValueError("boom-secret-free")
        except ValueError:
            record = _record(logger_name="app.errors", level=logging.ERROR, msg="failed", exc_info=sys.exc_info())
        data = json.loads(JsonLogFormatter().format(record))
        assert "boom-secret-free" in data["exception"]


class TestRequestContextFilter:
    def test_defaults_when_no_context_bound(self):
        record = _record()
        assert RequestContextFilter().filter(record) is True
        assert record.request_id is None
        assert record.subject is None
        assert record.client_ip is None

    def test_reads_bound_context(self):
        log_context.bind_request(request_id="rid-2", method="POST", path="/y", client_ip="1.2.3.4")
        log_context.bind_subject("user-42")
        record = _record()
        RequestContextFilter().filter(record)
        assert record.request_id == "rid-2"
        assert record.subject == "user-42"
        assert record.method == "POST"
        assert record.path == "/y"
        assert record.client_ip == "1.2.3.4"

    def test_does_not_override_explicitly_set_fields(self):
        log_context.bind_subject("context-subject")
        record = _record()
        record.subject = "explicit-subject"
        RequestContextFilter().filter(record)
        assert record.subject == "explicit-subject"


class TestConfigureLogging:
    def test_info_level_logs_are_captured(self):
        # configure_logging() dictConfig ile root.handlers'ı değiştirir; bu pytest'in
        # caplog handler'ını da siler — bu yüzden caplog yerine geçici handler kullanılır.
        configure_logging("INFO")
        captured: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                captured.append(record)

        handler = _Capture()
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            logging.getLogger("app.test_logging_config").info("hello-info-level")
        finally:
            root.removeHandler(handler)

        assert any(r.getMessage() == "hello-info-level" for r in captured)

    def test_uvicorn_access_logger_is_silenced(self):
        configure_logging("INFO")
        logger = logging.getLogger("uvicorn.access")
        assert logger.handlers == []
        assert logger.propagate is False

    def test_root_and_app_loggers_share_single_handler(self):
        config = build_logging_config("INFO")
        assert config["root"]["handlers"] == ["console"]
        assert "handlers" not in config["loggers"]["app"]
        assert config["disable_existing_loggers"] is False


class TestLogContextConcurrencyIsolation:
    def test_concurrent_async_tasks_do_not_leak_context(self):
        async def worker(request_id, subject, delay):
            tokens = log_context.bind_request(request_id=request_id, method="GET", path="/x", client_ip="9.9.9.9")
            log_context.bind_subject(subject)
            await asyncio.sleep(delay)
            result = (log_context.get_request_id(), log_context.get_subject())
            log_context.reset_request(tokens)
            return result

        async def run():
            return await asyncio.gather(
                worker("req-A", "user-A", 0.02),
                worker("req-B", "user-B", 0.0),
            )

        results = asyncio.run(run())
        assert results[0] == ("req-A", "user-A")
        assert results[1] == ("req-B", "user-B")

    def test_reset_restores_previous_context(self):
        outer_tokens = log_context.bind_request(request_id="outer", method="GET", path="/o", client_ip="1.1.1.1")
        inner_tokens = log_context.bind_request(request_id="inner", method="POST", path="/i", client_ip="2.2.2.2")
        assert log_context.get_request_id() == "inner"
        log_context.reset_request(inner_tokens)
        assert log_context.get_request_id() == "outer"
        log_context.reset_request(outer_tokens)
        assert log_context.get_request_id() is None
