import logging
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.enums import DataQualityStatus, SourceSystem, TargetScopeType
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi, KpiTarget
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord, PerformanceScore
from app.schemas.common import Filters
from app.services import analytics
from app.services.ingestion import run_ingestion
from app.services.kpi_engine import score_gsf
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord
from app.services.shift_rotation import actual_shift_for_date

from tests.helpers import unwrap

_TEST_DATE = date(2099, 6, 15)


def _pick_foreman_with_plants(db, min_count: int = 2):
    foreman_id = db.scalar(
        select(ForemanAssignment.foreman_id)
        .where(ForemanAssignment.is_active.is_(True))
        .group_by(ForemanAssignment.foreman_id)
        .having(func.count(ForemanAssignment.plant_id.distinct()) >= min_count)
        .limit(1)
    )
    assignments = list(
        db.scalars(
            select(ForemanAssignment).where(
                ForemanAssignment.foreman_id == foreman_id, ForemanAssignment.is_active.is_(True)
            )
        )
    )
    foreman = db.get(Foreman, foreman_id)
    plants = [db.get(Plant, a.plant_id) for a in assignments]
    return foreman, plants


def _make_gsf_record(foreman, plant, kpi, shift, run_id, performance_date, actual_pct, target_pct) -> PerformanceRecord:
    now = datetime.now(timezone.utc)
    chief = plant.chief
    return PerformanceRecord(
        id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC,
        source_record_id=f"TEST-EQW-{uuid.uuid4().hex[:8]}",
        integration_run_id=run_id, performance_date=performance_date,
        plant_id=plant.id, chief_id=chief.id, shift_id=shift.id, foreman_id=foreman.id, kpi_id=kpi.id,
        target_value=target_pct, actual_value=actual_pct,
        numerator_value=actual_pct, denominator_value=100.0, unit=kpi.unit,
        data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
    )


