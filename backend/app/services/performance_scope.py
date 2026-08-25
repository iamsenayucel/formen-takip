from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from uuid import UUID

from app.schemas.common import Filters


@dataclass(frozen=True)
class ForemanPerformanceScope:
    operational: Filters
    plant: Filters
    contribution_as_of: date


def resolve_foreman_scope(filters: Filters, primary_plant_id: UUID | None) -> ForemanPerformanceScope:
    plant_ids = filters.plant_ids or ([primary_plant_id] if primary_plant_id else None)
    return ForemanPerformanceScope(
        operational=filters,
        plant=replace(filters, plant_ids=plant_ids),
        contribution_as_of=filters.date_to,
    )


@dataclass(frozen=True)
class ChiefPerformanceScope:
    ranking: Filters


def resolve_chief_scope(filters: Filters) -> ChiefPerformanceScope:
    return ChiefPerformanceScope(ranking=replace(filters, chief_ids=None))
