import uuid
from tests.helpers import legacy_json
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import Chief, Foreman
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.schemas.common import Filters
from app.services import analytics

_TEST_DATE = date(2099, 6, 20)


def _pick_chief_with_plants(db, min_count=2):
    chief_id = db.scalar(
        select(Plant.chief_id).group_by(Plant.chief_id).having(func.count(Plant.id) >= min_count).limit(1)
    )
    chief = db.get(Chief, chief_id)
    plants = list(db.scalars(select(Plant).where(Plant.chief_id == chief_id).order_by(Plant.sequence_number)))
    return chief, plants


def _pick_other_chief(db, excluded_chief_id, excluded_factory_id):
    row = db.execute(
        select(Plant.chief_id, Plant.id)
        .where(Plant.chief_id != excluded_chief_id, Plant.factory_id != excluded_factory_id)
        .limit(1)
    ).first()
    assert row is not None
    return db.get(Chief, row.chief_id), db.get(Plant, row.id)


def _record(foreman, plant, kpi, shift, run_id, actual, target):
    now = datetime.now(timezone.utc)
    return PerformanceRecord(
        id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC,
        source_record_id=f"TEST-CHIEF-SCOPE-{uuid.uuid4().hex[:8]}",
        integration_run_id=run_id, performance_date=_TEST_DATE,
        plant_id=plant.id, chief_id=plant.chief_id, shift_id=shift.id,
        foreman_id=foreman.id, kpi_id=kpi.id,
        target_value=target, actual_value=actual,
        numerator_value=actual, denominator_value=100.0, unit=kpi.unit,
        data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
    )


class TestChiefDetailFilterScope:
    @pytest.fixture
    def scoped_data(self, db_session):
        chief, plants = _pick_chief_with_plants(db_session, min_count=2)
        plant_a, plant_b = plants[0], plants[1]
        kpi = db_session.scalar(select(Kpi).where(Kpi.code == "GSF"))
        shifts = list(db_session.scalars(select(Shift).order_by(Shift.sequence)))
        shift_a, shift_b = shifts[0], shifts[1]
        run_id = db_session.scalar(select(IntegrationRun.id).limit(1))
        foreman = db_session.scalar(select(Foreman).where(Foreman.is_active.is_(True)).limit(1))
        other_chief, other_plant = _pick_other_chief(db_session, chief.id, plant_a.factory_id)

        rec_a = _record(foreman, plant_a, kpi, shift_a, run_id, 0.70, 0.60)
        rec_b = _record(foreman, plant_b, kpi, shift_b, run_id, 0.30, 0.60)
        rec_other = _record(foreman, other_plant, kpi, shift_a, run_id, 0.65, 0.65)
        db_session.add_all([rec_a, rec_b, rec_other])
        db_session.flush()
        record_ids = [rec_a.id, rec_b.id, rec_other.id]
        db_session.commit()

        try:
            yield {
                "chief": chief, "other_chief": other_chief,
                "plant_a": plant_a, "plant_b": plant_b, "other_plant": other_plant,
                "kpi": kpi, "shift_a": shift_a, "shift_b": shift_b,
            }
        finally:
            db_session.rollback()
            db_session.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
            db_session.commit()

    def _get(self, client, auth_headers, chief_id, params):
        query = {"date_from": _TEST_DATE.isoformat(), "date_to": _TEST_DATE.isoformat()}
        query.update(params)
        resp = client.get(f"/api/v1/chiefs/{chief_id}", params=query, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return legacy_json(resp)

    def _expected_team_score(self, db_session, chief_id, filters):
        team = next((t for t in analytics.chief_team_scores(db_session, filters) if t.chief_id == chief_id), None)
        return team.total_score if team else 0.0

    def test_plant_filter_matches_service_layer_and_differs_from_company_wide(
        self, client, auth_headers, scoped_data, db_session
    ):
        d = scoped_data
        unfiltered = self._get(client, auth_headers, d["chief"].id, {"kpi_ids": str(d["kpi"].id)})

        params = {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id)}
        body = self._get(client, auth_headers, d["chief"].id, params)

        expected = self._expected_team_score(
            db_session, d["chief"].id,
            Filters(date_from=_TEST_DATE, date_to=_TEST_DATE, kpi_ids=[d["kpi"].id], plant_ids=[d["plant_a"].id]),
        )
        assert body["total_score"] == pytest.approx(expected, abs=0.01)
        assert body["total_score"] != pytest.approx(unfiltered["total_score"], abs=0.01)

    def test_factory_filter_for_unrelated_factory_excludes_chief(self, client, auth_headers, scoped_data):
        d = scoped_data
        body = self._get(
            client, auth_headers, d["chief"].id,
            {"kpi_ids": str(d["kpi"].id), "factory_ids": str(d["other_plant"].factory_id)},
        )
        assert body["total_score"] == 0.0
        assert body["company_rank"] is None

    def test_shift_filter_matches_service_layer(self, client, auth_headers, scoped_data, db_session):
        d = scoped_data
        params = {"kpi_ids": str(d["kpi"].id), "shift_ids": str(d["shift_a"].id)}
        body = self._get(client, auth_headers, d["chief"].id, params)
        expected = self._expected_team_score(
            db_session, d["chief"].id,
            Filters(date_from=_TEST_DATE, date_to=_TEST_DATE, kpi_ids=[d["kpi"].id], shift_ids=[d["shift_a"].id]),
        )
        assert body["total_score"] == pytest.approx(expected, abs=0.01)

    def test_own_chief_id_filter_does_not_corrupt_ranking_cohort(self, client, auth_headers, scoped_data):
        d = scoped_data
        unfiltered = self._get(client, auth_headers, d["chief"].id, {"kpi_ids": str(d["kpi"].id)})

        with_unrelated_chief_filter = self._get(
            client, auth_headers, d["chief"].id,
            {"kpi_ids": str(d["kpi"].id), "chief_ids": str(d["other_chief"].id)},
        )
        assert with_unrelated_chief_filter["total_score"] == pytest.approx(unfiltered["total_score"], abs=0.01)
        assert with_unrelated_chief_filter["company_total"] == unfiltered["company_total"]
        assert with_unrelated_chief_filter["company_rank"] == unfiltered["company_rank"]

    def test_ranking_cohort_narrows_with_plant_filter(self, client, auth_headers, scoped_data):
        d = scoped_data
        unfiltered = self._get(client, auth_headers, d["chief"].id, {"kpi_ids": str(d["kpi"].id)})
        assert unfiltered["company_total"] >= 2

        plant_scoped = self._get(
            client, auth_headers, d["chief"].id,
            {"kpi_ids": str(d["kpi"].id), "plant_ids": str(d["plant_a"].id)},
        )
        assert plant_scoped["company_total"] == 1
        assert plant_scoped["company_rank"] == 1
