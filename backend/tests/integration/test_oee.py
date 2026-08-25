from sqlalchemy import func, select, text

from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget
from app.models.enums import TargetScopeType
from app.models.performance import PerformanceRecord
from app.models.production import ProductionRecord
from app.services.kpi_engine import SHIFT_MINUTES, compute_score_for_rule


def _oee_kpi(db_session) -> Kpi:
    kpi = db_session.scalar(select(Kpi).where(Kpi.code == "OEE"))
    assert kpi is not None, "OEE KPI'sı seed/migration ile oluşturulmuş olmalı"
    return kpi


class TestOeeKpiDefinition:
    def test_oee_field_definitions_match_business_rules(self, db_session):
        kpi = _oee_kpi(db_session)
        assert float(kpi.default_target_value) == 100
        assert float(kpi.min_valid_value) == 0
        assert float(kpi.max_valid_value) == 100
        assert float(kpi.min_score) == 0
        assert float(kpi.max_score) == 105
        assert kpi.success_direction_higher is True
        assert kpi.unit == "%"
        assert kpi.is_active is True

    def test_oee_included_in_active_weight_sum(self, db_session):
        total = db_session.scalar(select(func.sum(Kpi.weight)).where(Kpi.is_active.is_(True)))
        assert abs(float(total) - 100.0) < 0.01

    def test_oee_has_company_target_of_100_percent(self, db_session):
        kpi = _oee_kpi(db_session)
        target = db_session.scalar(
            select(KpiTarget).where(
                KpiTarget.kpi_id == kpi.id, KpiTarget.scope_type == TargetScopeType.COMPANY, KpiTarget.is_active.is_(True)
            )
        )
        assert target is not None
        assert float(target.target_value) == 100

    def test_oee_has_active_calculation_rule(self, db_session):
        kpi = _oee_kpi(db_session)
        rule = db_session.scalar(
            select(KpiCalculationRule).where(KpiCalculationRule.kpi_id == kpi.id, KpiCalculationRule.is_active.is_(True))
        )
        assert rule is not None
        assert rule.parameters.get("formula_type") == "TARGET_RATIO_LINEAR_BONUS"


class TestOeeShiftLevelScoring:
    """Her OEE performance kaydı vardiya ölçeğindedir; actual, SHIFT_MINUTES (720) yüzdesidir.

    Aggregation granularity ne olursa olsun hedef %100'dür. actual/target oran olduğunda aynı
    TARGET_RATIO_LINEAR_BONUS kuralı vardiya, fabrika-gün ve dönemi aynı biçimde puanlar.
    """

    def _score(self, db_session, actual_percent: float) -> float:
        kpi = _oee_kpi(db_session)
        rule = db_session.scalar(
            select(KpiCalculationRule).where(KpiCalculationRule.kpi_id == kpi.id, KpiCalculationRule.is_active.is_(True))
        )
        result = compute_score_for_rule(
            rule.calculation_type, rule.parameters,
            actual=actual_percent, target=float(kpi.default_target_value),
            min_score=float(kpi.min_score), max_score=float(kpi.max_score),
        )
        return result.capped_score

    def test_v1_example_660_of_720_scores_96_25(self, db_session):
        actual_percent = 660.0 / SHIFT_MINUTES * 100.0
        assert abs(self._score(db_session, actual_percent) - 96.25) < 0.01

    def test_v2_example_540_of_720_scores_78_75(self, db_session):
        actual_percent = 540.0 / SHIFT_MINUTES * 100.0
        assert abs(self._score(db_session, actual_percent) - 78.75) < 0.01

    def test_plant_day_example_1200_of_1440_scores_87_50(self, db_session):
        actual_percent = 1200.0 / 1440.0 * 100.0
        assert abs(self._score(db_session, actual_percent) - 87.4965) < 0.01

    def test_full_utilization_scores_105(self, db_session):
        assert self._score(db_session, 100.0) == 105.0

    def test_zero_utilization_scores_zero(self, db_session):
        assert self._score(db_session, 0.0) == 0.0


class TestOeeWorkingTimeIsShiftLevel:
    def test_working_time_minutes_stays_within_0_and_720(self, db_session):
        out_of_range = db_session.scalar(
            select(func.count()).select_from(ProductionRecord).where(
                (ProductionRecord.working_time_minutes < 0) | (ProductionRecord.working_time_minutes > 720)
            )
        )
        assert out_of_range == 0

    def test_no_working_time_minutes_is_ever_zero(self, db_session):
        zero_rows = db_session.scalar(
            select(func.count()).select_from(ProductionRecord).where(ProductionRecord.working_time_minutes == 0)
        )
        assert zero_rows == 0, "Sentetik veri gerçekçi aralıkta olmalı; literal 0 çalışma süresi beklenmiyor"


