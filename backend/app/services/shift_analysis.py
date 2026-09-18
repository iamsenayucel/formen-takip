from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.models.performance import PerformanceRecord
from app.schemas.common import Filters
from app.services import analytics
from app.services.shift_rotation import ROTATION_EPOCH

TR_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


@dataclass(frozen=True)
class ShiftAnomalyThresholds:
    medium_pct: float = 8.0
    high_pct: float = 15.0
    min_records_per_side: int = 4
    min_abs_diff_points: float = 1.0
    critical_pct: float = 25.0


DEFAULT_THRESHOLDS = ShiftAnomalyThresholds()


def month_label(d: date) -> str:
    return f"{TR_MONTHS[d.month - 1]} {d.year}"


def previous_completed_month(today: date) -> tuple[date, date]:
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    return last_of_prev_month.replace(day=1), last_of_prev_month


def _week_index(d: date) -> int:
    return (d - ROTATION_EPOCH).days // 7


@dataclass
class _RawRow:
    plant_id: UUID
    shift_id: UUID
    foreman_id: UUID
    kpi_id: UUID
    performance_date: date
    numerator: float
    denominator: float


def _fetch_raw_rows(
    db: Session, month_start: date, month_end: date, *,
    plant_ids: list[UUID] | None = None, factory_ids: list[UUID] | None = None,
    kpi_ids: list[UUID] | None = None, shift_ids: list[UUID] | None = None,
) -> list[_RawRow]:
    stmt = select(
        PerformanceRecord.plant_id, PerformanceRecord.shift_id, PerformanceRecord.foreman_id,
        PerformanceRecord.kpi_id, PerformanceRecord.performance_date,
        PerformanceRecord.numerator_value, PerformanceRecord.denominator_value,
    ).where(
        PerformanceRecord.performance_date >= month_start,
        PerformanceRecord.performance_date <= month_end,
        PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
        PerformanceRecord.numerator_value.isnot(None),
        PerformanceRecord.denominator_value.isnot(None),
    )
    if plant_ids is not None:
        stmt = stmt.where(PerformanceRecord.plant_id.in_(plant_ids))
    if factory_ids is not None:
        stmt = stmt.where(PerformanceRecord.plant_id.in_(select(Plant.id).where(Plant.factory_id.in_(factory_ids))))
    if kpi_ids is not None:
        stmt = stmt.where(PerformanceRecord.kpi_id.in_(kpi_ids))
    if shift_ids is not None:
        stmt = stmt.where(PerformanceRecord.shift_id.in_(shift_ids))

    return [
        _RawRow(
            plant_id=r.plant_id, shift_id=r.shift_id, foreman_id=r.foreman_id, kpi_id=r.kpi_id,
            performance_date=r.performance_date,
            numerator=float(r.numerator_value), denominator=float(r.denominator_value),
        )
        for r in db.execute(stmt).all()
    ]


