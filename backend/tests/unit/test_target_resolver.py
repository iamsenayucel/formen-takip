from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

import pytest

from app.models.enums import TargetScopeType
from app.services.target_resolver import AmbiguousTargetError, NoTargetFoundError, resolve_target


@dataclass
class FakeTarget:
    scope_type: TargetScopeType
    scope_id: UUID | None
    target_value: float
    valid_from: date
    valid_to: date | None
    is_active: bool = True


FOREMAN_ID = uuid4()
CHIEF_ID = uuid4()
PLANT_ID = uuid4()
AS_OF = date(2026, 3, 1)


def resolve(candidates):
    return resolve_target(candidates, AS_OF, FOREMAN_ID, CHIEF_ID, PLANT_ID)


class TestTargetResolutionOrder:
    def test_foreman_specific_wins_over_everything(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.PLANT, PLANT_ID, 110, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.FOREMAN, FOREMAN_ID, 130, date(2025, 1, 1), None),
        ]
        result = resolve(candidates)
        assert result.target_value == 130
        assert result.resolved_scope == TargetScopeType.FOREMAN

    def test_falls_back_to_chief_when_no_foreman_target(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.CHIEF, CHIEF_ID, 120, date(2025, 1, 1), None),
        ]
        result = resolve(candidates)
        assert result.target_value == 120
        assert result.resolved_scope == TargetScopeType.CHIEF

    def test_falls_back_through_chief_to_plant(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.PLANT, PLANT_ID, 105, date(2025, 1, 1), None),
        ]
        assert resolve(candidates).resolved_scope == TargetScopeType.PLANT

    def test_ignores_target_for_other_foreman(self):
        other_foreman = uuid4()
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.FOREMAN, other_foreman, 999, date(2025, 1, 1), None),
        ]
        result = resolve(candidates)
        assert result.target_value == 100
        assert result.resolved_scope == TargetScopeType.COMPANY

    def test_ignores_expired_target(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.FOREMAN, FOREMAN_ID, 999, date(2024, 1, 1), date(2025, 6, 1)),
        ]
        result = resolve(candidates)
        assert result.target_value == 100

    def test_ignores_inactive_target(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.FOREMAN, FOREMAN_ID, 999, date(2025, 1, 1), None, is_active=False),
        ]
        result = resolve(candidates)
        assert result.target_value == 100

    def test_no_target_raises(self):
        with pytest.raises(NoTargetFoundError):
            resolve([])


class TestAmbiguousTargetDetection:
    def test_two_overlapping_active_targets_same_scope_raises(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.PLANT, PLANT_ID, 105, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.PLANT, PLANT_ID, 999, date(2025, 6, 1), None),
        ]
        with pytest.raises(AmbiguousTargetError):
            resolve(candidates)

    def test_ambiguity_is_detected_regardless_of_candidate_order(self):
        candidates = [
            FakeTarget(TargetScopeType.FOREMAN, FOREMAN_ID, 999, date(2025, 6, 1), None),
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.FOREMAN, FOREMAN_ID, 130, date(2025, 1, 1), None),
        ]
        with pytest.raises(AmbiguousTargetError):
            resolve(candidates)
        with pytest.raises(AmbiguousTargetError):
            resolve(list(reversed(candidates)))

    def test_non_overlapping_sequential_targets_are_not_ambiguous(self):
        candidates = [
            FakeTarget(TargetScopeType.COMPANY, None, 100, date(2025, 1, 1), None),
            FakeTarget(TargetScopeType.PLANT, PLANT_ID, 105, date(2025, 1, 1), date(2026, 2, 28)),
            FakeTarget(TargetScopeType.PLANT, PLANT_ID, 115, date(2026, 3, 1), None),
        ]
        result = resolve(candidates)
        assert result.target_value == 115
