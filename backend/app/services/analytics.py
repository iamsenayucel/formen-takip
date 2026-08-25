
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.enums import CalculationType, DataQualityStatus
from app.models.kpi import Kpi, KpiCalculationRule
from app.models.organization import Plant
from app.models.performance import PerformanceRecord, PerformanceScore
from app.schemas.common import Filters
from app.services.kpi_engine import (
    MIN_COVERED_WEIGHT_RATIO,
    CalculationRuleParams,
    ScoreResult,
    calculate_custom_score,
    calculate_score,
    plan_achievement_params,
    score_heavy_weight_from_period_ratio,
    score_plan_achievement,
    score_plan_compliance,
    score_plan_compliance_from_period_deviation,
    weighted_geometric_score,
)
from app.services.rule_resolver import NoRuleFoundError, resolve_rule

WEIGHT_TOLERANCE = 0.5


def _base_query() -> Select:
    return (
        select(PerformanceRecord, PerformanceScore)
        .join(PerformanceScore, PerformanceScore.performance_record_id == PerformanceRecord.id)
    )


def _apply_filters(stmt: Select, filters: Filters) -> Select:
    stmt = stmt.where(
        PerformanceRecord.performance_date >= filters.date_from,
        PerformanceRecord.performance_date <= filters.date_to,
    )
    if filters.plant_ids:
        stmt = stmt.where(PerformanceRecord.plant_id.in_(filters.plant_ids))
    if filters.factory_ids:
        stmt = stmt.where(
            PerformanceRecord.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(filters.factory_ids)))
        )
    if filters.chief_ids:
        stmt = stmt.where(PerformanceRecord.chief_id.in_(filters.chief_ids))
    if filters.shift_ids:
        stmt = stmt.where(PerformanceRecord.shift_id.in_(filters.shift_ids))
    if filters.kpi_ids:
        stmt = stmt.where(PerformanceRecord.kpi_id.in_(filters.kpi_ids))
    if filters.foreman_ids:
        stmt = stmt.where(PerformanceRecord.foreman_id.in_(filters.foreman_ids))
    return stmt


def active_kpi_weight_sum(db: Session, filters: Filters | None = None) -> float:
    stmt = select(func.sum(Kpi.weight)).where(Kpi.is_active.is_(True))
    if filters is not None and filters.kpi_ids:
        stmt = stmt.where(Kpi.id.in_(filters.kpi_ids))
    total = db.scalar(stmt)
    return float(total or 0)


def _active_kpis(db: Session) -> dict[UUID, Kpi]:
    return {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}


def _active_rules(db: Session, as_of: date | None = None) -> dict[UUID, KpiCalculationRule]:
    as_of = as_of or clock.today_local()
    candidates_by_kpi: dict[UUID, list[KpiCalculationRule]] = defaultdict(list)
    stmt = select(KpiCalculationRule).order_by(KpiCalculationRule.valid_from.desc(), KpiCalculationRule.id)
    for rule in db.scalars(stmt):
        candidates_by_kpi[rule.kpi_id].append(rule)

    resolved: dict[UUID, KpiCalculationRule] = {}
    for kpi_id, candidates in candidates_by_kpi.items():
        try:
            resolved[kpi_id] = resolve_rule(candidates, as_of)
        except NoRuleFoundError:
            continue
    return resolved




@dataclass
class _KpiPeriodStats:
    record_count: int
    numerator_sum: float
    denominator_sum: float
    expected_sum: float


def _group_key(row, n: int) -> tuple:
    return tuple(row[i] for i in range(n))


