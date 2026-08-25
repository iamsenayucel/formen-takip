
from __future__ import annotations

import math
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import clock
from app.models.enums import SourceSystem
from app.models.production import CompanyCalendarDay, ForemanWorkCalendar, Product, ProductionLine, ProductionRecord
from app.services.kpi_engine import SHIFT_MINUTES
from app.services.shift_rotation import actual_shift_for_date
from app.services.synthetic.reference_data import ReferenceData

FIXED_HOLIDAYS_MMDD = {(1, 1), (4, 23), (5, 1), (5, 19), (7, 15), (8, 30), (10, 29)}


def shift_window_utc(production_date: date, shift) -> tuple[datetime, datetime]:
    """`production_date` iş tarihinde çalışan vardiyanın UTC [start, end) aralığını döndürür.

    Yerel başlangıç/bitiş saatleri sabit offset yerine `settings.timezone` üzerinden
    `clock.to_utc` ile bağlanır; tarihsel DST kuralları doğru uygulanır.
    """
    end_date = production_date + timedelta(days=1) if shift.crosses_midnight else production_date
    start = clock.to_utc(datetime.combine(production_date, shift.start_time))
    end = clock.to_utc(datetime.combine(end_date, shift.end_time))
    return start, end

PRODUCT_CATALOG = [
    dict(code="MLZ-001", name="Yem Tipi A - 40gr Paket", standard_gram=40.0, tolerance_pct=0.05),
    dict(code="MLZ-002", name="Yem Tipi B - 25gr Paket", standard_gram=25.0, tolerance_pct=0.06),
    dict(code="MLZ-003", name="Yem Tipi C - 50gr Paket", standard_gram=50.0, tolerance_pct=0.04),
    dict(code="MLZ-004", name="Yem Tipi D - 20gr Paket", standard_gram=20.0, tolerance_pct=0.07),
    dict(code="MLZ-005", name="Yem Tipi E - 35gr Paket (standart tanımlanmadı)", standard_gram=None, tolerance_pct=None),
    dict(code="MLZ-006", name="Yem Tipi F - 60gr Paket", standard_gram=60.0, tolerance_pct=0.03),
    dict(code="MLZ-007", name="Yem Tipi G - 30gr Paket (standart tanımlanmadı)", standard_gram=None, tolerance_pct=None),
    dict(code="MLZ-008", name="Yem Tipi H - 45gr Paket", standard_gram=45.0, tolerance_pct=0.05),
]


@dataclass
class GenerationParams:
    missing_rate: float = 0.02
    error_rate: float = 0.01
    anomaly_rate: float = 0.015
    duplicate_rate: float = 0.005


@dataclass
class ProductionReferenceData:
    products: list[Product] = field(default_factory=list)
    lines_by_plant: dict = field(default_factory=dict)
    holiday_dates: set = field(default_factory=set)
    work_calendar: list[ForemanWorkCalendar] = field(default_factory=list)
    production_records: list[ProductionRecord] = field(default_factory=list)


def _is_holiday(d: date) -> bool:
    return (d.month, d.day) in FIXED_HOLIDAYS_MMDD


def _seasonal_factor(d: date) -> float:
    day_of_year = d.timetuple().tm_yday
    return 0.04 * math.sin(2 * math.pi * (day_of_year - 80) / 365)


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _seed_products(db: Session) -> list[Product]:
    products = []
    for spec in PRODUCT_CATALOG:
        std = spec["standard_gram"]
        tol = spec["tolerance_pct"]
        lower = (std * (1 - tol)) if (std is not None and tol is not None) else None
        upper = (std * (1 + tol)) if (std is not None and tol is not None) else None
        product = Product(
            code=spec["code"], name=spec["name"], unit="GR",
            standard_gram=std, lower_gram_limit=lower, upper_gram_limit=upper,
            is_active=True, sap_material_code=f"SAP-{spec['code']}",
        )
        db.add(product)
        products.append(product)
    db.flush()
    return products


