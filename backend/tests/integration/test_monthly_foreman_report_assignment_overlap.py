import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import DataQualityStatus, SourceSystem
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import IntegrationRun
from app.models.kpi import Kpi
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.services.monthly_foreman_report import _build_report_data

_YEAR, _MONTH = 2099, 8


def _make_plant(db, chief, suffix):
    plant = Plant(
        id=uuid.uuid4(), code=f"TESTMFR-{uuid.uuid4().hex[:6]}", name=f"Test Tesis {suffix}",
        sequence_number=500_000 + (uuid.uuid4().int % 400_000),
        factory_id=chief.plants[0].factory_id, chief_id=chief.id, is_active=True,
    )
    db.add(plant)
    db.flush()
    return plant


def _make_foreman(db, suffix):
    foreman = Foreman(
        id=uuid.uuid4(), employee_number=f"TEST-MFR-{uuid.uuid4().hex[:8]}",
        first_name="Test", last_name=f"Formen{suffix}", hire_date=date(2020, 1, 1), is_active=True,
    )
    db.add(foreman)
    db.flush()
    return foreman


def _make_assignment(foreman, plant, chief, shift, start_date, end_date=None):
    return ForemanAssignment(
        id=uuid.uuid4(), foreman_id=foreman.id, plant_id=plant.id, chief_id=chief.id, shift_id=shift.id,
        start_date=start_date, end_date=end_date, is_active=end_date is None,
    )


def _fill_all_active_kpis(db, foreman, plant, chief, shift, run_id, on_date, kpis):
    now = datetime.now(timezone.utc)
    records = [
        PerformanceRecord(
            id=uuid.uuid4(), source_system=SourceSystem.SYNTHETIC, source_record_id=f"TEST-MFR-{uuid.uuid4().hex[:10]}",
            integration_run_id=run_id, performance_date=on_date,
            plant_id=plant.id, chief_id=chief.id, shift_id=shift.id, foreman_id=foreman.id, kpi_id=kpi.id,
            target_value=100.0, actual_value=95.0, numerator_value=95.0, denominator_value=100.0, unit=kpi.unit,
            data_quality_status=DataQualityStatus.COMPLETE, source_updated_at=now, imported_at=now,
        )
        for kpi in kpis
    ]
    db.add_all(records)
    db.flush()
    return records


class _Scenario:
    def __init__(self):
        self.db = SessionLocal()
        self.plant_ids: list = []
        self.foreman_id = None
        self.record_ids: list = []

    def __enter__(self):
        self.chief = self.db.scalar(select(Chief).limit(1))
        self.shift = self.db.scalar(select(Shift).limit(1))
        self.run_id = self.db.scalar(select(IntegrationRun.id).limit(1))
        self.kpis = list(self.db.scalars(select(Kpi).where(Kpi.is_active.is_(True))))
        self.foreman = _make_foreman(self.db, uuid.uuid4().hex[:6])
        self.foreman_id = self.foreman.id
        return self

    def plant(self, suffix="A"):
        plant = _make_plant(self.db, self.chief, suffix)
        self.plant_ids.append(plant.id)
        return plant

    def assign(self, plant, start_date, end_date=None):
        assignment = _make_assignment(self.foreman, plant, self.chief, self.shift, start_date, end_date)
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def add_sufficient_performance(self, plant, on_date):
        records = _fill_all_active_kpis(self.db, self.foreman, plant, self.chief, self.shift, self.run_id, on_date, self.kpis)
        self.record_ids.extend(r.id for r in records)

    def build_report(self, year=_YEAR, month=_MONTH):
        self.db.commit()
        return _build_report_data(self.db, self.foreman, year, month)

    def __exit__(self, exc_type, exc, tb):
        self.db.rollback()
        if self.record_ids:
            self.db.execute(PerformanceRecord.__table__.delete().where(PerformanceRecord.id.in_(self.record_ids)))
        self.db.execute(ForemanAssignment.__table__.delete().where(ForemanAssignment.foreman_id == self.foreman_id))
        if self.plant_ids:
            self.db.execute(Plant.__table__.delete().where(Plant.id.in_(self.plant_ids)))
        self.db.execute(Foreman.__table__.delete().where(Foreman.id == self.foreman_id))
        self.db.commit()
        self.db.close()


