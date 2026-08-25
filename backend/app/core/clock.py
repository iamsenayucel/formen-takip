"""Merkezi iş saat dilimi/UTC clock sözleşmesi.

İş tarihleri, vardiyalar ve rapor dönemleri `settings.timezone` ile çözülür;
kalıcı timestamp'ler UTC tutulur. "Şimdi" gereken her yerde `now_utc()` kullanılır,
böylece testler tek fonksiyonu monkeypatch ederek zamanı sabitleyebilir.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def business_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    return now_utc().astimezone(business_tz())


def today_local() -> date:
    return now_local().date()


def to_utc(dt: datetime) -> datetime:
    """datetime değerini UTC'ye çevirir. Naive `dt`, yerel iş saatini temsil eder."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=business_tz())
    return dt.astimezone(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """datetime değerini yerel iş saatine çevirir. Naive `dt`, UTC kabul edilir."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(business_tz())


def local_datetime(d: date, t: time = time.min) -> datetime:
    """İş tarihi `d` ve saat `t` için timezone-aware yerel datetime üretir."""
    return datetime.combine(d, t, tzinfo=business_tz())


def local_day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    """İş tarihi `d` için yarı açık [start, end) UTC aralığını döndürür."""
    start_local = local_datetime(d)
    end_local = local_datetime(d + timedelta(days=1))
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def local_period_bounds_utc(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Dahilî [start_date, end_date] iş tarihlerini kapsayan yarı açık
    [start, end) UTC aralığını döndürür."""
    start_utc, _ = local_day_bounds_utc(start_date)
    _, end_utc = local_day_bounds_utc(end_date)
    return start_utc, end_utc
