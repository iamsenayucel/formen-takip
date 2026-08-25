from tests.helpers import legacy_json

class TestReports:
    def test_generate_requires_auth(self, client):
        resp = client.post("/api/v1/reports/generate", json={"report_type": "plant_comparison", "format": "csv"})
        assert resp.status_code == 401

    def test_generate_csv_and_download(self, client, auth_headers):
        gen = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "plant_comparison", "format": "csv"},
            headers=auth_headers,
        )
        assert gen.status_code == 201
        body = legacy_json(gen)
        assert body["row_count"] >= 1
        report_id = body["id"]

        download = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("text/csv")
        assert len(download.content) > 0

    def test_generate_xlsx(self, client, auth_headers):
        gen = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "foreman_performance", "format": "xlsx"},
            headers=auth_headers,
        )
        assert gen.status_code == 201
        report_id = legacy_json(gen)["id"]
        download = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert download.status_code == 200
        assert "spreadsheetml" in download.headers["content-type"]

    def test_generate_pdf_critical_performance(self, client, auth_headers):
        gen = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "critical_performance", "format": "pdf"},
            headers=auth_headers,
        )
        assert gen.status_code == 201
        report_id = legacy_json(gen)["id"]
        download = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/pdf"

    def test_generate_missing_data_report(self, client, auth_headers):
        resp = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "missing_data", "format": "csv"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_history_lists_generated_reports(self, client, auth_headers):
        client.post("/api/v1/reports/generate", json={"report_type": "kpi_analysis", "format": "csv"}, headers=auth_headers)
        resp = client.get("/api/v1/reports", headers=auth_headers)
        assert resp.status_code == 200
        assert legacy_json(resp)["total"] >= 1

    def test_download_unknown_report_404(self, client, auth_headers):
        import uuid

        resp = client.get(f"/api/v1/reports/{uuid.uuid4()}/download", headers=auth_headers)
        assert resp.status_code == 404


class TestPdfFiltersSummary:

    @staticmethod
    def _summary(db, **filter_kwargs) -> str:
        from datetime import date, timedelta

        from app.schemas.common import Filters
        from app.services.reporting import build_filters_summary

        to_date = date.today()
        filters = Filters(date_from=to_date - timedelta(days=30), date_to=to_date, **filter_kwargs)
        return build_filters_summary(db, filters)

    def test_no_filter_states_company_wide_scope(self, db_session):
        summary = self._summary(db_session)
        assert "Dönem:" in summary
        assert "Şirket geneli" in summary

    def test_factory_and_plant_names_are_resolved(self, db_session):
        from sqlalchemy import select

        from app.models.organization import Factory, Plant

        factory = db_session.scalars(select(Factory).order_by(Factory.code)).first()
        plant = db_session.scalars(
            select(Plant).where(Plant.factory_id == factory.id).order_by(Plant.sequence_number)
        ).first()

        summary = self._summary(db_session, factory_ids=[factory.id], plant_ids=[plant.id])
        assert f"<b>Fabrika:</b> {factory.name}" in summary
        assert f"<b>Tesis:</b> {plant.name}" in summary

    def test_shift_and_kpi_names_are_resolved(self, db_session):
        from sqlalchemy import select

        from app.models.kpi import Kpi
        from app.models.organization import Shift

        shift = db_session.scalars(select(Shift).order_by(Shift.sequence)).first()
        kpi = db_session.scalars(select(Kpi).order_by(Kpi.display_order)).first()

        summary = self._summary(db_session, shift_ids=[shift.id], kpi_ids=[kpi.id])
        assert f"<b>Vardiya:</b> {shift.name}" in summary
        assert f"<b>KPI:</b> {kpi.name}" in summary

    def test_long_selections_are_truncated(self, db_session):
        from sqlalchemy import select

        from app.models.organization import Plant
        from app.services.reporting import MAX_SUMMARY_ITEMS

        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(MAX_SUMMARY_ITEMS + 3)))
        summary = self._summary(db_session, plant_ids=[p.id for p in plants])
        assert "(+3 diğer)" in summary
        assert plants[-1].name not in summary

    def test_summary_reaches_the_generated_pdf(self, client, auth_headers, db_session):
        from sqlalchemy import select

        from app.models.organization import Plant

        plant = db_session.scalars(select(Plant).order_by(Plant.sequence_number)).first()
        gen = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "foreman_performance", "format": "pdf", "plant_ids": [str(plant.id)]},
            headers=auth_headers,
        )
        assert gen.status_code == 201
        pdf = client.get(f"/api/v1/reports/{legacy_json(gen)['id']}/download", headers=auth_headers).content
        assert pdf.startswith(b"%PDF-")
        assert legacy_json(gen)["row_count"] >= 1
