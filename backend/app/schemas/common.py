from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from fastapi import Query

from app.core import clock


@dataclass
class Filters:
    date_from: date
    date_to: date
    plant_ids: list[UUID] | None = None
    factory_ids: list[UUID] | None = None
    chief_ids: list[UUID] | None = None
    shift_ids: list[UUID] | None = None
    kpi_ids: list[UUID] | None = None
    foreman_ids: list[UUID] | None = None


def parse_uuid_list(value: str | None) -> list[UUID] | None:
    if not value:
        return None
    return [UUID(v) for v in value.split(",") if v.strip()]


def common_filters(
    date_from: date | None = Query(None, description="Başlangıç tarihi (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Bitiş tarihi (YYYY-MM-DD)"),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    chief_ids: str | None = Query(None, description="Virgülle ayrılmış şef ID listesi"),
    shift_ids: str | None = Query(None, description="Virgülle ayrılmış vardiya ID listesi"),
    kpi_ids: str | None = Query(None, description="Virgülle ayrılmış KPI ID listesi"),
    foreman_ids: str | None = Query(None, description="Virgülle ayrılmış formen ID listesi"),
) -> Filters:
    resolved_to = date_to or clock.today_local()
    resolved_from = date_from or (resolved_to - timedelta(days=30))
    if resolved_from > resolved_to:
        resolved_from, resolved_to = resolved_to, resolved_from
    return Filters(
        date_from=resolved_from,
        date_to=resolved_to,
        plant_ids=parse_uuid_list(plant_ids),
        factory_ids=parse_uuid_list(factory_ids),
        chief_ids=parse_uuid_list(chief_ids),
        shift_ids=parse_uuid_list(shift_ids),
        kpi_ids=parse_uuid_list(kpi_ids),
        foreman_ids=parse_uuid_list(foreman_ids),
    )


@dataclass
class CursorParams:
    cursor: str | None = None
    limit: int = 25


def cursor_params(
    cursor: str | None = Query(None),
    limit: int = Query(25, ge=1, le=200),
) -> CursorParams:
    return CursorParams(cursor=cursor, limit=limit)
