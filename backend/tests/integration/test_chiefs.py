
import uuid
from tests.helpers import legacy_json, unwrap_error, unwrap_page
from contextlib import contextmanager
from datetime import date

import pytest
from sqlalchemy import event, func, select

from app.db.session import engine
from app.models.foreman import Chief, ForemanAssignment
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant
from app.schemas.common import Filters
from app.services import analytics, contribution_bonus
from app.services.kpi_engine import weighted_geometric_score

PERIOD = {"date_from": "2025-08-01", "date_to": "2026-07-28"}
EMPTY_WINDOW = {"date_from": "2099-01-01", "date_to": "2099-01-31"}


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


class TestChiefList:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/chiefs").status_code == 401

    def test_returns_chiefs_with_team_scores(self, client, auth_headers):
        resp = client.get("/api/v1/chiefs", params={**PERIOD, "limit": 50}, headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["total"] > 0
        item = body["items"][0]
        assert item["plants"] and item["factory"] is not None
        assert item["foreman_count"] >= 1
        assert item["level"]["name"]

    def test_factory_filter_narrows_the_list(self, client, auth_headers, db_session):
        factories = list(db_session.scalars(select(Factory).order_by(Factory.code)))
        totals = []
        for factory in factories:
            resp = client.get(
                "/api/v1/chiefs",
                params={**PERIOD, "factory_ids": str(factory.id), "limit": 200},
                headers=auth_headers,
            )
            body = legacy_json(resp)
            totals.append(body["total"])
            assert all(i["factory"]["code"] == factory.code for i in body["items"])

        unfiltered = legacy_json(client.get("/api/v1/chiefs", params={**PERIOD, "limit": 1}, headers=auth_headers))
        assert sum(totals) == unfiltered["total"]

    def test_score_sort_is_monotonic(self, client, auth_headers):
        resp = client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "score", "sort_dir": "desc", "limit": 50},
            headers=auth_headers,
        )
        scores = [i["total_score"] for i in legacy_json(resp)["items"]]
        assert scores == sorted(scores, reverse=True)

    def test_search_matches_employee_number(self, client, auth_headers, db_session):
        sample = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        needle = sample.employee_number[:-1]
        resp = client.get("/api/v1/chiefs", params={**PERIOD, "search": needle, "limit": 50}, headers=auth_headers)
        items = legacy_json(resp)["items"]
        assert items and all(i["employee_number"].startswith(needle) for i in items)

    def test_pagination_matches_full_sorted_slice(self, client, auth_headers):
        """Python-slice pagination'ı kilitler: N. sayfa tam sıralı sonucun
        [start:start+page_size] dilimi olmalı, farklı sıralama üretebilecek DB
        LIMIT/OFFSET olmamalı."""
        full = legacy_json(client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "employee_number", "sort_dir": "asc", "limit": 200},
            headers=auth_headers,
        ))
        page1 = legacy_json(client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "employee_number", "sort_dir": "asc", "limit": 5},
            headers=auth_headers,
        ))
        page2 = legacy_json(client.get(
            "/api/v1/chiefs",
            params={
                **PERIOD,
                "sort_by": "employee_number",
                "sort_dir": "asc",
                "limit": 5,
                "cursor": page1["next_cursor"],
            },
            headers=auth_headers,
        ))
        assert [i["id"] for i in page1["items"]] == [i["id"] for i in full["items"][:5]]
        assert [i["id"] for i in page2["items"]] == [i["id"] for i in full["items"][5:10]]
        assert page1["has_more"] is True

    def test_plant_id_filter_narrows_to_the_owning_chief(self, client, auth_headers, db_session):
        plant = db_session.scalars(select(Plant).order_by(Plant.sequence_number)).first()
        resp = client.get(
            "/api/v1/chiefs", params={**PERIOD, "plant_id": str(plant.id), "limit": 200}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["total"] == 1
        assert body["items"][0]["id"] == str(plant.chief_id)

    def test_is_active_true_filter_matches_current_seed(self, client, auth_headers, db_session):
        """Güncel seed verisinde pasif şef yok; tüm kayıtlar is_active=True. Bu test
        yalnızca is_active=true tarafını karakterize eder, pasif fixture içermez."""
        total_chiefs = db_session.scalar(select(func.count()).select_from(Chief))
        inactive_chiefs = db_session.scalar(select(func.count()).select_from(Chief).where(Chief.is_active.is_(False)))
        assert inactive_chiefs == 0, "Beklenmedik: inactive chief bulundu — bu test artık kontrast durumu da kapsamalı"

        resp = client.get(
            "/api/v1/chiefs", params={**PERIOD, "is_active": "true", "limit": 200}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["total"] == total_chiefs
        assert all(i["is_active"] for i in body["items"])

    def test_employee_number_sort_is_lexicographic_ascending(self, client, auth_headers):
        resp = client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "employee_number", "sort_dir": "asc", "limit": 200},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        numbers = [i["employee_number"] for i in legacy_json(resp)["items"]]
        assert numbers == sorted(numbers)
        assert numbers[0] < numbers[-1]

    def test_kpi_only_filter_changes_score_without_changing_entity_count(self, client, auth_headers, db_session):
        """shift_ids/kpi_ids yalnızca score filtresidir; _chiefs_in_scope bunları kullanmaz.

        Fixture eklemeden tam sıfır score alan şef bulunamadığı için entity/score ayrımı
        doğrudan doğrulanır: kpi_ids filtresi entity id kümesini değiştirmez, en az bir
        şefin score'unu değiştirir.
        """
        kpi = db_session.scalars(select(Kpi).where(Kpi.code == "AGIR_GITME")).first()
        unfiltered = legacy_json(client.get("/api/v1/chiefs", params={**PERIOD, "limit": 200}, headers=auth_headers))
        filtered = legacy_json(client.get(
            "/api/v1/chiefs", params={**PERIOD, "kpi_ids": str(kpi.id), "limit": 200}, headers=auth_headers
        ))
        assert filtered["total"] == unfiltered["total"]
        scores_unfiltered = {i["id"]: i["total_score"] for i in unfiltered["items"]}
        scores_filtered = {i["id"]: i["total_score"] for i in filtered["items"]}
        assert scores_unfiltered.keys() == scores_filtered.keys()
        assert any(scores_unfiltered[k] != scores_filtered[k] for k in scores_unfiltered)


class TestChiefDetail:
    def test_unknown_id_returns_404(self, client, auth_headers):
        import uuid

        assert client.get(f"/api/v1/chiefs/{uuid.uuid4()}", headers=auth_headers).status_code == 404

    def test_query_chief_ids_is_ignored_for_ranking_cohort(self, client, auth_headers, db_session):
        """resolve_chief_scope, ranking cohort öncesinde filters.chief_ids'i kaldırır.
        Çakışan query chief_ids, path'teki şefin score/company_rank/company_total
        değerini değiştirmemeli."""
        chiefs = list(db_session.scalars(select(Chief).order_by(Chief.employee_number)))
        chief, other_chief = chiefs[0], chiefs[1]
        unfiltered = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}", params=PERIOD, headers=auth_headers))
        conflicting = legacy_json(client.get(
            f"/api/v1/chiefs/{chief.id}", params={**PERIOD, "chief_ids": str(other_chief.id)}, headers=auth_headers
        ))
        assert conflicting["total_score"] == pytest.approx(unfiltered["total_score"], abs=0.01)
        assert conflicting["company_total"] == unfiltered["company_total"]
        assert conflicting["company_rank"] == unfiltered["company_rank"]

    def test_unrelated_factory_filter_excludes_path_chief_without_404(self, client, auth_headers, db_session):
        """Path'teki şefi scoring cohort dışında bırakan filtre yine 200 ve sıfır/null
        score döndürmeli; entity lookup koşulsuzdur, filtrelenmiş cohort'tan bağımsızdır."""
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        chief_plant = db_session.scalars(select(Plant).where(Plant.chief_id == chief.id)).first()
        other_plant = db_session.scalars(select(Plant).where(Plant.factory_id != chief_plant.factory_id)).first()

        resp = client.get(
            f"/api/v1/chiefs/{chief.id}",
            params={**PERIOD, "factory_ids": str(other_plant.factory_id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["id"] == str(chief.id)
        assert body["total_score"] == 0.0
        assert body["is_reliable"] is False
        assert body["company_rank"] is None
        assert body["plants"]

    def test_zero_plants_chief_is_a_documented_coverage_gap(self, db_session):
        """Güncel seed verisinde her şefin en az bir fabrikası var; get_chief içindeki
        factory=None/factory_rank=None/factory_total=0 dalı fixture eklemeden runtime'da
        tetiklenemez — bilinen coverage sınırı."""
        no_plant_chiefs = set(db_session.scalars(select(Chief.id))) - set(
            db_session.scalars(select(Plant.chief_id).distinct())
        )
        assert no_plant_chiefs == set(), (
            "Beklenmedik: plantsız chief bulundu — bu durum artık canlı doğrulanabilir, "
            "bu test genişletilmeli"
        )

    def test_score_is_recomputed_from_chief_totals_not_averaged(self, client, auth_headers, db_session):
        listing = legacy_json(client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "sort_by": "foreman_count", "sort_dir": "desc", "limit": 5},
            headers=auth_headers,
        ))

        for row in listing["items"]:
            breakdown = legacy_json(client.get(f"/api/v1/chiefs/{row['id']}/kpis", params=PERIOD, headers=auth_headers))
            expected = weighted_geometric_score(
                [(i["avg_capped_score"], i["weight"]) for i in breakdown["items"]]
            )
            assert row["total_score"] == pytest.approx(expected, rel=0.01)

    def test_detail_exposes_rankings(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}", params=PERIOD, headers=auth_headers))
        assert 1 <= body["company_rank"] <= body["company_total"]
        assert 1 <= body["factory_rank"] <= body["factory_total"]
        assert body["factory_total"] <= body["company_total"]

    def test_detail_exposes_contact_info(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}", params=PERIOD, headers=auth_headers))
        assert body["phone_number"].startswith("+90")
        assert "@" in body["email"]

    def test_team_members_all_belong_to_the_chief(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        team = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=PERIOD, headers=auth_headers))
        assert team["items"]
        foremen = legacy_json(client.get(
            "/api/v1/foremen",
            params={**PERIOD, "chief_id": str(chief.id), "limit": 200},
            headers=auth_headers,
        ))
        assert {f["id"] for f in team["items"]} <= {f["id"] for f in foremen["items"]}

    def test_kpi_breakdown_returns_all_active_kpis(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/kpis", params=PERIOD, headers=auth_headers))
        assert len(body["items"]) == 6
        assert sum(i["weight"] for i in body["items"]) == pytest.approx(100)

    def test_trend_returns_ordered_points(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        body = legacy_json(client.get(
            f"/api/v1/chiefs/{chief.id}/trend", params={**PERIOD, "granularity": "month"}, headers=auth_headers
        ))
        dates = [p["date"] for p in body["points"]]
        assert dates == sorted(dates)

    def test_kpis_unknown_id_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/kpis", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp) == {"detail": "Şef bulunamadı."}

    def test_kpis_omits_kpis_with_no_data_in_window(self, client, auth_headers, db_session):
        """Fixture değiştirmeden hiç PerformanceRecord içermeyen gelecek pencereyi kullanır.

        Uygun verisi olmayan KPI'ların sıfırla doldurulmak yerine `items` dışında bırakılması
        contract'ını kilitler.
        """
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/kpis", params=EMPTY_WINDOW, headers=auth_headers)
        assert resp.status_code == 200
        assert legacy_json(resp) == {"items": []}

    def test_trend_unknown_id_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/trend", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp) == {"detail": "Şef bulunamadı."}

    def test_trend_matches_analytics_trend_exactly(self, client, auth_headers, db_session):
        """Endpoint sonucunu eşdeğer Filters ile doğrudan çağrılan `analytics.trend`
        sonucuyla alan alan karşılaştırır; chief_ids path'teki tek şefe sabitlenir.
        """
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(
            f"/api/v1/chiefs/{chief.id}/trend", params={**PERIOD, "granularity": "month"}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = legacy_json(resp)

        filters = Filters(
            date_from=date.fromisoformat(PERIOD["date_from"]),
            date_to=date.fromisoformat(PERIOD["date_to"]),
            chief_ids=[chief.id],
        )
        expected = analytics.trend(db_session, filters, "month")

        assert len(body["points"]) == len(expected)
        for actual_point, expected_point in zip(body["points"], expected):
            assert actual_point["date"] == expected_point.bucket.isoformat()
            assert actual_point["total_score"] == pytest.approx(round(expected_point.total_score, 2), abs=0.005)
            assert actual_point["is_reliable"] == expected_point.is_reliable

    def test_trend_empty_window_returns_empty_points(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(
            f"/api/v1/chiefs/{chief.id}/trend", params={**EMPTY_WINDOW, "granularity": "month"}, headers=auth_headers
        )
        assert resp.status_code == 200
        assert legacy_json(resp) == {"granularity": "month", "points": []}


class TestChiefKpisTrendQueryBaseline:
    """chief_kpis/chief_trend query-count baseline'ı; `before_cursor_execute` ile
    ölçülür. 404 short-circuit için yalnızca existence query çalışmasını kilitler."""

    def test_kpis_query_count_normal_and_unknown(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{chief.id}/kpis", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        normal_n = counter["n"]

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/kpis", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        unknown_n = counter["n"]

        # +2: get_auth_context (RBAC) her request'te role/scope'u DB'den okur (user_role_assignments get + user_scope_assignments select), 404 kisa devresinden once calisir.
        assert unknown_n == 3, f"404 yolunun (authz sonrasi) kisa devre yapmasi bekleniyor: {unknown_n}"
        assert normal_n >= unknown_n

    def test_trend_query_count_normal_and_unknown(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{chief.id}/trend", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        normal_n = counter["n"]

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/trend", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        unknown_n = counter["n"]

        # +2: get_auth_context (RBAC) her request'te role/scope'u DB'den okur (user_role_assignments get + user_scope_assignments select), 404 kisa devresinden once calisir.
        assert unknown_n == 3, f"404 yolunun (authz sonrasi) kisa devre yapmasi bekleniyor: {unknown_n}"
        assert normal_n >= unknown_n


class TestChiefForemen:
    def test_representative_item_matches_current_primitives(self, client, auth_headers, db_session):
        """Dönen bir item'ı doğrudan çağrılan chief_team_scores -> contribution_bonus
        pipeline sonucuyla alan alan karşılaştırır.
        """
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert items

        filters = Filters(
            date_from=date.fromisoformat(PERIOD["date_from"]),
            date_to=date.fromisoformat(PERIOD["date_to"]),
            chief_ids=[chief.id],
        )
        team = next(t for t in analytics.chief_team_scores(db_session, filters) if t.chief_id == chief.id)
        scores_by_key = {s.key: s for s in team.foreman_scores}
        bonuses = contribution_bonus.foreman_contribution_bonuses(
            db_session, filters.date_to, foreman_ids=list(scores_by_key.keys())
        )

        item = items[0]
        foreman_id = uuid.UUID(item["id"])
        expected_score = scores_by_key[foreman_id]
        expected_bonus = bonuses[foreman_id].bonus if foreman_id in bonuses else 0
        expected_general = contribution_bonus.general_performance_score(expected_score.total_score, expected_bonus)

        assert item["operational_score"] == pytest.approx(round(expected_score.total_score, 2), abs=0.005)
        assert item["contribution_bonus"] == expected_bonus
        assert item["general_performance_score"] == pytest.approx(round(expected_general, 2), abs=0.005)
        assert item["is_reliable"] == expected_score.is_reliable

    def test_items_sorted_by_general_score_descending(self, client, auth_headers, db_session):
        filters = Filters(
            date_from=date.fromisoformat(PERIOD["date_from"]),
            date_to=date.fromisoformat(PERIOD["date_to"]),
        )
        team = next(t for t in analytics.chief_team_scores(db_session, filters) if len(t.foreman_scores) >= 2)
        chief_id = team.chief_id
        resp = client.get(f"/api/v1/chiefs/{chief_id}/foremen", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        scores = [i["general_performance_score"] for i in legacy_json(resp)["items"]]
        assert len(scores) >= 2
        assert scores == sorted(scores, reverse=True)

    def test_unknown_chief_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/foremen", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp) == {"detail": "Şef bulunamadı."}

    def test_empty_window_returns_empty_items(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=EMPTY_WINDOW, headers=auth_headers)
        assert resp.status_code == 200
        assert legacy_json(resp) == {"items": []}

    def test_query_chief_ids_cannot_escape_path_chief(self, client, auth_headers, db_session):
        chiefs = list(db_session.scalars(select(Chief).order_by(Chief.employee_number)))
        path_chief, other_chief = chiefs[0], chiefs[1]
        scoped = legacy_json(client.get(f"/api/v1/chiefs/{path_chief.id}/foremen", params=PERIOD, headers=auth_headers))
        overridden = legacy_json(client.get(
            f"/api/v1/chiefs/{path_chief.id}/foremen",
            params={**PERIOD, "chief_ids": str(other_chief.id)},
            headers=auth_headers,
        ))
        assert {i["id"] for i in overridden["items"]} == {i["id"] for i in scoped["items"]}

    def test_returned_foremen_belong_to_path_chief(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=PERIOD, headers=auth_headers)
        returned_ids = {i["id"] for i in legacy_json(resp)["items"]}
        assert returned_ids

        assignments = list(db_session.scalars(select(ForemanAssignment).where(ForemanAssignment.chief_id == chief.id)))
        chief_foreman_ids = {str(a.foreman_id) for a in assignments}
        assert returned_ids <= chief_foreman_ids


class TestChiefForemanComparison:
    def test_unknown_chief_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/foreman-comparison", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp) == {"detail": "Şef bulunamadı."}

    def test_empty_window_returns_empty_foremen(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/foreman-comparison", params=EMPTY_WINDOW, headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["foremen"] == []
        assert body["kpis"] == []

    def test_shape_and_default_sort_is_total_score_descending(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/foreman-comparison", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)

        assert body["kpis"], "Aktif KPI'lar boş dönmemeli"
        assert set(body["group_average"].keys()) == {"total_score", "kpi_scores"}
        kpi_ids = {k["kpi_id"] for k in body["kpis"]}
        assert set(body["group_average"]["kpi_scores"].keys()) == kpi_ids

        assert len(body["foremen"]) >= 2
        scores = [f["total_score"] for f in body["foremen"]]
        assert scores == sorted(scores, reverse=True)

        for foreman in body["foremen"]:
            assert set(foreman["kpi_scores"].keys()) == kpi_ids
            for value in foreman["kpi_scores"].values():
                if value is not None:
                    assert set(value.keys()) == {"score", "actual", "target", "record_count"}

    def test_total_score_matches_chief_foremen_endpoint(self, client, auth_headers, db_session):
        """Genel Puan kolonu, mevcut /chiefs/{id}/foremen uç noktasındaki
        general_performance_score ile aynı pipeline'ı (contribution bonus dahil)
        paylaşmalı — iki uç nokta aynı formen için farklı 'genel puan' göstermemeli."""
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        comparison = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/foreman-comparison", params=PERIOD, headers=auth_headers))
        team = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=PERIOD, headers=auth_headers))

        team_by_id = {i["id"]: i for i in team["items"]}
        assert comparison["foremen"]
        for f in comparison["foremen"]:
            assert f["id"] in team_by_id
            assert f["total_score"] == pytest.approx(team_by_id[f["id"]]["general_performance_score"], abs=0.01)
            assert f["is_reliable"] == team_by_id[f["id"]]["is_reliable"]

    def test_group_average_total_score_matches_chief_detail(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        comparison = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/foreman-comparison", params=PERIOD, headers=auth_headers))
        detail = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}", params=PERIOD, headers=auth_headers))
        assert comparison["group_average"]["total_score"] == pytest.approx(detail["total_score"], abs=0.01)

    def test_group_average_kpi_scores_match_kpis_endpoint(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        comparison = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/foreman-comparison", params=PERIOD, headers=auth_headers))
        kpis = legacy_json(client.get(f"/api/v1/chiefs/{chief.id}/kpis", params=PERIOD, headers=auth_headers))

        kpis_by_id = {k["kpi_id"]: k for k in kpis["items"]}
        assert kpis_by_id
        for kpi_id, avg_score in comparison["group_average"]["kpi_scores"].items():
            assert avg_score == pytest.approx(kpis_by_id[kpi_id]["avg_capped_score"], abs=0.01)

    def test_kpi_ids_filter_narrows_kpi_columns_but_keeps_total_score(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        kpi = db_session.scalars(select(Kpi).where(Kpi.code == "AGIR_GITME")).first()
        resp = client.get(
            f"/api/v1/chiefs/{chief.id}/foreman-comparison",
            params={**PERIOD, "kpi_ids": str(kpi.id)},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert [k["kpi_id"] for k in body["kpis"]] == [str(kpi.id)]
        for foreman in body["foremen"]:
            assert set(foreman["kpi_scores"].keys()) == {str(kpi.id)}
            assert "total_score" in foreman

    def test_sort_by_total_score_is_score_not_alphabetical(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        resp = client.get(f"/api/v1/chiefs/{chief.id}/foreman-comparison", params=PERIOD, headers=auth_headers)
        body = legacy_json(resp)
        by_score = sorted(body["foremen"], key=lambda f: f["total_score"], reverse=True)
        assert [f["id"] for f in body["foremen"]] == [f["id"] for f in by_score]


class TestChiefsHeavyTripleQueryBaseline:
    """list/detail/foremen query-count invariant'larını kilitler. Kırılgan sabit sayı
    yerine doğrudan ölçüm kullanılır; ilgisiz seed değişiklikleri testi geçersiz kılmamalı."""

    def test_list_query_count_is_flat_across_page_sizes(self, client, auth_headers):
        counts = {}
        for page_size in (25, 100, 200):
            with _count_queries() as counter:
                resp = client.get("/api/v1/chiefs", params={**PERIOD, "limit": page_size}, headers=auth_headers)
            assert resp.status_code == 200
            counts[page_size] = counter["n"]
        assert counts[25] == counts[100] == counts[200], f"Sorgu sayısı page_size ile değişiyor: {counts}"

    def test_detail_query_count_normal_unknown_filtered_out(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()
        chief_plant = db_session.scalars(select(Plant).where(Plant.chief_id == chief.id)).first()
        other_plant = db_session.scalars(select(Plant).where(Plant.factory_id != chief_plant.factory_id)).first()

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{chief.id}", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        normal_n = counter["n"]

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        unknown_n = counter["n"]

        with _count_queries() as counter:
            resp = client.get(
                f"/api/v1/chiefs/{chief.id}",
                params={**PERIOD, "factory_ids": str(other_plant.factory_id)},
                headers=auth_headers,
            )
        assert resp.status_code == 200
        filtered_n = counter["n"]

        # +2: get_auth_context (RBAC) sabit ek yuku, bkz. yukaridaki not.
        assert unknown_n == 3, f"404 yolu (authz sonrasi) kisa devre yapmali: {unknown_n}"
        assert normal_n == filtered_n, f"Filtrelenmiş ve normal sorgu şekli aynı olmalı: {normal_n} vs {filtered_n}"

    def test_foremen_query_count_normal_unknown_empty(self, client, auth_headers, db_session):
        chief = db_session.scalars(select(Chief).order_by(Chief.employee_number)).first()

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 200
        normal_n = counter["n"]

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{uuid.uuid4()}/foremen", params=PERIOD, headers=auth_headers)
        assert resp.status_code == 404
        unknown_n = counter["n"]

        with _count_queries() as counter:
            resp = client.get(f"/api/v1/chiefs/{chief.id}/foremen", params=EMPTY_WINDOW, headers=auth_headers)
        assert resp.status_code == 200
        empty_n = counter["n"]

        # +2: get_auth_context (RBAC) sabit ek yuku, bkz. yukaridaki not.
        assert unknown_n == 3, f"404 yolu (authz sonrasi) kisa devre yapmali: {unknown_n}"
        assert normal_n >= empty_n >= unknown_n


class TestChiefPlantConsistency:
    def test_chief_plants_all_belong_to_the_same_factory(self, client, auth_headers, db_session):
        plants_by_id = {str(p.id): p for p in db_session.scalars(select(Plant))}
        body = legacy_json(client.get("/api/v1/chiefs", params={**PERIOD, "limit": 200}, headers=auth_headers))
        for item in body["items"]:
            assert item["plants"]
            plant_factory_ids = {str(plants_by_id[p["id"]].factory_id) for p in item["plants"]}
            assert plant_factory_ids == {item["factory"]["id"]}

    def test_every_foreman_belongs_to_exactly_one_chief(self, db_session):
        assignments = list(db_session.scalars(select(ForemanAssignment)))
        chiefs_by_foreman: dict = {}
        for a in assignments:
            chiefs_by_foreman.setdefault(a.foreman_id, set()).add(a.chief_id)
        assert chiefs_by_foreman
        assert all(len(chief_ids) == 1 for chief_ids in chiefs_by_foreman.values())

    def test_every_chief_has_multiple_foremen(self, db_session):
        assignments = list(db_session.scalars(select(ForemanAssignment)))
        foremen_by_chief: dict = {}
        for a in assignments:
            foremen_by_chief.setdefault(a.chief_id, set()).add(a.foreman_id)
        assert foremen_by_chief
        assert all(len(foreman_ids) > 1 for foreman_ids in foremen_by_chief.values())


class TestChiefListDbSideCursorPagination:
    def test_list_query_is_limited_in_sql(self, client, auth_headers):
        with _capture_statements() as statements:
            resp = client.get("/api/v1/chiefs", params={**PERIOD, "limit": 3}, headers=auth_headers)
        assert resp.status_code == 200
        matching = [s for s in statements if "chiefs" in s and "LIMIT" in s.upper()]
        assert matching

    def test_pagination_continues_without_duplicates(self, client, auth_headers):
        first = client.get("/api/v1/chiefs", params={**PERIOD, "limit": 3}, headers=auth_headers)
        items1, pagination1 = unwrap_page(first)
        assert len(items1) == 3
        assert pagination1["hasMore"] is True
        cursor = pagination1["nextCursor"]
        assert cursor

        second = client.get(
            "/api/v1/chiefs", params={**PERIOD, "limit": 3, "cursor": cursor}, headers=auth_headers
        )
        assert second.status_code == 200
        items2, _ = unwrap_page(second)
        ids1 = {i["id"] for i in items1}
        ids2 = {i["id"] for i in items2}
        assert ids1.isdisjoint(ids2)

    def test_invalid_cursor_on_sort_mismatch(self, client, auth_headers):
        first = client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "limit": 2, "sort_by": "name", "sort_dir": "asc"},
            headers=auth_headers,
        )
        _, pagination = unwrap_page(first)
        cursor = pagination["nextCursor"]
        assert cursor

        mismatch = client.get(
            "/api/v1/chiefs",
            params={**PERIOD, "limit": 2, "sort_by": "employee_number", "sort_dir": "asc", "cursor": cursor},
            headers=auth_headers,
        )
        assert mismatch.status_code == 400
        assert unwrap_error(mismatch)["code"] == "INVALID_CURSOR"

    def test_malformed_cursor_returns_invalid_cursor(self, client, auth_headers):
        resp = client.get("/api/v1/chiefs", params={**PERIOD, "cursor": "not-a-real-cursor"}, headers=auth_headers)
        assert resp.status_code == 400
        assert unwrap_error(resp)["code"] == "INVALID_CURSOR"
