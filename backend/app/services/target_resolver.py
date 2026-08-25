
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from app.models.enums import TargetScopeType
from app.services.validity import is_effective

SCOPE_PRIORITY: list[TargetScopeType] = [
    TargetScopeType.FOREMAN,
    TargetScopeType.CHIEF,
    TargetScopeType.PLANT,
    TargetScopeType.COMPANY,
]


class TargetCandidate(Protocol):
    scope_type: TargetScopeType
    scope_id: UUID | None
    target_value: float
    valid_from: date
    valid_to: date | None
    is_active: bool


@dataclass
class ResolvedTarget:
    target_value: float
    resolved_scope: TargetScopeType


class NoTargetFoundError(LookupError):
    pass


class AmbiguousTargetError(LookupError):
    pass


def resolve_target(
    candidates: list[TargetCandidate],
    as_of: date,
    foreman_id: UUID,
    chief_id: UUID,
    plant_id: UUID,
) -> ResolvedTarget:
    scope_ids: dict[TargetScopeType, UUID | None] = {
        TargetScopeType.FOREMAN: foreman_id,
        TargetScopeType.CHIEF: chief_id,
        TargetScopeType.PLANT: plant_id,
        TargetScopeType.COMPANY: None,
    }

    valid = [c for c in candidates if c.is_active and is_effective(c.valid_from, c.valid_to, as_of)]

    for scope in SCOPE_PRIORITY:
        expected_id = scope_ids[scope]
        matches = [
            c
            for c in valid
            if c.scope_type == scope and (scope == TargetScopeType.COMPANY or c.scope_id == expected_id)
        ]
        if not matches:
            continue
        if len(matches) > 1:
            raise AmbiguousTargetError(
                f"{as_of} tarihi için {scope.value} kapsamında birden fazla ({len(matches)}) geçerli hedef "
                "bulundu — kpi ve scope başına en fazla bir geçerli hedef olmalı. Veri bütünlüğü ihlali, "
                f"aday hedef değerleri: {[c.target_value for c in matches]}."
            )
        return ResolvedTarget(target_value=matches[0].target_value, resolved_scope=scope)

    raise NoTargetFoundError("Hiçbir seviyede geçerli hedef bulunamadı.")
