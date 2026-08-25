from dataclasses import dataclass
from datetime import date

import pytest

from app.services.rule_resolver import AmbiguousRuleError, NoRuleFoundError, resolve_rule


@dataclass
class FakeRule:
    version: int
    valid_from: date
    valid_to: date | None
    is_active: bool = True


AS_OF = date(2026, 3, 1)


class TestRuleResolution:
    def test_single_open_ended_rule_matches(self):
        rule = resolve_rule([FakeRule(1, date(2020, 1, 1), None)], AS_OF)
        assert rule.version == 1

    def test_ignores_expired_rule(self):
        candidates = [
            FakeRule(1, date(2020, 1, 1), date(2025, 12, 31)),
            FakeRule(2, date(2026, 1, 1), None),
        ]
        rule = resolve_rule(candidates, AS_OF)
        assert rule.version == 2

    def test_ignores_future_rule(self):
        with pytest.raises(NoRuleFoundError):
            resolve_rule([FakeRule(1, date(2026, 6, 1), None)], AS_OF)

    def test_ignores_inactive_rule(self):
        candidates = [
            FakeRule(1, date(2020, 1, 1), None, is_active=False),
        ]
        with pytest.raises(NoRuleFoundError):
            resolve_rule(candidates, AS_OF)

    def test_no_rule_raises(self):
        with pytest.raises(NoRuleFoundError):
            resolve_rule([], AS_OF)

    def test_boundary_dates_are_inclusive(self):
        candidates = [FakeRule(1, date(2026, 1, 1), date(2026, 3, 1))]
        rule = resolve_rule(candidates, date(2026, 3, 1))
        assert rule.version == 1
        with pytest.raises(NoRuleFoundError):
            resolve_rule(candidates, date(2026, 3, 2))


class TestAmbiguousRuleDetection:
    def test_two_overlapping_active_rules_raise(self):
        candidates = [
            FakeRule(1, date(2020, 1, 1), None),
            FakeRule(2, date(2025, 6, 1), None),
        ]
        with pytest.raises(AmbiguousRuleError):
            resolve_rule(candidates, AS_OF)

    def test_ambiguity_detected_regardless_of_order(self):
        candidates = [
            FakeRule(2, date(2025, 6, 1), None),
            FakeRule(1, date(2020, 1, 1), None),
        ]
        with pytest.raises(AmbiguousRuleError):
            resolve_rule(candidates, AS_OF)
        with pytest.raises(AmbiguousRuleError):
            resolve_rule(list(reversed(candidates)), AS_OF)

    def test_non_overlapping_sequential_rules_are_not_ambiguous(self):
        candidates = [
            FakeRule(1, date(2020, 1, 1), date(2025, 12, 31)),
            FakeRule(2, date(2026, 1, 1), None),
        ]
        rule = resolve_rule(candidates, AS_OF)
        assert rule.version == 2