def _group_cells(rows: list[_RawRow]) -> dict[tuple[UUID, UUID, UUID], dict[UUID, list[_RawRow]]]:
    cells: dict[tuple[UUID, UUID, UUID], dict[UUID, list[_RawRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        cells[(r.plant_id, r.shift_id, r.kpi_id)][r.foreman_id].append(r)
    return cells


@dataclass
class ForemanCellStat:
    foreman_id: UUID
    avg_actual: float
    record_count: int
    week_indices: list[int]


def _foreman_stat(foreman_id: UUID, records: list[_RawRow]) -> ForemanCellStat | None:
    denom_sum = sum(r.denominator for r in records)
    if denom_sum == 0:
        return None
    numer_sum = sum(r.numerator for r in records)
    weeks = sorted({_week_index(r.performance_date) for r in records})
    return ForemanCellStat(
        foreman_id=foreman_id, avg_actual=numer_sum / denom_sum * 100.0,
        record_count=len(records), week_indices=weeks,
    )


@dataclass
class PairComparison:
    better: ForemanCellStat
    worse: ForemanCellStat
    abs_diff: float
    pct_diff: float
    severity: str


def _extreme_pair(stats: list[ForemanCellStat], thresholds: ShiftAnomalyThresholds) -> tuple[ForemanCellStat, ForemanCellStat] | None:
    qualifying = [s for s in stats if s.record_count >= thresholds.min_records_per_side]
    if len(qualifying) < 2:
        return None
    best = max(qualifying, key=lambda s: s.avg_actual)
    worst = min(qualifying, key=lambda s: s.avg_actual)
    return best, worst


def _compare_pair(
    a: ForemanCellStat, b: ForemanCellStat, higher_is_better: bool, thresholds: ShiftAnomalyThresholds,
) -> PairComparison | None:
    if a.record_count < thresholds.min_records_per_side or b.record_count < thresholds.min_records_per_side:
        return None
    if higher_is_better:
        better, worse = (a, b) if a.avg_actual >= b.avg_actual else (b, a)
    else:
        better, worse = (a, b) if a.avg_actual <= b.avg_actual else (b, a)

    abs_diff = abs(better.avg_actual - worse.avg_actual)
    base = (abs(a.avg_actual) + abs(b.avg_actual)) / 2.0
    if base == 0:
        return None
    pct_diff = abs_diff / base * 100.0

    if abs_diff < thresholds.min_abs_diff_points:
        return None
    if pct_diff >= thresholds.high_pct:
        severity = "high"
    elif pct_diff >= thresholds.medium_pct:
        severity = "medium"
    else:
        return None
    return PairComparison(better=better, worse=worse, abs_diff=abs_diff, pct_diff=pct_diff, severity=severity)


HeatmapLevel = str


def classify_diff_level(
    a: ForemanCellStat | None, b: ForemanCellStat | None, thresholds: ShiftAnomalyThresholds,
) -> tuple[HeatmapLevel, float | None, float | None]:
    if a is None or b is None or a.record_count < thresholds.min_records_per_side or b.record_count < thresholds.min_records_per_side:
        return "no_data", None, None

    abs_diff = abs(a.avg_actual - b.avg_actual)
    base = (abs(a.avg_actual) + abs(b.avg_actual)) / 2.0
    if base == 0:
        return "normal", 0.0, 0.0
    pct_diff = abs_diff / base * 100.0

    if abs_diff < thresholds.min_abs_diff_points:
        return "normal", abs_diff, pct_diff
    if pct_diff >= thresholds.critical_pct:
        return "critical", abs_diff, pct_diff
    if pct_diff >= thresholds.high_pct:
        return "significant", abs_diff, pct_diff
    if pct_diff >= thresholds.medium_pct:
        return "attention", abs_diff, pct_diff
    return "normal", abs_diff, pct_diff


@dataclass
class HeatmapPlantRef:
    id: UUID
    name: str
    sequence_number: int
    factory_code: str


@dataclass
class HeatmapKpiRef:
    id: UUID
    code: str
    name: str
    unit: str


@dataclass
class HeatmapCell:
    plant_id: UUID
    kpi_id: UUID
    level: HeatmapLevel
    v1: ForemanCellStat | None
    v2: ForemanCellStat | None
    abs_diff: float | None
    pct_diff: float | None
    better_shift_id: UUID | None


def build_heatmap(
    db: Session, month_start: date, month_end: date, *,
    plant_ids: list[UUID] | None = None, factory_ids: list[UUID] | None = None,
    kpi_ids: list[UUID] | None = None, thresholds: ShiftAnomalyThresholds = DEFAULT_THRESHOLDS,
) -> tuple[list[HeatmapPlantRef], list[HeatmapKpiRef], list[HeatmapCell], list[Shift]]:
    rows = _fetch_raw_rows(db, month_start, month_end, plant_ids=plant_ids, factory_ids=factory_ids, kpi_ids=kpi_ids)

    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    v1_id, v2_id = (None, None)
    ordered_shifts = sorted(shifts_by_id.values(), key=lambda s: s.sequence)
    if len(ordered_shifts) >= 2:
        v1_id, v2_id = ordered_shifts[0].id, ordered_shifts[1].id

    plant_query = select(Plant).where(Plant.is_active.is_(True))
    if plant_ids is not None:
        plant_query = plant_query.where(Plant.id.in_(plant_ids))
    if factory_ids is not None:
        plant_query = plant_query.where(Plant.factory_id.in_(factory_ids))
    plants = sorted(db.scalars(plant_query), key=lambda p: p.sequence_number)
    factories_by_id = {f.id: f for f in db.scalars(select(Factory))}

    kpi_query = select(Kpi).where(Kpi.is_active.is_(True))
    if kpi_ids:
        kpi_query = kpi_query.where(Kpi.id.in_(kpi_ids))
    kpis = sorted(db.scalars(kpi_query), key=lambda k: k.display_order)

    by_plant_kpi_shift: dict[tuple[UUID, UUID], dict[UUID, list[_RawRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_plant_kpi_shift[(r.plant_id, r.kpi_id)][r.shift_id].append(r)

    plant_refs = [
        HeatmapPlantRef(
            id=p.id, name=p.name, sequence_number=p.sequence_number,
            factory_code=factories_by_id[p.factory_id].code if p.factory_id in factories_by_id else "",
        )
        for p in plants
    ]
    kpi_refs = [HeatmapKpiRef(id=k.id, code=k.code, name=k.name, unit=k.unit) for k in kpis]

    cells: list[HeatmapCell] = []
    for p in plants:
        for k in kpis:
            by_shift = by_plant_kpi_shift.get((p.id, k.id), {})
            v1_stat = _foreman_stat(v1_id, by_shift[v1_id]) if v1_id and by_shift.get(v1_id) else None
            v2_stat = _foreman_stat(v2_id, by_shift[v2_id]) if v2_id and by_shift.get(v2_id) else None
            level, abs_diff, pct_diff = classify_diff_level(v1_stat, v2_stat, thresholds)
            better_shift_id = None
            if v1_stat is not None and v2_stat is not None and level != "no_data":
                if k.success_direction_higher:
                    better_shift_id = v1_id if v1_stat.avg_actual >= v2_stat.avg_actual else v2_id
                else:
                    better_shift_id = v1_id if v1_stat.avg_actual <= v2_stat.avg_actual else v2_id
            cells.append(
                HeatmapCell(
                    plant_id=p.id, kpi_id=k.id, level=level,
                    v1=v1_stat, v2=v2_stat, abs_diff=abs_diff, pct_diff=pct_diff,
                    better_shift_id=better_shift_id,
                )
            )

    return plant_refs, kpi_refs, cells, ordered_shifts


@dataclass
class HeatmapSummary:
    period: tuple[date, date, str]
    anomaly_plant_count: int
    critical_cell_count: int
    top_kpi: tuple[UUID, str, int] | None
    priority_plant_count: int


NON_NORMAL_LEVELS = {"attention", "significant", "critical"}


def build_heatmap_summary(
    cells: list[HeatmapCell], kpi_refs: list[HeatmapKpiRef], month_start: date, month_end: date,
) -> HeatmapSummary:
    kpis_by_id = {k.id: k for k in kpi_refs}
    anomaly_plants: set[UUID] = set()
    priority_plants: set[UUID] = set()
    critical_count = 0
    kpi_anomaly_counts: Counter[UUID] = Counter()

    for c in cells:
        if c.level in NON_NORMAL_LEVELS:
            anomaly_plants.add(c.plant_id)
            kpi_anomaly_counts[c.kpi_id] += 1
        if c.level == "critical":
            critical_count += 1
            priority_plants.add(c.plant_id)

    top_kpi = None
    if kpi_anomaly_counts:
        kpi_id, count = kpi_anomaly_counts.most_common(1)[0]
        kpi = kpis_by_id.get(kpi_id)
        if kpi:
            top_kpi = (kpi_id, kpi.name, count)

    return HeatmapSummary(
        period=(month_start, month_end, month_label(month_end)),
        anomaly_plant_count=len(anomaly_plants),
        critical_cell_count=critical_count,
        top_kpi=top_kpi,
        priority_plant_count=len(priority_plants),
    )


@dataclass
class ForemanShiftCell:
    avg_actual: float
    avg_target: float
    capped_score: float
    record_count: int


@dataclass
class ForemanShiftRow:
    foreman_id: UUID
    name: str
    employee_number: str
    cells: dict[UUID, ForemanShiftCell]


@dataclass
class ForemanShiftMatrix:
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    kpi_unit: str
    success_direction_higher: bool
    reference_target: float
    shifts: list[Shift]
    rows: list[ForemanShiftRow]
    insight: str


def _shift_diff_classification(a: float, b: float, thresholds: ShiftAnomalyThresholds) -> HeatmapLevel:
    abs_diff = abs(a - b)
    base = (abs(a) + abs(b)) / 2.0
    if base == 0 or abs_diff < thresholds.min_abs_diff_points:
        return "normal"
    pct_diff = abs_diff / base * 100.0
    if pct_diff >= thresholds.critical_pct:
        return "critical"
    if pct_diff >= thresholds.high_pct:
        return "significant"
    if pct_diff >= thresholds.medium_pct:
        return "attention"
    return "normal"


def _build_matrix_insight(shifts: list[Shift], rows: list[ForemanShiftRow], thresholds: ShiftAnomalyThresholds) -> str:
    if len(rows) < 2 or len(shifts) < 2:
        return "Bu KPI için formen/vardiya kırılımında karşılaştırmaya yetecek veri bulunamadı."
    s1, s2 = shifts[0].id, shifts[1].id

    shift_effect_rows: list[ForemanShiftRow] = []
    for row in rows:
        c1, c2 = row.cells.get(s1), row.cells.get(s2)
        if c1 is None or c2 is None:
            continue
        level = _shift_diff_classification(c1.avg_actual, c2.avg_actual, thresholds)
        if level in NON_NORMAL_LEVELS:
            shift_effect_rows.append(row)

    foreman_effect_pairs: list[tuple[Shift, str, str]] = []
    for shift in shifts:
        vals = [(row, row.cells.get(shift.id)) for row in rows if row.cells.get(shift.id) is not None]
        if len(vals) < 2:
            continue
        (row_a, cell_a), (row_b, cell_b) = vals[0], vals[1]
        level = _shift_diff_classification(cell_a.avg_actual, cell_b.avg_actual, thresholds)
        if level in NON_NORMAL_LEVELS:
            foreman_effect_pairs.append((shift, row_a.name, row_b.name))

    if len(shift_effect_rows) == len(rows) and shift_effect_rows:
        names = ", ".join(r.name for r in shift_effect_rows)
        return (
            f"Her iki formende de ({names}) vardiyalar arasında belirgin bir performans farkı var; "
            f"bu KPI'da sorun formenden çok vardiya etkisiyle ilişkili görünüyor."
        )
    if len(shift_effect_rows) == 1:
        r = shift_effect_rows[0]
        return (
            f"{r.name}'nın vardiyalar arasındaki performansı belirgin şekilde değişiyor, diğer formende "
            f"aynı örüntü görülmüyor; bu KPI'da sorun vardiyadan çok {r.name} ile ilişkili görünüyor."
        )
    if foreman_effect_pairs:
        shift, name_a, name_b = foreman_effect_pairs[0]
        return (
            f"{shift.name} içinde {name_a} ile {name_b} arasında belirgin bir fark var; "
            f"bu KPI'da sorun vardiyadan çok formen performansıyla ilişkili görünüyor."
        )
    return "Formenler vardiyalar arasında istikrarlı bir performans gösteriyor; belirgin bir vardiya veya formen etkisi tespit edilmedi."


def build_foreman_shift_matrix(
    db: Session, filters: Filters, plant_id: UUID, kpi_id: UUID, thresholds: ShiftAnomalyThresholds = DEFAULT_THRESHOLDS,
) -> ForemanShiftMatrix | None:
    kpi = db.get(Kpi, kpi_id)
    if kpi is None or not kpi.is_active:
        return None
    plant = db.get(Plant, plant_id)
    if plant is None:
        return None
    shifts = sorted(db.scalars(select(Shift)), key=lambda s: s.sequence)
    if len(shifts) < 2:
        return None

    plant_filters = replace(filters, plant_ids=[plant_id], kpi_ids=[kpi_id])
    plant_summary = analytics.kpi_summary(db, plant_filters)
    reference_target = (
        plant_summary[0].avg_target
        if plant_summary and plant_summary[0].avg_target is not None
        else float(kpi.default_target_value)
    )

    per_shift_values: dict[UUID, dict[UUID, analytics.ForemanKpiValue]] = {}
    foreman_ids: set[UUID] = set()
    for shift in shifts:
        shift_filters = replace(plant_filters, shift_ids=[shift.id])
        values = analytics.foreman_kpi_values(db, shift_filters, kpi, reference_target)
        per_shift_values[shift.id] = {v.foreman_id: v for v in values}
        foreman_ids.update(per_shift_values[shift.id].keys())

    if not foreman_ids:
        return None

    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_(foreman_ids)))}
    rows: list[ForemanShiftRow] = []
    for fid in sorted(foreman_ids, key=lambda x: foremen_by_id[x].employee_number if x in foremen_by_id else str(x)):
        f = foremen_by_id.get(fid)
        if f is None:
            continue
        cell_map: dict[UUID, ForemanShiftCell] = {}
        for shift in shifts:
            v = per_shift_values[shift.id].get(fid)
            if v is not None:
                cell_map[shift.id] = ForemanShiftCell(
                    avg_actual=v.avg_actual, avg_target=v.avg_target,
                    capped_score=v.capped_score, record_count=v.record_count,
                )
        rows.append(ForemanShiftRow(foreman_id=fid, name=f"{f.first_name} {f.last_name}", employee_number=f.employee_number, cells=cell_map))

    insight = _build_matrix_insight(shifts, rows, thresholds)

    return ForemanShiftMatrix(
        kpi_id=kpi.id, kpi_code=kpi.code, kpi_name=kpi.name, kpi_unit=kpi.unit,
        success_direction_higher=kpi.success_direction_higher, reference_target=reference_target,
        shifts=shifts, rows=rows, insight=insight,
    )


@dataclass
class ForemanNamedStat:
    id: UUID
    name: str
    employee_number: str
    avg_actual: float
    record_count: int
    week_count: int


def _named(stat: ForemanCellStat, foreman: Foreman) -> ForemanNamedStat:
    return ForemanNamedStat(
        id=stat.foreman_id, name=f"{foreman.first_name} {foreman.last_name}",
        employee_number=foreman.employee_number, avg_actual=stat.avg_actual,
        record_count=stat.record_count, week_count=len(stat.week_indices),
    )


def _build_title(worse_name: str, better_name: str, shift_name: str, kpi_name: str) -> str:
    return f"{worse_name} ile {better_name} arasında {shift_name} vardiyasında {kpi_name} farkı tespit edildi"


@dataclass
class ShiftAnomalyCard:
    plant_id: UUID
    plant_name: str
    plant_sequence: int
    factory_id: UUID
    factory_code: str
    shift_id: UUID
    shift_name: str
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    kpi_unit: str
    kpi_decimal_places: int
    success_direction_higher: bool
    severity: str
    title: str
    better: ForemanNamedStat
    worse: ForemanNamedStat
    abs_diff: float
    pct_diff: float
    compared_weeks: int
    month_start: date
    month_end: date
    period_label: str


def build_cards(
    db: Session, month_start: date, month_end: date, *,
    plant_ids: list[UUID] | None = None, factory_ids: list[UUID] | None = None,
    kpi_ids: list[UUID] | None = None, shift_ids: list[UUID] | None = None,
    severity: str | None = None, thresholds: ShiftAnomalyThresholds = DEFAULT_THRESHOLDS,
) -> list[ShiftAnomalyCard]:
    rows = _fetch_raw_rows(
        db, month_start, month_end, plant_ids=plant_ids, factory_ids=factory_ids,
        kpi_ids=kpi_ids, shift_ids=shift_ids,
    )
    if not rows:
        return []
    cells = _group_cells(rows)

    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    plants_by_id = {p.id: p for p in db.scalars(select(Plant))}
    factories_by_id = {f.id: f for f in db.scalars(select(Factory))}
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    foreman_ids = {r.foreman_id for r in rows}
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_(foreman_ids)))}

    period_label = month_label(month_end)
    cards: list[ShiftAnomalyCard] = []

    for (plant_id, shift_id, kpi_id), by_foreman in cells.items():
        kpi = kpis_by_id.get(kpi_id)
        plant = plants_by_id.get(plant_id)
        shift = shifts_by_id.get(shift_id)
        if kpi is None or plant is None or shift is None:
            continue

        stats = [s for s in (_foreman_stat(fid, recs) for fid, recs in by_foreman.items()) if s is not None]
        extreme = _extreme_pair(stats, thresholds)
        if extreme is None:
            continue
        comparison = _compare_pair(*extreme, kpi.success_direction_higher, thresholds)
        if comparison is None:
            continue
        if severity and comparison.severity != severity:
            continue

        better_f = foremen_by_id.get(comparison.better.foreman_id)
        worse_f = foremen_by_id.get(comparison.worse.foreman_id)
        if better_f is None or worse_f is None:
            continue
        factory = factories_by_id.get(plant.factory_id)
        better_named = _named(comparison.better, better_f)
        worse_named = _named(comparison.worse, worse_f)

        cards.append(
            ShiftAnomalyCard(
                plant_id=plant_id, plant_name=plant.name, plant_sequence=plant.sequence_number,
                factory_id=plant.factory_id, factory_code=factory.code if factory else "",
                shift_id=shift_id, shift_name=shift.name,
                kpi_id=kpi_id, kpi_code=kpi.code, kpi_name=kpi.name, kpi_unit=kpi.unit,
                kpi_decimal_places=kpi.decimal_places,
                success_direction_higher=kpi.success_direction_higher,
                severity=comparison.severity,
                title=_build_title(worse_named.name, better_named.name, shift.name, kpi.name),
                better=better_named, worse=worse_named,
                abs_diff=comparison.abs_diff, pct_diff=comparison.pct_diff,
                compared_weeks=len(set(comparison.better.week_indices) | set(comparison.worse.week_indices)),
                month_start=month_start, month_end=month_end, period_label=period_label,
            )
        )

    severity_order = {"high": 0, "medium": 1}
    cards.sort(key=lambda c: (severity_order[c.severity], -c.pct_diff))
    return cards


