import uuid
from tests.helpers import legacy_json

from sqlalchemy import func, select

from app.models.performance import PerformanceRecord
from app.services.monthly_foreman_report import latest_completed_period


def _pick_foreman_with_data(db_session, year: int, month: int):
    from datetime import date

    date_from = date(year, month, 1)
    date_to = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    row = db_session.execute(
        select(PerformanceRecord.foreman_id, func.count())
        .where(PerformanceRecord.performance_date >= date_from, PerformanceRecord.performance_date < date_to)
        .group_by(PerformanceRecord.foreman_id)
        .order_by(func.count().desc())
        .limit(1)
    ).first()
    return row[0] if row else None


class TestMonthlyForemanReport:
    def test_requires_auth(self, client, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        resp = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/{year}/{month}")
        assert resp.status_code == 401

    def test_unknown_foreman_returns_404(self, client, auth_headers):
        year, month = latest_completed_period()
        resp = client.get(f"/api/v1/foremen/{uuid.uuid4()}/monthly-reports/{year}/{month}", headers=auth_headers)
        assert resp.status_code == 404

    def test_future_month_rejected(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        resp = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/2099/1", headers=auth_headers)
        assert resp.status_code == 400

    def test_generate_and_shape(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        assert foreman_id is not None, "seeded DB should have performance records for the latest completed month"

        resp = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/{year}/{month}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        assert body["year"] == year
        assert body["month"] == month
        data = body["report_data"]
        assert data["foreman"]["id"] == str(foreman_id)
        assert data["period"]["year"] == year

        if not data["insufficient_data"]:
            assert isinstance(data["overall"]["score"], float)
            assert data["overall"]["level"]["name"]
            assert isinstance(data["kpis"], list) and len(data["kpis"]) > 0
            for kpi in data["kpis"]:
                assert "success_direction_higher" in kpi
                if kpi["has_data"]:
                    assert kpi["level"] is not None

    def test_idempotent_generation(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)

        first = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/{year}/{month}", headers=auth_headers)
        second = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/{year}/{month}", headers=auth_headers)
        assert legacy_json(first)["generated_at"] == legacy_json(second)["generated_at"]

    def test_list_includes_generated_report(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/{year}/{month}", headers=auth_headers)

        resp = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports", headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert any(item["year"] == year and item["month"] == month for item in items)

    def test_latest_returns_available_report(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)

        resp = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert legacy_json(resp)["available"] is True

    def test_pdf_download_returns_valid_pdf(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)

        resp = client.get(f"/api/v1/foremen/{foreman_id}/monthly-reports/{year}/{month}/pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:5] == b"%PDF-"
        assert len(resp.content) > 500
