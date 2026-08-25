import pytest

from app.models.enums import CalculationType
from app.services.kpi_engine import (
    CalculationRuleParams,
    KpiCalculationError,
    KpiScoreInput,
    PerformanceLevel,
    aggregate_ratio_kpi,
    calculate_custom_score,
    calculate_raw_score,
    calculate_score,
    compute_score_for_rule,
    compute_weighted_total,
    direct_score,
    higher_is_better,
    is_outstanding_performance,
    lower_is_better,
    period_ratio_score,
    proportional_penalty,
    range_target,
    resolve_performance_level,
    score_gsf,
    score_heavy_weight,
    score_heavy_weight_from_period_ratio,
    score_inkita,
    score_iskarta,
    plan_achievement_params,
    score_plan_achievement,
    score_plan_achievement_from_signed_deviation,
    score_plan_compliance,
    score_plan_compliance_from_period_deviation,
    score_target_ratio_linear_bonus,
    validate_kpi_weights,
    weighted_geometric_score,
)


class TestHigherIsBetter:
    def test_exact_target(self):
        assert higher_is_better(1000, 1000, 0, 120) == 100

    def test_below_target(self):
        assert higher_is_better(950, 1000, 0, 120) == pytest.approx(95)

    def test_exceeds_max_score_is_capped(self):
        assert higher_is_better(1300, 1000, 0, 120) == 120

    def test_zero_target_zero_actual(self):
        assert higher_is_better(0, 0, 0, 120) == 0

    def test_zero_target_positive_actual(self):
        assert higher_is_better(5, 0, 0, 120) == 120

    def test_negative_actual_raises(self):
        with pytest.raises(KpiCalculationError):
            higher_is_better(-1, 1000, 0, 120)


class TestLowerIsBetter:
    def test_below_target_is_better_than_100(self):
        assert lower_is_better(20, 30, 0, 120) == 120

    def test_above_target(self):
        assert lower_is_better(40, 30, 0, 120) == pytest.approx(75)

    def test_zero_actual_is_best(self):
        assert lower_is_better(0, 30, 0, 120) == 120

    def test_zero_target_zero_actual(self):
        assert lower_is_better(0, 0, 0, 120) == 120

    def test_zero_target_positive_actual_is_worst(self):
        assert lower_is_better(5, 0, 0, 120) == 0

    def test_negative_raises(self):
        with pytest.raises(KpiCalculationError):
            lower_is_better(-1, 30, 0, 120)


class TestRangeTarget:
    def test_within_range_full_score(self):
        assert range_target(95, 90, 100, 0, 5, 0, 120) == 100

    def test_below_range_within_tolerance(self):
        assert range_target(88, 90, 100, 3, 5, 0, 120) == 100

    def test_below_range_beyond_tolerance(self):
        assert range_target(85, 90, 100, 3, 5, 0, 120) == pytest.approx(90)

    def test_above_range_beyond_tolerance(self):
        assert range_target(108, 90, 100, 3, 5, 0, 120) == pytest.approx(75)

    def test_score_floored_at_min(self):
        assert range_target(0, 90, 100, 0, 50, 10, 120) == 10

    def test_invalid_bounds_raise(self):
        with pytest.raises(KpiCalculationError):
            range_target(50, 100, 90, 0, 5, 0, 120)


class TestDirectScore:
    def test_within_bounds(self):
        assert direct_score(85, 0, 100) == 85

    def test_capped_at_max(self):
        assert direct_score(150, 0, 100) == 100

    def test_floored_at_min(self):
        assert direct_score(-10, 0, 100) == 0


class TestProportionalPenalty:
    def test_within_target_full_score(self):
        assert proportional_penalty(25, 30, 5, 5, 0, 120) == 100

    def test_overage_penalty(self):
        assert proportional_penalty(40, 30, 5, 5, 0, 120) == pytest.approx(90)

    def test_floored_at_min_score(self):
        assert proportional_penalty(1000, 30, 5, 5, 20, 120) == 20

    def test_zero_unit_size_raises(self):
        with pytest.raises(KpiCalculationError):
            proportional_penalty(40, 30, 5, 0, 0, 120)