@dataclass
class ShiftAnomalySummary:
    month_start: date
    month_end: date
    period_label: str
    total: int
    high_count: int
    medium_count: int
    top_plant: tuple[UUID, str, int] | None
    top_kpi: tuple[UUID, str, int] | None
    max_pct_diff: float | None


def build_summary(cards: list[ShiftAnomalyCard], month_start: date, month_end: date) -> ShiftAnomalySummary:
    plant_counts = Counter((c.plant_id, c.plant_name) for c in cards)
    kpi_counts = Counter((c.kpi_id, c.kpi_name) for c in cards)
    top_plant = None
    if plant_counts:
        (pid, pname), count = plant_counts.most_common(1)[0]
        top_plant = (pid, pname, count)
    top_kpi = None
    if kpi_counts:
        (kid, kname), count = kpi_counts.most_common(1)[0]
        top_kpi = (kid, kname, count)

    return ShiftAnomalySummary(
        month_start=month_start, month_end=month_end, period_label=month_label(month_end),
        total=len(cards),
        high_count=sum(1 for c in cards if c.severity == "high"),
        medium_count=sum(1 for c in cards if c.severity == "medium"),
        top_plant=top_plant, top_kpi=top_kpi,
        max_pct_diff=max((c.pct_diff for c in cards), default=None),
    )


