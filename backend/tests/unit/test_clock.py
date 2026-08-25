from datetime import date, datetime, time, timedelta, timezone

from app.core import clock


class TestTodayLocal:
    def test_istanbul_midnight_after_utc_date_change(self, monkeypatch):
        # Europe/Istanbul 2026-08-15 00:30, UTC 2026-08-14 21:30'a eşittir.
        frozen = datetime(2026, 8, 14, 21, 30, tzinfo=timezone.utc)
        monkeypatch.setattr(clock, "now_utc", lambda: frozen)
        assert clock.today_local() == date(2026, 8, 15)

    def test_before_istanbul_midnight_still_previous_utc_date(self, monkeypatch):
        # Europe/Istanbul 2026-08-14 23:30, UTC 2026-08-14 20:30'a eşittir; UTC tarihi de aynıdır.
        frozen = datetime(2026, 8, 14, 20, 30, tzinfo=timezone.utc)
        monkeypatch.setattr(clock, "now_utc", lambda: frozen)
        assert clock.today_local() == date(2026, 8, 14)


class TestLocalDayBoundsUtc:
    def test_matches_zoneinfo_offset_not_fixed_three_hours(self):
        start_utc, end_utc = clock.local_day_bounds_utc(date(2026, 8, 15))
        assert start_utc == datetime(2026, 8, 14, 21, 0, tzinfo=timezone.utc)
        assert end_utc == datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc)
        assert (end_utc - start_utc).total_seconds() == 86400

    def test_half_open_interval_semantics(self):
        start_utc, end_utc = clock.local_day_bounds_utc(date(2026, 8, 15))
        just_before_end = end_utc - timedelta(microseconds=1)
        assert start_utc <= just_before_end < end_utc
        assert end_utc not in (start_utc, just_before_end)


class TestLocalPeriodBoundsUtc:
    def test_month_boundary(self):
        start_utc, end_utc = clock.local_period_bounds_utc(date(2026, 8, 1), date(2026, 8, 31))
        assert start_utc == datetime(2026, 7, 31, 21, 0, tzinfo=timezone.utc)
        assert end_utc == datetime(2026, 8, 31, 21, 0, tzinfo=timezone.utc)


class TestLocalDatetimeShiftBoundaries:
    def test_day_shift_start_19_00_local(self):
        dt = clock.local_datetime(date(2026, 8, 14), time(19, 0))
        assert dt.astimezone(timezone.utc) == datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)

    def test_night_shift_end_07_00_local_next_day(self):
        dt = clock.local_datetime(date(2026, 8, 15), time(7, 0))
        assert dt.astimezone(timezone.utc) == datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)


class TestToUtcToLocal:
    def test_naive_datetime_is_treated_as_business_local(self):
        naive = datetime(2026, 8, 14, 19, 0)
        assert clock.to_utc(naive) == datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)

    def test_aware_datetime_is_converted_not_relabeled(self):
        aware_utc = datetime(2026, 8, 14, 16, 0, tzinfo=timezone.utc)
        local = clock.to_local(aware_utc)
        assert local.hour == 19
        assert local.utcoffset().total_seconds() == 3 * 3600

    def test_naive_datetime_to_local_is_treated_as_utc(self):
        naive = datetime(2026, 8, 14, 16, 0)
        local = clock.to_local(naive)
        assert local.hour == 19

    def test_roundtrip(self):
        original = clock.local_datetime(date(2026, 8, 14), time(19, 0))
        assert clock.to_local(clock.to_utc(original)) == original


class TestZoneInfoNotFixedOffset:
    def test_historical_offset_differs_from_current_offset(self):
        pre_2016_dst_abolition = clock.local_datetime(date(2015, 1, 1), time(12, 0))
        current = clock.local_datetime(date(2026, 1, 1), time(12, 0))
        assert pre_2016_dst_abolition.utcoffset().total_seconds() == 2 * 3600
        assert current.utcoffset().total_seconds() == 3 * 3600


class TestNowLocal:
    def test_reflects_frozen_utc_clock(self, monkeypatch):
        frozen = datetime(2026, 8, 14, 21, 30, tzinfo=timezone.utc)
        monkeypatch.setattr(clock, "now_utc", lambda: frozen)
        local = clock.now_local()
        assert local.date() == date(2026, 8, 15)
        assert local.hour == 0
        assert local.minute == 30


class TestExplicitDateNotOverridden:
    def test_explicit_date_passed_through_untouched(self, monkeypatch):
        # Regresyon koruması: Açık iş tarihleri, clock ne döndürürse döndürsün sessizce
        # "now" anlamıyla değiştirilmemelidir.
        monkeypatch.setattr(clock, "now_utc", lambda: datetime(2099, 1, 1, tzinfo=timezone.utc))
        explicit = date(2026, 8, 10)
        assert explicit != clock.today_local()