class TestDispatch:
    def test_calculate_raw_score_dispatches_higher_is_better(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.HIGHER_IS_BETTER, min_score=0, max_score=120)
        assert calculate_raw_score(950, 1000, rule) == pytest.approx(95)

    def test_custom_formula_not_supported(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.CUSTOM_FORMULA, min_score=0, max_score=120)
        with pytest.raises(KpiCalculationError):
            calculate_raw_score(10, 10, rule)

    def test_range_target_requires_bounds(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.RANGE_TARGET, min_score=0, max_score=120)
        with pytest.raises(KpiCalculationError):
            calculate_raw_score(50, 50, rule)


class TestRawVsCappedScore:
    def test_raw_score_exceeds_cap_but_capped_is_limited(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.HIGHER_IS_BETTER, min_score=0, max_score=120)
        result = calculate_score(1300, 1000, rule)
        assert result.raw_score == pytest.approx(130)
        assert result.capped_score == 120

    def test_raw_and_capped_equal_when_within_bounds(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.HIGHER_IS_BETTER, min_score=0, max_score=120)
        result = calculate_score(950, 1000, rule)
        assert result.raw_score == pytest.approx(95)
        assert result.capped_score == pytest.approx(95)

    def test_raw_score_below_min_but_capped_is_floored(self):
        rule = CalculationRuleParams(calculation_type=CalculationType.DIRECT_SCORE, min_score=0, max_score=100)
        result = calculate_score(-25, 0, rule)
        assert result.raw_score == -25
        assert result.capped_score == 0


class TestWeightValidation:
    def test_valid_weights(self):
        ok, msg = validate_kpi_weights([30, 20, 20, 20, 10])
        assert ok is True
        assert msg is None

    def test_invalid_weights(self):
        ok, msg = validate_kpi_weights([30, 20, 20, 20, 5])
        assert ok is False
        assert "100" in msg


class TestWeightedTotal:
    def test_all_present_matches_spec_example(self):
        scores = [
            KpiScoreInput("uretim", 90, 30),
            KpiScoreInput("fire", 85, 20),
            KpiScoreInput("durus", 100, 20),
            KpiScoreInput("kalite", 95, 20),
            KpiScoreInput("guvenlik", 80, 10),
        ]
        result = compute_weighted_total(scores)
        assert result.total_score == pytest.approx(91.0)
        assert result.is_reliable is True

    def test_missing_kpi_renormalizes_and_flags_unreliable(self):
        scores = [
            KpiScoreInput("uretim", 90, 30),
            KpiScoreInput("fire", 85, 20),
            KpiScoreInput("durus", 100, 20),
            KpiScoreInput("kalite", 95, 20),
        ]
        result = compute_weighted_total(scores, missing_kpi_codes=["guvenlik"])
        assert result.is_reliable is False
        assert result.missing_kpi_codes == ["guvenlik"]
        expected = (90 * 30 + 85 * 20 + 100 * 20 + 95 * 20) / 90
        assert result.total_score == pytest.approx(expected)

    def test_no_scores_returns_unreliable_zero(self):
        result = compute_weighted_total([])
        assert result.total_score == 0
        assert result.is_reliable is False


class TestPerformanceLevel:
    LEVELS = [
        PerformanceLevel("Kritik", 0, 69.99, "", "red", "alert-triangle", 1),
        PerformanceLevel("Geliştirilmeli", 70, 89.99, "", "orange", "trending-down", 2),
        PerformanceLevel("Başarılı", 90, 9999.99, "", "green", "check-circle", 3),
    ]

    def test_critical_low(self):
        assert resolve_performance_level(0, self.LEVELS).name == "Kritik"

    def test_critical_upper_boundary(self):
        assert resolve_performance_level(69.99, self.LEVELS).name == "Kritik"

    def test_needs_improvement_lower_boundary(self):
        assert resolve_performance_level(70, self.LEVELS).name == "Geliştirilmeli"

    def test_needs_improvement_upper_boundary(self):
        assert resolve_performance_level(89.99, self.LEVELS).name == "Geliştirilmeli"

    def test_successful_lower_boundary(self):
        assert resolve_performance_level(90, self.LEVELS).name == "Başarılı"

    def test_successful_mid_range(self):
        assert resolve_performance_level(100, self.LEVELS).name == "Başarılı"

    def test_above_max_clips_to_top(self):
        assert resolve_performance_level(150, self.LEVELS).name == "Başarılı"

    def test_no_levels_raises(self):
        with pytest.raises(KpiCalculationError):
            resolve_performance_level(50, [])


