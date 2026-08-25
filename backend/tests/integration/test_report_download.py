import uuid

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.orm import Session as SASession

import app.services.report_service as report_service_module
from app.api.deps import _DEV_BYPASS_SUBJECT
from app.core.config import get_settings
from app.db.session import engine
from app.models.enums import ReportFormat
from app.models.user import AuditLog
from tests.helpers import unwrap_error

from .conftest import TEST_SUBJECT


def _expected_authenticated_subject() -> str:
    settings = get_settings()
    if settings.auth_bypass and settings.environment == "development":
        return _DEV_BYPASS_SUBJECT
    return TEST_SUBJECT


def _patch_record_audit(monkeypatch, replacement):
    monkeypatch.setattr(report_service_module, "record_audit", replacement)


def _make_spy():
    calls = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))

    return spy, calls


def _content_type_for(report_format: ReportFormat) -> str:
    return {
        ReportFormat.CSV: "text/csv; charset=utf-8",
        ReportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ReportFormat.PDF: "application/pdf",
    }[report_format]


class TestReportDownload:
    @pytest.mark.parametrize("report_format", list(ReportFormat))
    def test_success_response_bytes_content_type_and_disposition(
        self, client, auth_headers, report_export_factory, monkeypatch, report_format
    ):
        existing = report_export_factory(report_format=report_format)
        expected_bytes = bytes(existing.file_content)
        expected_disposition = f'attachment; filename="{existing.file_name}"'

        spy, _ = _make_spy()
        _patch_record_audit(monkeypatch, spy)

        resp = client.get(f"/api/v1/reports/{existing.id}/download", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.content == expected_bytes
        assert resp.headers["content-type"] == _content_type_for(report_format)
        assert resp.headers["content-disposition"] == expected_disposition

    def test_success_audit_called_once_with_exact_arguments(
        self, client, auth_headers, report_export_factory, monkeypatch
    ):
        existing = report_export_factory()
        spy, calls = _make_spy()
        _patch_record_audit(monkeypatch, spy)

        resp = client.get(f"/api/v1/reports/{existing.id}/download", headers=auth_headers)
        assert resp.status_code == 200
        assert len(calls) == 1

        args, kwargs = calls[0]
        assert args[1] == _expected_authenticated_subject()
        assert args[2] == "report_downloaded"
        assert kwargs["entity"] == "report_export"
        assert kwargs["new_value"] == existing.file_name
        assert kwargs.get("old_value") is None
        assert kwargs["ip_address"] == "testclient"

    def test_success_audit_before_commit_order(
        self, client, auth_headers, report_export_factory, monkeypatch
    ):
        existing = report_export_factory()
        order = []

        def spy(*args, **kwargs):
            order.append("audit")

        _patch_record_audit(monkeypatch, spy)
        original_commit = SASession.commit

        def wrapped_commit(self):
            order.append("commit")
            return original_commit(self)

        monkeypatch.setattr(SASession, "commit", wrapped_commit)

        resp = client.get(f"/api/v1/reports/{existing.id}/download", headers=auth_headers)
        assert resp.status_code == 200
        assert order == ["audit", "commit"]

    def test_success_report_entity_unchanged(
        self, client, auth_headers, db_session, report_export_factory, monkeypatch
    ):
        existing = report_export_factory()
        report_id = existing.id
        before = {
            "file_name": existing.file_name,
            "status": existing.status,
            "requested_by_subject": existing.requested_by_subject,
            "created_at": existing.created_at,
            "row_count": existing.row_count,
            "file_content": bytes(existing.file_content),
        }

        spy, _ = _make_spy()
        _patch_record_audit(monkeypatch, spy)

        resp = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert resp.status_code == 200

        db_session.expire(existing)
        after = {
            "file_name": existing.file_name,
            "status": existing.status,
            "requested_by_subject": existing.requested_by_subject,
            "created_at": existing.created_at,
            "row_count": existing.row_count,
            "file_content": bytes(existing.file_content),
        }
        assert after == before

    def test_unknown_report_404_no_audit(self, client, auth_headers, db_session, monkeypatch):
        nonexistent = uuid.uuid4()
        audit_count_before = db_session.scalar(select(func.count()).select_from(AuditLog))

        spy, calls = _make_spy()
        _patch_record_audit(monkeypatch, spy)

        commit_calls = []
        original_commit = SASession.commit

        def counting_commit(self):
            commit_calls.append(1)
            return original_commit(self)

        monkeypatch.setattr(SASession, "commit", counting_commit)

        counter = {"n": 0}

        def _on_execute(conn, cursor, statement, parameters, context, executemany):
            counter["n"] += 1

        event.listen(engine, "before_cursor_execute", _on_execute)
        try:
            resp = client.get(f"/api/v1/reports/{nonexistent}/download", headers=auth_headers)
        finally:
            event.remove(engine, "before_cursor_execute", _on_execute)

        assert resp.status_code == 404
        assert unwrap_error(resp)["code"] == "REPORT_NOT_FOUND"
        assert counter["n"] == 1
        assert calls == []
        assert commit_calls == []

        audit_count_after = db_session.scalar(select(func.count()).select_from(AuditLog))
        assert audit_count_after == audit_count_before