def _month_week_indices(month_start: date, month_end: date) -> list[int]:
    n_days = (month_end - month_start).days + 1
    return sorted({_week_index(month_start + timedelta(days=i)) for i in range(n_days)})


def _foreman_week_values(records: list[_RawRow]) -> dict[int, tuple[float, int, UUID]]:
    by_week: dict[int, list[_RawRow]] = defaultdict(list)
    for r in records:
        by_week[_week_index(r.performance_date)].append(r)
    out: dict[int, tuple[float, int, UUID]] = {}
    for week_index, recs in by_week.items():
        denom = sum(x.denominator for x in recs)
        if denom == 0:
            continue
        numer = sum(x.numerator for x in recs)
        out[week_index] = (numer / denom * 100.0, len(recs), recs[0].shift_id)
    return out


def _fetch_assigned_week_indices(
    db: Session, month_start: date, month_end: date, plant_id: UUID, foreman_ids: set[UUID],
) -> dict[UUID, dict[int, UUID]]:
    """Bir formenin o hafta bu tesiste fiilen hangi vardiyada görevli olduğunu belirler.

    KPI/veri kalitesinden bağımsız olarak herhangi bir kayıt varlığı "o gün fiilen çalışıyor"
    sayılır; bu, "görevli değil" ile "görevli ama bu KPI için yeterli veri yok" durumlarını
    ayırt etmek için kullanılır.
    """
    stmt = select(PerformanceRecord.foreman_id, PerformanceRecord.performance_date, PerformanceRecord.shift_id).where(
        PerformanceRecord.plant_id == plant_id,
        PerformanceRecord.foreman_id.in_(foreman_ids),
        PerformanceRecord.performance_date >= month_start,
        PerformanceRecord.performance_date <= month_end,
    ).distinct()
    out: dict[UUID, dict[int, UUID]] = defaultdict(dict)
    for foreman_id, perf_date, shift_id in db.execute(stmt).all():
        out[foreman_id][_week_index(perf_date)] = shift_id
    return out


