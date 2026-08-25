from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.enums import TargetScopeType
from app.models.foreman import Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiTarget
from app.models.organization import Factory, Plant, Shift
from app.schemas.common import Filters
from app.services import analytics
from app.services.shift_analysis import month_label
from app.services.shift_rotation import actual_shift_for_date
from app.services.synthetic import world
from app.services.target_resolver import NoTargetFoundError, resolve_target


def _month_bounds(d: date) -> tuple[date, date]:
    start = d.replace(day=1)
    next_start = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    return start, next_start - timedelta(days=1)


def resolve_kpi_target(db: Session, kpi: Kpi, plant: Plant, as_of: date, foreman_id: UUID | None = None) -> float:
    candidates = list(db.scalars(select(KpiTarget).where(KpiTarget.kpi_id == kpi.id)))
    try:
        resolved = resolve_target(
            candidates, as_of=as_of, foreman_id=foreman_id or uuid4(), chief_id=plant.chief_id, plant_id=plant.id,
        )
        return float(resolved.target_value)
    except NoTargetFoundError:
        return float(kpi.default_target_value)


def resolve_company_kpi_target(db: Session, kpi: Kpi, as_of: date) -> float:
    """Dar FOREMAN/CHIEF/PLANT override'larını yok sayıp şirket geneli KPI hedefini döndürür.

    Birden fazla tesisi kapsayan değerlerde tesis hedefi tüm karşılaştırma satırlarına
    uygulanamayacağı için kullanılır.
    """
    candidates = [
        c for c in db.scalars(select(KpiTarget).where(KpiTarget.kpi_id == kpi.id))
        if c.scope_type == TargetScopeType.COMPANY
    ]
    try:
        resolved = resolve_target(candidates, as_of=as_of, foreman_id=uuid4(), chief_id=uuid4(), plant_id=uuid4())
        return float(resolved.target_value)
    except NoTargetFoundError:
        return float(kpi.default_target_value)


def _foreman_kpi_trend(db: Session, foreman_id: UUID, kpi: Kpi, plant_id: UUID, ref_date: date, months: int = 3) -> list[dict]:
    windows: list[tuple[date, date]] = []
    cursor = ref_date.replace(day=1)
    for _ in range(months):
        start, end = _month_bounds(cursor)
        windows.append((start, end))
        cursor = (start - timedelta(days=1)).replace(day=1)
    windows.reverse()

    out = []
    for start, end in windows:
        filters = Filters(date_from=start, date_to=end, plant_ids=[plant_id], foreman_ids=[foreman_id])
        rows = analytics.kpi_breakdown(db, filters, foreman_id=foreman_id)
        entry = next((r for r in rows if r["kpi_id"] == kpi.id), None)
        has_data = entry is not None and entry.get("avg_actual") is not None
        out.append(
            {
                "period_label": month_label(end),
                "avg_actual": round(entry["avg_actual"], 2) if has_data else None,
                "has_data": has_data,
            }
        )
    return out


def _foreman_ref(db: Session, foreman_id: UUID) -> dict | None:
    f = db.get(Foreman, foreman_id)
    if f is None:
        return None
    return {"id": str(f.id), "name": f"{f.first_name} {f.last_name}", "employee_number": f.employee_number}


def resolve_responsible_foreman(db: Session, anomaly: Anomaly) -> dict:
    shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence)))
    assignments = list(
        db.scalars(
            select(ForemanAssignment).where(
                ForemanAssignment.plant_id == anomaly.plant_id,
                ForemanAssignment.start_date <= anomaly.period_end,
                or_(ForemanAssignment.end_date.is_(None), ForemanAssignment.end_date >= anomaly.period_start),
            )
        )
    )

    empty = {"resolved": False, "shift_specific": anomaly.shift_id is not None, "reason": None, "note": None, "primary": None, "others": [], "kpi_trend": []}

    if not assignments or not shifts:
        return {**empty, "reason": "Bu dönem için formen ataması bulunamadı."}

    if anomaly.shift_id is None:
        foreman_ids = sorted({a.foreman_id for a in assignments}, key=str)
        refs = [r for fid in foreman_ids if (r := _foreman_ref(db, fid)) is not None]
        if not refs:
            return {**empty, "reason": "Sorumlu formen bilgisi bulunamadı."}
        return {
            "resolved": True, "shift_specific": False, "reason": None,
            "note": "Tespit belirli bir vardiyaya bağlı olmadığından dönem içinde tesiste görev yapan formenler listelenmiştir.",
            "primary": refs[0], "others": refs[1:], "kpi_trend": [],
        }

    day_counts: dict[UUID, int] = defaultdict(int)
    d = anomaly.period_start
    while d <= anomaly.period_end:
        for a in assignments:
            if a.start_date <= d and (a.end_date is None or a.end_date >= d):
                anchor = next((s for s in shifts if s.id == a.shift_id), None)
                if anchor is not None and actual_shift_for_date(d, anchor, shifts).id == anomaly.shift_id:
                    day_counts[a.foreman_id] += 1
        d += timedelta(days=1)

    if not day_counts:
        return {**empty, "reason": "Sorumlu formen bilgisi bulunamadı."}

    total_days = sum(day_counts.values())
    ordered = sorted(day_counts.items(), key=lambda kv: (-kv[1], str(kv[0])))
    primary_id, primary_days = ordered[0]
    primary_ref = _foreman_ref(db, primary_id)
    if primary_ref is None:
        return {**empty, "reason": "Sorumlu formen bilgisi bulunamadı."}

    others = []
    for fid, cnt in ordered[1:]:
        ref = _foreman_ref(db, fid)
        if ref is not None:
            others.append({**ref, "day_count": cnt})

    kpi = db.get(Kpi, anomaly.kpi_id)
    kpi_trend = _foreman_kpi_trend(db, primary_id, kpi, anomaly.plant_id, anomaly.detected_at.date()) if kpi is not None else []

    note = (
        "Dönem içinde vardiya rotasyonu nedeniyle birden fazla formen görev yapmıştır; "
        "aşağıdaki formen en fazla gün için sorumluydu."
        if others else None
    )

    return {
        "resolved": True, "shift_specific": True, "reason": None, "note": note,
        "primary": {**primary_ref, "day_count": primary_days, "total_days": total_days},
        "others": others, "kpi_trend": kpi_trend,
    }