class TestOutstandingPerformance:
    def test_below_threshold(self):
        assert is_outstanding_performance(104.99) is False

    def test_at_threshold(self):
        assert is_outstanding_performance(105) is True

    def test_above_threshold(self):
        assert is_outstanding_performance(120) is True

    def test_typical_successful_score_not_outstanding(self):
        assert is_outstanding_performance(100) is False


class TestRatioAggregation:
    def test_ratio_recompute_not_simple_average(self):
        result = aggregate_ratio_kpi(numerator_sum=50, denominator_sum=150)
        assert result == pytest.approx(33.333, abs=0.01)

    def test_zero_denominator_returns_zero(self):
        assert aggregate_ratio_kpi(0, 0) == 0


class TestPeriodRatioScore:
    def test_lower_is_better_target_met(self):
        assert period_ratio_score(actual_sum=2, expected_sum=2, success_direction_higher=False) == pytest.approx(100)

    def test_lower_is_better_below_target_scores_above_100(self):
        assert period_ratio_score(actual_sum=1, expected_sum=2, success_direction_higher=False) == pytest.approx(200)

    def test_lower_is_better_above_target_scores_below_100(self):
        assert period_ratio_score(actual_sum=4, expected_sum=2, success_direction_higher=False) == pytest.approx(50)

    def test_higher_is_better_above_target_scores_above_100(self):
        assert period_ratio_score(actual_sum=100, expected_sum=95, success_direction_higher=True) == pytest.approx(105.26, abs=0.01)

    def test_higher_is_better_below_target_scores_below_100(self):
        assert period_ratio_score(actual_sum=85, expected_sum=95, success_direction_higher=True) == pytest.approx(89.47, abs=0.01)

    def test_no_upper_or_lower_band_applied(self):
        assert period_ratio_score(actual_sum=1, expected_sum=1000, success_direction_higher=False) == pytest.approx(100000)

    def test_max_score_only_guards_against_near_zero_actual_overflow(self):
        assert period_ratio_score(actual_sum=1e-12, expected_sum=1000, success_direction_higher=False, max_score=999999.99) == 999999.99
        assert period_ratio_score(actual_sum=4, expected_sum=2, success_direction_higher=False, max_score=999999.99) == pytest.approx(50)


class TestScoreHeavyWeight:

    def test_target_met_exactly(self):
        assert score_heavy_weight(0.40, 0.40).capped_score == pytest.approx(100.0)

    def test_actual_zero_scores_above_100(self):
        assert score_heavy_weight(0.00, 0.20).capped_score == pytest.approx(109.00)

    def test_underweight_same_magnitude_as_overweight_scores_identically(self):
        assert score_heavy_weight(-0.02, 0.20).capped_score == pytest.approx(108.10)
        assert score_heavy_weight(0.02, 0.20).capped_score == pytest.approx(108.10)

    def test_worse_than_target_uses_log_penalty(self):
        assert score_heavy_weight(0.39, 0.20).capped_score == pytest.approx(88.44, abs=0.01)

    def test_extreme_value_floored_at_zero_not_negative(self):
        result = score_heavy_weight(-0.99, 0.10)
        assert result.capped_score == pytest.approx(60.31, abs=0.01)
        assert result.capped_score >= 0

    def test_missing_or_invalid_target_raises(self):
        with pytest.raises(KpiCalculationError):
            score_heavy_weight(0.10, 0)
        with pytest.raises(KpiCalculationError):
            score_heavy_weight(0.10, -1)

    def test_period_ratio_entry_point_matches_actual_target_entry_point(self):
        direct = score_heavy_weight(0.39, 0.20)
        via_ratio = score_heavy_weight_from_period_ratio(abs(0.39) / 0.20)
        assert via_ratio.capped_score == pytest.approx(direct.capped_score)


