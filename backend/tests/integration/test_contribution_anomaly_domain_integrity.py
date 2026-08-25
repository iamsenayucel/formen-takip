"""Pydantic doğrulayıcılarını tamamlayan CheckConstraint'lerin DB seviyesi testleri.

API/Pydantic katmanı atlanıp ORM üzerinden yazılan geçersiz verinin DB tarafından
reddedildiğini doğrular.
"""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.anomaly import Anomaly
from app.models.contribution import ContributionWork
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType
from app.models.kpi import Kpi
from app.models.organization import Plant

TEST_SUBJECT = "test-domain-integrity-subject"


def _work(**overrides) -> ContributionWork:
    fields = dict(title="Constraint testi", created_by_subject=TEST_SUBJECT)
    fields.update(overrides)
    return ContributionWork(**fields)


class TestContributionWorkNonNegativeConstraints:
    @pytest.mark.parametrize(
        "field",
        ["gain_amount", "previous_duration", "new_duration", "per_occurrence_saving", "repeat_count", "monthly_total_saving_minutes"],
    )
    def test_negative_value_rejected_at_db_level(self, field):
        db = SessionLocal()
        try:
            db.add(_work(**{field: -1}))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_zero_value_accepted_at_db_level(self):
        db = SessionLocal()
        try:
            work = _work(gain_amount=0, previous_duration=0)
            db.add(work)
            db.commit()
            work_id = work.id
        finally:
            db.rollback()
            db.close()
        cleanup = SessionLocal()
        try:
            cleanup.execute(ContributionWork.__table__.delete().where(ContributionWork.id == work_id))
            cleanup.commit()
        finally:
            cleanup.close()


class TestContributionWorkDateRangeConstraint:
    def test_end_before_start_rejected_at_db_level(self):
        db = SessionLocal()
        try:
            db.add(_work(work_date=date(2026, 8, 15), work_date_end=date(2026, 8, 14)))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_equal_dates_accepted_at_db_level(self):
        db = SessionLocal()
        try:
            work = _work(work_date=date(2026, 8, 14), work_date_end=date(2026, 8, 14))
            db.add(work)
            db.commit()
            work_id = work.id
        finally:
            db.rollback()
            db.close()
        cleanup = SessionLocal()
        try:
            cleanup.execute(ContributionWork.__table__.delete().where(ContributionWork.id == work_id))
            cleanup.commit()
        finally:
            cleanup.close()


def _reference_plant_and_kpi(db):
    plant = db.scalars(select(Plant).order_by(Plant.sequence_number)).first()
    kpi = db.scalars(select(Kpi)).first()
    assert plant is not None and kpi is not None, "Testler için önce 'python -m app.cli seed' çalıştırılmalı."
    return plant, kpi


def _anomaly(plant_id, kpi_id, **overrides) -> Anomaly:
    fields = dict(
        code=f"ANM-CONSTRAINT-TEST-{uuid.uuid4().hex[:10]}",
        title="Constraint testi",
        description="Constraint testi açıklaması.",
        anomaly_type=AnomalyType.SINGLE_DAY_SPIKE,
        severity=AnomalySeverity.MEDIUM,
        status=AnomalyStatus.NEW,
        analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED,
        detected_at=datetime.now(timezone.utc),
        plant_id=plant_id,
        shift_id=None,
        kpi_id=kpi_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 10),
        observed_value=1.0,
        expected_value=1.0,
        unit="%",
        deviation_percent=0.0,
        ml_confidence=0.5,
        comparison={},
        related_signals=[],
        evidence=[],
        foreman_ids=[],
    )
    fields.update(overrides)
    return Anomaly(**fields)


class TestAnomalyConfidenceRangeConstraint:
    def test_confidence_above_one_rejected_at_db_level(self):
        db = SessionLocal()
        try:
            plant, kpi = _reference_plant_and_kpi(db)
            db.add(_anomaly(plant.id, kpi.id, ml_confidence=1.35))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_negative_confidence_rejected_at_db_level(self):
        db = SessionLocal()
        try:
            plant, kpi = _reference_plant_and_kpi(db)
            db.add(_anomaly(plant.id, kpi.id, ml_confidence=-0.1))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestAnomalyDayCountConstraints:
    def test_affected_days_greater_than_total_days_rejected_at_db_level(self):
        db = SessionLocal()
        try:
            plant, kpi = _reference_plant_and_kpi(db)
            db.add(_anomaly(plant.id, kpi.id, affected_days=15, total_days=10))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_negative_affected_days_rejected_at_db_level(self):
        db = SessionLocal()
        try:
            plant, kpi = _reference_plant_and_kpi(db)
            db.add(_anomaly(plant.id, kpi.id, affected_days=-1, total_days=10))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_affected_days_equal_total_days_accepted_at_db_level(self):
        db = SessionLocal()
        try:
            plant, kpi = _reference_plant_and_kpi(db)
            anomaly = _anomaly(plant.id, kpi.id, affected_days=10, total_days=10)
            db.add(anomaly)
            db.commit()
            anomaly_id = anomaly.id
        finally:
            db.rollback()
            db.close()
        cleanup = SessionLocal()
        try:
            cleanup.execute(Anomaly.__table__.delete().where(Anomaly.id == anomaly_id))
            cleanup.commit()
        finally:
            cleanup.close()


class TestAnomalyPeriodRangeConstraint:
    def test_reversed_period_rejected_at_db_level(self):
        db = SessionLocal()
        try:
            plant, kpi = _reference_plant_and_kpi(db)
            db.add(_anomaly(plant.id, kpi.id, period_start=date(2026, 8, 20), period_end=date(2026, 8, 10)))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()