def _seed_production_lines(db: Session, rng: random.Random, plants) -> dict:
    lines_by_plant: dict = {}
    for plant in plants:
        count = rng.randint(1, 2)
        plant_lines = []
        for i in range(1, count + 1):
            line = ProductionLine(
                code=f"HAT-{plant.sequence_number:02d}-{i}", name=f"{plant.name} - Hat {i}",
                plant_id=plant.id, is_active=True,
            )
            db.add(line)
            plant_lines.append(line)
        lines_by_plant[plant.id] = plant_lines
    db.flush()
    return lines_by_plant


def _seed_holidays(db: Session, period_start: date, period_end: date) -> set:
    holiday_dates: set = set()
    d = period_start
    while d <= period_end:
        if _is_holiday(d):
            db.add(CompanyCalendarDay(calendar_date=d, is_holiday=True, note="Resmi tatil"))
            holiday_dates.add(d)
        d += timedelta(days=1)
    db.flush()
    return holiday_dates


def _build_plant_profiles(plants, rng: random.Random) -> dict:
    return {p.id: {"base": rng.uniform(-0.12, 0.12), "trend": rng.uniform(-0.00015, 0.00025)} for p in plants}


PERFORMANCE_TIER_WEIGHTS = {"LOW": 0.275, "MEDIUM": 0.375, "HIGH": 0.35}
TIER_SKILL_CENTER = {"LOW": -2.35, "MEDIUM": -0.60, "HIGH": 0.12}
TIER_SKILL_SPREAD = {"LOW": 0.45, "MEDIUM": 0.32, "HIGH": 0.42}
KPI_SKILL_DECORRELATION = 0.22
RECOVERY_SKILL_SPREAD = 0.35
ASSIGNMENT_SKILL_SIGMA = 0.05
DAILY_SKILL_SIGMA = 0.07
DAY_CONTEXT_SIGMA = 0.03
YEAR_SKILL_SIGMA = 0.25

AGIR_GITME_SENSITIVITY = 3.0
AGIR_GITME_TARGET_EXCESS_FRACTION = 0.015
SCRAP_FRACTION_BASELINE = 0.05
SCRAP_FRACTION_SENSITIVITY = 0.028
RECOVERABLE_FRACTION_BASELINE = 0.40
RECOVERABLE_FRACTION_SENSITIVITY = 0.16
DOWNTIME_TECHNICAL_BASELINE_MIN = 43.0
DOWNTIME_MANUFACTURING_BASELINE_MIN = 29.0
INKITA_SENSITIVITY = 0.55
PRODUCTION_FACTOR_SENSITIVITY = 0.35


def _assign_foreman_tiers(foremen, rng: random.Random) -> dict:
    n = len(foremen)
    tier_names = list(PERFORMANCE_TIER_WEIGHTS)
    counts: dict[str, int] = {}
    remaining = n
    for i, tier in enumerate(tier_names):
        if i == len(tier_names) - 1:
            counts[tier] = remaining
        else:
            count = round(n * PERFORMANCE_TIER_WEIGHTS[tier])
            counts[tier] = count
            remaining -= count
    pool: list[str] = []
    for tier, count in counts.items():
        pool.extend([tier] * count)
    rng.shuffle(pool)
    return {f.id: tier for f, tier in zip(foremen, pool)}