def _kpi_period_stats_multi(
    db: Session, filters: Filters, group_cols: list, kpi_id: UUID, extra_where: list | None = None
) -> dict[tuple, "_KpiPeriodStats"]:
    cols = [
        func.sum(PerformanceRecord.numerator_value).label("numerator_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
        func.sum(PerformanceRecord.denominator_value * PerformanceRecord.target_value / 100.0).label("expected_sum"),
        func.count().label("record_count"),
    ]
    stmt = select(*group_cols, *cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_cols:
        stmt = stmt.group_by(*group_cols)
    stmt = _apply_filters(stmt, filters)

    n = len(group_cols)
    out = {}
    for row in db.execute(stmt):
        out[_group_key(row, n)] = _KpiPeriodStats(
            record_count=row.record_count,
            numerator_sum=float(row.numerator_sum or 0.0),
            denominator_sum=float(row.denominator_sum or 0.0),
            expected_sum=float(row.expected_sum or 0.0),
        )
    return out


def _agir_gitme_period_ratio_multi(
    db: Session, filters: Filters, group_cols: list, kpi_id: UUID, extra_where: list | None = None
) -> dict[tuple, float]:
    ratio_expr = func.abs(PerformanceRecord.actual_value) / PerformanceRecord.target_value
    cols = [
        func.sum(PerformanceRecord.denominator_value * ratio_expr).label("weighted_ratio_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
    ]
    stmt = select(*group_cols, *cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_cols:
        stmt = stmt.group_by(*group_cols)
    stmt = _apply_filters(stmt, filters)

    n = len(group_cols)
    out = {}
    for row in db.execute(stmt):
        denom = float(row.denominator_sum or 0.0)
        out[_group_key(row, n)] = (float(row.weighted_ratio_sum or 0.0) / denom) if denom else 0.0
    return out


def _agir_gitme_avg_actual_multi(
    db: Session, filters: Filters, group_cols: list, kpi_id: UUID, extra_where: list | None = None
) -> dict[tuple, float]:
    cols = [
        func.sum(PerformanceRecord.denominator_value * func.abs(PerformanceRecord.actual_value)).label("weighted_abs_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
    ]
    stmt = select(*group_cols, *cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_cols:
        stmt = stmt.group_by(*group_cols)
    stmt = _apply_filters(stmt, filters)

    n = len(group_cols)
    out = {}
    for row in db.execute(stmt):
        denom = float(row.denominator_sum or 0.0)
        out[_group_key(row, n)] = (float(row.weighted_abs_sum or 0.0) / denom) if denom else 0.0
    return out


def _plana_uyum_period_deviation_multi(
    db: Session, filters: Filters, group_cols: list, kpi_id: UUID, extra_where: list | None = None
) -> dict[tuple, float]:
    cols = [
        func.sum(func.abs(PerformanceRecord.numerator_value - PerformanceRecord.denominator_value)).label("abs_dev_sum"),
        func.sum(PerformanceRecord.denominator_value).label("denominator_sum"),
    ]
    stmt = select(*group_cols, *cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if group_cols:
        stmt = stmt.group_by(*group_cols)
    stmt = _apply_filters(stmt, filters)

    n = len(group_cols)
    out = {}
    for row in db.execute(stmt):
        denom = float(row.denominator_sum or 0.0)
        out[_group_key(row, n)] = (float(row.abs_dev_sum or 0.0) / denom * 100.0) if denom else 0.0
    return out


def _plana_uyum_period_score_v3_multi(
    db: Session, filters: Filters, group_cols: list, kpi_id: UUID, params: dict, extra_where: list | None = None
) -> dict[tuple, float]:
    cols = [PerformanceRecord.numerator_value, PerformanceRecord.denominator_value]
    stmt = select(*group_cols, *cols).where(
        PerformanceRecord.kpi_id == kpi_id, PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
        PerformanceRecord.numerator_value.isnot(None), PerformanceRecord.denominator_value.isnot(None),
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    stmt = _apply_filters(stmt, filters)

    n = len(group_cols)
    plan_kwargs = plan_achievement_params(params)
    weighted_sum: dict[tuple, float] = defaultdict(float)
    weight_sum: dict[tuple, float] = defaultdict(float)
    for row in db.execute(stmt):
        key = _group_key(row, n)
        planned = float(row.denominator_value)
        actual = float(row.numerator_value)
        if planned <= 0:
            continue
        result = score_plan_achievement(planned=planned, actual=actual, **plan_kwargs)
        weighted_sum[key] += result.capped_score * planned
        weight_sum[key] += planned

    return {key: total / weight_sum[key] for key, total in weighted_sum.items() if weight_sum[key] > 0}


def _kpi_period_scores_multi(
    db: Session, filters: Filters, group_cols: list, kpi: Kpi, rule: KpiCalculationRule | None,
    extra_where: list | None = None,
) -> dict[tuple, tuple[ScoreResult, "_KpiPeriodStats"]]:
    stats_by_key = _kpi_period_stats_multi(db, filters, group_cols, kpi.id, extra_where=extra_where)
    stats_by_key = {k: s for k, s in stats_by_key.items() if s.denominator_sum > 0}
    if not stats_by_key:
        return {}

    params: dict = (rule.parameters if rule else {}) or {}
    formula_type = params.get("formula_type")

    if kpi.code == "AGIR_GITME":
        ratio_by_key = _agir_gitme_period_ratio_multi(db, filters, group_cols, kpi.id, extra_where=extra_where)
        good = params.get("good_coefficient", 9.0)
        bad = params.get("bad_coefficient", 12.0)
        return {
            key: (score_heavy_weight_from_period_ratio(ratio_by_key.get(key, 0.0), good, bad), stats)
            for key, stats in stats_by_key.items()
        }

    if kpi.code == "PLANA_UYUM":
        if formula_type == "ASYMMETRIC_PLAN_ACHIEVEMENT":
            score_by_key = _plana_uyum_period_score_v3_multi(db, filters, group_cols, kpi.id, params, extra_where=extra_where)
            return {
                key: (ScoreResult(raw_score=score_by_key[key], capped_score=score_by_key[key]), stats)
                for key, stats in stats_by_key.items() if key in score_by_key
            }
        dev_by_key = _plana_uyum_period_deviation_multi(db, filters, group_cols, kpi.id, extra_where=extra_where)
        limit = params.get("normal_deviation_limit", 5.0)
        coef = params.get("excess_deviation_coefficient", 10.0)
        return {
            key: (score_plan_compliance_from_period_deviation(dev_by_key.get(key, 0.0), limit, coef), stats)
            for key, stats in stats_by_key.items()
        }

    result: dict = {}
    for key, stats in stats_by_key.items():
        period_actual = stats.numerator_sum / stats.denominator_sum * 100.0
        period_target = stats.expected_sum / stats.denominator_sum * 100.0
        result[key] = (calculate_custom_score(period_actual, period_target, formula_type, params), stats)
    return result


def _unwrap_single(d: dict[tuple, object]) -> dict:
    return {(k[0] if k else None): v for k, v in d.items()}


def _kpi_period_stats(db: Session, filters: Filters, group_col, kpi_id: UUID, extra_where: list | None = None) -> dict:
    group_cols = [group_col] if group_col is not None else []
    return _unwrap_single(_kpi_period_stats_multi(db, filters, group_cols, kpi_id, extra_where=extra_where))


def _agir_gitme_avg_actual(db: Session, filters: Filters, group_col, kpi_id: UUID, extra_where: list | None = None) -> dict:
    group_cols = [group_col] if group_col is not None else []
    return _unwrap_single(_agir_gitme_avg_actual_multi(db, filters, group_cols, kpi_id, extra_where=extra_where))


def _kpi_period_scores(
    db: Session, filters: Filters, group_col, kpi: Kpi, rule: KpiCalculationRule | None, extra_where: list | None = None
) -> dict:
    group_cols = [group_col] if group_col is not None else []
    return _unwrap_single(_kpi_period_scores_multi(db, filters, group_cols, kpi, rule, extra_where=extra_where))


@dataclass
class PlantKpiEntry:
    plant_id: UUID
    actual: float | None
    target: float | None
    raw_score: float
    capped_score: float
    record_count: int


def _foreman_plant_kpi_entries(
    db: Session, filters: Filters, kpi: Kpi, rule: KpiCalculationRule | None, extra_where: list | None = None
) -> dict[UUID, dict[UUID, PlantKpiEntry]]:
    group_cols = [PerformanceRecord.foreman_id, PerformanceRecord.plant_id]
    scores_by_key = _kpi_period_scores_multi(db, filters, group_cols, kpi, rule, extra_where=extra_where)
    if not scores_by_key:
        return {}

    actual_by_key: dict[tuple, float] = {}
    if kpi.code == "AGIR_GITME":
        actual_by_key = _agir_gitme_avg_actual_multi(db, filters, group_cols, kpi.id, extra_where=extra_where)

    out: dict[UUID, dict[UUID, PlantKpiEntry]] = defaultdict(dict)
    for (foreman_id, plant_id), (score, stats) in scores_by_key.items():
        target = (stats.expected_sum / stats.denominator_sum * 100.0) if stats.denominator_sum else None
        if kpi.code == "AGIR_GITME":
            actual = actual_by_key.get((foreman_id, plant_id))
        else:
            actual = (stats.numerator_sum / stats.denominator_sum * 100.0) if stats.denominator_sum else None
        out[foreman_id][plant_id] = PlantKpiEntry(
            plant_id=plant_id, actual=actual, target=target,
            raw_score=score.raw_score, capped_score=score.capped_score, record_count=stats.record_count,
        )
    return out


def _equal_weight_plant_average(
    entries: dict[UUID, PlantKpiEntry],
) -> tuple[float, float, int, list[PlantKpiEntry]]:
    items = list(entries.values())
    count = len(items)
    if count == 0:
        return 0.0, 0.0, 0, []
    capped_avg = sum(e.capped_score for e in items) / count
    raw_avg = sum(e.raw_score for e in items) / count
    return capped_avg, raw_avg, count, items


def _combine_group(items: list[tuple[float, float, int]], total_active_weight: float) -> tuple[float, bool, int, float]:
    components = [(score, weight) for score, weight, _ in items]
    covered_weight = sum(weight for _, weight, _ in items)
    record_count = sum(count for _, _, count in items)
    insufficient = covered_weight < (total_active_weight * MIN_COVERED_WEIGHT_RATIO)
    is_reliable = (not insufficient) and covered_weight >= (total_active_weight - WEIGHT_TOLERANCE)
    total_score = 0.0 if insufficient else weighted_geometric_score(components)
    return total_score, is_reliable, record_count, covered_weight


@dataclass
class GroupScore:
    key: UUID
    total_score: float
    is_reliable: bool
    record_count: int
    weight_covered: float


def _grouped_scores(
    db: Session, filters: Filters, group_col, total_active_weight: float, extra_where: list | None = None
) -> list[GroupScore]:
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)

    per_group: dict[UUID, list[tuple[float, float, int]]] = defaultdict(list)
    for kpi in kpis_by_id.values():
        rule = rules_by_kpi.get(kpi.id)
        for key, (score_result, stats) in _kpi_period_scores(db, filters, group_col, kpi, rule, extra_where).items():
            per_group[key].append((score_result.capped_score, float(kpi.weight), stats.record_count))

    results = []
    for key, items in per_group.items():
        total_score, is_reliable, record_count, covered_weight = _combine_group(items, total_active_weight)
        results.append(
            GroupScore(
                key=key, total_score=total_score, is_reliable=is_reliable,
                record_count=record_count, weight_covered=covered_weight,
            )
        )
    return results


def foreman_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)

    per_foreman: dict[UUID, list[tuple[float, float, int]]] = defaultdict(list)
    for kpi in kpis_by_id.values():
        rule = rules_by_kpi.get(kpi.id)
        entries_by_foreman = _foreman_plant_kpi_entries(db, filters, kpi, rule)
        for foreman_id, plant_entries in entries_by_foreman.items():
            avg_capped, _avg_raw, count, items = _equal_weight_plant_average(plant_entries)
            if count == 0:
                continue
            record_count = sum(e.record_count for e in items)
            per_foreman[foreman_id].append((avg_capped, float(kpi.weight), record_count))

    results = []
    for foreman_id, items in per_foreman.items():
        total_score, is_reliable, record_count, covered_weight = _combine_group(items, total_weight)
        results.append(
            GroupScore(
                key=foreman_id, total_score=total_score, is_reliable=is_reliable,
                record_count=record_count, weight_covered=covered_weight,
            )
        )
    return results


def plant_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.plant_id, total_weight)


def shift_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.shift_id, total_weight)


def chief_scores(db: Session, filters: Filters) -> list[GroupScore]:
    total_weight = active_kpi_weight_sum(db, filters)
    return _grouped_scores(db, filters, PerformanceRecord.chief_id, total_weight)


@dataclass
class ChiefTeamScore:
    chief_id: UUID
    total_score: float
    foreman_count: int
    is_reliable: bool
    record_count: int
    foreman_scores: list[GroupScore]


def chief_team_scores(db: Session, filters: Filters) -> list[ChiefTeamScore]:
    chief_scores_by_id = {s.key: s for s in chief_scores(db, filters)}
    foreman_scores_by_id = {s.key: s for s in foreman_scores(db, filters)}

    membership_stmt = _apply_filters(
        select(PerformanceRecord.chief_id, PerformanceRecord.foreman_id).distinct(), filters
    )
    foremen_by_chief: dict[UUID, set[UUID]] = defaultdict(set)
    for chief_id, foreman_id in db.execute(membership_stmt):
        foremen_by_chief[chief_id].add(foreman_id)

    results = []
    for chief_id, foreman_ids in foremen_by_chief.items():
        chief_score = chief_scores_by_id.get(chief_id)
        foreman_list = [foreman_scores_by_id[fid] for fid in foreman_ids if fid in foreman_scores_by_id]
        results.append(
            ChiefTeamScore(
                chief_id=chief_id,
                total_score=chief_score.total_score if chief_score else 0.0,
                foreman_count=len(foreman_list),
                is_reliable=chief_score.is_reliable if chief_score else False,
                record_count=chief_score.record_count if chief_score else 0,
                foreman_scores=foreman_list,
            )
        )
    return results


@dataclass
class KpiSummary:
    kpi_id: UUID
    avg_capped_score: float
    avg_target: float | None
    avg_actual: float | None
    record_count: int


def kpi_summary(db: Session, filters: Filters) -> list[KpiSummary]:
    return [
        KpiSummary(
            kpi_id=row["kpi_id"], avg_capped_score=row["avg_capped_score"],
            avg_target=row["avg_target"], avg_actual=row["avg_actual"], record_count=row["record_count"],
        )
        for row in kpi_breakdown(db, filters)
    ]


@dataclass
class TrendPoint:
    bucket: date
    total_score: float
    is_reliable: bool


_GRANULARITY_TRUNC = {"day": "day", "week": "week", "month": "month", "quarter": "quarter", "year": "year"}


def trend(db: Session, filters: Filters, granularity: str = "day", foreman_id: UUID | None = None) -> list[TrendPoint]:
    trunc_unit = _GRANULARITY_TRUNC.get(granularity, "day")
    bucket_col = func.date_trunc(trunc_unit, PerformanceRecord.performance_date)
    total_weight = active_kpi_weight_sum(db, filters)

    if foreman_id is None:
        grouped = _grouped_scores(db, filters, bucket_col, total_weight)
        grouped.sort(key=lambda g: g.key)
        return [TrendPoint(bucket=g.key.date(), total_score=g.total_score, is_reliable=g.is_reliable) for g in grouped]

    extra_where = [PerformanceRecord.foreman_id == foreman_id]
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)

    per_bucket: dict[date, list[tuple[float, float, int]]] = defaultdict(list)
    for kpi in kpis_by_id.values():
        rule = rules_by_kpi.get(kpi.id)
        scores_by_key = _kpi_period_scores_multi(
            db, filters, [bucket_col, PerformanceRecord.plant_id], kpi, rule, extra_where=extra_where
        )
        by_bucket: dict[date, dict[UUID, tuple[ScoreResult, _KpiPeriodStats]]] = defaultdict(dict)
        for (bucket, plant_id), value in scores_by_key.items():
            by_bucket[bucket][plant_id] = value
        for bucket, plant_map in by_bucket.items():
            plant_scores = list(plant_map.values())
            count = len(plant_scores)
            if count == 0:
                continue
            avg_capped = sum(s.capped_score for s, _ in plant_scores) / count
            record_count = sum(st.record_count for _, st in plant_scores)
            per_bucket[bucket].append((avg_capped, float(kpi.weight), record_count))

    results = []
    for bucket, items in per_bucket.items():
        total_score, is_reliable, _record_count, _covered_weight = _combine_group(items, total_weight)
        results.append(TrendPoint(bucket=bucket.date(), total_score=total_score, is_reliable=is_reliable))
    results.sort(key=lambda p: p.bucket)
    return results


def kpi_breakdown(db: Session, filters: Filters, foreman_id: UUID | None = None) -> list[dict]:
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)
    extra_where = [PerformanceRecord.foreman_id == foreman_id] if foreman_id is not None else None

    results = []
    for kpi in kpis_by_id.values():
        rule = rules_by_kpi.get(kpi.id)
        scores = _kpi_period_scores(db, filters, None, kpi, rule, extra_where=extra_where)
        entry = scores.get(None)
        if entry is None:
            continue
        score_result, stats = entry
        weight = float(kpi.weight)
        avg_target = (stats.expected_sum / stats.denominator_sum * 100) if stats.denominator_sum else None
        if kpi.code == "AGIR_GITME":
            avg_actual = _agir_gitme_avg_actual(db, filters, None, kpi.id, extra_where=extra_where).get(None)
        else:
            avg_actual = (stats.numerator_sum / stats.denominator_sum * 100) if stats.denominator_sum else None
        results.append(
            {
                "kpi_id": kpi.id,
                "avg_target": avg_target,
                "avg_actual": avg_actual,
                "numerator_sum": stats.numerator_sum,
                "denominator_sum": stats.denominator_sum,
                "avg_raw_score": score_result.raw_score,
                "avg_capped_score": score_result.capped_score,
                "weight": weight,
                "contrib_sum": score_result.capped_score * (weight / 100.0),
                "record_count": stats.record_count,
                "calculation_version": rule.version if rule else None,
            }
        )
    return results


def foreman_kpi_breakdown(db: Session, filters: Filters, foreman_id: UUID) -> list[dict]:
    base_rows = kpi_breakdown(db, filters, foreman_id=foreman_id)
    kpis_by_id = _active_kpis(db)
    rules_by_kpi = _active_rules(db)
    extra_where = [PerformanceRecord.foreman_id == foreman_id]

    out = []
    for row in base_rows:
        kpi = kpis_by_id.get(row["kpi_id"])
        rule = rules_by_kpi.get(row["kpi_id"]) if kpi else None
        new_row = dict(row)
        evaluated_plant_count = 0
        plants_detail: list[dict] = []
        if kpi is not None:
            entries_by_foreman = _foreman_plant_kpi_entries(db, filters, kpi, rule, extra_where=extra_where)
            avg_capped, avg_raw, count, items = _equal_weight_plant_average(entries_by_foreman.get(foreman_id, {}))
            if count > 0:
                new_row["avg_capped_score"] = avg_capped
                new_row["avg_raw_score"] = avg_raw
                new_row["contrib_sum"] = avg_capped * (row["weight"] / 100.0)
                evaluated_plant_count = count
                plant_weight = 1.0 / count
                plants_detail = [
                    {
                        "plant_id": e.plant_id,
                        "actual": round(e.actual, kpi.decimal_places) if e.actual is not None else None,
                        "target": round(e.target, kpi.decimal_places) if e.target is not None else None,
                        "raw_score": round(e.raw_score, 2),
                        "score": round(e.capped_score, 2),
                        "weight": round(plant_weight, 6),
                        "record_count": e.record_count,
                    }
                    for e in items
                ]
        new_row["evaluated_plant_count"] = evaluated_plant_count
        new_row["plants"] = plants_detail
        out.append(new_row)
    return out


@dataclass
class ForemanKpiValue:
    foreman_id: UUID
    avg_actual: float
    avg_target: float
    capped_score: float
    record_count: int


def _point_score(kpi: Kpi, rule: KpiCalculationRule | None, actual: float, target: float) -> float:
    params: dict = (rule.parameters if rule else {}) or {}
    if kpi.calculation_type == CalculationType.CUSTOM_FORMULA:
        formula_type = params.get("formula_type")
        if formula_type == "ASYMMETRIC_PLAN_ACHIEVEMENT":
            result = score_plan_achievement(planned=target, actual=actual, **plan_achievement_params(params))
        elif formula_type == "PIECEWISE_LINEAR_LOGARITHMIC":
            result = score_plan_compliance(
                planned=target, actual=actual,
                normal_deviation_limit=params.get("normal_deviation_limit", 5.0),
                excess_deviation_coefficient=params.get("excess_deviation_coefficient", 10.0),
            )
        else:
            result = calculate_custom_score(actual, target, formula_type, params)
        return result.capped_score
    rule_params = CalculationRuleParams(
        calculation_type=kpi.calculation_type, min_score=float(kpi.min_score), max_score=float(kpi.max_score), **params
    )
    return calculate_score(actual, target, rule_params).capped_score


def foreman_kpi_values(db: Session, filters: Filters, kpi: Kpi, reference_target: float) -> list[ForemanKpiValue]:
    rule = _active_rules(db).get(kpi.id)
    stats_by_foreman = _kpi_period_stats(db, filters, PerformanceRecord.foreman_id, kpi.id)
    agir_gitme_actual_by_foreman = (
        _agir_gitme_avg_actual(db, filters, PerformanceRecord.foreman_id, kpi.id)
        if kpi.code == "AGIR_GITME" else {}
    )
    entries_by_foreman = _foreman_plant_kpi_entries(db, filters, kpi, rule)

    results = []
    for foreman_id, stats in stats_by_foreman.items():
        if stats.denominator_sum <= 0:
            continue
        if kpi.code == "AGIR_GITME":
            avg_actual = agir_gitme_actual_by_foreman.get(foreman_id, 0.0)
        else:
            avg_actual = stats.numerator_sum / stats.denominator_sum * 100
        avg_target = stats.expected_sum / stats.denominator_sum * 100
        avg_capped, _avg_raw, count, _items = _equal_weight_plant_average(entries_by_foreman.get(foreman_id, {}))
        capped_score = avg_capped if count > 0 else _point_score(kpi, rule, avg_actual, reference_target)
        results.append(
            ForemanKpiValue(
                foreman_id=foreman_id,
                avg_actual=avg_actual,
                avg_target=avg_target,
                capped_score=capped_score,
                record_count=stats.record_count,
            )
        )
    return results


def latest_foreman_kpi_record(db: Session, foreman_id: UUID, kpi_id: UUID):
    stmt = (
        _base_query()
        .where(
            PerformanceRecord.foreman_id == foreman_id,
            PerformanceRecord.kpi_id == kpi_id,
            PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
        )
        .order_by(PerformanceRecord.performance_date.desc())
        .limit(1)
    )
    return db.execute(stmt).first()