class TestScoreGsf:

    def test_target_met_exactly(self):
        assert score_gsf(0.35, 0.35).capped_score == pytest.approx(100.0)

    def test_below_target_scores_above_100(self):
        assert score_gsf(0.27, 0.33).capped_score == pytest.approx(101.82, abs=0.01)

    def test_tiny_target_uses_minimum_normalization_base(self):
        assert score_gsf(0.00, 0.08).capped_score == pytest.approx(110.00, abs=0.01)

    def test_worse_than_target(self):
        assert score_gsf(0.40, 0.34).capped_score == pytest.approx(96.25, abs=0.01)

    def test_extreme_value(self):
        assert score_gsf(1.30, 0.35).capped_score == pytest.approx(69.71, abs=0.01)
        assert score_gsf(3.81, 0.64).capped_score == pytest.approx(58.82, abs=0.01)

    def test_zero_target_zero_actual_scores_100(self):
        assert score_gsf(0.0, 0.0).capped_score == pytest.approx(100.0)

    def test_negative_actual_raises(self):
        with pytest.raises(KpiCalculationError):
            score_gsf(-1.0, 0.5)


class TestScoreIskarta:

    def test_target_met_exactly(self):
        assert score_iskarta(0.80, 0.80).capped_score == pytest.approx(100.0)

    def test_below_target_scores_above_100(self):
        assert score_iskarta(0.50, 0.80).capped_score == pytest.approx(104.50)

    def test_worse_than_target(self):
        assert score_iskarta(1.10, 0.80).capped_score == pytest.approx(94.49, abs=0.01)
        assert score_iskarta(1.80, 1.50).capped_score == pytest.approx(96.84, abs=0.01)

    def test_same_absolute_diff_different_targets_scores_differently(self):
        worse_relative = score_iskarta(1.10, 0.80).capped_score
        better_relative = score_iskarta(1.80, 1.50).capped_score
        assert worse_relative < better_relative

    def test_extreme_value(self):
        assert score_iskarta(1.00, 0.50).capped_score == pytest.approx(88.00)
        assert score_iskarta(12.72, 1.50).capped_score == pytest.approx(62.99, abs=0.01)

    def test_missing_or_invalid_target_raises(self):
        with pytest.raises(KpiCalculationError):
            score_iskarta(1.0, 0)
        with pytest.raises(KpiCalculationError):
            score_iskarta(1.0, -1)


class TestScoreInkita:

    def test_target_met_exactly(self):
        assert score_inkita(2.08, 2.08).capped_score == pytest.approx(100.0)

    def test_actual_zero_uses_minimum_base(self):
        assert score_inkita(0.00, 1.10).capped_score == pytest.approx(106.00, abs=0.01)
        assert score_inkita(0.00, 0.21).capped_score == pytest.approx(102.52, abs=0.01)

    def test_worse_than_target(self):
        assert score_inkita(2.01, 1.50).capped_score == pytest.approx(95.78, abs=0.01)
        assert score_inkita(4.51, 1.41).capped_score == pytest.approx(83.23, abs=0.05)

    def test_extreme_value(self):
        assert score_inkita(10.07, 1.40).capped_score == pytest.approx(71.53, abs=0.01)

    def test_target_zero_actual_zero_scores_100(self):
        assert score_inkita(0.0, 0.0).capped_score == pytest.approx(100.0)

    def test_target_zero_positive_actual_uses_bad_branch_with_minimum_base(self):
        result = score_inkita(0.5, 0.0)
        assert result.capped_score < 100.0

    def test_negative_values_raise(self):
        with pytest.raises(KpiCalculationError):
            score_inkita(-1.0, 1.0)
        with pytest.raises(KpiCalculationError):
            score_inkita(1.0, -1.0)


