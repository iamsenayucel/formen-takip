from __future__ import annotations

from datetime import date
from typing import Protocol, TypeVar

from app.services.validity import is_effective


class RuleCandidate(Protocol):
    valid_from: date
    valid_to: date | None
    is_active: bool


T = TypeVar("T", bound=RuleCandidate)


class NoRuleFoundError(LookupError):
    pass


class AmbiguousRuleError(LookupError):
    pass


def resolve_rule(candidates: list[T], as_of: date) -> T:
    valid = [c for c in candidates if c.is_active and is_effective(c.valid_from, c.valid_to, as_of)]

    if not valid:
        raise NoRuleFoundError(f"{as_of} tarihi için geçerli bir scoring rule bulunamadı.")

    if len(valid) > 1:
        raise AmbiguousRuleError(
            f"{as_of} tarihi için birden fazla ({len(valid)}) geçerli scoring rule bulundu — "
            "KPI başına en fazla bir geçerli rule olmalı. Veri bütünlüğü ihlali."
        )

    return valid[0]
