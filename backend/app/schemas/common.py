from dataclasses import dataclass, replace
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


def narrow_ids(requested: list[UUID] | None, scope: frozenset[UUID] | None) -> list[UUID] | None:
    """Bir istenen id listesini authorization scope'u ile kesiştirir.

    `scope=None` -> kısıtlama yok (ALL), `requested` aynen döner.
    `requested=None` -> kullanıcı filtre vermemiş, scope'un tamamı varsayılan olur.
    İkisi de doluysa kesişim döner ve bu **boş liste olabilir** (istenen id'lerin hiçbiri
    scope içinde değil) — bu, "filtre yok" ile karıştırılmamalıdır; tüketen taraflar
    (ör. analytics._apply_filters) `is not None` kontrolü yapmalı, truthiness değil.
    """
    if scope is None:
        return requested
    if requested is None:
        return sorted(scope, key=str)
    return [v for v in requested if v in scope]


def narrow_filters(filters: Filters, plant_ids_scope: frozenset[UUID] | None) -> Filters:
    """`Filters`'ı authorization scope'una göre daraltır. Scope kısıtlıysa (PLANT/FACTORY
    kaynaklı, genişletilmiş plant_ids seti) `factory_ids` bilinçli olarak yok sayılır —
    tek doğruluk ekseni `plant_ids`'tir, aksi halde iki eksen arasında tutarsızlık/bypass
    riski oluşur (bkz. app/api/authz_deps.py::_expand_plant_ids)."""
    if plant_ids_scope is None:
        return filters
    return replace(
        filters,
        plant_ids=narrow_ids(filters.plant_ids, plant_ids_scope),
        factory_ids=None,
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