@dataclass
class WeeklyForemanPoint:
    assigned: bool
    value: float | None
    day_count: int
    has_sufficient_data: bool
    shift_id: UUID | None = None
    shift_name: str | None = None


@dataclass
class ShiftWeeklyComparisonPoint:
    week_index: int
    week_label: str
    better: WeeklyForemanPoint
    worse: WeeklyForemanPoint


def _weekly_comparison(
    month_start: date, month_end: date, assigned_weeks: dict[UUID, dict[int, UUID]],
    better_id: UUID, better_values: dict[int, tuple[float, int, UUID]],
    worse_id: UUID, worse_values: dict[int, tuple[float, int, UUID]],
    shifts_by_id: dict[UUID, Shift],
) -> list[ShiftWeeklyComparisonPoint]:
    def point_for(foreman_id: UUID, week_index: int, values: dict[int, tuple[float, int, UUID]]) -> WeeklyForemanPoint:
        if week_index in values:
            value, day_count, shift_id = values[week_index]
            shift = shifts_by_id.get(shift_id)
            return WeeklyForemanPoint(
                assigned=True, value=value, day_count=day_count, has_sufficient_data=True,
                shift_id=shift_id, shift_name=shift.name if shift else None,
            )
        week_shift_id = assigned_weeks.get(foreman_id, {}).get(week_index)
        if week_shift_id is not None:
            shift = shifts_by_id.get(week_shift_id)
            return WeeklyForemanPoint(
                assigned=True, value=None, day_count=0, has_sufficient_data=False,
                shift_id=week_shift_id, shift_name=shift.name if shift else None,
            )
        return WeeklyForemanPoint(assigned=False, value=None, day_count=0, has_sufficient_data=False)

    week_indices = _month_week_indices(month_start, month_end)
    ordinal = {w: i + 1 for i, w in enumerate(week_indices)}
    return [
        ShiftWeeklyComparisonPoint(
            week_index=ordinal[w], week_label=f"Hafta {ordinal[w]}",
            better=point_for(better_id, w, better_values),
            worse=point_for(worse_id, w, worse_values),
        )
        for w in week_indices
    ]


