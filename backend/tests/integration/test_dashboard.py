from tests.helpers import legacy_json

class TestDashboardSummary:
    def test_summary_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    def test_summary_returns_expected_shape(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/summary",
            params={"date_from": "2026-06-27", "date_to": "2026-07-27"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["total_plants"] == 50
        assert body["active_plants"] == 50
        assert body["data_source"] == "SYNTHETIC"
        assert body["avg_company_score"] >= 0

    def test_summary_with_plant_filter_narrows_results(self, client, auth_headers):
        meta = legacy_json(client.get("/api/v1/meta/filters", headers=auth_headers))
        plant_id = meta["plants"][0]["id"]

        resp = client.get(
            "/api/v1/dashboard/summary",
            params={"date_from": "2026-06-27", "date_to": "2026-07-27", "plant_ids": plant_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_trend_endpoint_returns_points(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/trend",
            params={"date_from": "2026-01-01", "date_to": "2026-07-27", "granularity": "month"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        points = legacy_json(resp)["points"]
        assert len(points) > 0
        for p in points:
            assert "total_score" in p
            assert "is_reliable" in p

    def test_plant_ranking_sorted_desc_by_default(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/plant-ranking", headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        scores = [i["total_score"] for i in items]
        assert scores == sorted(scores, reverse=True)

    def test_performance_distribution_covers_all_levels(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/performance-distribution", headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        names = {item["name"] for item in body["items"]}
        assert names == {"Kritik", "Geliştirilmeli", "Başarılı"}
        assert "outstanding_count" in body


class TestDashboardSnapshot:
    def test_snapshot_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/snapshot")
        assert resp.status_code == 401

    def _individual_sections(self, client, auth_headers, params):
        summary = legacy_json(client.get("/api/v1/dashboard/summary", params=params, headers=auth_headers))
        kpi = legacy_json(client.get("/api/v1/dashboard/kpi-summary", params=params, headers=auth_headers))
        shift = legacy_json(client.get("/api/v1/dashboard/shift-comparison", params=params, headers=auth_headers))
        rank_top = legacy_json(client.get(
            "/api/v1/dashboard/foreman-ranking", params={**params, "order": "desc", "limit": 5}, headers=auth_headers
        ))
        rank_bottom = legacy_json(client.get(
            "/api/v1/dashboard/foreman-ranking", params={**params, "order": "asc", "limit": 5}, headers=auth_headers
        ))
        trend_up = legacy_json(client.get(
            "/api/v1/dashboard/foreman-trend-ranking", params={**params, "direction": "improving", "limit": 5}, headers=auth_headers
        ))
        trend_down = legacy_json(client.get(
            "/api/v1/dashboard/foreman-trend-ranking", params={**params, "direction": "declining", "limit": 5}, headers=auth_headers
        ))
        distribution = legacy_json(client.get("/api/v1/dashboard/performance-distribution", params=params, headers=auth_headers))
        return summary, kpi, shift, rank_top, rank_bottom, trend_up, trend_down, distribution

    def test_snapshot_matches_individual_endpoints(self, client, auth_headers):
        params = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
        resp = client.get("/api/v1/dashboard/snapshot", params=params, headers=auth_headers)
        assert resp.status_code == 200
        snap = legacy_json(resp)

        summary, kpi, shift, rank_top, rank_bottom, trend_up, trend_down, distribution = self._individual_sections(
            client, auth_headers, params
        )
        assert snap["summary"] == summary
        assert snap["kpi_summary"] == kpi
        assert snap["shift_comparison"] == shift
        assert snap["foreman_ranking"]["top"] == rank_top
        assert snap["foreman_ranking"]["bottom"] == rank_bottom
        assert snap["foreman_trend_ranking"]["improving"] == trend_up
        assert snap["foreman_trend_ranking"]["declining"] == trend_down
        assert snap["performance_distribution"] == distribution

    def test_snapshot_with_plant_filter_matches_individual_endpoints(self, client, auth_headers):
        meta = legacy_json(client.get("/api/v1/meta/filters", headers=auth_headers))
        plant_id = meta["plants"][0]["id"]
        params = {"date_from": "2026-06-27", "date_to": "2026-07-27", "plant_ids": plant_id}

        resp = client.get("/api/v1/dashboard/snapshot", params=params, headers=auth_headers)
        assert resp.status_code == 200
        snap = legacy_json(resp)

        summary, kpi, shift, rank_top, rank_bottom, trend_up, trend_down, distribution = self._individual_sections(
            client, auth_headers, params
        )
        assert snap["summary"] == summary
        assert snap["kpi_summary"] == kpi
        assert snap["shift_comparison"] == shift
        assert snap["foreman_ranking"]["top"] == rank_top
        assert snap["foreman_ranking"]["bottom"] == rank_bottom
        assert snap["foreman_trend_ranking"]["improving"] == trend_up
        assert snap["foreman_trend_ranking"]["declining"] == trend_down
        assert snap["performance_distribution"] == distribution

    def test_snapshot_issues_fewer_queries_than_sum_of_individual_endpoints(self, client, auth_headers):
        from sqlalchemy import event

        from app.db.session import engine

        params = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
        counts = {"n": 0}

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            counts["n"] += 1

        event.listen(engine, "before_cursor_execute", before_cursor_execute)
        try:
            counts["n"] = 0
            client.get("/api/v1/dashboard/snapshot", params=params, headers=auth_headers)
            snapshot_queries = counts["n"]

            counts["n"] = 0
            self._individual_sections(client, auth_headers, params)
            individual_queries = counts["n"]
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

        assert snapshot_queries < individual_queries * 0.6


class TestDashboardComparisonCharacterization:
    """kpi-summary, plant-ranking ve shift-comparison karakterizasyonu. Değer, sıralama,
    limit, filtre ve boş veri davranışını kilitler. Sonuçlar güncel seed'e bağlıdır,
    reseed sonrası geçerli olmaz.
    """

    _PARAMS = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
    _EMPTY_PARAMS = {"date_from": "2030-01-01", "date_to": "2030-01-02"}

    def test_kpi_summary_exact_values(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/kpi-summary", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert [item["code"] for item in items] == [
            "AGIR_GITME", "GSF", "ISKARTA", "INKITA", "PLANA_UYUM", "OEE",
        ]
        assert len({item["kpi_id"] for item in items}) == 6
        for item in items:
            assert item["unit"] == "%"
            assert isinstance(item["avg_score"], float)
            assert item["avg_target"] is not None
            assert item["avg_actual"] is not None
            assert item["record_count"] > 0

    def test_shift_comparison_exact_values(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/shift-comparison", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert [item["code"] for item in items] == ["V1", "V2"]
        assert len({item["shift_id"] for item in items}) == 2
        assert all(item["record_count"] > 0 for item in items)
        assert all(item["level"]["name"] in {"Kritik", "Geliştirilmeli", "Başarılı"} for item in items)

    def test_plant_ranking_default_desc_shape_and_boundaries(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/plant-ranking", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert len(items) == 50
        scores = [i["total_score"] for i in items]
        assert scores == sorted(scores, reverse=True), "Varsayılan sıralama total_score DESC olmalı."
        assert len({item["plant_id"] for item in items}) == 50
        assert all(item["code"].startswith("PLT") for item in items)
        assert items[0]["is_reliable"] is True
        assert items[-1]["is_reliable"] is True
        assert items[0]["total_score"] >= items[-1]["total_score"]

    def test_plant_ranking_asc_with_limit(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/plant-ranking", params={**self._PARAMS, "order": "asc", "limit": 3}, headers=auth_headers
        )
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert len(items) == 3
        assert [item["total_score"] for item in items] == sorted(item["total_score"] for item in items)
        assert len({item["plant_id"] for item in items}) == 3

    def test_plant_ranking_with_plant_filter(self, client, auth_headers):
        meta = legacy_json(client.get("/api/v1/meta/filters", headers=auth_headers))
        plant_id = meta["plants"][0]["id"]

        resp = client.get(
            "/api/v1/dashboard/plant-ranking", params={**self._PARAMS, "plant_ids": plant_id}, headers=auth_headers
        )
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert len(items) == 1
        assert items[0]["plant_id"] == plant_id
        assert items[0]["code"] == meta["plants"][0]["code"]

    def test_empty_window_returns_empty_items(self, client, auth_headers):
        for path in (
            "/api/v1/dashboard/kpi-summary",
            "/api/v1/dashboard/plant-ranking",
            "/api/v1/dashboard/shift-comparison",
        ):
            resp = client.get(path, params=self._EMPTY_PARAMS, headers=auth_headers)
            assert resp.status_code == 200, (path, resp.text)
            assert legacy_json(resp) == {"items": []}, path


class TestDashboardForemanCharacterization:
    """foreman-ranking, foreman-trend-ranking ve performance-distribution karakterizasyonu.
    Değer, sıralama, limit, filtre, boş veri ve eksik önceki dönem davranışını kilitler;
    değerler güncel seed'e bağlıdır.
    """

    _PARAMS = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
    _EMPTY_PARAMS = {"date_from": "2030-01-01", "date_to": "2030-01-02"}
    # Güncel pencere seed verisinin ilk tarihinde (2025-08-19) başlar; önceki dönem
    # penceresinin tamamı seed verisinden eskidir. Her formen güncel dönemde vardır,
    # önceki dönemde yoktur.
    _BOUNDARY_PARAMS = {"date_from": "2025-08-19", "date_to": "2025-09-18"}

    def test_foreman_ranking_default_desc_exact_values(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/foreman-ranking", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {
                    "foreman_id": "0ccffb07-ff5e-4762-a833-fa45de7cb140", "employee_number": "SCL-V2-006",
                    "full_name": "Volkan Aslan", "operational_score": 105.48, "contribution_bonus": 0,
                    "general_performance_score": 105.48, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": True,
                    },
                },
                {
                    "foreman_id": "3c73e7cc-f6c1-48c3-bc7e-2a727d689155", "employee_number": "SCL-V1-001",
                    "full_name": "Kemal Uçar", "operational_score": 102.37, "contribution_bonus": 0,
                    "general_performance_score": 102.37, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "475dacf9-4fa0-4831-a167-89ff8a3f09ea", "employee_number": "SCL-V1-004",
                    "full_name": "Kübra Özdemir", "operational_score": 102.19, "contribution_bonus": 0,
                    "general_performance_score": 102.19, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "28f3fc2e-2aeb-4306-b89e-a5eecac9ba16", "employee_number": "SCL-V2-001",
                    "full_name": "Ahmet Taş", "operational_score": 99.73, "contribution_bonus": 0,
                    "general_performance_score": 99.73, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "d8ece9d3-123b-410b-bb56-e8bdbcc966c1", "employee_number": "SCL-V1-011",
                    "full_name": "Esra Yıldırım", "operational_score": 89.94, "contribution_bonus": 9,
                    "general_performance_score": 98.94, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "49834b5c-3412-4f68-806d-7a292be897c3", "employee_number": "SCL-V2-008",
                    "full_name": "Yavuz Yalçın", "operational_score": 97.64, "contribution_bonus": 0,
                    "general_performance_score": 97.64, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "3a07b9ae-fec1-44f6-bcc1-a36d7f29bbd5", "employee_number": "SCL-V2-014",
                    "full_name": "Fatma Kurt", "operational_score": 93.19, "contribution_bonus": 3,
                    "general_performance_score": 96.19, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "257844b9-8d15-42d9-afc4-559c9fe9d5b9", "employee_number": "SCL-V2-007",
                    "full_name": "Halil Aslan", "operational_score": 90.18, "contribution_bonus": 0,
                    "general_performance_score": 90.18, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "2fef68f2-9f64-4d58-be66-efdbc5c5c53e", "employee_number": "SCL-V1-007",
                    "full_name": "Sevgi Kaplan", "operational_score": 89.6, "contribution_bonus": 0,
                    "general_performance_score": 89.6, "is_reliable": True,
                    "level": {
                        "name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.",
                        "color": "#EA580C", "icon": "trending-down", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "b0b03577-ee46-4a28-9631-ab7d020dae32", "employee_number": "SCL-V2-003",
                    "full_name": "Esra Ateş", "operational_score": 88.84, "contribution_bonus": 0,
                    "general_performance_score": 88.84, "is_reliable": True,
                    "level": {
                        "name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.",
                        "color": "#EA580C", "icon": "trending-down", "outstanding_performance": False,
                    },
                },
            ]
        }
        items = legacy_json(resp)["items"]
        assert len(items) == len(historical_snapshot["items"]) == 10
        assert [item["general_performance_score"] for item in items] == sorted(
            (item["general_performance_score"] for item in items), reverse=True
        )
        assert len({item["foreman_id"] for item in items}) == len(items)
        for item in items:
            assert item["general_performance_score"] == round(
                item["operational_score"] + item["contribution_bonus"], 2
            )
            assert item["level"]["outstanding_performance"] in {True, False}

    def test_foreman_ranking_asc_with_limit(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/foreman-ranking", params={**self._PARAMS, "order": "asc", "limit": 3}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {
                    "foreman_id": "620aa602-8e27-4dd1-8419-8b792f6f3099", "employee_number": "SCL-V1-010",
                    "full_name": "Pınar Ünal", "operational_score": 65.74, "contribution_bonus": 0,
                    "general_performance_score": 65.74, "is_reliable": True,
                    "level": {
                        "name": "Kritik", "description": "Acil aksiyon gerektiren kritik performans.",
                        "color": "#DC2626", "icon": "alert-triangle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "86bf977c-0311-4a4d-9fe8-0fd3bd75ef04", "employee_number": "SCL-V1-002",
                    "full_name": "Halil Genç", "operational_score": 66.57, "contribution_bonus": 0,
                    "general_performance_score": 66.57, "is_reliable": True,
                    "level": {
                        "name": "Kritik", "description": "Acil aksiyon gerektiren kritik performans.",
                        "color": "#DC2626", "icon": "alert-triangle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "0e547748-28cc-4554-923e-5b8db15bf445", "employee_number": "SCL-V2-013",
                    "full_name": "Emine Yılmaz", "operational_score": 67.03, "contribution_bonus": 0,
                    "general_performance_score": 67.03, "is_reliable": True,
                    "level": {
                        "name": "Kritik", "description": "Acil aksiyon gerektiren kritik performans.",
                        "color": "#DC2626", "icon": "alert-triangle", "outstanding_performance": False,
                    },
                },
            ]
        }
        items = legacy_json(resp)["items"]
        assert len(items) == len(historical_snapshot["items"]) == 3
        assert [item["general_performance_score"] for item in items] == sorted(
            item["general_performance_score"] for item in items
        )

    def test_foreman_ranking_with_plant_filter(self, client, auth_headers):
        meta = legacy_json(client.get("/api/v1/meta/filters", headers=auth_headers))
        plant_id = meta["plants"][0]["id"]

        resp = client.get(
            "/api/v1/dashboard/foreman-ranking",
            params={**self._PARAMS, "plant_ids": plant_id, "limit": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {
                    "foreman_id": "475dacf9-4fa0-4831-a167-89ff8a3f09ea", "employee_number": "SCL-V1-004",
                    "full_name": "Kübra Özdemir", "operational_score": 100.5, "contribution_bonus": 0,
                    "general_performance_score": 100.5, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "9b8afba8-f68e-461c-aac0-a2487f61aa04", "employee_number": "SCL-V2-004",
                    "full_name": "Yavuz Akın", "operational_score": 89.03, "contribution_bonus": 0,
                    "general_performance_score": 89.03, "is_reliable": True,
                    "level": {
                        "name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.",
                        "color": "#EA580C", "icon": "trending-down", "outstanding_performance": False,
                    },
                },
            ]
        }
        items = legacy_json(resp)["items"]
        assert len(items) == len(historical_snapshot["items"]) == 2
        assert [item["general_performance_score"] for item in items] == sorted(
            (item["general_performance_score"] for item in items), reverse=True
        )
        assert all(item["employee_number"].startswith("SCL-") for item in items)

    def test_foreman_trend_ranking_improving(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/foreman-trend-ranking", params={**self._PARAMS, "limit": 3}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {
                    "foreman_id": "257844b9-8d15-42d9-afc4-559c9fe9d5b9", "employee_number": "SCL-V2-007",
                    "full_name": "Halil Aslan", "operational_score": 90.18, "previous_operational_score": 89.33,
                    "delta": 0.85, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "49834b5c-3412-4f68-806d-7a292be897c3", "employee_number": "SCL-V2-008",
                    "full_name": "Yavuz Yalçın", "operational_score": 97.64, "previous_operational_score": 96.91,
                    "delta": 0.73, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "2fef68f2-9f64-4d58-be66-efdbc5c5c53e", "employee_number": "SCL-V1-007",
                    "full_name": "Sevgi Kaplan", "operational_score": 89.6, "previous_operational_score": 89.23,
                    "delta": 0.37, "is_reliable": True,
                    "level": {
                        "name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.",
                        "color": "#EA580C", "icon": "trending-down", "outstanding_performance": False,
                    },
                },
            ]
        }
        items = legacy_json(resp)["items"]
        assert len(items) == len(historical_snapshot["items"]) == 3
        assert [item["delta"] for item in items] == sorted(
            (item["delta"] for item in items), reverse=True
        )
        assert all(item["delta"] > 0 for item in items)

    def test_foreman_trend_ranking_declining(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/foreman-trend-ranking",
            params={**self._PARAMS, "direction": "declining", "limit": 3},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {
                    "foreman_id": "dfa1cb41-bf63-4c47-bf97-3950efcede92", "employee_number": "SCL-V1-015",
                    "full_name": "Sinan Uysal", "operational_score": 84.55, "previous_operational_score": 85.1,
                    "delta": -0.55, "is_reliable": True,
                    "level": {
                        "name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.",
                        "color": "#EA580C", "icon": "trending-down", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "3a07b9ae-fec1-44f6-bcc1-a36d7f29bbd5", "employee_number": "SCL-V2-014",
                    "full_name": "Fatma Kurt", "operational_score": 93.19, "previous_operational_score": 93.63,
                    "delta": -0.45, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
                {
                    "foreman_id": "28f3fc2e-2aeb-4306-b89e-a5eecac9ba16", "employee_number": "SCL-V2-001",
                    "full_name": "Ahmet Taş", "operational_score": 99.73, "previous_operational_score": 100.17,
                    "delta": -0.44, "is_reliable": True,
                    "level": {
                        "name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.",
                        "color": "#16A34A", "icon": "check-circle", "outstanding_performance": False,
                    },
                },
            ]
        }
        items = legacy_json(resp)["items"]
        assert len(items) == len(historical_snapshot["items"]) == 3
        assert [item["delta"] for item in items] == sorted(item["delta"] for item in items)
        assert all(item["delta"] < 0 for item in items)

    def test_foreman_trend_ranking_missing_previous_period_excludes_all(self, client, auth_headers):
        """Güncel pencere seed verisinin ilk tarihinde başlar; önceki dönem tüm veriden
        eskidir. Sentetik previous=0/None fallback yerine inner-join/exclusion nedeniyle
        boş sonuç döner."""
        resp = client.get(
            "/api/v1/dashboard/foreman-trend-ranking", params=self._BOUNDARY_PARAMS, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert legacy_json(resp) == {"items": []}

    def test_performance_distribution_exact_counts(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/performance-distribution", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {"name": "Kritik", "description": "Acil aksiyon gerektiren kritik performans.", "color": "#DC2626", "icon": "alert-triangle", "count": 4},
                {"name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.", "color": "#EA580C", "icon": "trending-down", "count": 16},
                {"name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.", "color": "#16A34A", "icon": "check-circle", "count": 8},
            ],
            "outstanding_count": 1,
        }
        body = legacy_json(resp)
        assert [item["name"] for item in body["items"]] == [
            item["name"] for item in historical_snapshot["items"]
        ]
        ranking = legacy_json(client.get(
            "/api/v1/dashboard/foreman-ranking",
            params={**self._PARAMS, "limit": 100},
            headers=auth_headers,
        ))["items"]
        assert sum(item["count"] for item in body["items"]) == len(ranking)
        assert body["outstanding_count"] == sum(
            1 for item in ranking if item["level"]["outstanding_performance"]
        )

    def test_empty_window_behavior(self, client, auth_headers):
        for path in ("/api/v1/dashboard/foreman-ranking", "/api/v1/dashboard/foreman-trend-ranking"):
            resp = client.get(path, params=self._EMPTY_PARAMS, headers=auth_headers)
            assert resp.status_code == 200, (path, resp.text)
            assert legacy_json(resp) == {"items": []}, path

        # Distribution, boş bucket'ları atlamak yerine yapılandırılmış her seviye
        # bucket'ını sıfır sayısıyla korur.
        resp = client.get(
            "/api/v1/dashboard/performance-distribution", params=self._EMPTY_PARAMS, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        historical_snapshot = {
            "items": [
                {"name": "Kritik", "description": "Acil aksiyon gerektiren kritik performans.", "color": "#DC2626", "icon": "alert-triangle", "count": 0},
                {"name": "Geliştirilmeli", "description": "Hedefin altında, iyileştirme gerekiyor.", "color": "#EA580C", "icon": "trending-down", "count": 0},
                {"name": "Başarılı", "description": "Hedef seviyesinde veya üzerinde başarılı performans.", "color": "#16A34A", "icon": "check-circle", "count": 0},
            ],
            "outstanding_count": 0,
        }
        body = legacy_json(resp)
        assert [item["name"] for item in body["items"]] == [
            item["name"] for item in historical_snapshot["items"]
        ]
        assert all(item["count"] == 0 for item in body["items"])
        assert body["outstanding_count"] == 0


class TestPerformanceLeaders:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/performance-leaders")
        assert resp.status_code == 401

    def test_monthly_leader_matches_foreman_ranking_for_last_calculated_month(self, client, auth_headers):
        import calendar
        from datetime import date

        from app.services.monthly_foreman_report import latest_completed_period
        from app.services.shift_analysis import month_label

        resp = client.get("/api/v1/dashboard/performance-leaders", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)

        year, month = latest_completed_period()
        last_day = calendar.monthrange(year, month)[1]
        assert body["year"] == year
        assert body["last_calculated_month"] == {
            "year": year, "month": month, "label": month_label(date(year, month, last_day)),
        }

        month_ranking = legacy_json(client.get(
            "/api/v1/dashboard/foreman-ranking",
            params={
                "date_from": f"{year:04d}-{month:02d}-01", "date_to": f"{year:04d}-{month:02d}-{last_day:02d}",
                "order": "desc", "limit": 1,
            },
            headers=auth_headers,
        ))["items"]

        if not month_ranking or not month_ranking[0]["is_reliable"]:
            assert body["monthly_leader"] is None
        else:
            assert body["monthly_leader"] == {
                "foreman_id": month_ranking[0]["foreman_id"],
                "full_name": month_ranking[0]["full_name"],
                "general_performance_score": month_ranking[0]["general_performance_score"],
            }

    def test_yearly_leader_matches_ytd_ranking_and_wins_are_bounded(self, client, auth_headers):
        import calendar

        from app.services.monthly_foreman_report import latest_completed_period

        resp = client.get("/api/v1/dashboard/performance-leaders", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)

        year, month = latest_completed_period()
        last_day = calendar.monthrange(year, month)[1]
        ytd_ranking = legacy_json(client.get(
            "/api/v1/dashboard/foreman-ranking",
            params={
                "date_from": f"{year:04d}-01-01", "date_to": f"{year:04d}-{month:02d}-{last_day:02d}",
                "order": "desc", "limit": 1,
            },
            headers=auth_headers,
        ))["items"]

        if not ytd_ranking or not ytd_ranking[0]["is_reliable"]:
            assert body["yearly_leader"] is None
        else:
            leader = body["yearly_leader"]
            assert leader["foreman_id"] == ytd_ranking[0]["foreman_id"]
            assert leader["full_name"] == ytd_ranking[0]["full_name"]
            assert leader["general_performance_score"] == ytd_ranking[0]["general_performance_score"]
            assert 1 <= leader["monthly_wins"] <= month

    def test_empty_leaders_when_period_predates_all_data(self, client, auth_headers, monkeypatch):
        from app.services import performance_leaders_service

        monkeypatch.setattr(performance_leaders_service, "latest_completed_period", lambda: (2000, 1))
        resp = client.get("/api/v1/dashboard/performance-leaders", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert legacy_json(resp) == {
            "year": 2000,
            "last_calculated_month": {"year": 2000, "month": 1, "label": "Ocak 2000"},
            "monthly_leader": None,
            "yearly_leader": None,
        }


def _expected_last_sync_at(db_session) -> str | None:
    from sqlalchemy import select

    from app.models.integration import IntegrationRun

    finished_at_values = list(db_session.scalars(select(IntegrationRun.finished_at)).all())
    if not finished_at_values or any(v is None for v in finished_at_values):
        return None
    return max(finished_at_values).isoformat()


class TestDashboardOverviewCharacterization:
    """summary ve snapshot karakterizasyonu. Değer, boş veri, filtre ve limit wiring
    davranışını kilitler; sonuçlar güncel seed'e bağlıdır.

    İki mevcut davranış bilerek korunur:
      - `plants_with_missing_data` yalnızca tarih filtresini uygular. Seed içinde MISSING/
        NEEDS_SOURCE_CORRECTION olmadığından değer filtreli/filtersiz her zaman 0'dır.
      - `last_sync_at` status filtrelemez; PostgreSQL DESC sıralamada NULL'ı öne alır.
        Seed'de tek tamamlanmış IntegrationRun olduğundan bu edge case yazma olmadan test edilemez.
    """

    _PARAMS = {"date_from": "2026-06-27", "date_to": "2026-07-27"}
    _EMPTY_PARAMS = {"date_from": "2030-01-01", "date_to": "2030-01-02"}

    def test_summary_exact_values(self, client, auth_headers, db_session):
        resp = client.get("/api/v1/dashboard/summary", params=self._PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        last_sync_at = body.pop("last_sync_at")
        assert last_sync_at == _expected_last_sync_at(db_session)
        historical_snapshot = {
            "total_plants": 50,
            "active_plants": 50,
            "total_active_foremen": 28,
            "avg_company_score": 84.59,
            "foremen_above_target": 3,
            "foremen_below_target": 25,
            "foremen_critical": 4,
            "foremen_successful": 8,
            "foremen_outstanding": 1,
            "best_plant": {"id": "550a404b-2f83-4679-bdfb-781fb647a362", "name": "5. Tesis", "code": "PLT05", "score": 103.34},
            "worst_plant": {"id": "bc1f3d12-267c-4b46-92ec-218dc0c4b60f", "name": "40. Tesis", "code": "PLT40", "score": 65.45},
            "best_shift": {"id": "a8c93025-3bba-4274-adf8-d76583787749", "name": "1. Vardiya", "score": 84.67},
            "worst_shift": {"id": "6b34d50b-a53f-459a-8374-2c2587a76a00", "name": "2. Vardiya", "score": 84.29},
            "best_foreman": {
                "id": "0ccffb07-ff5e-4762-a833-fa45de7cb140", "name": "Volkan Aslan",
                "employee_number": "SCL-V2-006", "score": 105.48,
            },
            "weakest_kpi": {"id": "25c46360-bf65-458a-be0b-a1d1196c48a7", "name": "Ağır Gitme Oranı", "avg_score": 66.27},
            "plants_with_missing_data": 0,
            "data_source": "SYNTHETIC",
        }
        assert body["total_plants"] == body["active_plants"] == historical_snapshot["total_plants"] == 50
        assert body["foremen_above_target"] + body["foremen_below_target"] == body["total_active_foremen"]
        plant_ranking = legacy_json(client.get(
            "/api/v1/dashboard/plant-ranking", params=self._PARAMS, headers=auth_headers
        ))["items"]
        assert body["best_plant"]["id"] == plant_ranking[0]["plant_id"]
        assert body["worst_plant"]["id"] == plant_ranking[-1]["plant_id"]
        assert body["best_plant"]["score"] == plant_ranking[0]["total_score"]
        assert body["worst_plant"]["score"] == plant_ranking[-1]["total_score"]
        shifts = legacy_json(client.get(
            "/api/v1/dashboard/shift-comparison", params=self._PARAMS, headers=auth_headers
        ))["items"]
        assert body["best_shift"]["score"] == max(item["total_score"] for item in shifts)
        assert body["worst_shift"]["score"] == min(item["total_score"] for item in shifts)
        foremen = legacy_json(client.get(
            "/api/v1/dashboard/foreman-ranking", params={**self._PARAMS, "limit": 1}, headers=auth_headers
        ))["items"]
        assert body["best_foreman"]["id"] == foremen[0]["foreman_id"]
        kpis = legacy_json(client.get(
            "/api/v1/dashboard/kpi-summary", params=self._PARAMS, headers=auth_headers
        ))["items"]
        assert body["weakest_kpi"]["avg_score"] == min(item["avg_score"] for item in kpis)

    def test_summary_with_plant_filter_exact_values(self, client, auth_headers, db_session):
        meta = legacy_json(client.get("/api/v1/meta/filters", headers=auth_headers))
        plant_id = meta["plants"][0]["id"]

        resp = client.get(
            "/api/v1/dashboard/summary", params={**self._PARAMS, "plant_ids": plant_id}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        last_sync_at = body.pop("last_sync_at")
        assert last_sync_at == _expected_last_sync_at(db_session)
        historical_snapshot = {
            "total_plants": 50,
            "active_plants": 50,
            "total_active_foremen": 2,
            "avg_company_score": 94.76,
            "foremen_above_target": 1,
            "foremen_below_target": 1,
            "foremen_critical": 0,
            "foremen_successful": 1,
            "foremen_outstanding": 0,
            "best_plant": {"id": "3f9d39b3-4be1-4e96-aa99-dcd37146055f", "name": "1. Tesis", "code": "PLT01", "score": 95.17},
            "worst_plant": {"id": "3f9d39b3-4be1-4e96-aa99-dcd37146055f", "name": "1. Tesis", "code": "PLT01", "score": 95.17},
            "best_shift": {"id": "a8c93025-3bba-4274-adf8-d76583787749", "name": "1. Vardiya", "score": 95.28},
            "worst_shift": {"id": "6b34d50b-a53f-459a-8374-2c2587a76a00", "name": "2. Vardiya", "score": 95.17},
            "best_foreman": {
                "id": "475dacf9-4fa0-4831-a167-89ff8a3f09ea", "name": "Kübra Özdemir",
                "employee_number": "SCL-V1-004", "score": 100.5,
            },
            "weakest_kpi": {"id": "618ee175-916d-4d94-88d2-91d523541196", "name": "Plana Uyum Oranı", "avg_score": 89.52},
            "plants_with_missing_data": 0,
            "data_source": "SYNTHETIC",
        }
        assert body["total_plants"] == historical_snapshot["total_plants"] == 50
        assert body["active_plants"] == historical_snapshot["active_plants"] == 50
        assert body["best_plant"]["id"] == plant_id
        assert body["worst_plant"]["id"] == plant_id
        assert body["best_plant"] == body["worst_plant"]
        assert body["foremen_above_target"] + body["foremen_below_target"] == body["total_active_foremen"]
        filtered_ranking = legacy_json(client.get(
            "/api/v1/dashboard/plant-ranking",
            params={**self._PARAMS, "plant_ids": plant_id},
            headers=auth_headers,
        ))["items"]
        assert len(filtered_ranking) == 1
        assert body["best_plant"]["score"] == filtered_ranking[0]["total_score"]
        # total_plants/active_plants ve plants_with_missing_data/last_sync_at fabrika
        # filtresinden bilerek etkilenmez; org-scoped değil şirket geneli sorgulardır.
        unfiltered = legacy_json(client.get("/api/v1/dashboard/summary", params=self._PARAMS, headers=auth_headers))
        assert body["total_plants"] == unfiltered["total_plants"] == 50
        assert body["active_plants"] == unfiltered["active_plants"] == 50
        assert body["plants_with_missing_data"] == unfiltered["plants_with_missing_data"] == 0
        assert last_sync_at == unfiltered["last_sync_at"]

    def test_summary_empty_window(self, client, auth_headers, db_session):
        resp = client.get("/api/v1/dashboard/summary", params=self._EMPTY_PARAMS, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        last_sync_at = body.pop("last_sync_at")
        assert last_sync_at == _expected_last_sync_at(db_session)
        assert body == {
            "total_plants": 50,
            "active_plants": 50,
            "total_active_foremen": 0,
            "avg_company_score": 0.0,
            "foremen_above_target": 0,
            "foremen_below_target": 0,
            "foremen_critical": 0,
            "foremen_successful": 0,
            "foremen_outstanding": 0,
            "best_plant": None,
            "worst_plant": None,
            "best_shift": None,
            "worst_shift": None,
            "best_foreman": None,
            "weakest_kpi": None,
            "plants_with_missing_data": 0,
            "data_source": "SYNTHETIC",
        }

    def test_summary_response_matches_snapshot_summary_section(self, client, auth_headers):
        """summary ile snapshot["summary"] byte-identical kalmalıdır; iki çağrı da aynı
        _summary_payload contract'ını kullanır.
        """
        standalone = legacy_json(client.get("/api/v1/dashboard/summary", params=self._PARAMS, headers=auth_headers))
        snap = legacy_json(client.get("/api/v1/dashboard/snapshot", params=self._PARAMS, headers=auth_headers))
        assert snap["summary"] == standalone

    def test_snapshot_structural_shape_and_limits(self, client, auth_headers):
        resp = client.get(
            "/api/v1/dashboard/snapshot",
            params={**self._PARAMS, "foreman_ranking_limit": 3, "foreman_trend_limit": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        assert sorted(body.keys()) == [
            "foreman_ranking", "foreman_trend_ranking", "kpi_summary",
            "performance_distribution", "shift_comparison", "summary",
        ]
        assert set(body["foreman_ranking"].keys()) == {"top", "bottom"}
        assert set(body["foreman_trend_ranking"].keys()) == {"improving", "declining"}
        assert len(body["foreman_ranking"]["top"]["items"]) == 3
        assert len(body["foreman_ranking"]["bottom"]["items"]) == 3
        assert len(body["foreman_trend_ranking"]["improving"]["items"]) == 2
        assert len(body["foreman_trend_ranking"]["declining"]["items"]) == 2