class TestScoreOee:

    def test_full_day_scores_105(self):
        result = score_target_ratio_linear_bonus(1440, 1440)
        assert result.capped_score == pytest.approx(105.0)

    def test_1200_minutes_scores_87_5(self):
        result = score_target_ratio_linear_bonus(1200, 1440)
        assert result.raw_score == pytest.approx(87.5)
        assert result.capped_score == pytest.approx(87.5)

    def test_720_minutes_scores_52_5(self):
        result = score_target_ratio_linear_bonus(720, 1440)
        assert result.capped_score == pytest.approx(52.5)

    def test_zero_minutes_scores_zero(self):
        result = score_target_ratio_linear_bonus(0, 1440)
        assert result.capped_score == pytest.approx(0.0)

    def test_score_never_exceeds_max_score(self):
        result = score_target_ratio_linear_bonus(1440, 100)
        assert result.raw_score > 105.0
        assert result.capped_score == pytest.approx(105.0)

    def test_score_never_below_zero(self):
        result = score_target_ratio_linear_bonus(-10, 1440)
        assert result.capped_score == pytest.approx(0.0)

    def test_missing_or_invalid_target_raises(self):
        with pytest.raises(KpiCalculationError):
            score_target_ratio_linear_bonus(100, 0)
        with pytest.raises(KpiCalculationError):
            score_target_ratio_linear_bonus(100, -1)

    def test_custom_ratio_multiplier_and_max_score_params(self):
        result = score_target_ratio_linear_bonus(100, 100, ratio_multiplier=1.10, max_score=110.0)
        assert result.capped_score == pytest.approx(110.0)


class TestScorePlanCompliance:

    @pytest.mark.parametrize(
        "deviation,expected",
        [(0, 100), (1, 99), (3, 97), (5, 95), (10, 85), (20, 75), (40, 65)],
    )
    def test_deviation_examples_match_spec(self, deviation, expected):
        assert score_plan_compliance_from_period_deviation(deviation).capped_score == pytest.approx(expected, abs=0.01)

    def test_continuous_at_the_5_percent_boundary(self):
        just_below = score_plan_compliance_from_period_deviation(4.999).capped_score
        at_boundary = score_plan_compliance_from_period_deviation(5.0).capped_score
        just_above = score_plan_compliance_from_period_deviation(5.001).capped_score
        assert just_below == pytest.approx(at_boundary, abs=0.01)
        assert just_above == pytest.approx(at_boundary, abs=0.01)

    def test_over_plan_and_under_plan_score_identically(self):
        over = score_plan_compliance(planned=1000, actual=1100)
        under = score_plan_compliance(planned=1000, actual=900)
        assert over.capped_score == pytest.approx(under.capped_score)

    def test_production_record_examples_match_spec(self):
        assert score_plan_compliance(15120, 15120).capped_score == pytest.approx(100.00, abs=0.01)
        assert score_plan_compliance(28226, 28198).capped_score == pytest.approx(99.90, abs=0.01)
        assert score_plan_compliance(46055, 47775).capped_score == pytest.approx(96.27, abs=0.01)
        assert score_plan_compliance(24467, 28963).capped_score == pytest.approx(76.22, abs=0.01)
        assert score_plan_compliance(262191, 182368).capped_score == pytest.approx(68.94, abs=0.01)

    def test_missing_or_invalid_planned_raises(self):
        with pytest.raises(KpiCalculationError):
            score_plan_compliance(0, 100)
        with pytest.raises(KpiCalculationError):
            score_plan_compliance(-10, 100)