class TestForemanPlantEqualWeightAggregation:

    def test_same_actual_different_plant_targets_yield_different_scores(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            foreman, plants = _pick_foreman_with_plants(db, min_count=2)
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            shift = db.scalar(select(Shift).limit(1))
            run_id = db.scalar(select(IntegrationRun.id).limit(1))

            plant_a, plant_b = plants[0], plants[1]
            rec_a = _make_gsf_record(foreman, plant_a, kpi, shift, run_id, _TEST_DATE, 0.70, 0.60)
            rec_b = _make_gsf_record(foreman, plant_b, kpi, shift, run_id, _TEST_DATE, 0.70, 1.00)
            db.add_all([rec_a, rec_b])
            db.flush()
            record_ids = [rec_a.id, rec_b.id]
            db.commit()

            filters = Filters(date_from=_TEST_DATE, date_to=_TEST_DATE)
            rows = analytics.foreman_kpi_breakdown(db, filters, foreman.id)
            gsf_row = next(r for r in rows if r["kpi_id"] == kpi.id)

            plants_by_id = {p["plant_id"]: p for p in gsf_row["plants"]}
            score_a = plants_by_id[plant_a.id]["score"]
            score_b = plants_by_id[plant_b.id]["score"]

            assert score_a != score_b
            expected_a = score_gsf(0.70, 0.60).capped_score
            expected_b = score_gsf(0.70, 1.00).capped_score
            assert score_a == round(expected_a, 2)
            assert score_b == round(expected_b, 2)
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()

    def test_plant_scores_are_averaged_equally_regardless_of_capacity(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            foreman, plants = _pick_foreman_with_plants(db, min_count=2)
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            shift = db.scalar(select(Shift).limit(1))
            run_id = db.scalar(select(IntegrationRun.id).limit(1))

            plant_a, plant_b = plants[0], plants[1]
            actual_a, target_a = 0.70, 0.60
            actual_b, target_b = 0.90, 1.00

            now = datetime.now(timezone.utc)
            rec_a = PerformanceRecord(
                id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC, source_record_id=f"TEST-EQW-{uuid.uuid4().hex[:8]}",
                integration_run_id=run_id, performance_date=_TEST_DATE,
                plant_id=plant_a.id, chief_id=plant_a.chief_id, shift_id=shift.id, foreman_id=foreman.id, kpi_id=kpi.id,
                target_value=target_a, actual_value=actual_a,
                numerator_value=actual_a, denominator_value=100.0, unit=kpi.unit,
                data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
            )
            rec_b = PerformanceRecord(
                id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC, source_record_id=f"TEST-EQW-{uuid.uuid4().hex[:8]}",
                integration_run_id=run_id, performance_date=_TEST_DATE,
                plant_id=plant_b.id, chief_id=plant_b.chief_id, shift_id=shift.id, foreman_id=foreman.id, kpi_id=kpi.id,
                target_value=target_b, actual_value=actual_b,
                numerator_value=actual_b * 1000.0, denominator_value=100000.0, unit=kpi.unit,
                data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
            )
            db.add_all([rec_a, rec_b])
            db.flush()
            record_ids = [rec_a.id, rec_b.id]
            db.commit()

            filters = Filters(date_from=_TEST_DATE, date_to=_TEST_DATE)
            rows = analytics.foreman_kpi_breakdown(db, filters, foreman.id)
            gsf_row = next(r for r in rows if r["kpi_id"] == kpi.id)

            expected_a = score_gsf(actual_a, target_a).capped_score
            expected_b = score_gsf(actual_b, target_b).capped_score
            expected_avg = (expected_a + expected_b) / 2.0

            assert gsf_row["evaluated_plant_count"] == 2
            assert gsf_row["avg_capped_score"] == pytest.approx(expected_avg, abs=0.01)
            for p in gsf_row["plants"]:
                assert p["weight"] == pytest.approx(0.5, abs=1e-6)

            kpi_filters = Filters(date_from=_TEST_DATE, date_to=_TEST_DATE, kpi_ids=[kpi.id])
            foreman_total = {s.key: s for s in analytics.foreman_scores(db, kpi_filters)}[foreman.id]
            assert foreman_total.total_score == pytest.approx(expected_avg, abs=0.01)
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()

    def test_missing_plant_data_is_excluded_not_scored_as_zero(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            foreman, plants = _pick_foreman_with_plants(db, min_count=3)
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            shift = db.scalar(select(Shift).limit(1))
            run_id = db.scalar(select(IntegrationRun.id).limit(1))

            plant_a, plant_b = plants[0], plants[1]
            rec_a = _make_gsf_record(foreman, plant_a, kpi, shift, run_id, _TEST_DATE, 0.50, 0.60)
            rec_b = _make_gsf_record(foreman, plant_b, kpi, shift, run_id, _TEST_DATE, 0.80, 0.60)
            db.add_all([rec_a, rec_b])
            db.flush()
            record_ids = [rec_a.id, rec_b.id]
            db.commit()

            filters = Filters(date_from=_TEST_DATE, date_to=_TEST_DATE)
            rows = analytics.foreman_kpi_breakdown(db, filters, foreman.id)
            gsf_row = next(r for r in rows if r["kpi_id"] == kpi.id)

            assert gsf_row["evaluated_plant_count"] == 2
            expected_a = score_gsf(0.50, 0.60).capped_score
            expected_b = score_gsf(0.80, 0.60).capped_score
            expected_avg = (expected_a + expected_b) / 2.0
            assert gsf_row["avg_capped_score"] == pytest.approx(expected_avg, abs=0.01)
            assert gsf_row["avg_capped_score"] != pytest.approx(expected_avg * 2.0 / 3.0, abs=0.01)
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()

    def test_three_plants_average_to_arithmetic_mean(self):
        db = SessionLocal()
        record_ids: list = []
        try:
            foreman, plants = _pick_foreman_with_plants(db, min_count=3)
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            shift = db.scalar(select(Shift).limit(1))
            run_id = db.scalar(select(IntegrationRun.id).limit(1))

            combos = [(0.40, 0.34), (0.27, 0.33), (0.35, 0.35)]
            recs = [
                _make_gsf_record(foreman, plants[i], kpi, shift, run_id, _TEST_DATE, a, t)
                for i, (a, t) in enumerate(combos)
            ]
            db.add_all(recs)
            db.flush()
            record_ids = [r.id for r in recs]
            db.commit()

            filters = Filters(date_from=_TEST_DATE, date_to=_TEST_DATE)
            rows = analytics.foreman_kpi_breakdown(db, filters, foreman.id)
            gsf_row = next(r for r in rows if r["kpi_id"] == kpi.id)

            expected_scores = [score_gsf(a, t).capped_score for a, t in combos]
            expected_avg = sum(expected_scores) / 3.0

            assert gsf_row["evaluated_plant_count"] == 3
            assert gsf_row["avg_capped_score"] == pytest.approx(expected_avg, abs=0.01)
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()

    def test_api_response_matches_service_layer_and_db(self, client, auth_headers):
        db = SessionLocal()
        record_ids: list = []
        try:
            foreman, plants = _pick_foreman_with_plants(db, min_count=3)
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            shift = db.scalar(select(Shift).limit(1))
            run_id = db.scalar(select(IntegrationRun.id).limit(1))

            combos = [(0.70, 0.60), (0.90, 1.00), (0.80, 0.75)]
            recs = [
                _make_gsf_record(foreman, plants[i], kpi, shift, run_id, _TEST_DATE, a, t)
                for i, (a, t) in enumerate(combos)
            ]
            db.add_all(recs)
            db.flush()
            record_ids = [r.id for r in recs]
            db.commit()

            filters = Filters(date_from=_TEST_DATE, date_to=_TEST_DATE)
            service_rows = analytics.foreman_kpi_breakdown(db, filters, foreman.id)
            service_gsf = next(r for r in service_rows if r["kpi_id"] == kpi.id)

            resp = client.get(
                f"/api/v1/foremen/{foreman.id}/kpis",
                params={"date_from": _TEST_DATE.isoformat(), "date_to": _TEST_DATE.isoformat()},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            api_gsf = next(i for i in unwrap(resp) if i["code"] == "GSF")

            assert api_gsf["evaluatedPlantCount"] == service_gsf["evaluated_plant_count"] == 3
            assert api_gsf["avgCappedScore"] == pytest.approx(service_gsf["avg_capped_score"], abs=0.01)
            assert len(api_gsf["plants"]) == 3
            api_plants_by_id = {p["plantId"]: p for p in api_gsf["plants"]}
            for e in service_gsf["plants"]:
                api_p = api_plants_by_id[str(e["plant_id"])]
                assert api_p["score"] == pytest.approx(e["score"], abs=0.01)
                assert api_p["target"] == pytest.approx(e["target"], abs=0.01)
                assert api_p["weight"] == pytest.approx(1.0 / 3.0, abs=1e-6)

            expected_avg = sum(score_gsf(a, t).capped_score for a, t in combos) / 3.0
            assert api_gsf["avgCappedScore"] == pytest.approx(expected_avg, abs=0.01)
        finally:
            db.rollback()
            if record_ids:
                db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(record_ids)))
                db.commit()
            db.close()


class TestTargetResolutionFallbackObservability:

    def test_missing_plant_target_falls_back_to_company_and_logs_warning(self, caplog):
        db = SessionLocal()
        deactivated_target_id = None
        try:
            kpi = db.scalar(select(Kpi).where(Kpi.code == "GSF"))
            assignment = db.scalar(select(ForemanAssignment).where(ForemanAssignment.is_active.is_(True)).limit(1))
            plant = db.get(Plant, assignment.plant_id)
            chief = db.get(Chief, assignment.chief_id)
            foreman = db.get(Foreman, assignment.foreman_id)
            anchor_shift = db.get(Shift, assignment.shift_id)
            all_shifts = list(db.scalars(select(Shift)))
            shift = actual_shift_for_date(_TEST_DATE, anchor_shift, all_shifts)

            plant_target = db.scalar(
                select(KpiTarget).where(
                    KpiTarget.kpi_id == kpi.id, KpiTarget.scope_type == TargetScopeType.PLANT,
                    KpiTarget.scope_id == plant.id, KpiTarget.is_active.is_(True),
                )
            )
            assert plant_target is not None
            deactivated_target_id = plant_target.id
            plant_target.is_active = False
            db.commit()

            class _OneRecordProvider(PerformanceDataProvider):
                source_system = SourceSystem.SYNTHETIC

                def fetch(self, date_from, date_to, plant_codes=None):
                    yield RawPerformanceRecord(
                        source_record_id=f"TEST-FALLBACK-{uuid.uuid4().hex[:8]}",
                        performance_date=_TEST_DATE, plant_code=plant.code,
                        chief_employee_number=chief.employee_number, shift_code=shift.code,
                        foreman_employee_number=foreman.employee_number, kpi_code=kpi.code,
                        actual_value=0.5, unit="%", target_value=None,
                        numerator_value=0.5, denominator_value=100.0,
                        source_updated_at=None, production_record_id=None,
                    )

            with caplog.at_level(logging.WARNING, logger="app.services.ingestion"):
                run = run_ingestion(db, _OneRecordProvider(), _TEST_DATE, _TEST_DATE, plant_codes=[plant.code])

            assert run.success_count == 1
            record = db.scalar(
                select(PerformanceRecord).where(
                    PerformanceRecord.foreman_id == foreman.id, PerformanceRecord.plant_id == plant.id,
                    PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.performance_date == _TEST_DATE,
                )
            )
            assert record is not None
            assert record.data_quality_status == DataQualityStatus.COMPLETE
            company_target = db.scalar(
                select(KpiTarget).where(
                    KpiTarget.kpi_id == kpi.id, KpiTarget.scope_type == TargetScopeType.COMPANY, KpiTarget.is_active.is_(True)
                )
            )
            assert float(record.target_value) == float(company_target.target_value)
            assert any("PLANT seviyesinde hedef bulamadı" in m for m in caplog.messages)

            db.execute(PerformanceScore.__table__.delete().where(PerformanceScore.performance_record_id == record.id))
            db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id == record.id))
            db.commit()
        finally:
            if deactivated_target_id is not None:
                db.rollback()
                target = db.get(KpiTarget, deactivated_target_id)
                if target is not None:
                    target.is_active = True
                    db.commit()
            db.close()
