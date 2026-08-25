import uuid

import pytest
from sqlalchemy import select

from app.core.turkish import turkish_sort_key
from app.models.contribution import ContributionWork, ContributionWorkForeman
from app.models.enums import ContributionStatus
from app.models.foreman import Foreman
from app.models.organization import Plant
from tests.helpers import unwrap, unwrap_error, unwrap_page

from .conftest import TEST_SUBJECT


@pytest.fixture(autouse=True)
def _cleanup_contribution_works(db_session):
    yield
    db_session.query(ContributionWork).filter(
        ContributionWork.created_by_subject == TEST_SUBJECT
    ).delete(synchronize_session=False)
    db_session.commit()


def _sample_plant_and_foreman(db_session):
    plant = db_session.scalars(select(Plant).order_by(Plant.sequence_number)).first()
    has_published_work = select(ContributionWorkForeman.foreman_id).join(
        ContributionWork, ContributionWork.id == ContributionWorkForeman.work_id
    ).where(ContributionWork.status == ContributionStatus.PUBLISHED)
    foreman = db_session.scalars(
        select(Foreman).where(Foreman.is_active.is_(True), Foreman.id.notin_(has_published_work))
    ).first()
    return plant, foreman


def _full_payload(plant, foreman, status="published"):
    return {
        "title": "Kalıp Değişim Süresinin Kısaltılması",
        "status": status,
        "work_type": "smed",
        "summary": "Kalıp değişim adımları standartlaştırıldı.",
        "problem_description": "Kalıp değişimi uzun sürüyordu.",
        "solution_description": "Adımlar paralel hale getirildi.",
        "result_description": "Süre kısaldı.",
        "foreman_ids": [str(foreman.id)],
        "plant_ids": [str(plant.id)],
        "work_date": "2026-01-15",
        "impact_level": "high",
        "previous_duration": 45,
        "new_duration": 28,
        "duration_unit": "minute",
        "repeat_period": "monthly",
        "repeat_count": 30,
        "financial_gain_status": "yes",
        "gain_amount": 250000,
        "currency": "TRY",
        "gain_period": "yearly",
    }


