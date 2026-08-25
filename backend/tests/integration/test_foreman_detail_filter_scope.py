import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import Foreman, ForemanAssignment
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.services.kpi_engine import score_gsf

from tests.helpers import unwrap

from .test_foreman_plant_equal_weight import _pick_foreman_with_plants

_TEST_DATE = date(2099, 6, 15)


def _pick_foreman_outside_zone(db, excluded_chief_id, excluded_factory_id):
    row = db.execute(
        select(ForemanAssignment.foreman_id, ForemanAssignment.plant_id)
        .join(Plant, Plant.id == ForemanAssignment.plant_id)
        .where(
            ForemanAssignment.is_active.is_(True),
            ForemanAssignment.chief_id != excluded_chief_id,
            Plant.factory_id != excluded_factory_id,
        )
        .limit(1)
    ).first()
    assert row is not None
    return db.get(Foreman, row.foreman_id), db.get(Plant, row.plant_id)


def _record(foreman, plant, kpi, shift, run_id, actual, target):
    now = datetime.now(timezone.utc)
    return PerformanceRecord(
        id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC,
        source_record_id=f"TEST-SCOPE-{uuid.uuid4().hex[:8]}",
        integration_run_id=run_id, performance_date=_TEST_DATE,
        plant_id=plant.id, chief_id=plant.chief_id, shift_id=shift.id,
        foreman_id=foreman.id, kpi_id=kpi.id,
        target_value=target, actual_value=actual,
        numerator_value=actual, denominator_value=100.0, unit=kpi.unit,
        data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
    )


