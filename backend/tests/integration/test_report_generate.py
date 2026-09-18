import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone

import pytest

import app.api.v1.reports as reports_module
import app.core.clock as clock_module
import app.services.report_service as report_service_module
from app.api.deps import _DEV_BYPASS_SUBJECT
from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.authorization import UserRoleAssignment, UserScopeAssignment
from app.models.enums import ReportType, Role, ScopeType
from app.models.report import ReportExport
from app.models.user import AuditLog
from app.services.reporting import _BUILDERS

from tests.helpers import unwrap

from .conftest import TEST_SUBJECT


class RecordingSession:
    def __init__(self, fail_on_flush=False, fail_on_commit=False, fail_on_refresh=False):
        self.events = []
        self.report_exports = []
        self.audit_logs = []
        self.fail_on_flush = fail_on_flush
        self.fail_on_commit = fail_on_commit
        self.fail_on_refresh = fail_on_refresh

    def add(self, obj):
        if isinstance(obj, ReportExport):
            self.events.append("add_report")
            self.report_exports.append(obj)
        elif isinstance(obj, AuditLog):
            self.events.append("audit")
            self.audit_logs.append(obj)
        else:
            raise AssertionError(f"RecordingSession.add called with unexpected type: {type(obj)!r}")

    def flush(self):
        self.events.append("flush")
        if self.fail_on_flush:
            raise RuntimeError("test-flush-failure")
        for export in self.report_exports:
            if export.id is None:
                export.id = uuid.uuid4()
            if export.created_at is None:
                export.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def commit(self):
        self.events.append("commit")
        if self.fail_on_commit:
            raise RuntimeError("test-commit-failure")

    def refresh(self, obj):
        self.events.append("refresh")
        if self.fail_on_refresh:
            raise RuntimeError("test-refresh-failure")

    # get_auth_context (RBAC), bu fake session'ı da get_db üzerinden kullanır — bu
    # orkestrasyon testleri tam yetkili bir OPERATIONS_MANAGER/ALL scope varsayar,
    # yetkilendirme mekanizmasının kendisini değil rapor üretim akışını test eder.
    def get(self, model, pk):
        if model is UserRoleAssignment:
            return UserRoleAssignment(subject=pk, role=Role.OPERATIONS_MANAGER)
        return None

    def scalars(self, stmt):
        return [UserScopeAssignment(subject=TEST_SUBJECT, scope_type=ScopeType.ALL)]


@contextmanager
def db_override(fake_session):
    app.dependency_overrides[get_db] = lambda: fake_session
    try:
        yield fake_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _patch_both(monkeypatch, name, replacement):
    monkeypatch.setattr(reports_module, name, replacement, raising=False)
    monkeypatch.setattr(report_service_module, name, replacement, raising=False)


def _make_capturing_builder(headers=None, rows=None):
    calls = []
    fixed_headers = headers if headers is not None else ["Kolon A", "Kolon B"]
    fixed_rows = rows if rows is not None else [{"Kolon A": "1", "Kolon B": "2"}, {"Kolon A": "3", "Kolon B": "4"}]

    def fake_build_report_rows(db, report_type, filters):
        calls.append((report_type, filters))
        return fixed_headers, fixed_rows

    return fake_build_report_rows, calls


def _make_render_spy(return_value):
    calls = []

    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return return_value

    return spy, calls


def _expected_authenticated_subject() -> str:
    settings = get_settings()
    if settings.auth_bypass and settings.environment == "development":
        return _DEV_BYPASS_SUBJECT
    return TEST_SUBJECT


def _freeze_today(monkeypatch, frozen_date):
    monkeypatch.setattr(clock_module, "today_local", lambda: frozen_date)
    monkeypatch.setattr(clock_module, "now_utc", lambda: datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc))


class TestReportingBuildersMapping:
    def test_all_seven_report_types_mapped(self):
        assert set(_BUILDERS.keys()) == {
            ReportType.COMPANY_SUMMARY, ReportType.PLANT_COMPARISON, ReportType.SHIFT_COMPARISON,
            ReportType.FOREMAN_PERFORMANCE, ReportType.KPI_ANALYSIS, ReportType.CRITICAL_PERFORMANCE,
            ReportType.MISSING_DATA,
        }