class TestScorePlanAchievement:

    @pytest.mark.parametrize(
        "planned,actual,expected",
        [
            (100, 100, 100.0),
            (100, 103, 103.0),
            (100, 105, 105.0),
            (100, 110, 110.0),
            (100, 120, 115.0),
            (100, 97, 97.0),
            (100, 95, 95.0),
            (100, 90, 85.0),
            (100, 80, 75.0),
        ],
    )
    def test_spec_examples_match(self, planned, actual, expected):
        assert score_plan_achievement(planned=planned, actual=actual).capped_score == pytest.approx(expected, abs=0.01)

    @pytest.mark.parametrize(
        "planned,actual,expected",
        [
            (15120, 15120, 100.00),
            (46055, 47775, 103.73),
            (804781, 822628, 102.22),
            (24467, 28963, 114.39),
            (46087, 45263, 98.21),
            (107783, 91038, 78.64),
            (262191, 182368, 68.94),
        ],
    )
    def test_production_record_examples_match_spec(self, planned, actual, expected):
        assert score_plan_achievement(planned=planned, actual=actual).capped_score == pytest.approx(expected, abs=0.01)

    def test_continuous_at_the_positive_5_percent_boundary(self):
        just_below = score_plan_achievement(planned=100, actual=104.999).capped_score
        at_boundary = score_plan_achievement(planned=100, actual=105).capped_score
        just_above = score_plan_achievement(planned=100, actual=105.001).capped_score
        assert just_below == pytest.approx(at_boundary, abs=0.01)
        assert just_above == pytest.approx(at_boundary, abs=0.01)

    def test_continuous_at_the_negative_5_percent_boundary(self):
        just_below = score_plan_achievement(planned=100, actual=95.001).capped_score
        at_boundary = score_plan_achievement(planned=100, actual=95).capped_score
        just_above = score_plan_achievement(planned=100, actual=94.999).capped_score
        assert just_below == pytest.approx(at_boundary, abs=0.01)
        assert just_above == pytest.approx(at_boundary, abs=0.01)

    def test_continuous_at_zero_deviation(self):
        just_above = score_plan_achievement(planned=100, actual=100.001).capped_score
        just_below = score_plan_achievement(planned=100, actual=99.999).capped_score
        assert just_above == pytest.approx(100.0, abs=0.01)
        assert just_below == pytest.approx(100.0, abs=0.01)

    def test_over_plan_and_under_plan_score_asymmetrically(self):
        over = score_plan_achievement(planned=1000, actual=1100)
        under = score_plan_achievement(planned=1000, actual=900)
        assert over.capped_score == pytest.approx(110.0, abs=0.01)
        assert under.capped_score == pytest.approx(85.0, abs=0.01)
        assert (100.0 - under.capped_score) > (over.capped_score - 100.0)

    def test_no_ceiling_for_very_high_overproduction(self):
        result = score_plan_achievement(planned=100, actual=1000)
        assert result.capped_score > 120

    def test_missing_or_invalid_planned_raises(self):
        with pytest.raises(KpiCalculationError):
            score_plan_achievement(planned=0, actual=100)
        with pytest.raises(KpiCalculationError):
            score_plan_achievement(planned=-10, actual=100)

    def test_from_signed_deviation_matches_direct_call(self):
        direct = score_plan_achievement(planned=1000, actual=1123).capped_score
        from_dev = score_plan_achievement_from_signed_deviation(12.3).capped_score
        assert direct == pytest.approx(from_dev, abs=0.01)

    def test_minimum_score_floor_applies_even_without_explicit_maximum(self):
        result = score_plan_achievement(planned=100, actual=0.0001, minimum_score=0.0)
        assert result.capped_score >= 0.0

    def test_plan_achievement_params_reads_overrides_and_defaults(self):
        parsed = plan_achievement_params({"positive_log_coefficient": 7.5})
        assert parsed["positive_log_coefficient"] == 7.5
        assert parsed["negative_log_coefficient"] == 10.0
        assert parsed["target_score"] == 100.0


class TestCustomFormulaDispatch:
    def test_dispatches_signed_absolute_piecewise(self):
        result = calculate_custom_score(0.39, 0.20, "SIGNED_ABSOLUTE_PIECEWISE", {"good_coefficient": 9, "bad_coefficient": 12})
        assert result.capped_score == pytest.approx(88.44, abs=0.01)

    def test_dispatches_hybrid_base_piecewise_log(self):
        result = calculate_custom_score(
            0.40, 0.34, "HYBRID_BASE_PIECEWISE_LOG",
            {"minimum_normalization_base": 0.05, "good_coefficient": 10, "bad_coefficient": 16},
        )
        assert result.capped_score == pytest.approx(96.25, abs=0.01)

    def test_dispatches_target_ratio_piecewise(self):
        result = calculate_custom_score(1.10, 0.80, "TARGET_RATIO_PIECEWISE", {"good_coefficient": 12, "bad_coefficient": 12})
        assert result.capped_score == pytest.approx(94.49, abs=0.01)

    def test_dispatches_target_ratio_linear_bonus(self):
        result = calculate_custom_score(1200, 1440, "TARGET_RATIO_LINEAR_BONUS", {"ratio_multiplier": 1.05, "max_score": 105})
        assert result.capped_score == pytest.approx(87.5)

    def test_unknown_formula_type_raises(self):
        with pytest.raises(KpiCalculationError):
            calculate_custom_score(1.0, 1.0, "NOT_A_REAL_FORMULA", {})