class TestContributionWorkList:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/contribution-works").status_code == 401

    def test_list_returns_items(self, client, auth_headers):
        resp = client.get("/api/v1/contribution-works", params={"limit": 5}, headers=auth_headers)
        assert resp.status_code == 200
        data, pagination = unwrap_page(resp)
        assert isinstance(data, list)
        assert set(pagination.keys()) == {"nextCursor", "hasMore", "total"}
        assert pagination["total"] is None

    def test_sql_sortable_pages_do_not_overlap(self, client, auth_headers):
        created_ids = set()
        for i in range(8):
            resp = client.post(
                "/api/v1/contribution-works", json={"title": f"Sayfalama testi #{i}"}, headers=auth_headers
            )
            created_ids.add(unwrap(resp)["id"])

        first_items, first_pagination = unwrap_page(
            client.get(
                "/api/v1/contribution-works", params={"sort_by": "date", "limit": 4}, headers=auth_headers
            )
        )
        second_items, second_pagination = unwrap_page(
            client.get(
                "/api/v1/contribution-works",
                params={"sort_by": "date", "limit": 4, "cursor": first_pagination["nextCursor"]},
                headers=auth_headers,
            )
        )
        first_ids = {i["id"] for i in first_items}
        second_ids = {i["id"] for i in second_items}
        assert first_ids.isdisjoint(second_ids)

        all_items, _ = unwrap_page(
            client.get(
                "/api/v1/contribution-works",
                params={"search": "Sayfalama testi", "limit": 200}, headers=auth_headers,
            )
        )
        assert created_ids == {i["id"] for i in all_items}

    def test_title_sort_uses_turkish_collation_in_db(self, client, auth_headers):
        titles = ["Çelik İşleme", "Ağır Sanayi", "Öğütme", "Şeker", "Isı Kaybı", "Zincir"]
        for t in titles:
            client.post("/api/v1/contribution-works", json={"title": f"Trkoll {t}"}, headers=auth_headers)
        resp = client.get(
            "/api/v1/contribution-works",
            params={"search": "Trkoll", "sort_by": "title", "sort_dir": "asc", "limit": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = unwrap(resp)
        returned = [i["title"] for i in data]
        expected = [f"Trkoll {t}" for t in sorted(titles, key=turkish_sort_key)]
        assert returned == expected

    def test_gain_sort_orders_by_resolved_highlighted_gain_value(self, client, auth_headers):
        token = uuid.uuid4().hex[:8]
        payloads = [
            (f"Gain sort {token} A", 100),
            (f"Gain sort {token} B", 500),
            (f"Gain sort {token} C", 250),
        ]
        for title, amount in payloads:
            resp = client.post(
                "/api/v1/contribution-works",
                json={"title": title, "gain_amount": amount, "currency": "TRY"},
                headers=auth_headers,
            )
            assert resp.status_code == 201, resp.text

        resp = client.get(
            "/api/v1/contribution-works",
            params={"search": f"Gain sort {token}", "sort_by": "gain", "sort_dir": "desc", "limit": 2},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items, pagination = unwrap_page(resp)
        assert pagination["hasMore"] is True
        assert [i["title"] for i in items] == [f"Gain sort {token} B", f"Gain sort {token} C"]

        all_items, all_pagination = unwrap_page(
            client.get(
                "/api/v1/contribution-works",
                params={"search": f"Gain sort {token}", "sort_by": "gain", "sort_dir": "desc", "limit": 10},
                headers=auth_headers,
            )
        )
        assert len(all_items) == 3
        assert all_pagination["hasMore"] is False

    def test_foreman_sort_orders_by_min_turkish_collated_name(self, client, auth_headers, db_session):
        foremen = list(db_session.scalars(select(Foreman).where(Foreman.is_active.is_(True)).limit(2)))
        assert len(foremen) == 2
        names = sorted((f"{f.first_name} {f.last_name}" for f in foremen), key=turkish_sort_key)

        token = uuid.uuid4().hex[:8]
        for f in foremen:
            resp = client.post(
                "/api/v1/contribution-works",
                json={"title": f"Foreman sort {token} {f.employee_number}", "foreman_ids": [str(f.id)]},
                headers=auth_headers,
            )
            assert resp.status_code == 201, resp.text

        resp = client.get(
            "/api/v1/contribution-works",
            params={"search": f"Foreman sort {token}", "sort_by": "foreman", "sort_dir": "asc", "limit": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        returned_first_names = [i["foremen"][0]["name"] for i in unwrap(resp)]
        assert returned_first_names == names

    def test_plant_sort_orders_by_min_sequence_number(self, client, auth_headers, db_session):
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(3)))
        assert len(plants) == 3

        token = uuid.uuid4().hex[:8]
        for p in plants:
            resp = client.post(
                "/api/v1/contribution-works",
                json={"title": f"Plant sort {token} {p.code}", "plant_ids": [str(p.id)]},
                headers=auth_headers,
            )
            assert resp.status_code == 201, resp.text

        resp = client.get(
            "/api/v1/contribution-works",
            params={"search": f"Plant sort {token}", "sort_by": "plant", "sort_dir": "desc", "limit": 10},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        returned_seqs = [db_session.get(Plant, i["plants"][0]["id"]).sequence_number for i in unwrap(resp)]
        assert returned_seqs == sorted((p.sequence_number for p in plants), reverse=True)

    def test_pagination_has_no_duplicates_or_gaps(self, client, auth_headers):
        token = uuid.uuid4().hex[:8]
        created_ids = set()
        for i in range(60):
            resp = client.post(
                "/api/v1/contribution-works", json={"title": f"Pagination testi {token} #{i}"}, headers=auth_headers
            )
            created_ids.add(unwrap(resp)["id"])

        seen_ids: list[str] = []
        cursor = None
        for _ in range(10):
            params = {"search": f"Pagination testi {token}", "sort_by": "date", "limit": 25}
            if cursor:
                params["cursor"] = cursor
            resp = client.get("/api/v1/contribution-works", params=params, headers=auth_headers)
            assert resp.status_code == 200
            items, pagination = unwrap_page(resp)
            seen_ids.extend(i["id"] for i in items)
            if not pagination["hasMore"]:
                break
            cursor = pagination["nextCursor"]

        assert len(seen_ids) == len(set(seen_ids)), "Sayfalar arasında tekrar eden kayıt var"
        assert set(seen_ids) == created_ids
        assert len(seen_ids) == 60

    def test_plant_filter_combined_with_gain_sort_and_pagination(self, client, auth_headers, db_session):
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(2)))
        plant_a, plant_b = plants[0], plants[1]
        token = uuid.uuid4().hex[:8]

        for title, amount, plant in (
            (f"Filtre sort {token} P1-100", 100, plant_a),
            (f"Filtre sort {token} P1-300", 300, plant_a),
            (f"Filtre sort {token} P2-1000", 1000, plant_b),
        ):
            resp = client.post(
                "/api/v1/contribution-works",
                json={
                    "title": title, "gain_amount": amount, "currency": "TRY", "plant_ids": [str(plant.id)],
                },
                headers=auth_headers,
            )
            assert resp.status_code == 201, resp.text

        first_items, first_pagination = unwrap_page(
            client.get(
                "/api/v1/contribution-works",
                params={
                    "search": f"Filtre sort {token}", "plant_ids": str(plant_a.id),
                    "sort_by": "gain", "sort_dir": "desc", "limit": 1,
                },
                headers=auth_headers,
            )
        )
        assert [i["title"] for i in first_items] == [f"Filtre sort {token} P1-300"]
        assert first_pagination["hasMore"] is True

        second_items, second_pagination = unwrap_page(
            client.get(
                "/api/v1/contribution-works",
                params={
                    "search": f"Filtre sort {token}", "plant_ids": str(plant_a.id),
                    "sort_by": "gain", "sort_dir": "desc", "limit": 1,
                    "cursor": first_pagination["nextCursor"],
                },
                headers=auth_headers,
            )
        )
        assert [i["title"] for i in second_items] == [f"Filtre sort {token} P1-100"]
        assert second_pagination["hasMore"] is False


class TestContributionWorkCreate:
    def test_draft_requires_only_title(self, client, auth_headers):
        resp = client.post("/api/v1/contribution-works", json={"title": "Taslak Çalışma"}, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = unwrap(resp)
        assert body["status"] == "draft"
        assert body["title"] == "Taslak Çalışma"
        assert body["foremen"] == []

    def test_publish_without_required_fields_returns_422_with_field_errors(self, client, auth_headers):
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Eksik Çalışma", "status": "published"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        error = unwrap_error(resp)
        assert error["code"] == "CONTRIBUTION_WORK_VALIDATION_FAILED"
        fields = {f["field"] for f in error["details"]["fields"]}
        assert "foremanIds" in fields
        assert "plantIds" in fields

    def test_publish_with_all_required_fields_succeeds(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman
        resp = client.post(
            "/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers
        )
        assert resp.status_code == 201, resp.text
        body = unwrap(resp)
        assert body["status"] == "published"
        assert body["publishedAt"] is not None
        assert body["foremen"][0]["id"] == str(foreman.id)
        assert body["plants"][0]["id"] == str(plant.id)

        assert body["perOccurrenceSaving"] == 17
        assert body["monthlyTotalSavingMinutes"] == 510
        assert body["highlightedGain"]["source"] == "financial"
        assert body["beforeAfter"]["before"] == "45.0 dakika"
        assert body["beforeAfter"]["after"] == "28.0 dakika"

    def test_created_by_ignores_client_supplied_value(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = {"title": "Sahte kullanıcı testi", "created_by_user_id": str(uuid.uuid4())}
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert unwrap(resp)["createdBy"]


class TestContributionWorkTypes:
    """5S / Çeşit Dönüşü Verimliliği / Personel Tasarrufu / Müşteri Şikayet / Poke Yoke."""

    @pytest.mark.parametrize(
        "work_type,expected_label",
        [
            ("5s", "5S"),
            ("variety_changeover_efficiency", "Çeşit Dönüşü Verimliliği"),
            ("staff_saving", "Personel Tasarrufu"),
            ("customer_complaint", "Müşteri Şikayet"),
            ("poka_yoke", "Poke Yoke"),
        ],
    )
    def test_new_work_type_can_be_created_and_read_back(
        self, client, auth_headers, db_session, work_type, expected_label
    ):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = _full_payload(plant, foreman)
        payload["work_type"] = work_type
        create_resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert create_resp.status_code == 201, create_resp.text
        body = unwrap(create_resp)
        assert body["workType"] == work_type
        assert body["workTypeLabel"] == expected_label

        get_resp = client.get(f"/api/v1/contribution-works/{body['id']}", headers=auth_headers)
        assert get_resp.status_code == 200
        get_body = unwrap(get_resp)
        assert get_body["workType"] == work_type
        assert get_body["workTypeLabel"] == expected_label

    @pytest.mark.parametrize(
        "work_type,expected_label",
        [("time_saving", "Zaman Kazancı"), ("quality_improvement", "Kalite İyileştirme")],
    )
    def test_legacy_work_type_still_readable(self, client, auth_headers, db_session, work_type, expected_label):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = _full_payload(plant, foreman)
        payload["work_type"] = work_type
        create_resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert create_resp.status_code == 201, create_resp.text
        body = unwrap(create_resp)
        assert body["workType"] == work_type
        assert body["workTypeLabel"] == expected_label

        get_resp = client.get(f"/api/v1/contribution-works/{body['id']}", headers=auth_headers)
        assert get_resp.status_code == 200
        assert unwrap(get_resp)["workTypeLabel"] == expected_label


class TestContributionWorkValidation:
    def test_negative_duration_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Negatif süre testi", "previous_duration": -5},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_negative_gain_amount_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Negatif kazanç testi", "gain_amount": -10000},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_reversed_date_range_rejected_on_create(self, client, auth_headers):
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Ters tarih testi", "work_date": "2026-08-15", "work_date_end": "2026-08-14"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_same_start_and_end_date_accepted(self, client, auth_headers):
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Aynı tarih testi", "work_date": "2026-08-14", "work_date_end": "2026-08-14"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text

    def test_partial_update_creating_invalid_merged_range_rejected(self, client, auth_headers):
        created = unwrap(
            client.post(
                "/api/v1/contribution-works",
                json={"title": "Kısmi güncelleme testi", "work_date": "2026-08-20"},
                headers=auth_headers,
            )
        )

        resp = client.patch(
            f"/api/v1/contribution-works/{created['id']}",
            json={"work_date_end": "2026-08-10"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestContributionWorkDetailAndUpdate:
    def test_unknown_id_returns_404(self, client, auth_headers):
        assert client.get(f"/api/v1/contribution-works/{uuid.uuid4()}", headers=auth_headers).status_code == 404

    def test_update_draft_then_publish(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = unwrap(
            client.post(
                "/api/v1/contribution-works", json={"title": "Aşamalı Yayın Testi"}, headers=auth_headers
            )
        )

        incomplete_publish = client.patch(
            f"/api/v1/contribution-works/{created['id']}", json={"status": "published"}, headers=auth_headers
        )
        assert incomplete_publish.status_code == 422

        full_update = {
            "work_type": "kaizen", "summary": "Özet", "problem_description": "Problem",
            "solution_description": "Çözüm", "foreman_ids": [str(foreman.id)],
            "plant_ids": [str(plant.id)], "work_date": "2026-02-01", "status": "published",
        }
        resp = client.patch(f"/api/v1/contribution-works/{created['id']}", json=full_update, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = unwrap(resp)
        assert body["status"] == "published"
        assert body["publishedAt"] is not None
        assert body["foremen"][0]["id"] == str(foreman.id)


class TestContributionWorkGains:
    def test_gain_change_is_computed_server_side(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = _full_payload(plant, foreman, status="draft")
        payload["gains"] = [
            {"gain_type": "scrap_reduction", "previous_value": 4.2, "next_value": 3.1, "unit": "%"}
        ]
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        gain = unwrap(resp)["gains"][0]
        assert gain["changeAmount"] == -1.1
        assert gain["changePercent"] == pytest.approx(-26.19, rel=0.01)
        assert gain["isImprovement"] is True


class TestContributionScore:
    def test_score_and_label_are_present_on_create(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = _full_payload(plant, foreman)
        payload["is_permanent_solution"] = True
        payload["is_standardized"] = True
        payload["is_applicable_other_plants"] = True
        payload["work_instruction_updated"] = True
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        body = unwrap(resp)
        assert body["contributionScore"] == 5
        assert body["contributionScoreLabel"] == "Çok Yüksek Operational Impact+"
        assert isinstance(body["contributionScoreBreakdown"], list) and body["contributionScoreBreakdown"]

    def test_minimal_work_scores_minimum(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        resp = client.post(
            "/api/v1/contribution-works",
            json={"title": "Minimal katkı", "foreman_ids": [str(foreman.id)]},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert unwrap(resp)["contributionScore"] == 1

    def test_client_supplied_score_is_ignored(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        payload = {"title": "Sahte puan testi", "foreman_ids": [str(foreman.id)], "score": 5, "contribution_score": 5}
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text
        assert unwrap(resp)["contributionScore"] == 1

    def test_score_recomputed_on_update(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = unwrap(
            client.post(
                "/api/v1/contribution-works",
                json={"title": "Yeniden hesaplama testi", "foreman_ids": [str(foreman.id)], "impact_level": "low"},
                headers=auth_headers,
            )
        )
        assert created["contributionScore"] == 1

        updated = client.patch(
            f"/api/v1/contribution-works/{created['id']}",
            json={
                "impact_level": "high", "is_permanent_solution": True, "is_standardized": True,
                "is_applicable_other_plants": True, "work_instruction_updated": True,
                "financial_gain_status": "yes", "gain_amount": 50000, "currency": "TRY",
            },
            headers=auth_headers,
        )
        assert updated.status_code == 200, updated.text
        assert unwrap(updated)["contributionScore"] == 5


class TestContributionWorkPdf:
    def test_pdf_download(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = unwrap(
            client.post(
                "/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers
            )
        )
        resp = client.get(f"/api/v1/contribution-works/{created['id']}/pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"


class TestContributionWorkSummary:
    def test_summary_shape(self, client, auth_headers):
        resp = client.get("/api/v1/contribution-works/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        for key in (
            "totalWorks", "addedThisMonth", "totalGainAmount",
            "totalMonthlyTimeSavingMinutes", "byPlant", "byWorkType", "topForemen",
            "applicableOtherPlantsCount", "standardizedRatio",
        ):
            assert key in body


class TestContributionWorkForemanRole:
    def test_solo_work_defaults_foreman_role_to_lead(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        created = unwrap(
            client.post(
                "/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers
            )
        )
        assert created["foremen"][0]["role"] == "lead"

    def test_shared_work_defaults_foreman_roles_to_contributor(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        second = db_session.scalars(
            select(Foreman).where(Foreman.is_active.is_(True), Foreman.id != foreman.id)
        ).first()
        assert second is not None

        payload = _full_payload(plant, foreman)
        payload["foreman_ids"] = [str(foreman.id), str(second.id)]
        created = unwrap(client.post("/api/v1/contribution-works", json=payload, headers=auth_headers))
        assert {f["role"] for f in created["foremen"]} == {"contributor"}


class TestForemanContributionSummary:
    def test_unknown_foreman_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/foremen/{uuid.uuid4()}/contribution-summary", headers=auth_headers)
        assert resp.status_code == 404

    def test_empty_state_for_foreman_without_contributions(self, client, auth_headers, db_session):
        covered = select(ContributionWorkForeman.foreman_id)
        foreman = db_session.scalar(select(Foreman).where(Foreman.id.notin_(covered)))
        assert foreman is not None

        resp = client.get(f"/api/v1/foremen/{foreman.id}/contribution-summary", headers=auth_headers)
        assert resp.status_code == 200
        assert unwrap(resp) == {
            "totalContributions": 0, "smedCount": 0, "ledContributions": 0,
            "financialGain": {},
            "totalTimeSavingMinutes": 0.0, "lastContributionDate": None,
        }

    def test_summary_counts_only_published_and_splits_shared_gain_evenly(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        second = db_session.scalars(
            select(Foreman).where(Foreman.is_active.is_(True), Foreman.id != foreman.id)
        ).first()
        assert second is not None

        client.post("/api/v1/contribution-works", json=_full_payload(plant, foreman), headers=auth_headers)

        shared_payload = _full_payload(plant, foreman)
        shared_payload["title"] = "Ortak SMED Çalışması"
        shared_payload["foreman_ids"] = [str(foreman.id), str(second.id)]
        client.post("/api/v1/contribution-works", json=shared_payload, headers=auth_headers)

        client.post(
            "/api/v1/contribution-works",
            json={"title": "Taslak - sayılmamalı", "foreman_ids": [str(foreman.id)]},
            headers=auth_headers,
        )

        resp = client.get(f"/api/v1/foremen/{foreman.id}/contribution-summary", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        assert body["totalContributions"] == 2
        assert body["smedCount"] == 2
        assert body["ledContributions"] == 1
        assert body["financialGain"]["TRY"] == pytest.approx(375000, rel=0.001)
        assert body["totalTimeSavingMinutes"] == pytest.approx(765, rel=0.001)
        assert body["lastContributionDate"] == "2026-01-15"