def _is_consistent_pattern(weekly_points: list[dict], better_id: UUID, worse_id: UUID, higher_is_better: bool) -> bool:
    better_vals = [p["avg_actual"] for p in weekly_points if p["foreman_id"] == better_id]
    worse_vals = [p["avg_actual"] for p in weekly_points if p["foreman_id"] == worse_id]
    if not better_vals or not worse_vals:
        return False
    if higher_is_better:
        return min(better_vals) > max(worse_vals)
    return max(better_vals) < min(worse_vals)


@dataclass
class CrossKpiSignal:
    kpi_id: UUID
    kpi_code: str
    kpi_name: str
    pct_diff: float
    severity: str
    same_foreman_better: bool


def _cross_kpi_signals(
    by_kpi: dict[UUID, dict[UUID, list[_RawRow]]], current_kpi_id: UUID,
    better_id: UUID, worse_id: UUID, kpis_by_id: dict[UUID, Kpi], thresholds: ShiftAnomalyThresholds,
) -> list[CrossKpiSignal]:
    signals = []
    for kid, by_foreman in by_kpi.items():
        if kid == current_kpi_id:
            continue
        kpi = kpis_by_id.get(kid)
        if kpi is None:
            continue
        better_recs = by_foreman.get(better_id)
        worse_recs = by_foreman.get(worse_id)
        if not better_recs or not worse_recs:
            continue
        better_stat = _foreman_stat(better_id, better_recs)
        worse_stat = _foreman_stat(worse_id, worse_recs)
        if better_stat is None or worse_stat is None:
            continue
        comparison = _compare_pair(better_stat, worse_stat, kpi.success_direction_higher, thresholds)
        if comparison is None:
            continue
        signals.append(
            CrossKpiSignal(
                kpi_id=kid, kpi_code=kpi.code, kpi_name=kpi.name,
                pct_diff=comparison.pct_diff, severity=comparison.severity,
                same_foreman_better=comparison.better.foreman_id == better_id,
            )
        )
    signals.sort(key=lambda s: -s.pct_diff)
    return signals