class TestOeeNoDateParityAttribution:
    def test_plant_days_with_both_shifts_produce_two_oee_records_not_one(self, db_session):
        kpi = _oee_kpi(db_session)
        rows = db_session.execute(
            select(PerformanceRecord.plant_id, PerformanceRecord.performance_date, func.count())
            .where(PerformanceRecord.kpi_id == kpi.id)
            .group_by(PerformanceRecord.plant_id, PerformanceRecord.performance_date)
        ).all()
        assert rows, "OEE performance kaydı bulunamadı"
        counts = {n for _, _, n in rows}
        assert counts <= {1, 2}, f"Beklenmeyen plant-day başına OEE kayıt sayısı: {counts}"
        assert 2 in counts, "En az bazı plant-day'lerde her iki vardiyanın da (V1+V2) OEE kaydı olmalı"

    def test_no_more_than_two_oee_records_per_plant_day(self, db_session):
        kpi = _oee_kpi(db_session)
        rows = db_session.execute(
            select(PerformanceRecord.plant_id, PerformanceRecord.performance_date, func.count())
            .where(PerformanceRecord.kpi_id == kpi.id)
            .group_by(PerformanceRecord.plant_id, PerformanceRecord.performance_date)
            .having(func.count() > 2)
        ).all()
        assert rows == [], f"Plant-day başına ikiden fazla OEE kaydı (natural key ihlali): {rows[:5]}"

    def test_oee_record_shift_matches_its_own_production_record_shift(self, db_session):
        kpi = _oee_kpi(db_session)
        rows = db_session.execute(text("""
            SELECT pr.shift_id AS perf_shift_id, prod.shift_id AS prod_shift_id
            FROM performance_records pr
            JOIN production_records prod ON prod.id = pr.production_record_id
            JOIN kpis k ON k.id = pr.kpi_id
            WHERE k.code = 'OEE'
            LIMIT 500
        """)).all()
        assert rows, "OEE performance kaydı bulunamadı"
        assert all(r.perf_shift_id == r.prod_shift_id for r in rows)


class TestOeeMissingShiftIsNotZero:
    def test_single_shift_plant_days_have_target_of_720_not_1440(self, db_session):
        kpi = _oee_kpi(db_session)
        rows = db_session.execute(
            select(PerformanceRecord.plant_id, PerformanceRecord.performance_date, func.sum(PerformanceRecord.denominator_value))
            .where(PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.data_quality_status == "COMPLETE")
            .group_by(PerformanceRecord.plant_id, PerformanceRecord.performance_date)
            .having(func.count() == 1)
            .limit(5)
        ).all()
        assert rows, "Tek vardiyalı en az bir plant-day örneği bekleniyor"
        for _plant_id, _date, denom_sum in rows:
            assert abs(float(denom_sum) - SHIFT_MINUTES) < 0.01


class TestOeePlantDayAggregation:
    def test_plant_day_actual_equals_sum_of_both_shifts_over_1440(self, db_session):
        kpi = _oee_kpi(db_session)
        rows = db_session.execute(
            select(
                PerformanceRecord.plant_id, PerformanceRecord.performance_date,
                func.sum(PerformanceRecord.numerator_value), func.sum(PerformanceRecord.denominator_value),
            )
            .where(PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.data_quality_status == "COMPLETE")
            .group_by(PerformanceRecord.plant_id, PerformanceRecord.performance_date)
            .having(func.count() == 2)
            .limit(10)
        ).all()
        assert rows, "İki vardiyalı en az bir plant-day örneği bekleniyor"
        for _plant_id, _date, num_sum, den_sum in rows:
            assert abs(float(den_sum) - 1440.0) < 0.01
            oee_pct = float(num_sum) / float(den_sum) * 100.0
            assert 0.0 <= oee_pct <= 100.0


class TestOeeForemanPeriodAggregation:
    def test_foreman_period_oee_matches_numerator_denominator_sum(self, db_session):
        kpi = _oee_kpi(db_session)
        foreman_id = db_session.scalar(
            select(PerformanceRecord.foreman_id)
            .where(PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.data_quality_status == "COMPLETE")
            .limit(1)
        )
        assert foreman_id is not None

        num_sum, den_sum, n = db_session.execute(
            select(
                func.sum(PerformanceRecord.numerator_value), func.sum(PerformanceRecord.denominator_value), func.count()
            ).where(
                PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.foreman_id == foreman_id,
                PerformanceRecord.data_quality_status == "COMPLETE",
            )
        ).one()
        assert n > 0
        assert abs(float(den_sum) - n * SHIFT_MINUTES) < 0.01, "Her formen kaydının hedefi kendi vardiyası (720) olmalı"
        period_oee_pct = float(num_sum) / float(den_sum) * 100.0
        assert 0.0 <= period_oee_pct <= 100.0