def _build_foreman_profiles(foremen, tiers_by_foreman: dict, rng: random.Random) -> dict:
    profiles: dict = {}
    for f in foremen:
        tier = tiers_by_foreman[f.id]
        center = TIER_SKILL_CENTER[tier] + rng.uniform(-TIER_SKILL_SPREAD[tier], TIER_SKILL_SPREAD[tier])
        skills = {
            "agir_gitme": center + rng.uniform(-KPI_SKILL_DECORRELATION, KPI_SKILL_DECORRELATION),
            "scrap": center + rng.uniform(-KPI_SKILL_DECORRELATION, KPI_SKILL_DECORRELATION),
            "recovery": rng.uniform(-RECOVERY_SKILL_SPREAD, RECOVERY_SKILL_SPREAD),
            "inkita": center + rng.uniform(-KPI_SKILL_DECORRELATION, KPI_SKILL_DECORRELATION),
            "plana_uyum": center + rng.uniform(-KPI_SKILL_DECORRELATION, KPI_SKILL_DECORRELATION),
        }
        profiles[f.id] = {"tier": tier, "skills": skills, "trend": rng.uniform(-0.0004, 0.0004)}
    return profiles


def _build_assignment_offsets(assignments, rng: random.Random) -> dict:
    return {(a.foreman_id, a.plant_id): rng.gauss(0, ASSIGNMENT_SKILL_SIGMA) for a in assignments}


def _build_maintenance_windows(plants, rng: random.Random, period_start: date, period_end: date) -> dict:
    windows: dict = defaultdict(set)
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return windows
    for plant in plants:
        for _ in range(rng.randint(1, 3)):
            start = period_start + timedelta(days=rng.randint(0, total_days - 1))
            for i in range(rng.randint(1, 3)):
                windows[plant.id].add(start + timedelta(days=i))
    return windows


def _plant_product_pool(plants, products: list[Product], rng: random.Random) -> dict:
    pool: dict = {}
    for plant in plants:
        count = rng.randint(2, 4)
        pool[plant.id] = rng.sample(products, k=min(count, len(products)))
    return pool


