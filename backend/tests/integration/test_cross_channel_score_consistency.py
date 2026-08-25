from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.contribution import ContributionWork
from app.models.enums import ReportType
from app.models.foreman import Foreman
from app.models.organization import Plant
from app.schemas.common import Filters
from app.services import analytics
from app.services.monthly_foreman_report import get_or_generate_monthly_report, latest_completed_period
from app.services.reporting import build_report_rows

from tests.helpers import unwrap, unwrap_page

from .conftest import TEST_SUBJECT
from .test_contribution_works import _sample_plant_and_foreman
from .test_general_performance_score import _high_impact_payload


@pytest.fixture(autouse=True)
def _cleanup_contribution_works(db_session):
    yield
    db_session.query(ContributionWork).filter(ContributionWork.created_by_subject == TEST_SUBJECT).delete(
        synchronize_session=False
    )
    db_session.commit()


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    date_from = date(year, month, 1)
    date_to = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    return date_from, date_to


def _pick_reliable_foreman(db_session, year: int, month: int):
    date_from, date_to = _month_bounds(year, month)
    scores = analytics.foreman_scores(db_session, Filters(date_from=date_from, date_to=date_to))
    reliable = [s for s in scores if s.is_reliable]
    if not reliable:
        return None
    return reliable[0].key


class TestMonthlyReportMatchesProfileGeneralScore:
    def test_report_overall_equals_profile_general_score_for_same_period(self, client, auth_headers, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_reliable_foreman(db_session, year, month)
        if foreman_id is None:
            pytest.skip("no foreman with reliable KPI data for the latest completed month")
        date_from, date_to = _month_bounds(year, month)

        plant = db_session.scalar(select(Plant).order_by(Plant.sequence_number))
        foreman = db_session.get(Foreman, foreman_id)

        resp = client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date_from + timedelta(days=3), "Çapraz kanal tutarlılık testi"),
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text

        report = get_or_generate_monthly_report(db_session, foreman_id, year, month, force=True)
        overall = report.report_data["overall"]
        assert overall["contribution_bonus"] >= 5

        profile = unwrap(
            client.get(
                f"/api/v1/foremen/{foreman_id}",
                params={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
                headers=auth_headers,
            )
        )

        assert overall["operational_score"] == pytest.approx(profile["operationalScore"], abs=0.01)
        assert overall["contribution_bonus"] == profile["contributionBonus"]
        assert overall["score"] == pytest.approx(profile["generalPerformanceScore"], abs=0.01)
        assert overall["score"] != overall["operational_score"]
        assert overall["level"]["name"] == profile["level"]["name"]


class TestDashboardDistributionMatchesForemenLevelCounts:
    def test_counts_agree_for_scored_foremen_before_and_after_a_contribution_bonus(
        self, client, auth_headers, db_session
    ):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        filters = Filters(date_from=date.today() - timedelta(days=30), date_to=date.today())

        def _assert_counts_agree():
            scored_ids = {str(s.key) for s in analytics.foreman_scores(db_session, filters)}
            dist = unwrap(client.get("/api/v1/dashboard/performance-distribution", headers=auth_headers))

            level_by_foreman_id: dict[str, str] = {}
            cursor = None
            while True:
                params = {"limit": 200}
                if cursor:
                    params["cursor"] = cursor
                resp = client.get("/api/v1/foremen", params=params, headers=auth_headers)
                items, pagination = unwrap_page(resp)
                for item in items:
                    level_by_foreman_id[item["id"]] = item["level"]["name"]
                if not pagination["hasMore"]:
                    break
                cursor = pagination["nextCursor"]

            counts: dict[str, int] = {}
            for fid in scored_ids:
                name = level_by_foreman_id.get(fid)
                if name:
                    counts[name] = counts.get(name, 0) + 1

            for item in dist["items"]:
                assert counts.get(item["name"], 0) == item["count"], f"mismatch for level {item['name']}"

        _assert_counts_agree()

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Dağılım tutarlılığı testi"),
            headers=auth_headers,
        )

        _assert_counts_agree()


class TestDashboardSummaryUsesGeneralScore:
    def test_avg_company_score_reflects_contribution_bonus(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        before = unwrap(client.get("/api/v1/dashboard/summary", headers=auth_headers))

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Şirket ortalaması testi"),
            headers=auth_headers,
        )

        after = unwrap(client.get("/api/v1/dashboard/summary", headers=auth_headers))
        n = after["totalActiveForemen"]
        assert n > 0
        expected_min_increase = 5 / n - 0.05
        assert after["avgCompanyScore"] >= before["avgCompanyScore"] + expected_min_increase


class TestPlantScoreUnaffectedByContributionBonus:
    def test_plant_score_stable_when_foreman_bonus_changes(self, client, auth_headers, db_session):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        before = unwrap(client.get(f"/api/v1/plants/{plant.id}/summary", headers=auth_headers))

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Tesis skoru sabitliği testi"),
            headers=auth_headers,
        )

        after = unwrap(client.get(f"/api/v1/plants/{plant.id}/summary", headers=auth_headers))
        assert after["totalScore"] == pytest.approx(before["totalScore"], abs=0.001)


class TestForemanExportUsesGeneralScore:
    def test_foreman_performance_export_columns_and_ranking_use_general_score(
        self, client, auth_headers, db_session
    ):
        plant, foreman = _sample_plant_and_foreman(db_session)
        assert plant and foreman

        client.post(
            "/api/v1/contribution-works",
            json=_high_impact_payload(plant, foreman, date.today(), "Rapor export testi"),
            headers=auth_headers,
        )

        headers, rows = build_report_rows(
            db_session, ReportType.FOREMAN_PERFORMANCE,
            Filters(date_from=date.today() - timedelta(days=30), date_to=date.today()),
        )
        assert {"Operasyonel Puan", "Operational Impact+ Bonusu", "Genel Puan"}.issubset(set(headers))
        row = next(r for r in rows if r["Sicil No"] == foreman.employee_number)
        assert row["Genel Puan"] == pytest.approx(row["Operasyonel Puan"] + row["Operational Impact+ Bonusu"], abs=0.01)
        assert row["Operational Impact+ Bonusu"] >= 5
