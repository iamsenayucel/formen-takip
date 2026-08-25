from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.synthetic.production_generator import _assign_shift_working_time

V1_ID, V2_ID = uuid4(), uuid4()


def _record(plant_id, production_date, shift_id, **overrides):
    base = dict(
        plant_id=plant_id, production_date=production_date, shift_id=shift_id,
        planned_start_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        planned_end_at=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        technical_downtime_minutes=0.0, manufacturing_downtime_minutes=0.0, other_downtime_minutes=0.0,
        working_time_minutes=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestDirectFormula:
    def test_working_time_is_720_minus_shift_downtime(self):
        plant = uuid4()
        d = date(2026, 1, 1)
        record = _record(
            plant, d, V1_ID, technical_downtime_minutes=30.0, manufacturing_downtime_minutes=20.0, other_downtime_minutes=10.0,
        )
        _assign_shift_working_time([record])
        assert record.working_time_minutes == 660.0

    def test_zero_downtime_gives_full_shift(self):
        record = _record(uuid4(), date(2026, 1, 1), V1_ID)
        _assign_shift_working_time([record])
        assert record.working_time_minutes == 720.0

    def test_full_shift_downtime_gives_zero_working_time(self):
        record = _record(uuid4(), date(2026, 1, 1), V1_ID, technical_downtime_minutes=720.0)
        _assign_shift_working_time([record])
        assert record.working_time_minutes == 0.0

    def test_downtime_beyond_a_full_shift_clamps_to_zero_not_negative(self):
        record = _record(
            uuid4(), date(2026, 1, 1), V1_ID,
            technical_downtime_minutes=500.0, manufacturing_downtime_minutes=300.0, other_downtime_minutes=100.0,
        )
        _assign_shift_working_time([record])
        assert record.working_time_minutes == 0.0


class TestRangeGuarantee:
    def test_all_values_within_0_and_720(self):
        plant = uuid4()
        records = [
            _record(plant, date(2026, 1, 1) + timedelta(days=i), V1_ID, technical_downtime_minutes=i * 15.0)
            for i in range(60)
        ]
        _assign_shift_working_time(records)
        for r in records:
            assert 0.0 <= r.working_time_minutes <= 720.0


class TestEachShiftIndependent:
    def test_v1_and_v2_each_get_their_own_value_from_their_own_downtime(self):
        plant = uuid4()
        d = date(2026, 1, 1)
        v1 = _record(plant, d, V1_ID, technical_downtime_minutes=60.0)
        v2 = _record(plant, d, V2_ID, technical_downtime_minutes=180.0)
        _assign_shift_working_time([v1, v2])
        assert v1.working_time_minutes == 660.0
        assert v2.working_time_minutes == 540.0

    def test_a_shifts_downtime_never_leaks_into_the_other_shifts_value(self):
        plant = uuid4()
        d = date(2026, 1, 1)
        v1 = _record(plant, d, V1_ID, technical_downtime_minutes=0.0)
        v2 = _record(plant, d, V2_ID, technical_downtime_minutes=300.0)
        _assign_shift_working_time([v1, v2])
        assert v1.working_time_minutes == 720.0
        assert v2.working_time_minutes == 420.0


class TestNoDateParityAttribution:
    def test_both_even_and_odd_days_assign_both_shifts_independently(self):
        plant = uuid4()
        for offset in range(4):
            d = date(2026, 1, 1) + timedelta(days=offset)
            v1 = _record(plant, d, V1_ID, technical_downtime_minutes=10.0)
            v2 = _record(plant, d, V2_ID, technical_downtime_minutes=20.0)
            _assign_shift_working_time([v1, v2])
            assert v1.working_time_minutes == 710.0
            assert v2.working_time_minutes == 700.0

    def test_single_shift_present_still_gets_assigned_without_needing_the_other(self):
        record = _record(uuid4(), date(2026, 1, 1), V2_ID, technical_downtime_minutes=10.0)
        _assign_shift_working_time([record])
        assert record.working_time_minutes == 710.0


class TestMissingWhenNoShiftWindow:
    def test_no_planned_window_leaves_working_time_none(self):
        record = _record(uuid4(), date(2026, 1, 1), V1_ID, planned_start_at=None, planned_end_at=None)
        _assign_shift_working_time([record])
        assert record.working_time_minutes is None


class TestDeterminism:
    def test_same_input_gives_identical_results(self):
        plant = uuid4()
        d = date(2026, 1, 1)
        record_a = _record(plant, d, V1_ID, technical_downtime_minutes=42.5, manufacturing_downtime_minutes=13.0)
        record_b = _record(plant, d, V1_ID, technical_downtime_minutes=42.5, manufacturing_downtime_minutes=13.0)
        _assign_shift_working_time([record_a])
        _assign_shift_working_time([record_b])
        assert record_a.working_time_minutes == record_b.working_time_minutes == 720.0 - 42.5 - 13.0
