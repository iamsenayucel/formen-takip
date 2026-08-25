from types import SimpleNamespace

import pytest

from app.models.enums import FinancialGainStatus, ImpactLevel, OtherGainType, RepeatPeriod, TimeUnit
from app.services.contribution_calc import (
    CONTRIBUTION_SCORE_LABELS,
    compute_change,
    compute_contribution_score,
    compute_monthly_total,
    compute_time_saving,
    duration_to_minutes,
    is_improvement,
    validate_for_publish,
)


class TestDurationToMinutes:
    def test_minute_passthrough(self):
        assert duration_to_minutes(17, TimeUnit.MINUTE) == 17

    def test_hour_conversion(self):
        assert duration_to_minutes(2, TimeUnit.HOUR) == 120

    def test_second_conversion(self):
        assert duration_to_minutes(120, TimeUnit.SECOND) == pytest.approx(2.0)

    def test_none_value_returns_none(self):
        assert duration_to_minutes(None, TimeUnit.MINUTE) is None


class TestComputeTimeSaving:
    def test_spec_example(self):
        assert compute_time_saving(45, 28) == 17

    def test_new_duration_equal_returns_none(self):
        assert compute_time_saving(30, 30) is None

    def test_new_duration_greater_returns_none(self):
        assert compute_time_saving(20, 25) is None

    def test_missing_input_returns_none(self):
        assert compute_time_saving(None, 10) is None


class TestComputeMonthlyTotal:
    def test_spec_example(self):
        assert compute_monthly_total(17, RepeatPeriod.MONTHLY, 30) == 510

    def test_daily_repeat_scales_by_days_per_month(self):
        result = compute_monthly_total(10, RepeatPeriod.DAILY, 1)
        assert result == pytest.approx(300, rel=0.01)

    def test_missing_repeat_period_returns_none(self):
        assert compute_monthly_total(10, None, 5) is None


class TestComputeChange:
    def test_spec_example_scrap_reduction(self):
        amount, percent = compute_change(4.2, 3.1)
        assert amount == pytest.approx(-1.1)
        assert percent == pytest.approx(-26.19, rel=0.01)

    def test_zero_previous_guards_percent(self):
        amount, percent = compute_change(0, 5)
        assert amount == 5
        assert percent is None

    def test_missing_values_return_none_tuple(self):
        assert compute_change(None, 5) == (None, None)


class TestIsImprovement:
    def test_capacity_increase_is_improvement_when_positive(self):
        assert is_improvement(OtherGainType.CAPACITY_INCREASE, 5) is True
        assert is_improvement(OtherGainType.CAPACITY_INCREASE, -5) is False

    def test_scrap_reduction_is_improvement_when_negative(self):
        assert is_improvement(OtherGainType.SCRAP_REDUCTION, -1.1) is True
        assert is_improvement(OtherGainType.SCRAP_REDUCTION, 1.1) is False

    def test_none_change_returns_none(self):
        assert is_improvement(OtherGainType.SCRAP_REDUCTION, None) is None


class TestValidateForPublish:
    VALID = {
        "title": "Başlık", "foreman_ids": ["id"], "plant_ids": ["id"], "work_date": "2026-01-01",
        "work_type": "smed", "summary": "Özet", "problem_description": "Problem", "solution_description": "Çözüm",
    }

    def test_complete_payload_has_no_errors(self):
        assert validate_for_publish(self.VALID) == {}

    def test_missing_title_is_reported(self):
        data = {**self.VALID, "title": ""}
        assert "title" in validate_for_publish(data)

    def test_missing_foremen_is_reported(self):
        data = {**self.VALID, "foreman_ids": []}
        assert "foreman_ids" in validate_for_publish(data)

    def test_other_work_type_requires_note(self):
        data = {**self.VALID, "work_type": "other"}
        errors = validate_for_publish(data)
        assert "work_type_other_note" in errors

    def test_other_work_type_with_note_is_valid(self):
        data = {**self.VALID, "work_type": "other", "work_type_other_note": "Açıklama"}
        assert validate_for_publish(data) == {}

    def test_date_range_end_before_start_is_reported(self):
        data = {**self.VALID, "work_date": "2026-02-01", "work_date_end": "2026-01-01"}
        assert "work_date_end" in validate_for_publish(data)


def _work(**overrides):
    defaults = dict(
        impact_level=ImpactLevel.LOW,
        is_applicable_other_plants=False,
        is_permanent_solution=False,
        is_standardized=False,
        work_instruction_updated=False,
        financial_gain_status=FinancialGainStatus.NOT_CALCULATED,
        monthly_total_saving_minutes=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestComputeContributionScore:
    def test_minimal_work_scores_minimum(self):
        score, _ = compute_contribution_score(_work(), [])
        assert score == 1

    def test_maximal_work_scores_maximum(self):
        work = _work(
            impact_level=ImpactLevel.HIGH,
            is_applicable_other_plants=True,
            is_permanent_solution=True,
            is_standardized=True,
            work_instruction_updated=True,
            financial_gain_status=FinancialGainStatus.YES,
        )
        score, _ = compute_contribution_score(work, [])
        assert score == 5

    def test_score_never_below_one(self):
        work = _work(impact_level=None)
        score, _ = compute_contribution_score(work, [])
        assert score == 1

    def test_score_never_above_five(self):
        work = _work(
            impact_level=ImpactLevel.HIGH, is_applicable_other_plants=True, is_permanent_solution=True,
            is_standardized=True, work_instruction_updated=True, financial_gain_status=FinancialGainStatus.YES,
        )
        gains = [SimpleNamespace(change_amount=-1.0, change_percent=-10.0)]
        score, _ = compute_contribution_score(work, gains)
        assert 1 <= score <= 5

    def test_higher_impact_never_scores_lower(self):
        low_score, _ = compute_contribution_score(_work(impact_level=ImpactLevel.LOW), [])
        medium_score, _ = compute_contribution_score(_work(impact_level=ImpactLevel.MEDIUM), [])
        high_score, _ = compute_contribution_score(_work(impact_level=ImpactLevel.HIGH), [])
        assert low_score <= medium_score <= high_score

    def test_measurable_financial_gain_scores_at_least_as_high_as_none(self):
        no_gain, _ = compute_contribution_score(_work(), [])
        with_gain, _ = compute_contribution_score(_work(financial_gain_status=FinancialGainStatus.YES), [])
        assert with_gain >= no_gain

    def test_measurable_gain_from_gain_rows_counts_toward_verifiability(self):
        no_gain, _ = compute_contribution_score(_work(), [])
        with_gain, _ = compute_contribution_score(
            _work(), [SimpleNamespace(change_amount=-1.1, change_percent=-26.19)]
        )
        assert with_gain >= no_gain

    def test_manual_score_override_is_impossible_by_construction(self):
        # compute_contribution_score client tarafından verilen score'u kabul eden bir
        # parametre içermez; tek girdiler çalışmanın kendi alanları ve kazanımlarıdır.
        import inspect

        assert list(inspect.signature(compute_contribution_score).parameters) == ["work", "gains"]

    def test_breakdown_total_matches_returned_score(self):
        work = _work(impact_level=ImpactLevel.MEDIUM, is_permanent_solution=True)
        score, breakdown = compute_contribution_score(work, [])
        total_entry = next(b for b in breakdown if b["label"] == "Toplam")
        assert str(score) in total_entry["detail"]
        assert CONTRIBUTION_SCORE_LABELS[score] in total_entry["detail"]

    @pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
    def test_all_scores_have_labels(self, score):
        assert score in CONTRIBUTION_SCORE_LABELS
