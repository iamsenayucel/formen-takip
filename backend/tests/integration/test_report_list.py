from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import event, select

from app.db.session import engine
from app.models.enums import ReportFormat, ReportType
from app.models.report import ReportExport
from tests.helpers import unwrap_error, unwrap_page

from .conftest import TEST_SUBJECT


@contextmanager
def count_queries():
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


@pytest.fixture
def report_exports(report_export_factory):
    base = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    formats = [ReportFormat.CSV, ReportFormat.XLSX, ReportFormat.PDF, ReportFormat.CSV]
    types = [
        ReportType.COMPANY_SUMMARY,
        ReportType.PLANT_COMPARISON,
        ReportType.SHIFT_COMPARISON,
        ReportType.KPI_ANALYSIS,
    ]
    reports = [
        report_export_factory(
            report_format=report_format,
            report_type=report_type,
            requested_by_subject=TEST_SUBJECT if index < 3 else "another-integration-subject",
            created_at=base + timedelta(minutes=index),
            row_count=index + 1,
        )
        for index, (report_format, report_type) in enumerate(zip(formats, types))
    ]
    return sorted(reports, key=lambda report: (report.created_at, report.id), reverse=True)


class TestReportList:
    def test_exact_response_and_item_field_shape(self, client, auth_headers, report_exports):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert set(body) == {"data", "pagination"}
        assert set(body["pagination"]) == {"nextCursor", "hasMore", "total"}
        assert body["data"]
        for item in body["data"]:
            assert set(item) == {
                "id", "fileName", "reportType", "format", "rowCount",
                "status", "requestedBy", "createdAt",
            }

    def test_reports_do_not_publish_total(self, client, auth_headers, report_exports):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        _, pagination = unwrap_page(resp)
        assert pagination["total"] is None

    def test_default_pagination_values(self, client, auth_headers, report_exports):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        items, pagination = unwrap_page(resp)
        assert len(items) == len(report_exports)
        assert pagination["hasMore"] is False
        assert pagination["nextCursor"] is None

    def test_newest_first_ordering(self, client, auth_headers, report_exports):
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        items, _ = unwrap_page(resp)
        assert [item["id"] for item in items] == [str(report.id) for report in report_exports]

    def test_cursor_pagination_slices_without_duplicates(self, client, auth_headers, report_exports):
        first_resp = client.get("/api/v1/reports", headers=auth_headers, params={"limit": 2})
        assert first_resp.status_code == 200
        first_items, first_page = unwrap_page(first_resp)
        assert [item["id"] for item in first_items] == [str(report.id) for report in report_exports[:2]]
        assert first_page["hasMore"] is True
        assert first_page["nextCursor"]

        second_resp = client.get(
            "/api/v1/reports",
            headers=auth_headers,
            params={"limit": 2, "cursor": first_page["nextCursor"]},
        )
        assert second_resp.status_code == 200
        second_items, second_page = unwrap_page(second_resp)
        assert [item["id"] for item in second_items] == [str(report.id) for report in report_exports[2:]]
        assert second_page["hasMore"] is False
        assert second_page["nextCursor"] is None
        assert {item["id"] for item in first_items}.isdisjoint(item["id"] for item in second_items)

    def test_invalid_cursor_returns_stable_error(self, client, auth_headers, report_exports):
        resp = client.get(
            "/api/v1/reports", headers=auth_headers, params={"cursor": "not-a-valid-cursor"}
        )
        assert resp.status_code == 400
        assert unwrap_error(resp)["code"] == "INVALID_CURSOR"

    def test_query_count_is_exactly_one(self, client, auth_headers, report_exports):
        first_resp = client.get("/api/v1/reports", headers=auth_headers, params={"limit": 1})
        _, first_page = unwrap_page(first_resp)
        cases = (None, {"limit": 1}, {"limit": 1, "cursor": first_page["nextCursor"]})

        for params in cases:
            with count_queries() as counter:
                resp = client.get("/api/v1/reports", headers=auth_headers, params=params)
            assert resp.status_code == 200
            # +2: RBAC get_auth_context sabit ek yuku (user_role_assignments get + user_scope_assignments select)
            assert counter["n"] == 3, f"params={params!r}"

    def test_enum_fields_serialize_as_values(self, client, auth_headers, db_session, report_exports):
        resp = client.get("/api/v1/reports", headers=auth_headers, params={"limit": 25})
        assert resp.status_code == 200
        items, _ = unwrap_page(resp)

        entities_by_id = {
            str(entity.id): entity
            for entity in db_session.scalars(
                select(ReportExport).where(ReportExport.id.in_([UUID(item["id"]) for item in items]))
            )
        }
        for item in items:
            entity = entities_by_id[item["id"]]
            assert item["reportType"] == entity.report_type.value
            assert item["format"] == entity.format.value
            assert item["status"] == entity.status.value
            assert item["createdAt"] == entity.created_at.isoformat()
            assert item["requestedBy"] == entity.requested_by_subject

    def test_no_current_user_scoping(self, client, auth_headers, report_exports):
        resp = client.get("/api/v1/reports", headers=auth_headers, params={"limit": 25})
        assert resp.status_code == 200
        items, _ = unwrap_page(resp)
        returned_requesters = {item["requestedBy"] for item in items}
        assert TEST_SUBJECT in returned_requesters
        assert "another-integration-subject" in returned_requesters