_GENITIVE_SUFFIX_BY_VOWEL = {
    "a": "ın", "ı": "ın", "A": "ın", "I": "ın",
    "e": "in", "i": "in", "E": "in", "İ": "in",
    "o": "un", "u": "un", "O": "un", "U": "un",
    "ö": "ün", "ü": "ün", "Ö": "ün", "Ü": "ün",
}
_TURKISH_VOWELS = set(_GENITIVE_SUFFIX_BY_VOWEL)


def _possessive_form(name: str) -> str:
    """Bir kişi adına Türkçe iyelik eki ekler — büyük ünlü uyumuna göre 'ın/'in/'un/'ün seçer.

    Örn. "Ali Öztürk" -> "Ali Öztürk'ün", "Volkan Aslan" -> "Volkan Aslan'ın". Sabit bir ek
    (örn. her zaman "'ün") kullanmak isim setine göre yanlış sonuç üretir; bu yüzden adın son
    ünlüsüne bakılır. Ad bir ünlüyle bitiyorsa araya kaynaştırma "n" harfi eklenir.
    """
    last_vowel = next((ch for ch in reversed(name) if ch in _TURKISH_VOWELS), None)
    if last_vowel is None:
        return f"{name}'in"
    suffix = _GENITIVE_SUFFIX_BY_VOWEL[last_vowel]
    buffer = "n" if name[-1] in _TURKISH_VOWELS else ""
    return f"{name}'{buffer}{suffix}"


def _build_pattern_commentary(
    *, kpi_name: str, worse_name: str, better_name: str, is_consistent: bool, has_enough_weeks: bool,
    cross_kpi_signals: list[CrossKpiSignal],
) -> tuple[str, str]:
    if not has_enough_weeks:
        headline = "Sınırlı veri — örüntü netleştirilemedi."
        detail = (
            "Bu karşılaştırma az sayıda haftaya dayanıyor; farkın kalıcı bir örüntü mü yoksa tek seferlik "
            "bir sapma mı olduğu bu ayın verisiyle netleşmiyor."
        )
    elif is_consistent:
        headline = "Fark ay boyunca tekrar ediyor."
        detail = (
            f"{_possessive_form(worse_name)} görev aldığı haftalarda {kpi_name}, {_possessive_form(better_name)} "
            f"görev aldığı haftalara göre belirgin şekilde farklı seyrediyor."
        )
    else:
        headline = "Fark haftalara göre değişkenlik gösteriyor."
        detail = (
            "Ay geneline yayılmış tutarlı bir örüntüden ziyade belirli haftalarda yoğunlaşan bir sapma olabilir; "
            "haftalık kırılıma bakılması önerilir."
        )

    signal_names = [s.kpi_name for s in cross_kpi_signals]
    if signal_names:
        joined = ", ".join(signal_names)
        count = len(signal_names)
        detail += (
            f" Aynı formen çifti arasında {count} farklı KPI'da ({joined}) da anlamlı fark bulunuyor; bu durum "
            f"tekrarlayan bir performans örüntüsüne işaret ediyor. Ek operasyonel inceleme önerilir."
        )
    else:
        detail += f" Bu fark yalnızca {kpi_name} KPI'ında gözlemleniyor; diğer KPI'larda benzer bir sapma tespit edilmedi."

    return headline, detail


@dataclass
class ShiftAnomalyDetail(ShiftAnomalyCard):
    reference_target: float = 0.0
    weekly_comparison: list[ShiftWeeklyComparisonPoint] = field(default_factory=list)
    cross_kpi_signals: list[CrossKpiSignal] = field(default_factory=list)
    pattern_headline: str = ""
    pattern_detail: str = ""
    is_recurring_pattern: bool = False