class TestForemanDetailFilterScope:
    @pytest.fixture
    def scoped_data(self, db_session):
        foreman, plants = _pick_foreman_with_plants(db_session, min_count=2)
        plant_a, plant_b = plants[0], plants[1]
        kpi = db_session.scalar(select(Kpi).where(Kpi.code == "GSF"))
        shifts = list(db_session.scalars(select(Shift).order_by(Shift.sequence)))
        shift_a, shift_b = shifts[0], shifts[1]
        run_id = db_session.scalar(select(IntegrationRun.id).limit(1))
        other_foreman, other_plant = _pick_foreman_outside_zone(
            db_session, plant_a.chief_id, plant_a.factory_id
        )

        rec_a = _record(foreman, plant_a, kpi, shift_a, run_id, 0.70, 0.60)
        rec_b = _record(foreman, plant_b, kpi, shift_b, run_id, 0.70, 1.00)
        rec_other = _record(other_foreman, other_plant, kpi, shift_a, run_id, 0.65, 0.65)
        db_session.add_all([rec_a, rec_b, rec_other])
        db_session.flush()
        record_ids = [rec_a.id, rec_b.id, rec_other.id]
        db_session.commit()

        try:
            yield {
                "foreman": foreman, "other_foreman": other_foreman,
                "plant_a": plant_a, "plant_b": plant_b, "other_plant": other_plant,
                "kpi": kpi, "shift_a": shift_a, "shift_b": shift_b,
                "score_a": round(score_gsf(0.70, 0.60).capped_score, 2),
                "score_b": round(score_gsf(0.70, 1.00).capped_score, 2),
            }
        finally:
            db_session.rollback()
            db_session.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
            db_session.commit()

    def _get(self, client, auth_headers, foreman_id, params):
        query = {"date_from": _TEST_DATE.isoformat(), "date_to": _TEST_DATE.isoformat()}
        query.update(params)
        resp = client.get(f"/api/v1/foremen/{foreman_id}", params=query, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return unwrap(resp)

    def test_date_only_filter_combines_all_plants(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(client, auth_headers, d["foreman"].id, {"kpi_ids": str(d["kpi"].id)})
        expected = round((d["score_a"] + d["score_b"]) / 2, 2)
        assert body["operationalScore"] == pytest.approx(expected, abs=0.01)

    def test_plant_filter_scopes_score_to_single_plant_not_company_wide(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id)},
        )
        assert body["operationalScore"] == pytest.approx(d["score_a"], abs=0.01)
        company_wide = round((d["score_a"] + d["score_b"]) / 2, 2)
        assert body["operationalScore"] != pytest.approx(company_wide, abs=0.01)
        assert body["inScope"] is True

    def test_other_plant_filter_returns_other_plant_score(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_b"].id)},
        )
        assert body["operationalScore"] == pytest.approx(d["score_b"], abs=0.01)

    def test_shift_filter_isolates_matching_record(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "shift_ids": str(d["shift_a"].id)},
        )
        assert body["operationalScore"] == pytest.approx(d["score_a"], abs=0.01)

    def test_chief_filter_for_own_chief_keeps_full_score(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "chief_ids": str(d["plant_a"].chief_id)},
        )
        expected = round((d["score_a"] + d["score_b"]) / 2, 2)
        assert body["operationalScore"] == pytest.approx(expected, abs=0.01)

    def test_chief_filter_for_unrelated_chief_excludes_foreman(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "chief_ids": str(d["other_plant"].chief_id)},
        )
        assert body["operationalScore"] == 0.0
        assert body["isReliable"] is False
        assert body["inScope"] is False
        assert body["companyRank"] is None

    def test_factory_filter_for_unrelated_factory_excludes_foreman(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "factory_ids": str(d["other_plant"].factory_id)},
        )
        assert body["operationalScore"] == 0.0
        assert body["inScope"] is False
        assert body["companyRank"] is None

    def test_combined_plant_and_shift_filters_apply_together(self, client, auth_headers, scoped_data):
        d = scoped_data
        matching = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id), "shift_ids": str(d["shift_a"].id)},
        )
        assert matching["operationalScore"] == pytest.approx(d["score_a"], abs=0.01)
        assert matching["inScope"] is True

        mismatched = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id), "shift_ids": str(d["shift_b"].id)},
        )
        assert mismatched["operationalScore"] == 0.0
        assert mismatched["inScope"] is False
        assert mismatched["companyRank"] is None

    def test_score_and_kpi_breakdown_share_the_same_scope(self, client, auth_headers, scoped_data):
        d = scoped_data
        params = {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id)}
        detail = self._get(client, auth_headers, d["foreman"].id, params)

        query = {"date_from": _TEST_DATE.isoformat(), "date_to": _TEST_DATE.isoformat()}
        query.update(params)
        kpis_resp = client.get(f"/api/v1/foremen/{d['foreman'].id}/kpis", params=query, headers=auth_headers)
        assert kpis_resp.status_code == 200
        gsf_row = next(i for i in unwrap(kpis_resp) if i["code"] == "GSF")

        assert detail["operationalScore"] == pytest.approx(gsf_row["avgCappedScore"], abs=0.01)

    def test_ranking_cohort_narrows_with_plant_filter(self, client, auth_headers, scoped_data):
        d = scoped_data
        company_wide = self._get(client, auth_headers, d["foreman"].id, {"kpi_ids": str(d["kpi"].id)})
        assert company_wide["companyTotal"] >= 2

        plant_scoped = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id)},
        )
        assert plant_scoped["companyTotal"] == 1
        assert plant_scoped["companyRank"] == 1

    def test_no_filters_matches_explicit_default_date_range(self, client, auth_headers, db_session):
        foreman = db_session.scalar(select(Foreman).where(Foreman.is_active.is_(True)).limit(1))
        today = date.today()
        no_filters = client.get(f"/api/v1/foremen/{foreman.id}", headers=auth_headers)
        explicit = client.get(
            f"/api/v1/foremen/{foreman.id}",
            params={"date_from": (today - timedelta(days=30)).isoformat(), "date_to": today.isoformat()},
            headers=auth_headers,
        )
        assert no_filters.status_code == explicit.status_code == 200
        assert unwrap(no_filters)["operationalScore"] == unwrap(explicit)["operationalScore"]
        assert unwrap(no_filters)["companyRank"] == unwrap(explicit)["companyRank"]

    def test_in_scope_is_false_exactly_when_company_rank_is_null(self, client, auth_headers, scoped_data):
        d = scoped_data
        excluded = self._get(
            client, auth_headers, d["foreman"].id,
            {"kpi_ids": str(d["kpi"].id), "chief_ids": str(d["other_plant"].chief_id)},
        )
        assert excluded["inScope"] is False
        assert excluded["companyRank"] is None

        included = self._get(client, auth_headers, d["foreman"].id, {"kpi_ids": str(d["kpi"].id)})
        assert included["inScope"] is True
        assert included["companyRank"] is not None