class TestComputeScoreForRule:
    def test_custom_formula_dispatches_to_new_engine(self):
        result = compute_score_for_rule(
            CalculationType.CUSTOM_FORMULA,
            {"formula_type": "TARGET_RATIO_PIECEWISE", "good_coefficient": 12, "bad_coefficient": 12},
            actual=1.10, target=0.80,
        )
        assert result.capped_score == pytest.approx(94.49, abs=0.01)

    def test_plana_uyum_formula_type_uses_numerator_denominator_not_actual_target(self):
        result = compute_score_for_rule(
            CalculationType.CUSTOM_FORMULA,
            {"formula_type": "PIECEWISE_LINEAR_LOGARITHMIC"},
            actual=999, target=999,
            numerator=15120, denominator=15120,
        )
        assert result.capped_score == pytest.approx(100.0)

    def test_asymmetric_plan_achievement_formula_type_uses_numerator_denominator(self):
        result = compute_score_for_rule(
            CalculationType.CUSTOM_FORMULA,
            {"formula_type": "ASYMMETRIC_PLAN_ACHIEVEMENT"},
            actual=999, target=999,
            numerator=1100, denominator=1000,
        )
        assert result.capped_score == pytest.approx(110.0, abs=0.01)

    def test_asymmetric_plan_achievement_missing_numerator_denominator_raises(self):
        with pytest.raises(KpiCalculationError):
            compute_score_for_rule(
                CalculationType.CUSTOM_FORMULA, {"formula_type": "ASYMMETRIC_PLAN_ACHIEVEMENT"}, actual=100, target=100,
            )

    def test_oee_formula_type_uses_actual_target_directly(self):
        result = compute_score_for_rule(
            CalculationType.CUSTOM_FORMULA,
            {"formula_type": "TARGET_RATIO_LINEAR_BONUS", "ratio_multiplier": 1.05, "max_score": 105},
            actual=720, target=1440,
        )
        assert result.capped_score == pytest.approx(52.5)

    def test_non_custom_formula_falls_back_to_generic_engine(self):
        result = compute_score_for_rule(CalculationType.HIGHER_IS_BETTER, {}, actual=950, target=1000, min_score=0, max_score=120)
        assert result.capped_score == pytest.approx(95.0)

    def test_no_ceiling_even_for_very_good_performance(self):
        result = compute_score_for_rule(
            CalculationType.CUSTOM_FORMULA,
            {"formula_type": "SIGNED_ABSOLUTE_PIECEWISE", "good_coefficient": 9, "bad_coefficient": 12},
            actual=0.0, target=0.20,
        )
        assert result.capped_score == pytest.approx(109.0)
        assert result.raw_score == result.capped_score


class TestWeightedGeometricScore:
    def test_equal_scores_return_same_score(self):
        assert weighted_geometric_score([(100.0, 50.0), (100.0, 50.0)]) == pytest.approx(100)

    def test_low_score_pulls_average_down_more_than_arithmetic_mean(self):
        geometric = weighted_geometric_score([(200.0, 50.0), (50.0, 50.0)])
        arithmetic = (200.0 * 0.5) + (50.0 * 0.5)
        assert geometric == pytest.approx(100.0)
        assert geometric < arithmetic

    def test_missing_components_renormalize_weights(self):
        assert weighted_geometric_score([(100.0, 30.0), (100.0, 20.0)]) == pytest.approx(100)

    def test_no_components_returns_zero(self):
        assert weighted_geometric_score([]) == 0