def build_baseline_comparison(db: Session, anomaly: Anomaly, plant: Plant, kpi: Kpi, shift: Shift | None) -> dict:
    period_days = (anomaly.period_end - anomaly.period_start).days + 1
    baseline_end = anomaly.period_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=period_days - 1)

    baseline_series = world.kpi_daily_series(db, plant, kpi, shift, baseline_start, baseline_end)
    if not baseline_series:
        return {"available": False, "reason": "Karşılaştırma için yeterli geçmiş veri bulunmuyor."}

    baseline_avg = round(sum(p["value"] for p in baseline_series) / len(baseline_series), 2)
    current_avg = float(anomaly.observed_value)
    abs_change = round(current_avg - baseline_avg, 2)
    pct_change = round((abs_change / baseline_avg) * 100, 1) if baseline_avg else None

    higher_is_better = kpi.success_direction_higher
    if abs(abs_change) < 0.005:
        direction = "unchanged"
    elif (abs_change > 0) == higher_is_better:
        direction = "improved"
    else:
        direction = "worsened"

    return {
        "available": True,
        "baseline_period": {"start": baseline_start.isoformat(), "end": baseline_end.isoformat(), "days": period_days},
        "current_period": {"start": anomaly.period_start.isoformat(), "end": anomaly.period_end.isoformat(), "days": period_days},
        "baseline_avg": baseline_avg, "current_avg": current_avg,
        "abs_change": abs_change, "pct_change": pct_change, "direction": direction,
    }


def build_related_kpi_changes(db: Session, anomaly: Anomaly, plant: Plant, shift: Shift | None) -> list[dict]:
    if not anomaly.related_signals:
        return []

    out = []
    for signal in anomaly.related_signals:
        code = signal.get("kpi_code")
        related_kpi = db.scalar(select(Kpi).where(Kpi.code == code)) if code else None
        current_value = float(signal.get("value", 0))
        change_percent = float(signal.get("change_percent", 0))
        baseline_value = round(current_value / (1 + change_percent / 100), 2) if change_percent != -100 else current_value
        abs_change = round(current_value - baseline_value, 2)
        direction = signal.get("direction", "increase")

        higher_is_better = related_kpi.success_direction_higher if related_kpi is not None else None
        performance_direction = None
        if higher_is_better is not None:
            performance_direction = "improved" if (direction == "increase") == higher_is_better else "worsened"

        sparkline: list[float] = []
        if related_kpi is not None:
            series = world.kpi_daily_series(db, plant, related_kpi, shift, anomaly.period_start, anomaly.period_end)
            sparkline = [p["value"] for p in series]

        out.append(
            {
                "kpi": signal.get("kpi"), "kpi_code": code,
                "baseline_value": baseline_value, "current_value": current_value,
                "abs_change": abs_change, "change_percent": change_percent,
                "direction": direction, "performance_direction": performance_direction,
                "sparkline": sparkline,
            }
        )
    return out


def build_downtime_breakdown(db: Session, anomaly: Anomaly, plant: Plant, shift: Shift | None, kpi: Kpi) -> dict | None:
    if kpi.code != "INKITA":
        return None
    return world.downtime_breakdown(db, plant, shift, kpi, anomaly.period_start, anomaly.period_end)