def seed_production_data(
    db: Session,
    rng: random.Random,
    ref: ReferenceData,
    period_start: date,
    period_end: date,
    params: GenerationParams,
) -> ProductionReferenceData:
    result = ProductionReferenceData()
    result.products = _seed_products(db)
    result.lines_by_plant = _seed_production_lines(db, rng, ref.plants)
    result.holiday_dates = _seed_holidays(db, period_start, period_end)

    plant_profiles = _build_plant_profiles(ref.plants, rng)
    foreman_tiers = _assign_foreman_tiers(ref.foremen, rng)
    foreman_profiles = _build_foreman_profiles(ref.foremen, foreman_tiers, rng)
    assignment_offsets = _build_assignment_offsets(ref.assignments, rng)
    maintenance_days = _build_maintenance_windows(ref.plants, rng, period_start, period_end)
    plant_products = _plant_product_pool(ref.plants, result.products, rng)

    shifts_by_id = {s.id: s for s in ref.shifts}
    assignments_by_foreman: dict = defaultdict(list)
    for a in ref.assignments:
        assignments_by_foreman[a.foreman_id].append(a)

    seq = 0

    for foreman in ref.foremen:
        f_profile = foreman_profiles[foreman.id]
        foreman_assignments = assignments_by_foreman[foreman.id]
        if not foreman_assignments:
            continue

        tenure_start = foreman_assignments[0].start_date
        tenure_end = foreman_assignments[0].end_date
        range_start = max(tenure_start, period_start)
        range_end = min(tenure_end or period_end, period_end)
        if range_start > range_end:
            continue

        anchor_shift = shifts_by_id[foreman_assignments[0].shift_id]
        year_offsets = {year: rng.gauss(0, YEAR_SKILL_SIGMA) for year in range(range_start.year, range_end.year + 1)}

        for assignment in foreman_assignments:
            plant_profile = plant_profiles[assignment.plant_id]
            plant_lines = result.lines_by_plant[assignment.plant_id]
            products = plant_products[assignment.plant_id]

            assignment_offset = assignment_offsets.get((foreman.id, assignment.plant_id), 0.0)
            skills = f_profile["skills"]

            d = range_start
            while d <= range_end:
                shift = actual_shift_for_date(d, anchor_shift, ref.shifts)

                is_holiday = d in result.holiday_dates
                is_absent = (not is_holiday) and rng.random() < 0.03
                is_working = not is_holiday and not is_absent
                line = rng.choice(plant_lines)

                calendar_row = ForemanWorkCalendar(
                    foreman_id=foreman.id, work_date=d, plant_id=assignment.plant_id,
                    chief_id=assignment.chief_id, shift_id=shift.id, line_id=line.id,
                    is_working=is_working,
                )
                db.add(calendar_row)
                result.work_calendar.append(calendar_row)

                if not is_working:
                    d += timedelta(days=1)
                    continue

                weekday = d.weekday()
                weekend_factor = -0.033 if weekday >= 5 else 0.0
                night_penalty = -0.017 if shift.code == "V2" else 0.0
                is_maintenance = d in maintenance_days.get(assignment.plant_id, set())
                maintenance_factor = -0.18 if is_maintenance else 0.0

                anomaly = 0.0
                if rng.random() < params.anomaly_rate:
                    anomaly = rng.choice([-1, 1]) * rng.uniform(0.05, 0.12)

                day_context = (
                    plant_profile["base"] + plant_profile["trend"] * (d - period_start).days
                    + f_profile["trend"] * (d - tenure_start).days + assignment_offset
                    + night_penalty + weekend_factor + maintenance_factor
                    + _seasonal_factor(d) * 0.4 + anomaly + rng.gauss(0, DAY_CONTEXT_SIGMA)
                    + year_offsets[d.year]
                )

                def _daily_skill(base_skill: float) -> float:
                    return base_skill + day_context + rng.gauss(0, DAILY_SKILL_SIGMA)

                skill_agir = _daily_skill(skills["agir_gitme"])
                skill_scrap = _daily_skill(skills["scrap"])
                skill_recovery = _daily_skill(skills["recovery"])
                skill_inkita = _daily_skill(skills["inkita"])
                skill_plana = _daily_skill(skills["plana_uyum"])

                downtime_multiplier = _clip(1.0 - skill_inkita * INKITA_SENSITIVITY, 0.15, 3.2)
                technical_minutes = max(0.0, DOWNTIME_TECHNICAL_BASELINE_MIN * downtime_multiplier + rng.gauss(0, 6))
                manufacturing_minutes = max(0.0, DOWNTIME_MANUFACTURING_BASELINE_MIN * downtime_multiplier + rng.gauss(0, 4))
                other_minutes = max(0.0, rng.uniform(10, 25) + rng.gauss(0, 3))
                if is_maintenance:
                    other_minutes += rng.uniform(90, 220)

                production_factor = _clip(1.0 + skill_plana * PRODUCTION_FACTOR_SENSITIVITY, 0.15, 1.8)
                planned_qty = 1000.0
                actual_qty = max(0.0, planned_qty * production_factor + rng.gauss(0, 15))

                scrap_fraction = _clip(
                    SCRAP_FRACTION_BASELINE - skill_scrap * SCRAP_FRACTION_SENSITIVITY + rng.gauss(0, 0.004), 0.0, 0.35
                )
                scrap_qty = actual_qty * scrap_fraction
                recoverable_fraction = _clip(
                    RECOVERABLE_FRACTION_BASELINE + skill_recovery * RECOVERABLE_FRACTION_SENSITIVITY
                    + rng.gauss(0, 0.03), 0.05, 0.95,
                )
                iskarta_qty = scrap_qty * recoverable_fraction
                gsf_qty = scrap_qty - iskarta_qty

                product = rng.choice(products)
                if product.standard_gram is not None and product.upper_gram_limit is not None:
                    standard_gram = float(product.standard_gram)
                    threshold_overage = float(product.upper_gram_limit) - standard_gram
                    neutral_overage = threshold_overage + AGIR_GITME_TARGET_EXCESS_FRACTION * standard_gram
                    gram_overage = neutral_overage * (1 - skill_agir * AGIR_GITME_SENSITIVITY) + rng.gauss(0, 0.4)
                    measured_avg_gram = standard_gram + gram_overage
                else:
                    measured_avg_gram = 35.0 + rng.gauss(0, 1.0)
                gram_sample_count = rng.randint(15, 40)

                planned_start, planned_end = shift_window_utc(d, shift)
                actual_start = planned_start + timedelta(minutes=rng.gauss(0, 4))
                actual_end = planned_end + timedelta(minutes=rng.gauss(0, 6))
                shift_hours = (planned_end - planned_start).total_seconds() / 3600.0

                roll = rng.random()
                if roll < params.missing_rate:
                    actual_qty = None
                    actual_speed = None
                    actual_start_val = None
                    actual_end_val = None
                elif roll < params.missing_rate + params.error_rate:
                    actual_qty = -abs(actual_qty) - rng.uniform(1, 50)
                    actual_speed = actual_qty / shift_hours if actual_qty else None
                    actual_start_val = actual_start
                    actual_end_val = actual_end
                else:
                    actual_speed = actual_qty / shift_hours
                    actual_start_val = actual_start
                    actual_end_val = actual_end

                seq += 1
                record = ProductionRecord(
                    source_system=SourceSystem.SYNTHETIC,
                    source_record_id=f"PROD-{seq:09d}-{uuid.uuid4().hex[:8]}",
                    production_order_number=f"45{seq:08d}",
                    batch_number=f"LOT-{d.strftime('%y%m%d')}-{seq % 100:02d}",
                    plant_id=assignment.plant_id, line_id=line.id, product_id=product.id,
                    foreman_id=foreman.id, chief_id=assignment.chief_id, shift_id=shift.id,
                    production_date=d, unit="KG",
                    planned_qty=planned_qty, actual_qty=actual_qty,
                    planned_start_at=planned_start, planned_end_at=planned_end,
                    actual_start_at=actual_start_val, actual_end_at=actual_end_val,
                    standard_speed=planned_qty / shift_hours, actual_speed=actual_speed,
                    measured_avg_gram=measured_avg_gram, gram_sample_count=gram_sample_count,
                    gsf_qty=gsf_qty, iskarta_qty=iskarta_qty,
                    technical_downtime_minutes=technical_minutes, manufacturing_downtime_minutes=manufacturing_minutes,
                    other_downtime_minutes=other_minutes,
                    plan_revision_no=1, plan_revision_at=planned_start - timedelta(days=1),
                    source_updated_at=clock.to_utc(datetime.combine(d, datetime.min.time())),
                    imported_at=clock.now_utc(),
                )
                db.add(record)
                result.production_records.append(record)

                d += timedelta(days=1)

    _assign_shift_working_time(result.production_records)

    db.commit()
    return result


def _assign_shift_working_time(records: list[ProductionRecord]) -> None:
    """Her vardiya kaydı için working_time_minutes = 720 - shift_downtime_minutes hesaplar.

    V1/V2 kendi downtime değerini kullanır; fabrika-gün canonical kaydı veya date-parity
    ataması yoktur. Formen OEE yalnızca sorumlu olduğu vardiyayı yansıtır. Fabrika/dönem
    OEE, analytics katmanında kapsamdaki vardiyaların pay/payda (çalışma dakikası/720)
    toplamından üretilir. Hesap deterministiktir; RNG kullanılmaz.
    """
    for record in records:
        if record.planned_start_at is None or record.planned_end_at is None:
            continue
        shift_downtime_minutes = (
            float(record.technical_downtime_minutes or 0.0)
            + float(record.manufacturing_downtime_minutes or 0.0)
            + float(record.other_downtime_minutes or 0.0)
        )
        working_time_minutes = _clip(SHIFT_MINUTES - shift_downtime_minutes, 0.0, SHIFT_MINUTES)
        record.working_time_minutes = round(working_time_minutes, 2)