class TestAssignmentReportPeriodOverlap:

    def test_a_full_month_active_assignment(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 8, 1))
            s.add_sufficient_performance(plant, date(_YEAR, 8, 15))
            data = s.build_report()

            assert data["insufficient_data"] is False
            assert data["organization_history"][0]["date_from"] == "2099-08-01"
            assert data["organization_history"][0]["date_to"] == "2099-08-31"

    def test_b_assignment_ends_before_month_end_with_sufficient_data(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 8, 1), date(_YEAR, 8, 25))
            s.add_sufficient_performance(plant, date(_YEAR, 8, 10))
            data = s.build_report()

            assert data["insufficient_data"] is False, (
                "assignment.end_date < month_end should not, by itself, mark the report insufficient_data"
            )
            assert data["overall"] is not None
            assert data["organization_history"][0]["date_to"] == "2099-08-25"

    def test_c_assignment_starts_mid_month(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 8, 15))
            s.add_sufficient_performance(plant, date(_YEAR, 8, 20))
            data = s.build_report()

            assert data["insufficient_data"] is False
            assert data["organization_history"][0]["date_from"] == "2099-08-15"
            assert data["organization_history"][0]["date_to"] == "2099-08-31"

    def test_d_assignment_spans_previous_month_into_this_one(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 7, 10), date(_YEAR, 8, 10))
            s.add_sufficient_performance(plant, date(_YEAR, 8, 5))
            data = s.build_report()

            assert data["insufficient_data"] is False
            assert data["organization_history"][0]["date_from"] == "2099-08-01"
            assert data["organization_history"][0]["date_to"] == "2099-08-10"

    def test_e_assignment_does_not_overlap_report_period(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 7, 1), date(_YEAR, 7, 31))
            data = s.build_report()

            assert data["insufficient_data"] is True
            assert data["org"] is None
            assert data["organization_history"] == []

    def test_f_two_assignments_within_the_month(self):
        with _Scenario() as s:
            plant_a = s.plant("A")
            plant_b = s.plant("B")
            s.assign(plant_a, date(_YEAR, 8, 1), date(_YEAR, 8, 15))
            s.assign(plant_b, date(_YEAR, 8, 16))
            s.add_sufficient_performance(plant_a, date(_YEAR, 8, 5))
            data = s.build_report()

            assert data["insufficient_data"] is False
            history = data["organization_history"]
            assert len(history) == 2
            assert history[0]["date_from"] == "2099-08-01"
            assert history[0]["date_to"] == "2099-08-15"
            assert history[1]["date_from"] == "2099-08-16"
            assert history[1]["date_to"] == "2099-08-31"
            assert history[0]["plants"][0]["name"] != history[1]["plants"][0]["name"]
            assert data["org"] == history[-1]

    def test_g_open_ended_assignment_from_before_the_month(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 7, 10))
            s.add_sufficient_performance(plant, date(_YEAR, 8, 1))
            data = s.build_report()

            assert data["insufficient_data"] is False
            assert data["organization_history"][0]["date_from"] == "2099-08-01"
            assert data["organization_history"][0]["date_to"] == "2099-08-31"

    def test_h_assignment_exists_but_performance_data_is_insufficient(self):
        with _Scenario() as s:
            plant = s.plant()
            s.assign(plant, date(_YEAR, 8, 1))
            data = s.build_report()

            assert data["insufficient_data"] is True
            assert data["org"] is not None, "assignment is real; only performance coverage is insufficient"
            assert data["overall"] is None
