from tests.helpers import unwrap


class TestShiftAnalysisCards:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/shift-analysis/cards").status_code == 401

    def test_cards_response_includes_summary_in_one_request(self, client, auth_headers):
        resp = client.get("/api/v1/shift-analysis/cards", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        assert "items" in body
        assert "summary" in body
        summary = body["summary"]
        for key in ("period", "totalAnomalies", "highCount", "mediumCount", "topPlant", "topKpi", "maxPctDiff"):
            assert key in summary
        assert summary["totalAnomalies"] == len(body["items"])

    def test_standalone_summary_endpoint_removed(self, client, auth_headers):
        resp = client.get("/api/v1/shift-analysis/summary", headers=auth_headers)
        assert resp.status_code == 404


class TestShiftAnalysisHeatmap:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/shift-analysis/heatmap").status_code == 401

    def test_returns_full_plant_by_kpi_grid(self, client, auth_headers):
        resp = client.get("/api/v1/shift-analysis/heatmap", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        for key in ("period", "shifts", "plants", "kpis", "cells", "summary"):
            assert key in body
        assert len(body["shifts"]) == 2
        assert len(body["plants"]) > 0
        assert len(body["kpis"]) > 0
        assert len(body["cells"]) == len(body["plants"]) * len(body["kpis"])

        for key in ("anomalyPlantCount", "criticalCellCount", "priorityPlantCount", "topKpi"):
            assert key in body["summary"]

        valid_levels = {"no_data", "normal", "attention", "significant", "critical"}
        for cell in body["cells"]:
            assert cell["level"] in valid_levels
            for pkey in ("plantId", "kpiId"):
                assert pkey in cell
            if cell["level"] == "no_data":
                assert cell["absDiff"] is None and cell["pctDiff"] is None
            else:
                assert cell["absDiff"] is not None and cell["pctDiff"] is not None

    def test_plant_filter_narrows_grid(self, client, auth_headers):
        full = unwrap(client.get("/api/v1/shift-analysis/heatmap", headers=auth_headers))
        one_plant_id = full["plants"][0]["id"]
        resp = client.get(
            "/api/v1/shift-analysis/heatmap", headers=auth_headers, params={"plant_ids": one_plant_id}
        )
        assert resp.status_code == 200
        body = unwrap(resp)
        assert len(body["plants"]) == 1
        assert body["plants"][0]["id"] == one_plant_id
        assert all(c["plantId"] == one_plant_id for c in body["cells"])

    def test_shifts_are_all_shifts_ordered_by_sequence(self, client, auth_headers, db_session):
        from sqlalchemy import select

        from app.models.organization import Shift

        expected_shifts = [
            {"id": str(s.id), "code": s.code, "name": s.name}
            for s in sorted(db_session.scalars(select(Shift)), key=lambda s: s.sequence)
        ]

        resp = client.get("/api/v1/shift-analysis/heatmap", headers=auth_headers)
        assert resp.status_code == 200
        assert unwrap(resp)["shifts"] == expected_shifts


class TestPlantForemanShiftMatrix:
    def test_requires_auth(self, client, db_session):
        from sqlalchemy import select

        from app.models.organization import Plant

        plant = db_session.scalars(select(Plant)).first()
        assert client.get(f"/api/v1/plants/{plant.id}/foreman-shift-matrix").status_code in (401, 422)

    def test_returns_two_shift_columns_for_a_plant_with_data(self, client, auth_headers, db_session):
        from sqlalchemy import select

        from app.models.kpi import Kpi
        from app.models.organization import Plant
        from app.models.performance import PerformanceRecord

        plant_id, kpi_id = db_session.execute(
            select(PerformanceRecord.plant_id, PerformanceRecord.kpi_id).distinct().limit(1)
        ).first()
        plant = db_session.get(Plant, plant_id)
        kpi = db_session.get(Kpi, kpi_id)

        resp = client.get(
            f"/api/v1/plants/{plant.id}/foreman-shift-matrix",
            headers=auth_headers,
            params={"kpi_id": str(kpi.id)},
        )
        assert resp.status_code == 200
        body = unwrap(resp)
        assert body["kpi"]["id"] == str(kpi.id)
        assert len(body["shifts"]) == 2
        assert isinstance(body["insight"], str) and body["insight"]
        for r in body["rows"]:
            assert "fullName" in r and "cells" in r
            for shift in body["shifts"]:
                cell = r["cells"].get(shift["id"])
                if cell is not None:
                    for k in ("avgActual", "avgTarget", "score", "recordCount", "level"):
                        assert k in cell

    def test_unknown_kpi_returns_404(self, client, auth_headers, db_session):
        from uuid import uuid4

        from sqlalchemy import select

        from app.models.organization import Plant

        plant = db_session.scalars(select(Plant)).first()
        resp = client.get(
            f"/api/v1/plants/{plant.id}/foreman-shift-matrix",
            headers=auth_headers,
            params={"kpi_id": str(uuid4())},
        )
        assert resp.status_code == 404