def build_similar_cases(db: Session, anomaly: Anomaly, plant: Plant, kpi: Kpi, factory: Factory | None, limit: int = 5) -> list[dict]:
    return world.similar_historical_cases(
        db, exclude_anomaly_id=anomaly.id, kpi=kpi, anomaly_type=anomaly.anomaly_type.value,
        factory=factory, plant=plant, limit=limit,
    )


def build_impact(downtime: dict | None) -> dict:
    additional_minutes = None
    additional_note = None
    if downtime is not None:
        prev = downtime.get("previous_period_total_minutes")
        cur = downtime.get("total_downtime_minutes")
        if prev is not None and cur is not None:
            additional_minutes = cur - prev
    if additional_minutes is None:
        additional_note = "Ek duruş süresi hesaplanamadı — bu KPI için duruş verisi mevcut değil."

    return {
        "additional_downtime_minutes": additional_minutes,
        "additional_downtime_note": additional_note,
        "production_loss_note": "Üretim kaybı hesaplanamadı — bu tespit için üretim hızı verisi mevcut değil.",
        "cost_note": "Maliyet etkisi hesaplanamadı — birim maliyet verisi mevcut değil.",
    }


def build_shift_comparison(db: Session, anomaly: Anomaly, plant: Plant, kpi: Kpi) -> list[dict]:
    shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence)))
    if not shifts:
        return []
    comparison = world.compare_shifts(db, plant, kpi, anomaly.period_start, anomaly.period_end)
    return [
        {
            "shift_id": str(s.id), "code": s.code, "name": s.name,
            "value": comparison.per_shift.get(s.code),
            "is_anomaly_shift": anomaly.shift_id == s.id,
        }
        for s in shifts
    ]


def build_factory_comparison(db: Session, anomaly: Anomaly, kpi: Kpi, anomaly_factory_code: str | None) -> list[dict]:
    values = world.compare_factories(db, kpi, anomaly.period_start, anomaly.period_end)
    factories = list(db.scalars(select(Factory).order_by(Factory.code)))
    return [
        {
            "code": f.code, "name": f.name, "value": values.get(f.code),
            "is_anomaly_factory": f.code == anomaly_factory_code,
        }
        for f in factories
    ]


def build_previous_month_comparison(db: Session, anomaly: Anomaly, plant: Plant, kpi: Kpi, shift: Shift | None) -> dict:
    month_start, _ = _month_bounds(anomaly.period_start)
    prev_end = month_start - timedelta(days=1)
    prev_start, prev_end = _month_bounds(prev_end)

    value = world.period_average(db, plant, kpi, shift, prev_start, prev_end)
    current = float(anomaly.observed_value)
    change_percent = round((current - value) / abs(value) * 100, 1) if value else None

    return {
        "available": True,
        "label": month_label(prev_end),
        "period": {"start": prev_start.isoformat(), "end": prev_end.isoformat()},
        "value": value,
        "current_value": current,
        "change_percent": change_percent,
    }


def build_investigation(db: Session, anomaly: Anomaly) -> dict:
    plant = db.get(Plant, anomaly.plant_id)
    factory = db.get(Factory, plant.factory_id) if plant else None
    shift = db.get(Shift, anomaly.shift_id) if anomaly.shift_id else None
    kpi = db.get(Kpi, anomaly.kpi_id)

    responsible_foreman = resolve_responsible_foreman(db, anomaly)
    baseline_comparison = (
        build_baseline_comparison(db, anomaly, plant, kpi, shift)
        if plant is not None and kpi is not None
        else {"available": False, "reason": "Tesis veya KPI bilgisi eksik."}
    )
    related_kpi_changes = build_related_kpi_changes(db, anomaly, plant, shift) if plant is not None else []
    downtime = build_downtime_breakdown(db, anomaly, plant, shift, kpi) if plant is not None and kpi is not None else None
    similar_cases = build_similar_cases(db, anomaly, plant, kpi, factory) if plant is not None and kpi is not None else []
    impact = build_impact(downtime)

    shift_comparison = build_shift_comparison(db, anomaly, plant, kpi) if plant is not None and kpi is not None else []
    factory_comparison = (
        build_factory_comparison(db, anomaly, kpi, factory.code if factory else None) if kpi is not None else []
    )
    previous_month = (
        build_previous_month_comparison(db, anomaly, plant, kpi, shift)
        if plant is not None and kpi is not None
        else {"available": False}
    )
    comparison_target_value = resolve_company_kpi_target(db, kpi, anomaly.period_end) if kpi is not None else None

    return {
        "responsible_foreman": responsible_foreman,
        "baseline_comparison": baseline_comparison,
        "related_kpi_changes": related_kpi_changes,
        "downtime_breakdown": downtime,
        "impact": impact,
        "similar_cases": similar_cases,
        "shift_comparison": shift_comparison,
        "factory_comparison": factory_comparison,
        "previous_month": previous_month,
        "comparison_target_value": comparison_target_value,
    }
