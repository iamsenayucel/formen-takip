from dataclasses import dataclass
from datetime import date, datetime, time, timezone

from app.services.synthetic.production_generator import shift_window_utc


@dataclass
class _FakeShift:
    start_time: time
    end_time: time
    crosses_midnight: bool


V1 = _FakeShift(start_time=time(7, 0), end_time=time(19, 0), crosses_midnight=False)
V2 = _FakeShift(start_time=time(19, 0), end_time=time(7, 0), crosses_midnight=True)


class TestDayShiftWindow:
    def test_v1_07_00_to_19_00_local_converts_to_utc(self):
        start, end = shift_window_utc(date(2026, 8, 15), V1)
        assert start == datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 8, 15, 16, 0, tzinfo=timezone.utc)


class TestNightShiftWindow:
    def test_v2_19_00_crosses_midnight_into_next_local_day(self):
        start, end = shift_window_utc(date(2026, 8, 14), V2)
        assert start == datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)
        assert end == datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)

    def test_business_date_is_the_shift_start_day_not_the_utc_day(self):
        # Gece vardiyasının ikinci yarısı (yerel bitiş 07:00) UTC takviminde 15 Ağustos'a
        # denk gelse de iş/üretim tarihi 14 Ağustos'tur.
        start, end = shift_window_utc(date(2026, 8, 14), V2)
        assert start.date() == date(2026, 8, 14)
        assert end.date() == date(2026, 8, 15)
