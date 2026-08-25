import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import ForemanAssignment
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.schemas.common import Filters
from app.services import analytics
from app.services.kpi_engine import score_gsf

from tests.helpers import unwrap, unwrap_page

_DAY_1 = date(2099, 3, 10)
_DAY_2 = date(2099, 3, 11)


def _pick_plant_with_two_foremen(db):
    plant_id = db.scalar(
        select(ForemanAssignment.plant_id)
        .where(ForemanAssignment.is_active.is_(True))
        .group_by(ForemanAssignment.plant_id)
        .having(func.count(ForemanAssignment.foreman_id.distinct()) == 2)
        .limit(1)
    )
    plant = db.get(Plant, plant_id)
    assignments = list(
        db.scalars(
            select(ForemanAssignment).where(
                ForemanAssignment.plant_id == plant_id, ForemanAssignment.is_active.is_(True)
            )
        )
    )
    foreman_ids = sorted({a.foreman_id for a in assignments})
    assert len(foreman_ids) == 2
    return plant, foreman_ids


def _make_record(plant, chief_id, shift_id, foreman_id, kpi, run_id, performance_date, actual, target):
    now = datetime.now(timezone.utc)
    return PerformanceRecord(
        id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC,
        source_record_id=f"TEST-PLANTSCORE-{uuid.uuid4().hex[:8]}",
        integration_run_id=run_id, performance_date=performance_date,
        plant_id=plant.id, chief_id=chief_id, shift_id=shift_id, foreman_id=foreman_id, kpi_id=kpi.id,
        target_value=target, actual_value=actual,
        numerator_value=actual, denominator_value=100.0, unit=kpi.unit,
        data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
    )


class TestPlantScoreConsistency:
    @pytest.fixture
    def scenario(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            plant, foreman_ids = _pick_plant_with_two_foremen(db)
            foreman_a, foreman_b = foreman_ids
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            shift_v1 = db.scalar(select(Shift).where(Shift.code == "V1"))
            shift_v2 = db.scalar(select(Shift).where(Shift.code == "V2"))
            run_id = db.scalar(select(IntegrationRun.id).limit(1))

            records = [
                _make_record(plant, plant.chief_id, shift_v1.id, foreman_a, kpi, run_id, _DAY_1, 0.10, 0.60),
                _make_record(plant, plant.chief_id, shift_v1.id, foreman_b, kpi, run_id, _DAY_1, 2.00, 0.60),
                _make_record(plant, plant.chief_id, shift_v2.id, foreman_a, kpi, run_id, _DAY_2, 0.20, 0.60),
                _make_record(plant, plant.chief_id, shift_v2.id, foreman_b, kpi, run_id, _DAY_2, 1.50, 0.60),
            ]
            db.add_all(records)
            db.flush()
            record_ids = [r.id for r in records]
            db.commit()

            yield {
                "db": db, "plant": plant, "foreman_a": foreman_a, "foreman_b": foreman_b,
                "kpi": kpi, "shift_v1": shift_v1, "shift_v2": shift_v2,
            }
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()

    def test_plant_score_diverges_from_foreman_average_but_list_and_detail_agree(self, scenario, client, auth_headers):
        db = scenario["db"]
        plant = scenario["plant"]
        kpi = scenario["kpi"]

        filters = Filters(date_from=_DAY_1, date_to=_DAY_1, kpi_ids=[kpi.id])
        plant_score = next(s.total_score for s in analytics.plant_scores(db, filters) if s.key == plant.id)
        foreman_totals = [
            s.total_score for s in analytics.foreman_scores(db, filters)
            if s.key in (scenario["foreman_a"], scenario["foreman_b"])
        ]
        foremen_average = sum(foreman_totals) / len(foreman_totals)

        expected_plant_actual = (0.10 + 2.00) / 2
        expected_plant_score = score_gsf(expected_plant_actual, 0.60).capped_score
        assert plant_score == pytest.approx(expected_plant_score, abs=0.05)
        assert plant_score != pytest.approx(foremen_average, abs=0.5)

        params = {"date_from": _DAY_1.isoformat(), "date_to": _DAY_1.isoformat(), "kpi_ids": str(kpi.id)}
        list_resp = client.get(
            "/api/v1/plants", params={**params, "search": plant.code, "limit": 5}, headers=auth_headers
        )
        assert list_resp.status_code == 200
        list_items, _pagination = unwrap_page(list_resp)
        list_item = next(i for i in list_items if i["id"] == str(plant.id))

        detail_resp = client.get(f"/api/v1/plants/{plant.id}/summary", params=params, headers=auth_headers)
        assert detail_resp.status_code == 200
        detail = unwrap(detail_resp)

        assert detail["totalScore"] == pytest.approx(list_item["totalScore"], abs=0.01)
        assert detail["level"]["name"] == list_item["level"]["name"]
        assert detail["totalScore"] != pytest.approx(detail["foremenAverageScore"], abs=0.1)

    @pytest.mark.parametrize(
        "date_from,date_to,use_shift_filter,use_kpi_filter",
        [
            (_DAY_1, _DAY_1, False, False),
            (_DAY_1, _DAY_2, False, False),
            (_DAY_1, _DAY_1, True, False),
            (_DAY_1, _DAY_1, False, True),
            (_DAY_1, _DAY_2, False, True),
        ],
        ids=["single_day_no_filter", "date_range_no_filter", "shift_filtered", "kpi_filtered", "date_range_kpi_filtered"],
    )
    def test_plant_list_and_detail_score_and_level_agree_across_filters(
        self, scenario, client, auth_headers, date_from, date_to, use_shift_filter, use_kpi_filter
    ):
        plant = scenario["plant"]
        query = {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()}
        if use_shift_filter:
            query["shift_ids"] = str(scenario["shift_v1"].id)
        if use_kpi_filter:
            query["kpi_ids"] = str(scenario["kpi"].id)

        list_resp = client.get(
            "/api/v1/plants", params={**query, "search": plant.code, "limit": 5}, headers=auth_headers
        )
        assert list_resp.status_code == 200
        list_items, _pagination = unwrap_page(list_resp)
        list_item = next(i for i in list_items if i["id"] == str(plant.id))

        detail_resp = client.get(f"/api/v1/plants/{plant.id}/summary", params=query, headers=auth_headers)
        assert detail_resp.status_code == 200
        detail = unwrap(detail_resp)

        assert detail["totalScore"] == pytest.approx(list_item["totalScore"], abs=0.01)
        assert detail["level"]["name"] == list_item["level"]["name"]
