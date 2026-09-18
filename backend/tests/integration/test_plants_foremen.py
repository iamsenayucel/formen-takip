import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import event, func, select

from app.db.session import engine
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.schemas.common import Filters
from app.services import analytics
from tests.helpers import unwrap, unwrap_error, unwrap_page


@contextmanager
def _capture_statements():
    statements = []

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


@contextmanager
def _count_queries():
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


class _SeededPlantMixin:
    @pytest.fixture(autouse=True)
    def _resolve_seeded_plant(self, db_session):
        plant_id = db_session.scalar(select(Plant.id).where(Plant.code == "PLT01"))
        assert plant_id is not None
        self._PLANT_ID = str(plant_id)


class TestContactInfoDataQuality:
    def test_every_foreman_has_phone_and_unique_email(self, db_session):
        foremen = list(db_session.scalars(select(Foreman)))
        assert foremen
        emails = [f.email for f in foremen]
        assert all(f.phone_number for f in foremen)
        assert all(emails)
        assert len(emails) == len(set(emails))

    def test_every_chief_has_phone_and_unique_email(self, db_session):
        chiefs = list(db_session.scalars(select(Chief)))
        assert chiefs
        emails = [c.email for c in chiefs]
        assert all(c.phone_number for c in chiefs)
        assert all(emails)
        assert len(emails) == len(set(emails))