def build_detail(
    db: Session, *, plant_id: UUID, shift_id: UUID, kpi_id: UUID, month_start: date, month_end: date,
    thresholds: ShiftAnomalyThresholds = DEFAULT_THRESHOLDS,
) -> ShiftAnomalyDetail | None:
    rows = _fetch_raw_rows(db, month_start, month_end, plant_ids=[plant_id], shift_ids=[shift_id])
    if not rows:
        return None

    by_kpi: dict[UUID, dict[UUID, list[_RawRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by_kpi[r.kpi_id][r.foreman_id].append(r)
    if kpi_id not in by_kpi:
        return None

    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    kpi = kpis_by_id.get(kpi_id)
    if kpi is None:
        return None

    stats = [s for s in (_foreman_stat(fid, recs) for fid, recs in by_kpi[kpi_id].items()) if s is not None]
    extreme = _extreme_pair(stats, thresholds)
    if extreme is None:
        return None
    comparison = _compare_pair(*extreme, kpi.success_direction_higher, thresholds)
    if comparison is None:
        return None

    plant = db.get(Plant, plant_id)
    shift = db.get(Shift, shift_id)
    if plant is None or shift is None:
        return None
    factory = db.get(Factory, plant.factory_id)

    better_id, worse_id = comparison.better.foreman_id, comparison.worse.foreman_id
    foremen_by_id = {f.id: f for f in db.scalars(select(Foreman).where(Foreman.id.in_([better_id, worse_id])))}
    better_f, worse_f = foremen_by_id.get(better_id), foremen_by_id.get(worse_id)
    if better_f is None or worse_f is None:
        return None
    better_named = _named(comparison.better, better_f)
    worse_named = _named(comparison.worse, worse_f)
    period_label = month_label(month_end)

    all_shift_rows = _fetch_raw_rows(db, month_start, month_end, plant_ids=[plant_id], kpi_ids=[kpi_id])
    by_foreman_any_shift: dict[UUID, list[_RawRow]] = defaultdict(list)
    for r in all_shift_rows:
        if r.foreman_id in (better_id, worse_id):
            by_foreman_any_shift[r.foreman_id].append(r)

    better_week_values = _foreman_week_values(by_foreman_any_shift.get(better_id, []))
    worse_week_values = _foreman_week_values(by_foreman_any_shift.get(worse_id, []))
    assigned_weeks = _fetch_assigned_week_indices(db, month_start, month_end, plant_id, {better_id, worse_id})
    shifts_by_id = {s.id: s for s in db.scalars(select(Shift))}
    weekly_comparison = _weekly_comparison(
        month_start, month_end, assigned_weeks,
        better_id, better_week_values, worse_id, worse_week_values, shifts_by_id,
    )

    flat_points = [{"foreman_id": better_id, "avg_actual": v} for v, _, _ in better_week_values.values()] + [
        {"foreman_id": worse_id, "avg_actual": v} for v, _, _ in worse_week_values.values()
    ]
    has_enough_weeks = comparison.better.week_indices and comparison.worse.week_indices and (
        len(comparison.better.week_indices) >= 2 or len(comparison.worse.week_indices) >= 2
    )
    is_consistent = has_enough_weeks and _is_consistent_pattern(
        flat_points, better_id, worse_id, kpi.success_direction_higher
    )
    signals = _cross_kpi_signals(by_kpi, kpi_id, better_id, worse_id, kpis_by_id, thresholds)
    pattern_headline, pattern_detail = _build_pattern_commentary(
        kpi_name=kpi.name, worse_name=worse_named.name, better_name=better_named.name,
        is_consistent=is_consistent, has_enough_weeks=bool(has_enough_weeks), cross_kpi_signals=signals,
    )

    target_filters = Filters(date_from=month_start, date_to=month_end, plant_ids=[plant_id], kpi_ids=[kpi_id])
    target_summary = analytics.kpi_summary(db, target_filters)
    reference_target = (
        target_summary[0].avg_target
        if target_summary and target_summary[0].avg_target is not None
        else float(kpi.default_target_value)
    )

    return ShiftAnomalyDetail(
        plant_id=plant_id, plant_name=plant.name, plant_sequence=plant.sequence_number,
        factory_id=plant.factory_id, factory_code=factory.code if factory else "",
        shift_id=shift_id, shift_name=shift.name,
        kpi_id=kpi_id, kpi_code=kpi.code, kpi_name=kpi.name, kpi_unit=kpi.unit,
        kpi_decimal_places=kpi.decimal_places,
        success_direction_higher=kpi.success_direction_higher,
        severity=comparison.severity,
        title=_build_title(worse_named.name, better_named.name, shift.name, kpi.name),
        better=better_named, worse=worse_named,
        abs_diff=comparison.abs_diff, pct_diff=comparison.pct_diff,
        compared_weeks=len(set(comparison.better.week_indices) | set(comparison.worse.week_indices)),
        month_start=month_start, month_end=month_end, period_label=period_label,
        reference_target=reference_target, weekly_comparison=weekly_comparison, cross_kpi_signals=signals,
        pattern_headline=pattern_headline, pattern_detail=pattern_detail, is_recurring_pattern=is_consistent,
    )