class TestReportGenerateOrchestration:
    def test_success_event_order_and_response(self, client, auth_headers, monkeypatch):
        _freeze_today(monkeypatch, date(2026, 6, 15))
        builder, builder_calls = _make_capturing_builder()
        render_spy, render_calls = _make_render_spy(b"FAKE-CSV-BYTES")
        _patch_both(monkeypatch, "build_report_rows", builder)
        _patch_both(monkeypatch, "render_csv", render_spy)

        with db_override(RecordingSession()) as fake:
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "company_summary", "format": "csv"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        assert fake.events == ["add_report", "flush", "audit", "commit"]
        assert len(render_calls) == 1
        assert len(builder_calls) == 1

        data = unwrap(resp)
        assert set(data.keys()) == {
            "id", "fileName", "reportType", "format", "rowCount", "status", "requestedBy", "createdAt",
        }
        assert data["reportType"] == "company_summary"
        assert data["format"] == "csv"
        assert data["rowCount"] == 2
        assert data["fileName"] == "company_summary_2026-05-16_2026-06-15.csv"
        assert data["id"] == str(fake.report_exports[0].id)
        assert data["createdAt"] == fake.report_exports[0].created_at.isoformat()

    def test_success_audit_object_fields(self, client, auth_headers, monkeypatch):
        builder, _ = _make_capturing_builder()
        render_spy, _ = _make_render_spy(b"FAKE-CSV-BYTES")
        _patch_both(monkeypatch, "build_report_rows", builder)
        _patch_both(monkeypatch, "render_csv", render_spy)

        with db_override(RecordingSession()) as fake:
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "company_summary", "format": "csv"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        assert len(fake.audit_logs) == 1
        audit = fake.audit_logs[0]
        assert audit.subject == _expected_authenticated_subject()
        assert audit.action == "report.created"
        assert audit.entity == "report_export"
        assert audit.new_value == unwrap(resp)["fileName"]
        assert audit.old_value is None
        assert audit.ip_address == "testclient"
        assert audit.success is True
        assert audit.error_message is None

    def test_csv_format_dispatch(self, client, auth_headers, monkeypatch):
        builder, _ = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        csv_spy, csv_calls = _make_render_spy(b"CSV")
        xlsx_spy, xlsx_calls = _make_render_spy(b"XLSX")
        pdf_spy, pdf_calls = _make_render_spy(b"PDF")
        summary_spy, summary_calls = _make_render_spy("SUMMARY")
        _patch_both(monkeypatch, "render_csv", csv_spy)
        _patch_both(monkeypatch, "render_xlsx", xlsx_spy)
        _patch_both(monkeypatch, "render_pdf", pdf_spy)
        _patch_both(monkeypatch, "build_filters_summary", summary_spy)

        with db_override(RecordingSession()):
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "company_summary", "format": "csv"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        assert len(csv_calls) == 1
        assert xlsx_calls == []
        assert pdf_calls == []
        assert summary_calls == []
        assert unwrap(resp)["fileName"].endswith(".csv")

    def test_xlsx_format_dispatch(self, client, auth_headers, monkeypatch):
        builder, _ = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        csv_spy, csv_calls = _make_render_spy(b"CSV")
        xlsx_spy, xlsx_calls = _make_render_spy(b"XLSX")
        pdf_spy, pdf_calls = _make_render_spy(b"PDF")
        summary_spy, summary_calls = _make_render_spy("SUMMARY")
        _patch_both(monkeypatch, "render_csv", csv_spy)
        _patch_both(monkeypatch, "render_xlsx", xlsx_spy)
        _patch_both(monkeypatch, "render_pdf", pdf_spy)
        _patch_both(monkeypatch, "build_filters_summary", summary_spy)

        with db_override(RecordingSession()):
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "company_summary", "format": "xlsx"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        assert csv_calls == []
        assert len(xlsx_calls) == 1
        assert pdf_calls == []
        assert summary_calls == []
        assert unwrap(resp)["fileName"].endswith(".xlsx")

    def test_pdf_format_dispatch_and_title(self, client, auth_headers, monkeypatch):
        from app.services.reporting import REPORT_TITLES

        builder, _ = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        csv_spy, csv_calls = _make_render_spy(b"CSV")
        xlsx_spy, xlsx_calls = _make_render_spy(b"XLSX")
        pdf_spy, pdf_calls = _make_render_spy(b"PDF")
        summary_spy, summary_calls = _make_render_spy("SUMMARY-TEXT")
        _patch_both(monkeypatch, "render_csv", csv_spy)
        _patch_both(monkeypatch, "render_xlsx", xlsx_spy)
        _patch_both(monkeypatch, "render_pdf", pdf_spy)
        _patch_both(monkeypatch, "build_filters_summary", summary_spy)

        with db_override(RecordingSession()):
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "kpi_analysis", "format": "pdf"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        assert csv_calls == []
        assert xlsx_calls == []
        assert len(summary_calls) == 1
        assert len(pdf_calls) == 1
        pdf_args, _ = pdf_calls[0]
        assert pdf_args[0] == REPORT_TITLES[ReportType.KPI_ANALYSIS]
        assert pdf_args[1] == "SUMMARY-TEXT"
        assert unwrap(resp)["fileName"].endswith(".pdf")

    @pytest.mark.parametrize("report_type", [
        "company_summary", "plant_comparison", "shift_comparison", "foreman_performance",
        "kpi_analysis", "critical_performance", "missing_data",
    ])
    def test_report_type_passed_through_to_builder(self, client, auth_headers, monkeypatch, report_type):
        builder, calls = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        render_spy, _ = _make_render_spy(b"CSV")
        _patch_both(monkeypatch, "render_csv", render_spy)

        with db_override(RecordingSession()):
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": report_type, "format": "csv"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        assert len(calls) == 1
        assert calls[0][0] == ReportType(report_type)
        assert unwrap(resp)["fileName"].startswith(report_type)

    @pytest.mark.parametrize("payload_dates,expected_from,expected_to", [
        ({}, date(2026, 5, 16), date(2026, 6, 15)),
        ({"date_from": "2026-01-01"}, date(2026, 1, 1), date(2026, 6, 15)),
        ({"date_to": "2026-03-10"}, date(2026, 2, 8), date(2026, 3, 10)),
        ({"date_from": "2026-01-01", "date_to": "2026-01-31"}, date(2026, 1, 1), date(2026, 1, 31)),
        ({"date_from": "2026-01-31", "date_to": "2026-01-01"}, date(2026, 1, 1), date(2026, 1, 31)),
        ({"date_from": "2026-02-14", "date_to": "2026-02-14"}, date(2026, 2, 14), date(2026, 2, 14)),
    ])
    def test_date_resolution_cases(self, client, auth_headers, monkeypatch, payload_dates, expected_from, expected_to):
        _freeze_today(monkeypatch, date(2026, 6, 15))
        builder, calls = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        render_spy, _ = _make_render_spy(b"CSV")
        _patch_both(monkeypatch, "render_csv", render_spy)

        with db_override(RecordingSession()):
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "company_summary", "format": "csv", **payload_dates},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        filters = calls[0][1]
        assert filters.date_from == expected_from
        assert filters.date_to == expected_to
        assert unwrap(resp)["fileName"] == f"company_summary_{expected_from}_{expected_to}.csv"

    def test_dimension_filters_transfer_exactly(self, client, auth_headers, monkeypatch):
        builder, calls = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        render_spy, _ = _make_render_spy(b"CSV")
        _patch_both(monkeypatch, "render_csv", render_spy)

        plant_id = str(uuid.uuid4())
        factory_id = str(uuid.uuid4())

        with db_override(RecordingSession()):
            resp = client.post(
                "/api/v1/reports/generate",
                json={
                    "report_type": "company_summary", "format": "csv",
                    "plant_ids": [plant_id], "factory_ids": [],
                    "chief_ids": None, "shift_ids": None, "kpi_ids": None,
                },
                headers=auth_headers,
            )

        assert resp.status_code == 201
        filters = calls[0][1]
        assert [str(p) for p in filters.plant_ids] == [plant_id]
        assert filters.factory_ids == []
        assert filters.chief_ids is None
        assert filters.shift_ids is None
        assert filters.kpi_ids is None
        assert filters.foreman_ids is None

    def test_filters_json_stores_raw_request_not_resolved_filters(self, client, auth_headers, monkeypatch):
        _freeze_today(monkeypatch, date(2026, 6, 15))
        builder, _ = _make_capturing_builder()
        _patch_both(monkeypatch, "build_report_rows", builder)
        render_spy, _ = _make_render_spy(b"CSV")
        _patch_both(monkeypatch, "render_csv", render_spy)

        with db_override(RecordingSession()) as fake:
            resp = client.post(
                "/api/v1/reports/generate",
                json={"report_type": "company_summary", "format": "csv"},
                headers=auth_headers,
            )

        assert resp.status_code == 201
        export = fake.report_exports[0]
        assert export.filters_json["date_from"] is None
        assert export.filters_json["date_to"] is None