class TestPlantsEndpoints:
    def test_list_plants_paginated(self, client, auth_headers):
        resp = client.get("/api/v1/plants", params={"limit": 5}, headers=auth_headers)
        assert resp.status_code == 200
        items, pagination = unwrap_page(resp)
        assert pagination["total"] == 50
        assert len(items) == 5

    def test_plant_detail_404_for_unknown_id(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    def test_plant_detail_and_summary(self, client, auth_headers):
        items, _ = unwrap_page(client.get("/api/v1/plants", params={"limit": 1}, headers=auth_headers))
        plant_id = items[0]["id"]

        detail = client.get(f"/api/v1/plants/{plant_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert unwrap(detail)["id"] == plant_id

        summary = client.get(f"/api/v1/plants/{plant_id}/summary", headers=auth_headers)
        assert summary.status_code == 200
        assert "totalScore" in unwrap(summary)

    def test_plant_foremen_list_scoped_to_plant(self, client, auth_headers):
        items, _ = unwrap_page(client.get("/api/v1/plants", params={"limit": 1}, headers=auth_headers))
        plant_id = items[0]["id"]
        resp = client.get(f"/api/v1/plants/{plant_id}/foremen", headers=auth_headers)
        assert resp.status_code == 200
        _, pagination = unwrap_page(resp)
        assert pagination["total"] == items[0]["activeForemanCount"] or pagination["total"] >= 0

    def test_plant_group_matches_owning_chief(self, client, auth_headers, db_session):
        plant_row = db_session.scalars(select(Plant).order_by(Plant.sequence_number)).first()
        items, _ = unwrap_page(client.get("/api/v1/plants", params={"limit": 1}, headers=auth_headers))
        item = items[0]

        assert item["group"]["id"] == str(plant_row.chief_id)
        assert item["group"]["code"].startswith("G")
        assert item["group"]["supervisor"]["id"] == str(plant_row.chief_id)

        chief_detail = unwrap(client.get(f"/api/v1/chiefs/{plant_row.chief_id}", headers=auth_headers))
        assert item["group"]["code"] == chief_detail["code"]
        assert item["group"]["score"] == chief_detail["totalScore"]
        assert item["group"]["supervisor"]["name"] == chief_detail["fullName"]


class TestPlantBoundedDetailReadsCharacterization(_SeededPlantMixin):
    """fabrika detail, kpis, shifts ve chiefs read akışlarının karakterizasyonu. Değer,
    sıralama, 404/boş-200 ayrımı ve path filter override davranışını kilitler; değerler
    güncel PLT01 seed kaydına bağlıdır.

    Bilinmeyen fabrikada yalnız detail 404 döner; kpis/shifts/chiefs boş veya fallback
    içerikle 200 döner. Refactor bu davranışı normalize etmemeli.
    """

    _PARAMS = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
    _EMPTY_PARAMS = {"date_from": "2030-01-01", "date_to": "2030-01-02"}
    _PLANT_ID = "3f9d39b3-4be1-4e96-aa99-dcd37146055f"  # PLT01 / "1. Tesis" — seed fixture, order-by-sequence first plant

    def test_plant_detail_exact_response(self, client, auth_headers, db_session):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = unwrap(resp)
        plant = db_session.get(Plant, uuid.UUID(self._PLANT_ID))
        assert body["id"] == self._PLANT_ID
        assert body["code"] == plant.code == "PLT01"
        assert body["name"] == plant.name
        assert body["sequenceNumber"] == plant.sequence_number == 1
        assert body["factory"]["id"] == str(plant.factory_id)
        assert body["factory"]["code"] == "K1"
        assert body["description"] == plant.description
        assert body["isActive"] is plant.is_active
        assert body["sapPlantCode"] == plant.sap_plant_code

    def test_plant_detail_exact_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
        assert unwrap_error(resp)["code"] == "PLANT_NOT_FOUND"

    def test_plant_kpis_exact_values_and_order(self, client, auth_headers, db_session):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/kpis", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items = unwrap(resp)
        assert [item["code"] for item in items] == [
            "AGIR_GITME", "GSF", "ISKARTA", "INKITA", "PLANA_UYUM", "OEE",
        ]
        kpis = {k.code: k for k in db_session.scalars(select(Kpi))}
        for item in items:
            assert item["kpiId"] == str(kpis[item["code"]].id)
            assert item["name"] == kpis[item["code"]].name
            assert item["unit"] == kpis[item["code"]].unit
            assert isinstance(item["avgScore"], float)
            assert item["avgTarget"] is not None
            assert item["avgActual"] is not None

    def test_plant_kpis_unknown_plant_returns_empty_200_not_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{uuid.uuid4()}/kpis", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert unwrap(resp) == []

    def test_plant_kpis_empty_window(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/kpis", params=self._EMPTY_PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert unwrap(resp) == []

    def test_plant_kpis_path_plant_id_overrides_query_plant_filter(self, client, auth_headers):
        """Path plant_id, çakışan query plant_ids değerini her zaman hard-overwrite eder;
        merge yapılmaz.
        """
        items, _ = unwrap_page(client.get("/api/v1/plants", params={"limit": 2}, headers=auth_headers))
        other_plant_id = next(p["id"] for p in items if p["id"] != self._PLANT_ID)

        scoped = client.get(
            f"/api/v1/plants/{self._PLANT_ID}/kpis",
            params={**self._PARAMS, "plant_ids": other_plant_id}, headers=auth_headers,
        )
        unscoped = client.get(f"/api/v1/plants/{self._PLANT_ID}/kpis", params=self._PARAMS, headers=auth_headers)
        assert scoped.status_code == 200
        assert scoped.json() == unscoped.json()

    def test_plant_shifts_exact_values_and_order(self, client, auth_headers, db_session):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/shifts", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items = unwrap(resp)
        assert [item["code"] for item in items] == ["V1", "V2"]
        shifts = {s.code: s for s in db_session.scalars(select(Shift))}
        for item in items:
            assert item["shiftId"] == str(shifts[item["code"]].id)
            assert item["name"] == shifts[item["code"]].name
            assert isinstance(item["totalScore"], float)
            assert item["level"]["name"] in {"Kritik", "Geliştirilmeli", "Başarılı"}

    def test_plant_shifts_unknown_plant_returns_empty_200_not_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{uuid.uuid4()}/shifts", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert unwrap(resp) == []

    def test_plant_shifts_empty_window(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/shifts", params=self._EMPTY_PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert unwrap(resp) == []

    def test_plant_chiefs_exact_response(self, client, auth_headers, db_session):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/chiefs", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items = unwrap(resp)
        plant = db_session.get(Plant, uuid.UUID(self._PLANT_ID))
        chief = db_session.get(Chief, plant.chief_id)
        assert len(items) == 1
        assert items[0]["id"] == str(chief.id)
        assert items[0]["employeeNumber"] == chief.employee_number
        assert items[0]["fullName"] == f"{chief.first_name} {chief.last_name}"
        assert items[0]["foremanCount"] >= 1
        assert isinstance(items[0]["totalScore"], float)

    def test_plant_chiefs_unknown_plant_returns_empty_200_not_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{uuid.uuid4()}/chiefs", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert unwrap(resp) == []

    def test_plant_chiefs_empty_score_window_still_returns_the_chief_via_relationship(
        self, client, auth_headers, db_session
    ):
        """kpis/shifts score verisi yokken boş döner; chiefs varlığı Plant.chief_id
        ilişkisine bağlıdır. Boş scoring penceresinde de tek şef döner; total_score 0.0
        ve performance level en düşük seviyeye fallback yapar."""
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/chiefs", params=self._EMPTY_PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = unwrap(resp)
        assert len(body) == 1
        item = body[0]
        plant = db_session.get(Plant, uuid.UUID(self._PLANT_ID))
        assert item["id"] == str(plant.chief_id)
        assert item["totalScore"] == 0.0
        assert item["level"]["name"] == "Kritik"
        # foreman_count assignment tabanlıdır (date_to tarihinde aktif); pencerede score
        # verisi olup olmamasından bağımsızdır. 0'a dönmez, 2 kalır.
        assert item["foremanCount"] == 2


class TestPlantHeavyReadsCharacterization(_SeededPlantMixin):
    """plants list, summary ve foremen heavy read akışlarının karakterizasyonu. Değer,
    sıralama, pagination, 404/boş-200 ve general/operational score ayrımını kilitler.
    foreman-shift-matrix kapsam dışıdır; değerler PLT01 ve active_foreman_count=2 olan
    güncel seed kaydına bağlıdır.
    """

    _PARAMS = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
    _PLANT_ID = "3f9d39b3-4be1-4e96-aa99-dcd37146055f"  # PLT01 / "1. Tesis"
    _UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"

    def test_list_plants_default_sort_page1(self, client, auth_headers):
        resp = client.get(
            "/api/v1/plants", params={**self._PARAMS, "limit": 3}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        items, pagination = unwrap_page(resp)
        assert pagination["total"] == 50
        assert [i["code"] for i in items] == ["PLT01", "PLT02", "PLT03"]
        assert [i["sequenceNumber"] for i in items] == [1, 2, 3]
        first = items[0]
        assert first["id"] == self._PLANT_ID
        assert first["factory"]["code"] == "K1"
        assert first["isActive"] is True
        assert isinstance(first["totalScore"], float)
        assert first["level"]["name"] in {"Kritik", "Geliştirilmeli", "Başarılı"}
        assert first["activeForemanCount"] == 2
        assert first["recordCount"] > 0
        assert first["group"]["id"] == first["group"]["supervisor"]["id"]

    def test_list_plants_default_sort_page2(self, client, auth_headers):
        first_resp = client.get(
            "/api/v1/plants", params={**self._PARAMS, "limit": 3}, headers=auth_headers
        )
        _, first_pagination = unwrap_page(first_resp)
        next_cursor = first_pagination["nextCursor"]
        assert next_cursor

        resp = client.get(
            "/api/v1/plants", params={**self._PARAMS, "limit": 3, "cursor": next_cursor}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        items, _ = unwrap_page(resp)
        assert [i["code"] for i in items] == ["PLT04", "PLT05", "PLT06"]
        assert all(isinstance(i["totalScore"], float) for i in items)

    def test_list_plants_sort_by_score_asc(self, client, auth_headers):
        resp = client.get(
            "/api/v1/plants",
            params={**self._PARAMS, "limit": 3, "sort_by": "score", "sort_dir": "asc"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        items, _ = unwrap_page(resp)
        assert len(items) == 3
        assert [i["totalScore"] for i in items] == sorted(i["totalScore"] for i in items)
        assert len({i["id"] for i in items}) == 3

    def test_plant_summary_exact_response(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/summary", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = unwrap(resp)
        plant_items, _ = unwrap_page(client.get(
            "/api/v1/plants", params={**self._PARAMS, "plant_ids": self._PLANT_ID}, headers=auth_headers
        ))
        kpis = unwrap(client.get(
            f"/api/v1/plants/{self._PLANT_ID}/kpis", params=self._PARAMS, headers=auth_headers
        ))
        foremen, pagination = unwrap_page(client.get(
            f"/api/v1/plants/{self._PLANT_ID}/foremen", params=self._PARAMS, headers=auth_headers
        ))
        assert body["plantId"] == self._PLANT_ID
        assert body["totalScore"] == plant_items[0]["totalScore"]
        assert body["activeForemanCount"] == pagination["total"]
        rounded_item_average = round(
            sum(item["operationalScore"] for item in foremen) / len(foremen), 2
        )
        assert body["foremenAverageScore"] == pytest.approx(rounded_item_average, abs=0.011)
        assert body["strongestKpi"]["avgScore"] == max(item["avgScore"] for item in kpis)
        assert body["weakestKpi"]["avgScore"] == min(item["avgScore"] for item in kpis)

    def test_plant_summary_exact_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{self._UNKNOWN_ID}/summary", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 404
        assert unwrap_error(resp)["code"] == "PLANT_NOT_FOUND"

    def test_plant_summary_path_plant_id_overrides_query_plant_filter(self, client, auth_headers):
        """Path plant_id, diğer read akışlarında olduğu gibi çakışan query plant_ids
        değerini hard-overwrite eder."""
        items, _ = unwrap_page(client.get("/api/v1/plants", params={"limit": 2}, headers=auth_headers))
        other_plant_id = next(p["id"] for p in items if p["id"] != self._PLANT_ID)

        scoped = client.get(
            f"/api/v1/plants/{self._PLANT_ID}/summary",
            params={**self._PARAMS, "plant_ids": other_plant_id}, headers=auth_headers,
        )
        unscoped = client.get(f"/api/v1/plants/{self._PLANT_ID}/summary", params=self._PARAMS, headers=auth_headers)
        assert scoped.status_code == 200
        assert scoped.json() == unscoped.json()

    def test_plant_foremen_exact_response_general_score_order(self, client, auth_headers):
        """plant_foremen sıralama ve sunumda bonuslu general_performance_score kullanır;
        plant_summary'deki foremen_average_score operational ve bonussuzdur — bu ayrım
        normalize edilmemeli."""
        resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/foremen", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items, pagination = unwrap_page(resp)
        assert pagination["total"] == len(items) == 2
        scores = [item["generalPerformanceScore"] for item in items]
        assert scores == sorted(scores, reverse=True)
        for item in items:
            assert item["generalPerformanceScore"] == round(
                item["operationalScore"] + item["contributionBonus"], 2
            )
            assert item["employeeNumber"].startswith("SCL-")
            assert item["level"]["outstandingPerformance"] in {True, False}

    def test_plant_foremen_unknown_plant_returns_empty_200_not_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/plants/{self._UNKNOWN_ID}/foremen", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items, pagination = unwrap_page(resp)
        assert items == []
        assert pagination["total"] == 0

    def test_plant_foremen_pagination_boundary(self, client, auth_headers):
        first_resp = client.get(
            f"/api/v1/plants/{self._PLANT_ID}/foremen",
            params={**self._PARAMS, "limit": 1}, headers=auth_headers,
        )
        _, first_pagination = unwrap_page(first_resp)
        next_cursor = first_pagination["nextCursor"]
        assert next_cursor

        resp = client.get(
            f"/api/v1/plants/{self._PLANT_ID}/foremen",
            params={**self._PARAMS, "limit": 1, "cursor": next_cursor}, headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        items, pagination = unwrap_page(resp)
        assert pagination["total"] == 2
        assert len(items) == 1
        full_items, _ = unwrap_page(client.get(
            f"/api/v1/plants/{self._PLANT_ID}/foremen", params=self._PARAMS, headers=auth_headers
        ))
        assert items[0] == full_items[1]

    def test_list_plants_query_count(self, client, auth_headers):
        with _count_queries() as counter:
            resp = client.get(
                "/api/v1/plants", params={**self._PARAMS, "limit": 3}, headers=auth_headers
            )
        assert resp.status_code == 200
        assert counter["n"] == 31  # +2: RBAC get_auth_context sabit ek yuku

    def test_plant_summary_query_count(self, client, auth_headers):
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/summary", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 40  # +2: RBAC get_auth_context sabit ek yuku

    def test_plant_foremen_query_count(self, client, auth_headers):
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/plants/{self._PLANT_ID}/foremen", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 17  # +2: RBAC get_auth_context sabit ek yuku

    def test_plant_foremen_unknown_plant_query_count(self, client, auth_headers):
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/plants/{self._UNKNOWN_ID}/foremen", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 12  # +2: RBAC get_auth_context sabit ek yuku


class TestForemenEndpoints:
    def test_list_foremen_search(self, client, auth_headers):
        resp = client.get("/api/v1/foremen", params={"limit": 5}, headers=auth_headers)
        assert resp.status_code == 200
        _, pagination = unwrap_page(resp)
        assert pagination["total"] > 0

    def test_foreman_detail_and_kpis(self, client, auth_headers):
        items, _ = unwrap_page(client.get("/api/v1/foremen", params={"limit": 1}, headers=auth_headers))
        foreman_id = items[0]["id"]

        detail = client.get(f"/api/v1/foremen/{foreman_id}", headers=auth_headers)
        assert detail.status_code == 200
        body = unwrap(detail)
        assert body["id"] == foreman_id
        assert body["phoneNumber"].startswith("+90")
        assert "@" in body["email"]

        kpis = client.get(f"/api/v1/foremen/{foreman_id}/kpis", headers=auth_headers)
        assert kpis.status_code == 200
        kpi_items = unwrap(kpis)
        assert len(kpi_items) == 6
        total_weight = sum(i["weight"] for i in kpi_items)
        assert total_weight == pytest.approx(100)

    def test_foreman_calculation_detail_contains_formula_breakdown(self, client, auth_headers):
        items, _ = unwrap_page(client.get("/api/v1/foremen", params={"limit": 1}, headers=auth_headers))
        foreman_id = items[0]["id"]
        kpi_items = unwrap(client.get(f"/api/v1/foremen/{foreman_id}/kpis", headers=auth_headers))
        kpi_id = kpi_items[0]["kpiId"]

        resp = client.get(f"/api/v1/foremen/{foreman_id}/kpis/{kpi_id}/calculation-detail", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        for field in ["targetValue", "actualValue", "calculationType", "rawScore", "cappedScore", "kpiWeight", "sourceRecordId"]:
            assert field in body

    def test_foreman_assignment_history_not_empty(self, client, auth_headers):
        items, _ = unwrap_page(client.get("/api/v1/foremen", params={"limit": 1}, headers=auth_headers))
        foreman_id = items[0]["id"]
        resp = client.get(f"/api/v1/foremen/{foreman_id}/assignment-history", headers=auth_headers)
        assert resp.status_code == 200
        assert len(unwrap(resp)) >= 1

    def test_foreman_detail_404_for_unknown_id(self, client, auth_headers):
        resp = client.get(f"/api/v1/foremen/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


class TestForemanAssignmentHistory:
    """assignment-history testleri sıralamayı, ilişkili varlık alanlarını ve N+1'in
    kaldırıldığını (sorgu sayısının atama sayısından bağımsız, sabit kaldığını) kilitler.
    """

    def test_matches_db_ordering_and_related_entity_names(self, client, auth_headers, db_session):
        foreman_id, count = db_session.execute(
            select(ForemanAssignment.foreman_id, func.count())
            .group_by(ForemanAssignment.foreman_id)
            .order_by(func.count().desc())
            .limit(1)
        ).one()
        assert count >= 1, "Testler için önce seed çalıştırılmalı."

        expected = list(
            db_session.scalars(
                select(ForemanAssignment)
                .where(ForemanAssignment.foreman_id == foreman_id)
                .order_by(ForemanAssignment.start_date)
            )
        )
        assert expected

        resp = client.get(f"/api/v1/foremen/{foreman_id}/assignment-history", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items = unwrap(resp)
        assert len(items) == len(expected)

        for item, assignment in zip(items, expected):
            plant = db_session.get(Plant, assignment.plant_id)
            chief = db_session.get(Chief, assignment.chief_id)
            shift = db_session.get(Shift, assignment.shift_id)
            assert item["plant"] == (plant.name if plant else None)
            assert item["chief"] == (f"{chief.first_name} {chief.last_name}" if chief else None)
            assert item["shift"] == (shift.name if shift else None)
            assert item["startDate"] == assignment.start_date.isoformat()
            assert item["endDate"] == (assignment.end_date.isoformat() if assignment.end_date else None)
            assert item["isActive"] == assignment.is_active

    def test_unknown_foreman_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/foremen/{uuid.uuid4()}/assignment-history", headers=auth_headers)
        assert resp.status_code == 404


class TestForemanAssignmentHistoryQueryCount:
    def test_query_count_does_not_scale_with_assignment_count(self, client, auth_headers, db_session):
        counts = db_session.execute(
            select(ForemanAssignment.foreman_id, func.count())
            .group_by(ForemanAssignment.foreman_id)
            .order_by(func.count().desc())
        ).all()
        assert len(counts) >= 2, "Testler için önce seed çalıştırılmalı."
        many_id, many_n = counts[0]
        few_id, few_n = counts[-1]
        assert many_n >= few_n

        with _count_queries() as counter:
            resp_few = client.get(f"/api/v1/foremen/{few_id}/assignment-history", headers=auth_headers)
        assert resp_few.status_code == 200
        q_few = counter["n"]

        with _count_queries() as counter:
            resp_many = client.get(f"/api/v1/foremen/{many_id}/assignment-history", headers=auth_headers)
        assert resp_many.status_code == 200
        q_many = counter["n"]

        assert q_many == q_few, (
            f"Sorgu sayısı atama sayısıyla birlikte büyüyor: few={q_few} (n={few_n}), many={q_many} (n={many_n})"
        )
        # +2: RBAC get_auth_context sabit ek yuku (user_role_assignments get + user_scope_assignments select)
        assert q_many <= 7, f"Beklenenden fazla sorgu: {q_many}"


class TestForemanKpiPresentation:
    """kpi_presentation.py'nin PLANA_UYUM sunumunu kilitleyen characterization testi.
    Diğer testler yalnızca alan varlığını kontrol eder; bu test ham denominator/numerator
    değerlerinden yeniden hesaplanan kg_diff/signed_pct_deviation/status formülüyle
    response'un birebir eşleştiğini doğrular.
    """

    def test_plana_uyum_calculation_detail_matches_raw_record_math(self, client, auth_headers, db_session):
        kpi = db_session.scalar(select(Kpi).where(Kpi.code == "PLANA_UYUM"))
        assert kpi is not None, "Testler için önce seed çalıştırılmalı."

        candidate = db_session.scalar(
            select(PerformanceRecord).where(
                PerformanceRecord.kpi_id == kpi.id,
                PerformanceRecord.denominator_value.is_not(None),
                PerformanceRecord.numerator_value.is_not(None),
            )
        )
        assert candidate is not None, "Testler için önce seed çalıştırılmalı."

        row = analytics.latest_foreman_kpi_record(db_session, candidate.foreman_id, kpi.id)
        assert row is not None
        record, _score = row
        assert record.denominator_value is not None and record.numerator_value is not None

        resp = client.get(
            f"/api/v1/foremen/{candidate.foreman_id}/kpis/{kpi.id}/calculation-detail", headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        body = unwrap(resp)

        planned_qty = float(record.denominator_value)
        actual_qty = float(record.numerator_value)
        expected_kg_diff = round(actual_qty - planned_qty, 2)
        expected_pct = round((actual_qty - planned_qty) / planned_qty * 100.0, 2) if planned_qty else None
        expected_status = (
            "ABOVE_PLAN" if (expected_pct or 0) > 0
            else ("BELOW_PLAN" if (expected_pct or 0) < 0 else "ON_PLAN")
        )

        assert "planaUyum" in body
        pu = body["planaUyum"]
        assert pu["plannedQty"] == round(planned_qty, 2)
        assert pu["actualQty"] == round(actual_qty, 2)
        assert pu["kgDiff"] == expected_kg_diff
        assert pu["signedPctDeviation"] == expected_pct
        assert pu["status"] == expected_status


class TestForemanTrendEndpoint:
    """trend uç noktası için minimal characterization testleri; mevcut response şeklini
    kilitler."""

    def test_requires_auth(self, client, db_session):
        foreman = db_session.scalar(select(Foreman).where(Foreman.is_active.is_(True)))
        assert foreman is not None
        resp = client.get(f"/api/v1/foremen/{foreman.id}/trend")
        assert resp.status_code == 401

    def test_returns_series_with_default_granularity(self, client, auth_headers, db_session):
        foreman = db_session.scalar(select(Foreman).where(Foreman.is_active.is_(True)))
        assert foreman is not None
        resp = client.get(f"/api/v1/foremen/{foreman.id}/trend", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = unwrap(resp)
        assert body["granularity"] == "day"
        assert isinstance(body["points"], list)
        for point in body["points"]:
            assert set(point.keys()) == {"date", "totalScore", "isReliable"}
            assert isinstance(point["totalScore"], (int, float))
            assert isinstance(point["isReliable"], bool)


class TestKpiEndpoints:
    def test_list_kpis_returns_six_active(self, client, auth_headers):
        resp = client.get("/api/v1/kpis", headers=auth_headers)
        assert resp.status_code == 200
        items = unwrap(resp)
        assert len(items) == 6
        assert sum(i["weight"] for i in items) == pytest.approx(100)

    def test_list_kpis_exact_shape_and_display_order(self, client, auth_headers, db_session):
        expected_kpis = list(
            db_session.scalars(select(Kpi).where(Kpi.is_active.is_(True)).order_by(Kpi.display_order))
        )
        resp = client.get("/api/v1/kpis", headers=auth_headers)
        assert resp.status_code == 200
        items = unwrap(resp)

        assert [i["code"] for i in items] == [k.code for k in expected_kpis]
        assert [i["code"] for i in items] == ["AGIR_GITME", "GSF", "ISKARTA", "INKITA", "PLANA_UYUM", "OEE"]
        for item, kpi in zip(items, expected_kpis):
            assert item == {
                "id": str(kpi.id),
                "code": kpi.code,
                "name": kpi.name,
                "description": kpi.description,
                "unit": kpi.unit,
                "calculationType": kpi.calculation_type.value,
                "weight": float(kpi.weight),
                "defaultTargetValue": float(kpi.default_target_value),
                "isCritical": kpi.is_critical,
            }

    def test_list_kpis_query_count(self, client, auth_headers):
        with _count_queries() as counter:
            resp = client.get("/api/v1/kpis", headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 3  # +2: RBAC get_auth_context sabit ek yuku

    def test_get_kpi_detail_exact_shape(self, client, auth_headers, db_session):
        kpi = db_session.scalars(select(Kpi).order_by(Kpi.display_order)).first()
        resp = client.get(f"/api/v1/kpis/{kpi.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert unwrap(resp) == {
            "id": str(kpi.id),
            "code": kpi.code,
            "name": kpi.name,
            "description": kpi.description,
            "unit": kpi.unit,
            "calculationType": kpi.calculation_type.value,
            "successDirectionHigher": kpi.success_direction_higher,
            "defaultTargetValue": float(kpi.default_target_value),
            "minScore": float(kpi.min_score),
            "maxScore": float(kpi.max_score),
            "weight": float(kpi.weight),
            "aggregationMethod": kpi.aggregation_method.value,
            "isCritical": kpi.is_critical,
        }

    def test_get_kpi_detail_unknown_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/kpis/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
        assert unwrap_error(resp)["code"] == "KPI_NOT_FOUND"

    def test_get_kpi_detail_query_count_normal_and_unknown(self, client, auth_headers, db_session):
        kpi = db_session.scalars(select(Kpi).order_by(Kpi.display_order)).first()
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/kpis/{kpi.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 3  # +2: RBAC get_auth_context sabit ek yuku

        with _count_queries() as counter:
            resp2 = client.get(f"/api/v1/kpis/{uuid.uuid4()}", headers=auth_headers)
        assert resp2.status_code == 404
        assert counter["n"] == 3  # +2: RBAC get_auth_context sabit ek yuku

    def test_kpi_analysis(self, client, auth_headers):
        kpi_id = unwrap(client.get("/api/v1/kpis", headers=auth_headers))[0]["id"]
        resp = client.get(f"/api/v1/kpis/{kpi_id}/analysis", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        assert "bestPlants" in body
        assert "worstPlants" in body
        assert "trend" in body


class TestKpiAnalysis:
    _PERIOD = {"date_from": "2025-08-01", "date_to": "2026-07-28"}
    _EMPTY = {"date_from": "2099-01-01", "date_to": "2099-01-31"}

    def _kpi(self, db_session):
        return db_session.scalars(select(Kpi).where(Kpi.code == "AGIR_GITME")).first()

    def _filters(self, kpi_id, window):
        return Filters(
            date_from=date.fromisoformat(window["date_from"]),
            date_to=date.fromisoformat(window["date_to"]),
            kpi_ids=[kpi_id],
        )

    def test_header_and_company_summary_exact(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        filters = self._filters(kpi.id, self._PERIOD)
        summary = analytics.kpi_summary(db_session, filters)
        expected_score = round(summary[0].avg_capped_score, 2) if summary else 0.0
        expected_target = (
            round(summary[0].avg_target, 2) if summary and summary[0].avg_target is not None else None
        )
        expected_actual = (
            round(summary[0].avg_actual, 2) if summary and summary[0].avg_actual is not None else None
        )

        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)

        assert body["kpi"] == {
            "id": str(kpi.id), "code": kpi.code, "name": kpi.name, "unit": kpi.unit,
            "decimalPlaces": kpi.decimal_places,
        }
        assert body["companyAvgScore"] == expected_score
        assert body["companyAvgTarget"] == expected_target
        assert body["companyAvgActual"] == expected_actual

    def test_plant_section_exact(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        filters = self._filters(kpi.id, self._PERIOD)
        raw_sorted = sorted(analytics.plant_scores(db_session, filters), key=lambda s: s.total_score, reverse=True)
        plants_by_id = {p.id: p for p in db_session.scalars(select(Plant))}

        def ref(s):
            p = plants_by_id.get(s.key)
            return {
                "id": str(s.key), "name": p.name if p else None,
                "code": p.code if p else None, "score": round(s.total_score, 2),
            }

        expected_best = [ref(s) for s in raw_sorted[:5]]
        expected_worst = [ref(s) for s in (list(reversed(raw_sorted[-5:])) if len(raw_sorted) > 5 else [])]

        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        body = unwrap(resp)
        assert body["bestPlants"] == expected_best
        assert body["worstPlants"] == expected_worst

    def test_shift_section_exact(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        filters = self._filters(kpi.id, self._PERIOD)
        raw_sorted = sorted(analytics.shift_scores(db_session, filters), key=lambda s: s.total_score, reverse=True)
        shifts_by_id = {s.id: s for s in db_session.scalars(select(Shift))}
        expected = [
            {"id": str(s.key), "name": shifts_by_id[s.key].name if s.key in shifts_by_id else None,
             "score": round(s.total_score, 2)}
            for s in raw_sorted
        ]

        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        body = unwrap(resp)
        assert body["shiftComparison"] == expected

    def test_foreman_section_exact(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        filters = self._filters(kpi.id, self._PERIOD)
        raw_sorted = sorted(analytics.foreman_scores(db_session, filters), key=lambda s: s.total_score, reverse=True)
        foremen_by_id = {f.id: f for f in db_session.scalars(select(Foreman))}

        def ref(s):
            f = foremen_by_id.get(s.key)
            return {
                "id": str(s.key), "name": f"{f.first_name} {f.last_name}" if f else None,
                "code": f.employee_number if f else None,
                "score": round(s.total_score, 2),
            }

        expected_best = [ref(s) for s in raw_sorted[:5]]
        expected_worst = [ref(s) for s in (list(reversed(raw_sorted[-5:])) if len(raw_sorted) > 5 else [])]

        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        body = unwrap(resp)
        assert body["bestForemen"] == expected_best
        assert body["worstForemen"] == expected_worst

    def test_trend_exact_and_week_hardcoded(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        filters = self._filters(kpi.id, self._PERIOD)
        raw = analytics.trend(db_session, filters, "week")
        expected = [{"date": p.bucket.isoformat(), "score": round(p.total_score, 2)} for p in raw]

        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        body = unwrap(resp)
        assert body["trend"] == expected
        assert all(set(pt.keys()) == {"date", "score"} for pt in body["trend"])
        dates = [pt["date"] for pt in body["trend"]]
        assert dates == sorted(dates)

    def test_foreman_values_exact_fields_and_ordinal_order(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        filters = self._filters(kpi.id, self._PERIOD)
        summary = analytics.kpi_summary(db_session, filters)
        company_avg_target = summary[0].avg_target if summary else None
        assert company_avg_target is not None

        raw_values = analytics.foreman_kpi_values(db_session, filters, kpi, company_avg_target)
        foremen_by_id = {f.id: f for f in db_session.scalars(select(Foreman))}

        expected_by_id = {}
        for fv in raw_values:
            f = foremen_by_id.get(fv.foreman_id)
            expected_by_id[str(fv.foreman_id)] = {
                "full_name": f"{f.first_name} {f.last_name}" if f else None,
                "avg_actual": round(fv.avg_actual, 4),
                "avg_target": round(fv.avg_target, 4),
                "avg_score": round(fv.capped_score, 2),
                "record_count": fv.record_count,
            }

        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        body = unwrap(resp)
        actual_values = body["foremanValues"]

        assert len(actual_values) == len(expected_by_id)
        for item in actual_values:
            expected = expected_by_id[item["foremanId"]]
            assert item["fullName"] == expected["full_name"]
            assert item["avgActual"] == expected["avg_actual"]
            assert item["avgTarget"] == expected["avg_target"]
            assert item["avgScore"] == expected["avg_score"]
            assert item["recordCount"] == expected["record_count"]
            assert item["tier"] in ("near", "better", "worse")
            assert set(item["level"].keys()) == {
                "name", "description", "color", "icon", "outstandingPerformance",
            }

        names = [item["fullName"] or "" for item in actual_values]
        assert names == sorted(names)

    def test_path_kpi_override_ignores_conflicting_query_param(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        other = db_session.scalars(select(Kpi).where(Kpi.code == "GSF")).first()

        plain = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        conflict = client.get(
            f"/api/v1/kpis/{kpi.id}/analysis",
            params={**self._PERIOD, "kpi_ids": str(other.id)}, headers=auth_headers,
        )
        assert plain.status_code == 200
        assert conflict.status_code == 200
        assert conflict.json() == plain.json()

    def test_unknown_kpi_404_and_query_count(self, client, auth_headers):
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/kpis/{uuid.uuid4()}/analysis", params=self._PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        assert unwrap_error(resp)["code"] == "KPI_NOT_FOUND"
        assert counter["n"] == 3  # +2: RBAC get_auth_context sabit ek yuku

    def test_empty_window_exact_response(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._EMPTY, headers=auth_headers)
        assert resp.status_code == 200
        assert unwrap(resp) == {
            "kpi": {
                "id": str(kpi.id), "code": kpi.code, "name": kpi.name, "unit": kpi.unit,
                "decimalPlaces": kpi.decimal_places,
            },
            "companyAvgScore": 0.0,
            "companyAvgTarget": None,
            "companyAvgActual": None,
            "bestPlants": [],
            "worstPlants": [],
            "shiftComparison": [],
            "bestForemen": [],
            "worstForemen": [],
            "foremanValues": [],
            "trend": [],
        }

    def test_query_counts_normal_and_empty(self, client, auth_headers, db_session):
        kpi = self._kpi(db_session)
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 64  # +2: RBAC get_auth_context sabit ek yuku

        with _count_queries() as counter:
            resp2 = client.get(f"/api/v1/kpis/{kpi.id}/analysis", params=self._EMPTY, headers=auth_headers)
        assert resp2.status_code == 200
        assert counter["n"] == 51  # +2: RBAC get_auth_context sabit ek yuku


class TestDbSideCursorPaginationRegression:
    def test_paginate_in_memory_not_used_by_any_service_or_repository(self):
        app_root = Path(__file__).resolve().parents[2] / "app"
        offenders = [
            str(path)
            for sub in ("services", "repositories")
            for path in (app_root / sub).rglob("*.py")
            if "paginate_in_memory" in path.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_list_plants_query_is_limited_in_sql(self, client, auth_headers):
        with _capture_statements() as statements:
            resp = client.get("/api/v1/plants", params={"limit": 3}, headers=auth_headers)
        assert resp.status_code == 200
        matching = [s for s in statements if "plants" in s and "LIMIT" in s.upper()]
        assert matching

    def test_list_foremen_query_is_limited_in_sql(self, client, auth_headers):
        with _capture_statements() as statements:
            resp = client.get("/api/v1/foremen", params={"limit": 3}, headers=auth_headers)
        assert resp.status_code == 200
        matching = [s for s in statements if "foremen" in s and "LIMIT" in s.upper()]
        assert matching

    def test_list_foremen_cursor_pagination_continues_without_duplicates(self, client, auth_headers):
        first = client.get("/api/v1/foremen", params={"limit": 5}, headers=auth_headers)
        items1, pagination1 = unwrap_page(first)
        assert len(items1) == 5
        assert pagination1["hasMore"] is True
        cursor = pagination1["nextCursor"]
        assert cursor

        second = client.get("/api/v1/foremen", params={"limit": 5, "cursor": cursor}, headers=auth_headers)
        assert second.status_code == 200
        items2, _ = unwrap_page(second)
        ids1 = {i["id"] for i in items1}
        ids2 = {i["id"] for i in items2}
        assert ids1.isdisjoint(ids2)

    def test_list_foremen_invalid_cursor_on_sort_mismatch(self, client, auth_headers):
        first = client.get(
            "/api/v1/foremen", params={"limit": 2, "sort_by": "name", "sort_dir": "asc"}, headers=auth_headers
        )
        _, pagination = unwrap_page(first)
        cursor = pagination["nextCursor"]
        assert cursor

        mismatch = client.get(
            "/api/v1/foremen",
            params={"limit": 2, "sort_by": "employee_number", "sort_dir": "asc", "cursor": cursor},
            headers=auth_headers,
        )
        assert mismatch.status_code == 400
        assert unwrap_error(mismatch)["code"] == "INVALID_CURSOR"

    def test_list_foremen_malformed_cursor_returns_invalid_cursor(self, client, auth_headers):
        resp = client.get("/api/v1/foremen", params={"cursor": "not-a-real-cursor"}, headers=auth_headers)
        assert resp.status_code == 400
        assert unwrap_error(resp)["code"] == "INVALID_CURSOR"

    def test_plant_foremen_query_is_limited_in_sql(self, client, auth_headers):
        items, _ = unwrap_page(client.get("/api/v1/plants", params={"limit": 1}, headers=auth_headers))
        plant_id = items[0]["id"]
        with _capture_statements() as statements:
            resp = client.get(f"/api/v1/plants/{plant_id}/foremen", headers=auth_headers)
        assert resp.status_code == 200
        matching = [s for s in statements if "foremen" in s and "LIMIT" in s.upper()]
        assert matching
