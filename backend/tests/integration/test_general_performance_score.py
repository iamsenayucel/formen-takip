from datetime import date, timedelta

import pytest

from app.models.contribution import ContributionWork

from tests.helpers import unwrap, unwrap_page

from .conftest import TEST_SUBJECT
from .test_contribution_works import _sample_plant_and_foreman


@pytest.fixture(autouse=True)
def _cleanup_contribution_works(db_session):
    yield
    db_session.query(ContributionWork).filter(ContributionWork.created_by_subject == TEST_SUBJECT).delete(
        synchronize_session=False
    )
    db_session.commit()


def _high_impact_payload(plant, foreman, work_date: date, title: str) -> dict:
    return {
        "title": title,
        "status": "published",
        "work_type": "kaizen",
        "summary": "Özet",
        "problem_description": "Problem",
        "solution_description": "Çözüm",
        "foreman_ids": [str(foreman.id)],
        "plant_ids": [str(plant.id)],
        "work_date": work_date.isoformat(),
        "impact_level": "high",
        "is_permanent_solution": True,
        "is_standardized": True,
        "is_applicable_other_plants": True,
        "work_instruction_updated": True,
        "financial_gain_status": "yes",
        "gain_amount": 100000,
        "currency": "TRY",
    }


class TestGeneralPerformanceScore:
    def test_bonus_adds_on_top_of_operational_score_and_is_capped(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        baseline = unwrap(client.get(f"/api/v1/foremen/{foreman.id}", headers=auth_headers))
        operational_score = baseline["operationalScore"]
        assert baseline["contributionBonus"] == 0
        assert baseline["generalPerformanceScore"] == operational_score

        resp = client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Genel puan testi"),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        assert unwrap(resp)["contributionScore"] == 5

        after = unwrap(client.get(f"/api/v1/foremen/{foreman.id}", headers=auth_headers))
        assert after["operationalScore"] == operational_score
        assert after["contributionBonus"] == 5
        assert after["generalPerformanceScore"] == min(operational_score + 5, 120)
        assert after["generalPerformanceScore"] <= 120
        assert len(after["contributionBonusBreakdown"]) == 1
        assert after["contributionBonusBreakdown"][0]["score"] == 5

    def test_contribution_outside_rolling_window_is_excluded(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        old_date = date.today() - timedelta(days=200)
        resp = client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, old_date, "Pencere dışı katkı"),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text

        after = unwrap(client.get(f"/api/v1/foremen/{foreman.id}", headers=auth_headers))
        assert after["contributionBonus"] == 0
        assert after["generalPerformanceScore"] == after["operationalScore"]

    def test_multiple_contributions_sum_within_window(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Katkı 1"),
            headers=auth_headers,
        )
        second_payload = _high_impact_payload(plant, foreman, date.today() - timedelta(days=10), "Katkı 2")
        second_payload["impact_level"] = "medium"
        client.post("/api/v1/contribution-works", json=second_payload, headers=auth_headers)

        after = unwrap(client.get(f"/api/v1/foremen/{foreman.id}", headers=auth_headers))
        assert after["contributionBonus"] >= 5 + 1
        assert len(after["contributionBonusBreakdown"]) == 2

    def test_draft_contributions_do_not_contribute_bonus(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        payload = _high_impact_payload(plant, foreman, date.today(), "Taslak katkı")
        payload["status"] = "draft"
        resp = client.post("/api/v1/contribution-works", json=payload, headers=auth_headers)
        assert resp.status_code == 201, resp.text

        after = unwrap(client.get(f"/api/v1/foremen/{foreman.id}", headers=auth_headers))
        assert after["contributionBonus"] == 0

    def test_foremen_list_ranks_by_general_score(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Sıralama testi"),
            headers=auth_headers,
        )

        resp = client.get(
            "/api/v1/foremen", params={"search": foreman.employee_number}, headers=auth_headers
        )
        assert resp.status_code == 200
        items, _pagination = unwrap_page(resp)
        assert len(items) == 1
        item = items[0]
        assert item["generalPerformanceScore"] == min(item["operationalScore"] + item["contributionBonus"], 120)
        assert item["contributionBonus"] == 5

    def test_kpi_scoped_endpoints_stay_operational_only(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "KPI ayrımı testi"),
            headers=auth_headers,
        )

        summary = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert summary.status_code == 200
        assert "generalPerformanceScore" not in unwrap(summary)

        plant_ranking = client.get("/api/v1/dashboard/plant-ranking", headers=auth_headers)
        assert plant_ranking.status_code == 200
        for item in unwrap(plant_ranking):
            assert "contributionBonus" not in item
