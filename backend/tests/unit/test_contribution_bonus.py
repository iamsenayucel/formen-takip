import pytest

from app.services.contribution_bonus import (
    CONTRIBUTION_BONUS_WINDOW_DAYS,
    MAX_GENERAL_SCORE,
    general_performance_score,
)


class TestGeneralPerformanceScore:
    def test_spec_example_one(self):
        assert general_performance_score(90, 5 + 5 + 5) == 105

    def test_spec_example_two(self):
        assert general_performance_score(82, 4 + 5 + 3 + 2) == 96

    def test_no_contributions_leaves_operational_score_unchanged(self):
        assert general_performance_score(90, 0) == 90

    def test_single_contribution_minimum(self):
        assert general_performance_score(90, 1) == 91

    def test_single_contribution_maximum(self):
        assert general_performance_score(90, 5) == 95

    def test_multiple_contributions_sum(self):
        assert general_performance_score(70, 5 + 4 + 3 + 2) == 84

    def test_spec_example_three_caps_at_120(self):
        assert general_performance_score(98, 25) == 120

    def test_cap_is_exactly_120(self):
        assert general_performance_score(100, 100) == MAX_GENERAL_SCORE

    def test_score_just_under_cap_is_not_clamped(self):
        assert general_performance_score(100, 19) == 119

    def test_window_is_ninety_days(self):
        assert CONTRIBUTION_BONUS_WINDOW_DAYS == 90
