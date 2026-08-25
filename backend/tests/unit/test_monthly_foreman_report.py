import uuid
from datetime import date

import pytest

from app.models.foreman import ForemanAssignment
from app.services.monthly_foreman_report import (
    _classify_trend_shape,
    _compare_to_reference,
    _month_bounds,
    _previous_month,
    group_assignment_episodes,
    is_month_completed,
)


def _assignment(
    foreman_id, plant_id, chief_id, shift_id, start_date, end_date=None,
):
    return ForemanAssignment(
        id=uuid.uuid4(), foreman_id=foreman_id, plant_id=plant_id, chief_id=chief_id,
        shift_id=shift_id, start_date=start_date, end_date=end_date, is_active=end_date is None,
    )


class TestMonthBounds:
    def test_regular_month(self):
        assert _month_bounds(2026, 7) == (date(2026, 7, 1), date(2026, 7, 31))

    def test_february_leap_year(self):
        assert _month_bounds(2024, 2) == (date(2024, 2, 1), date(2024, 2, 29))

    def test_february_non_leap_year(self):
        assert _month_bounds(2026, 2) == (date(2026, 2, 1), date(2026, 2, 28))


class TestPreviousMonth:
    def test_mid_year(self):
        assert _previous_month(2026, 7) == (2026, 6)

    def test_january_crosses_year_boundary(self):
        assert _previous_month(2026, 1) == (2025, 12)


class TestIsMonthCompleted:
    def test_far_past_month_is_completed(self):
        assert is_month_completed(2020, 1) is True

    def test_far_future_month_is_not_completed(self):
        assert is_month_completed(2099, 1) is False


class TestCompareToReference:
    def test_none_actual_returns_none(self):
        assert _compare_to_reference(None, 5.0, True) is None

    def test_none_reference_returns_none(self):
        assert _compare_to_reference(5.0, None, True) is None

    def test_higher_is_better_above_target_is_favorable(self):
        result = _compare_to_reference(actual=90.0, reference=80.0, success_direction_higher=True)
        assert result["status"] == "above"
        assert result["is_favorable"] is True

    def test_higher_is_better_below_target_is_unfavorable(self):
        result = _compare_to_reference(actual=70.0, reference=80.0, success_direction_higher=True)
        assert result["status"] == "below"
        assert result["is_favorable"] is False

    def test_lower_is_better_below_target_is_favorable(self):
        result = _compare_to_reference(actual=0.5, reference=0.8, success_direction_higher=False)
        assert result["status"] == "below"
        assert result["is_favorable"] is True

    def test_lower_is_better_above_target_is_unfavorable(self):
        result = _compare_to_reference(actual=1.2, reference=0.8, success_direction_higher=False)
        assert result["status"] == "above"
        assert result["is_favorable"] is False

    def test_within_tolerance_is_at(self):
        result = _compare_to_reference(actual=80.001, reference=80.0, success_direction_higher=True)
        assert result["status"] == "at"
        assert result["is_favorable"] is True

    def test_zero_reference_handles_diff_pct_gracefully(self):
        result = _compare_to_reference(actual=1.0, reference=0.0, success_direction_higher=False)
        assert result["diff_pct"] is None


class TestClassifyTrendShape:
    def test_insufficient_weeks_returns_none(self):
        assert _classify_trend_shape([80.0, 82.0]) is None

    def test_stable_scores(self):
        assert _classify_trend_shape([90.0, 91.0, 89.5, 90.5]) == "stabil"

    def test_improving_scores(self):
        assert _classify_trend_shape([70.0, 72.0, 85.0, 88.0]) == "iyileşme"

    def test_worsening_scores(self):
        assert _classify_trend_shape([90.0, 88.0, 75.0, 70.0]) == "kötüleşme"

    def test_volatile_scores(self):
        assert _classify_trend_shape([95.0, 60.0, 95.0, 60.0]) == "dalgalı"


class TestGroupAssignmentEpisodes:
    def test_single_episode_multiple_plants_grouped_together(self):
        foreman_id, chief_id, shift_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        plant_a, plant_b = uuid.uuid4(), uuid.uuid4()
        assignments = [
            _assignment(foreman_id, plant_a, chief_id, shift_id, date(2026, 8, 1)),
            _assignment(foreman_id, plant_b, chief_id, shift_id, date(2026, 8, 1)),
        ]
        episodes = group_assignment_episodes(assignments)
        assert len(episodes) == 1
        assert len(episodes[0]) == 2

    def test_two_episodes_ordered_by_start_date(self):
        foreman_id, shift_id = uuid.uuid4(), uuid.uuid4()
        chief_a, chief_b = uuid.uuid4(), uuid.uuid4()
        plant_a, plant_b = uuid.uuid4(), uuid.uuid4()
        assignments = [
            _assignment(foreman_id, plant_b, chief_b, shift_id, date(2026, 8, 16)),
            _assignment(foreman_id, plant_a, chief_a, shift_id, date(2026, 8, 1), date(2026, 8, 15)),
        ]
        episodes = group_assignment_episodes(assignments)
        assert len(episodes) == 2
        assert episodes[0][0].start_date == date(2026, 8, 1)
        assert episodes[1][0].start_date == date(2026, 8, 16)

    def test_empty_input_returns_empty_list(self):
        assert group_assignment_episodes([]) == []
