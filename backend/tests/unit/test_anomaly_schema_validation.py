import uuid
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import AnomalySeverity, AnomalyType
from app.schemas.anomaly import AnomalyCreate


def _base_payload(**overrides) -> dict:
    payload = dict(
        code="ANM-TEST-0001",
        title="Test Tespiti",
        description="Test açıklaması.",
        anomaly_type=AnomalyType.SINGLE_DAY_SPIKE,
        severity=AnomalySeverity.MEDIUM,
        detected_at=datetime.now(timezone.utc),
        plant_id=uuid.uuid4(),
        kpi_id=uuid.uuid4(),
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 10),
        observed_value=12.3,
        expected_value=5.0,
        unit="%",
        deviation_percent=146.0,
        ml_confidence=0.8,
    )
    payload.update(overrides)
    return payload


class TestMlConfidenceBounds:
    def test_lower_bound_zero_is_valid(self):
        assert AnomalyCreate(**_base_payload(ml_confidence=0)).ml_confidence == 0

    def test_upper_bound_one_is_valid(self):
        assert AnomalyCreate(**_base_payload(ml_confidence=1)).ml_confidence == 1

    def test_negative_confidence_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCreate(**_base_payload(ml_confidence=-0.01))

    def test_confidence_above_one_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCreate(**_base_payload(ml_confidence=1.01))


class TestAffectedDaysBounds:
    def test_affected_equal_total_is_valid(self):
        anomaly = AnomalyCreate(**_base_payload(affected_days=10, total_days=10))
        assert anomaly.affected_days == 10

    def test_affected_greater_than_total_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCreate(**_base_payload(affected_days=11, total_days=10))

    def test_negative_affected_days_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCreate(**_base_payload(affected_days=-1, total_days=10))

    def test_negative_total_days_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCreate(**_base_payload(affected_days=1, total_days=-1))

    def test_both_none_is_valid(self):
        anomaly = AnomalyCreate(**_base_payload(affected_days=None, total_days=None))
        assert anomaly.affected_days is None and anomaly.total_days is None


class TestPeriodRange:
    def test_reversed_period_rejected(self):
        with pytest.raises(ValidationError):
            AnomalyCreate(**_base_payload(period_start=date(2026, 8, 20), period_end=date(2026, 8, 10)))

    def test_equal_period_start_end_is_valid(self):
        anomaly = AnomalyCreate(**_base_payload(period_start=date(2026, 8, 10), period_end=date(2026, 8, 10)))
        assert anomaly.period_start == anomaly.period_end