class TestOeePlantPeriodAggregation:
    def test_plant_period_oee_matches_numerator_denominator_sum(self, db_session):
        kpi = _oee_kpi(db_session)
        plant_id = db_session.scalar(
            select(PerformanceRecord.plant_id)
            .where(PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.data_quality_status == "COMPLETE")
            .limit(1)
        )
        assert plant_id is not None

        num_sum, den_sum, n = db_session.execute(
            select(
                func.sum(PerformanceRecord.numerator_value), func.sum(PerformanceRecord.denominator_value), func.count()
            ).where(
                PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.plant_id == plant_id,
                PerformanceRecord.data_quality_status == "COMPLETE",
            )
        ).one()
        assert n > 0
        assert abs(float(den_sum) - n * SHIFT_MINUTES) < 0.01
        period_oee_pct = float(num_sum) / float(den_sum) * 100.0
        assert 0.0 <= period_oee_pct <= 100.0


class TestOeeInkitaCorrelation:
    def test_negative_correlation_between_oee_and_inkita_at_shift_level(self, db_session):
        rows = db_session.execute(text("""
            WITH inkita AS (
                SELECT pr.plant_id, pr.shift_id, pr.performance_date, pr.actual_value AS inkita_pct
                FROM performance_records pr JOIN kpis k ON k.id = pr.kpi_id
                WHERE k.code = 'INKITA' AND pr.data_quality_status = 'COMPLETE'
            ),
            oee AS (
                SELECT pr.plant_id, pr.shift_id, pr.performance_date, pr.actual_value AS oee_pct
                FROM performance_records pr JOIN kpis k ON k.id = pr.kpi_id
                WHERE k.code = 'OEE' AND pr.data_quality_status = 'COMPLETE'
            )
            SELECT inkita.inkita_pct, oee.oee_pct
            FROM inkita JOIN oee
                ON oee.plant_id = inkita.plant_id AND oee.shift_id = inkita.shift_id
                AND oee.performance_date = inkita.performance_date
        """)).all()
        assert len(rows) > 500, "Korelasyon için yeterli örtüşen vardiya-günü verisi yok"

        xs = [float(r.inkita_pct) for r in rows]
        ys = [float(r.oee_pct) for r in rows]
        n = len(xs)
        mean_x, mean_y = sum(xs) / n, sum(ys) / n
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / n
        std_x = (sum((x - mean_x) ** 2 for x in xs) / n) ** 0.5
        std_y = (sum((y - mean_y) ** 2 for y in ys) / n) ** 0.5
        pearson = cov / (std_x * std_y)

        assert pearson < -0.15, f"OEE ile INKITA arasında beklenen negatif ilişki gözlenmedi (Pearson={pearson:.3f})"
        assert pearson > -0.999, "Korelasyon mekanik/kusursuz (-1.0'a çok yakın) görünüyor, gerçekçi değil"


class TestOeeDistributionSanity:
    def test_not_everything_is_near_perfect(self, db_session):
        kpi = _oee_kpi(db_session)
        total = db_session.scalar(
            select(func.count()).select_from(PerformanceRecord).where(PerformanceRecord.kpi_id == kpi.id)
        )
        near_perfect = db_session.scalar(
            select(func.count()).select_from(PerformanceRecord).where(
                PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.actual_value >= 99.99
            )
        )
        assert total > 0
        assert near_perfect / total < 0.10, "%100 civarındaki vardiyalar dataset'i domine etmemeli"

    def test_low_performance_shifts_are_a_minority(self, db_session):
        kpi = _oee_kpi(db_session)
        total = db_session.scalar(
            select(func.count()).select_from(PerformanceRecord).where(PerformanceRecord.kpi_id == kpi.id)
        )
        poor = db_session.scalar(
            select(func.count()).select_from(PerformanceRecord).where(
                PerformanceRecord.kpi_id == kpi.id, PerformanceRecord.actual_value < 50
            )
        )
        assert poor / total < 0.15, "Düşük OEE vardiyaları dataset'in çoğunluğunu oluşturmamalı"
