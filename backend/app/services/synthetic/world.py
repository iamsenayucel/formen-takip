
from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.services.anomaly_kpi_defs import ANOMALY_TYPE_LABELS, KPI_DEFINITIONS


class WorldLookupError(Exception):
    pass


def _rng(*parts: object) -> random.Random:
    return random.Random("|".join(str(p) for p in parts))



def resolve_factory(db: Session, value: str) -> Factory:
    value = (value or "").strip()
    factory = db.scalar(select(Factory).where(Factory.code == value.upper()))
    if factory is None:
        raise WorldLookupError(f"Fabrika bulunamadı: {value!r} (geçerli: K1, K2)")
    return factory


def resolve_plant(db: Session, value: str) -> Plant:
    value = (value or "").strip()
    plant = None
    try:
        plant = db.get(Plant, UUID(value))
    except (ValueError, AttributeError):
        pass
    if plant is None:
        plant = db.scalar(select(Plant).where(Plant.code == value.upper()))
    if plant is None and value.isdigit():
        plant = db.scalar(select(Plant).where(Plant.sequence_number == int(value)))
    if plant is None:
        plant = db.scalar(select(Plant).where(Plant.name == value))
    if plant is None:
        raise WorldLookupError(f"Tesis bulunamadı: {value!r}")
    return plant


def resolve_shift(db: Session, value: str | int | None) -> Shift | None:
    if value in (None, "", "all", "tumu", "tümü"):
        return None
    text = str(value).strip()
    shift = None
    try:
        shift = db.get(Shift, UUID(text))
    except (ValueError, AttributeError):
        pass
    if shift is None:
        shift = db.scalar(select(Shift).where(Shift.code == text.upper()))
    if shift is None and text.isdigit():
        shift = db.scalar(select(Shift).where(Shift.sequence == int(text)))
    if shift is None:
        shift = db.scalar(select(Shift).where(Shift.name.ilike(f"%{text}%")))
    if shift is None:
        raise WorldLookupError(f"Vardiya bulunamadı: {value!r} (geçerli: V1, V2 veya 1-2)")
    return shift


def resolve_kpi(db: Session, value: str) -> Kpi:
    text = (value or "").strip()
    kpi = None
    try:
        kpi = db.get(Kpi, UUID(text))
    except (ValueError, AttributeError):
        pass
    if kpi is None:
        kpi = db.scalar(select(Kpi).where(Kpi.code == text.upper()))
    if kpi is None:
        kpi = db.scalar(select(Kpi).where(Kpi.name.ilike(f"%{text}%")))
    if kpi is None:
        raise WorldLookupError(f"KPI bulunamadı: {value!r} (geçerli kodlar: {', '.join(KPI_DEFINITIONS)})")
    return kpi


def resolve_anomaly(db: Session, value: str) -> Anomaly:
    anomaly = None
    try:
        anomaly = db.get(Anomaly, UUID(value))
    except (ValueError, AttributeError):
        pass
    if anomaly is None:
        anomaly = db.scalar(select(Anomaly).where(Anomaly.code == value))
    if anomaly is None:
        raise WorldLookupError(f"Tespit bulunamadı: {value!r}")
    return anomaly



def find_anchor(db: Session, plant_id: UUID, kpi_id: UUID) -> Anomaly | None:
    return db.scalar(
        select(Anomaly)
        .where(Anomaly.plant_id == plant_id, Anomaly.kpi_id == kpi_id)
        .order_by(Anomaly.detected_at.desc())
    )


def generic_baseline(kpi: Kpi) -> float:
    d = KPI_DEFINITIONS.get(kpi.code, {})
    warning = d.get("warning_threshold", 90.0 if kpi.success_direction_higher else 8.0)
    if kpi.success_direction_higher:
        return round(min(99.0, warning + 4.0), 2)
    return round(max(0.5, warning * 0.4), 2)


def _cached_anchor(db: Session, plant: Plant, kpi: Kpi, anchor_cache: dict | None) -> Anomaly | None:
    if anchor_cache is None:
        return find_anchor(db, plant.id, kpi.id)
    key = (plant.id, kpi.id)
    if key not in anchor_cache:
        anchor_cache[key] = find_anchor(db, plant.id, kpi.id)
    return anchor_cache[key]


def _value_for_date(
    db: Session, plant: Plant, kpi: Kpi, shift: Shift | None, d: date, anchor_cache: dict | None = None,
    active_shifts: Sequence[Shift] | None = None,
) -> float:
    if shift is None:
        shifts = (
            active_shifts if active_shifts is not None
            else list(db.scalars(select(Shift).where(Shift.is_active.is_(True))))
        )
        if shifts:
            values = [_value_for_date(db, plant, kpi, s, d, anchor_cache, active_shifts) for s in shifts]
            return round(sum(values) / len(values), 2)

    anchor = _cached_anchor(db, plant, kpi, anchor_cache)
    noise = _rng(plant.id, kpi.code, shift.code if shift else "all", d.isoformat()).uniform(-0.35, 0.35)

    if anchor is None:
        return round(generic_baseline(kpi) + noise, 2)

    expected = float(anchor.expected_value)
    observed = float(anchor.observed_value)
    flagged_shift_id = anchor.shift_id
    is_flagged_line = shift is None or flagged_shift_id is None or shift.id == flagged_shift_id

    if not is_flagged_line:
        recorded = anchor.comparison.get(f"{shift.code.lower()}_average") if shift else None
        center = float(recorded) if recorded is not None else expected
        return round(center + noise, 2)

    if anchor.period_start <= d <= anchor.period_end:
        total_days = max((anchor.period_end - anchor.period_start).days, 1)
        progress = (d - anchor.period_start).days / total_days
        value = expected + (observed - expected) * (0.35 + 0.65 * progress)
        return round(value + noise * 0.6, 2)

    return round(expected + noise, 2)


def kpi_daily_series(
    db: Session, plant: Plant, kpi: Kpi, shift: Shift | None, start: date, end: date, anchor_cache: dict | None = None,
    active_shifts: Sequence[Shift] | None = None,
) -> list[dict]:
    target = float(kpi.default_target_value)
    if anchor_cache is None:
        anchor_cache = {}
    points = []
    d = start
    while d <= end:
        value = _value_for_date(db, plant, kpi, shift, d, anchor_cache, active_shifts)
        points.append(
            {
                "date": d.isoformat(),
                "value": value,
                "target": target,
                "deviation": round(value - target, 2),
                "unit": kpi.unit,
                "data_quality": "valid",
            }
        )
        d += timedelta(days=1)
    return points


def period_average(
    db: Session, plant: Plant, kpi: Kpi, shift: Shift | None, start: date, end: date, anchor_cache: dict | None = None,
    active_shifts: Sequence[Shift] | None = None,
) -> float:
    series = kpi_daily_series(db, plant, kpi, shift, start, end, anchor_cache, active_shifts)
    return round(sum(p["value"] for p in series) / len(series), 2) if series else 0.0


@dataclass
class ShiftComparisonResult:
    plant_name: str
    kpi_name: str
    unit: str
    per_shift: dict[str, float]
    plant_average: float
    best_shift: str | None
    worst_shift: str | None
    max_deviation_between_shifts: float
    observation_count: int


def compare_shifts(db: Session, plant: Plant, kpi: Kpi, start: date, end: date) -> ShiftComparisonResult:
    shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence)))
    anchor_cache: dict = {}
    per_shift = {s.code: period_average(db, plant, kpi, s, start, end, anchor_cache) for s in shifts}
    # period_average içindeki shift=None yolunun her gün yeniden sorgulaması yerine
    # yukarıda yüklenen listeyi kullan.
    plant_average = period_average(db, plant, kpi, None, start, end, anchor_cache, shifts)

    if per_shift:
        worse_is_lower = kpi.success_direction_higher
        worst = min(per_shift, key=lambda k: per_shift[k]) if worse_is_lower else max(per_shift, key=lambda k: per_shift[k])
        best = max(per_shift, key=lambda k: per_shift[k]) if worse_is_lower else min(per_shift, key=lambda k: per_shift[k])
        spread = round(max(per_shift.values()) - min(per_shift.values()), 2)
    else:
        worst = best = None
        spread = 0.0

    return ShiftComparisonResult(
        plant_name=plant.name, kpi_name=kpi.name, unit=kpi.unit, per_shift=per_shift,
        plant_average=plant_average, best_shift=best, worst_shift=worst,
        max_deviation_between_shifts=spread, observation_count=(end - start).days + 1,
    )


@dataclass
class PlantComparisonResult:
    plant_name: str
    plant_value: float
    factory_code: str
    factory_average: float
    peers: list[dict]
    rank: int
    compared_plant_count: int


def compare_plants(db: Session, factory: Factory, plant: Plant, kpi: Kpi, start: date, end: date, peer_limit: int = 5) -> PlantComparisonResult:
    all_plants = list(
        db.scalars(select(Plant).where(Plant.factory_id == factory.id, Plant.is_active.is_(True)).order_by(Plant.sequence_number))
    )
    rng = _rng("compare_plants", factory.code, kpi.code)
    others = [p for p in all_plants if p.id != plant.id]
    rng.shuffle(others)
    peer_plants = others[:peer_limit]

    anchor_cache: dict = {}
    plant_value = period_average(db, plant, kpi, None, start, end, anchor_cache)
    peers = [{"plant_name": p.name, "value": period_average(db, p, kpi, None, start, end, anchor_cache)} for p in peer_plants]
    all_values = [plant_value] + [p["value"] for p in peers]
    factory_average = round(sum(all_values) / len(all_values), 2)

    worse_is_lower = kpi.success_direction_higher
    ranked = sorted(all_values, reverse=not worse_is_lower)
    rank = ranked.index(plant_value) + 1

    return PlantComparisonResult(
        plant_name=plant.name, plant_value=plant_value, factory_code=factory.code,
        factory_average=factory_average, peers=peers, rank=rank, compared_plant_count=len(all_values),
    )


def compare_factories(db: Session, kpi: Kpi, start: date, end: date) -> dict[str, float | None]:
    factories = list(db.scalars(select(Factory).order_by(Factory.code)))
    anchor_cache: dict = {}
    # Bu çağrı için bir kez yüklenip her fabrika/günde kullanılır. Aksi halde
    # _value_for_date içindeki shift=None dalı aynı sorguyu her gün x fabrika için yineler;
    # GET /anomalies/{id}/investigation maliyetinin ana kaynağı budur. Yerini aldığı sorguyla
    # aynı Shift.is_active filtresini kullandığından davranış değişmez.
    active_shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True))))
    result: dict[str, float | None] = {}
    for factory in factories:
        plants = list(
            db.scalars(
                select(Plant).where(Plant.factory_id == factory.id, Plant.is_active.is_(True)).order_by(Plant.sequence_number)
            )
        )
        if not plants:
            result[factory.code] = None
            continue
        values = [period_average(db, p, kpi, None, start, end, anchor_cache, active_shifts) for p in plants]
        result[factory.code] = round(sum(values) / len(values), 2)
    return result


def related_kpi_changes(db: Session, plant: Plant, shift: Shift | None, primary_kpi: Kpi, start: date, end: date) -> list[dict]:
    anchor = find_anchor(db, plant.id, primary_kpi.id)
    if anchor is not None and anchor.related_signals:
        return [
            {
                "kpi": s["kpi"], "kpi_code": s["kpi_code"], "value": s["value"],
                "previous_value": round(s["value"] / (1 + s["change_percent"] / 100), 2) if s["change_percent"] != -100 else s["value"],
                "change_percent": s["change_percent"], "direction": s["direction"],
                "correlation_note": "Aynı dönemde eş zamanlı gözlenen sinyal — nedensellik iddia edilmez.",
            }
            for s in anchor.related_signals
        ]

    pool = {
        "PLANA_UYUM": ["AGIR_GITME", "INKITA"], "GSF": ["ISKARTA", "AGIR_GITME"],
        "ISKARTA": ["GSF", "AGIR_GITME"], "INKITA": ["PLANA_UYUM", "ISKARTA", "OEE"], "AGIR_GITME": ["GSF", "PLANA_UYUM"],
        "OEE": ["INKITA", "PLANA_UYUM"],
    }
    rng = _rng("related_kpis", plant.id, primary_kpi.code, start, end)
    results = []
    for code in pool.get(primary_kpi.code, [])[:1]:
        related = db.scalar(select(Kpi).where(Kpi.code == code))
        if related is None:
            continue
        value = period_average(db, plant, related, shift, start, end)
        change = round(rng.uniform(-6.0, 6.0), 1)
        results.append(
            {
                "kpi": related.name, "kpi_code": code, "value": value,
                "previous_value": round(value / (1 + change / 100), 2) if change != -100 else value,
                "change_percent": change, "direction": "increase" if change > 0 else "decrease",
                "correlation_note": "Belirgin bir sapma tespit edilmedi.",
            }
        )
    return results


_DOWNTIME_CATEGORIES = [
    "Teknik duruş", "İmalat kaynaklı duruş", "Ürün değişimi",
    "Malzeme bekleme", "Kalite bekleme", "Personel kaynaklı duruş", "Diğer",
]


def _trouble_score(db: Session, plant: Plant, kpi: Kpi) -> float:
    anchor = find_anchor(db, plant.id, kpi.id)
    if anchor is None:
        return 0.05
    severity_weight = {"low": 0.2, "medium": 0.45, "high": 0.7, "critical": 0.95}
    return severity_weight.get(anchor.severity.value, 0.3)


def downtime_breakdown(
    db: Session, plant: Plant, shift: Shift | None, kpi: Kpi | None, start: date, end: date,
    _include_peer_comparison: bool = True,
) -> dict:
    days = (end - start).days + 1
    trouble = _trouble_score(db, plant, kpi) if kpi is not None else 0.1
    rng = _rng("downtime", plant.id, shift.code if shift else "all", start, end)

    categories = []
    total_minutes = 0
    total_count = 0
    for i, cat in enumerate(_DOWNTIME_CATEGORIES):
        weighted = trouble * 2.2 if cat in ("Teknik duruş", "İmalat kaynaklı duruş") else 0.4
        base_minutes_per_day = rng.uniform(2, 8) * (1 + weighted)
        minutes = round(base_minutes_per_day * days)
        count = max(1, round(minutes / rng.uniform(15, 35)))
        categories.append({"category": cat, "total_minutes": minutes, "occurrence_count": count})
        total_minutes += minutes
        total_count += count

    categories.sort(key=lambda c: c["total_minutes"], reverse=True)
    prev_period_days = days
    prev_start = start - timedelta(days=prev_period_days)
    prev_trouble = trouble * rng.uniform(0.55, 0.85)
    previous_total_minutes = round(total_minutes * (prev_trouble / trouble) if trouble else total_minutes * 0.8)

    other_shift_minutes = None
    if shift is not None and _include_peer_comparison:
        shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True))))
        other_avg = []
        for s in shifts:
            if s.id == shift.id:
                continue
            other_avg.append(
                downtime_breakdown(db, plant, s, None, start, end, _include_peer_comparison=False)["total_downtime_minutes"]
            )
        other_shift_minutes = round(sum(other_avg) / len(other_avg)) if other_avg else None

    return {
        "plant_name": plant.name, "shift_name": shift.name if shift else "Tüm vardiyalar",
        "period_days": days, "total_downtime_minutes": total_minutes, "total_downtime_count": total_count,
        "categories": categories, "top_reasons": [c["category"] for c in categories[:3]],
        "longest_single_event_minutes": max((c["total_minutes"] // max(c["occurrence_count"], 1) for c in categories), default=0),
        "previous_period_total_minutes": previous_total_minutes,
        "other_shifts_average_minutes": other_shift_minutes,
    }


_FAULT_EQUIPMENT = ["Hat ekipmanı", "Tartım sistemi", "Paketleme ünitesi", "Fırın kontrol ünitesi", "Konveyör motoru"]
_FAULT_SIGNALS = [
    "Titreşim değerinde artış", "Kalibrasyon tarihi yaklaşıyor/geçti", "Sıcaklık sapması gözlendi",
    "Tekrarlayan aynı arıza kodu", "Beklenmedik duruş sinyali",
]


def maintenance_signals(db: Session, plant: Plant, kpi: Kpi | None, start: date, end: date) -> list[dict]:
    trouble = _trouble_score(db, plant, kpi) if kpi is not None else 0.1
    rng = _rng("maintenance", plant.id, start, end)
    count = 1 if trouble < 0.3 else (2 if trouble < 0.6 else rng.randint(3, 5))

    records = []
    open_requests = 0
    delayed_planned = 0
    for i in range(count):
        equipment = rng.choice(_FAULT_EQUIPMENT)
        recurrence = rng.randint(1, 2) if trouble < 0.5 else rng.randint(2, 6)
        is_open = rng.random() < (0.2 + trouble * 0.4)
        is_delayed = rng.random() < (0.15 + trouble * 0.3)
        open_requests += int(is_open)
        delayed_planned += int(is_delayed)
        records.append(
            {
                "equipment": equipment, "signal": rng.choice(_FAULT_SIGNALS),
                "fault_code": f"FLT-{abs(hash((plant.id, equipment, i))) % 9000 + 1000}",
                "detected_days_ago": rng.randint(1, max((end - start).days, 1) + 20),
                "recurrence_count": recurrence, "is_open_request": is_open, "is_delayed_planned_maintenance": is_delayed,
                "average_resolution_hours": round(rng.uniform(2.0, 30.0), 1),
            }
        )

    return {
        "plant_name": plant.name, "records": records, "open_request_count": open_requests,
        "delayed_planned_maintenance_count": delayed_planned,
        "recurring_fault_count": sum(1 for r in records if r["recurrence_count"] >= 3),
    }


def product_mix(db: Session, plant: Plant, shift: Shift | None, start: date, end: date) -> list[dict]:
    rng = _rng("product_mix", plant.id, shift.code if shift else "all", start, end)
    groups = ["A Ürün Grubu", "B Ürün Grubu", "C Ürün Grubu"]
    shares = [rng.uniform(15, 45) for _ in groups]
    total = sum(shares)
    complexity = ["Düşük", "Orta", "Yüksek"]
    return [
        {
            "product_group": g, "share_percent": round(s / total * 100, 1),
            "target_cycle_seconds": round(rng.uniform(8, 25), 1),
            "actual_cycle_seconds": round(rng.uniform(8, 28), 1),
            "changeover_count": rng.randint(1, 5),
            "complexity_class": complexity[i % len(complexity)],
        }
        for i, (g, s) in enumerate(zip(groups, shares))
    ]


def changeover_records(db: Session, plant: Plant, shift: Shift | None, start: date, end: date) -> list[dict]:
    rng = _rng("changeover", plant.id, shift.code if shift else "all", start, end)
    products = ["A Ürün Grubu", "B Ürün Grubu", "C Ürün Grubu"]
    days = (end - start).days + 1
    count = max(1, days // 3)
    records = []
    d = start
    for i in range(count):
        prev_p, new_p = rng.sample(products, 2)
        target = round(rng.uniform(15, 40), 1)
        actual = round(target * rng.uniform(0.85, 1.6), 1)
        records.append(
            {
                "date": d.isoformat(), "previous_product": prev_p, "new_product": new_p,
                "target_minutes": target, "actual_minutes": actual, "deviation_minutes": round(actual - target, 1),
                "shift": shift.name if shift else rng.choice(["1. Vardiya", "2. Vardiya"]),
                "description": "Standart ürün değişimi." if actual <= target * 1.15 else "Hedeften belirgin sapma gözlendi.",
            }
        )
        d += timedelta(days=max(days // count, 1))
    return records


_SHIFT_NOTE_POOL = [
    ("Personel eksikliği", "Vardiyada planlanan personel sayısının altında çalışıldığı not edilmiş."),
    ("Ekipman arızası", "Vardiya sırasında kısa süreli bir ekipman arızası yaşanmış."),
    ("Ham madde gecikmesi", "Hammadde tedarikinde gecikme nedeniyle üretime geç başlanmış."),
    ("Ürün değişiminin uzaması", "Planlanan ürün değişimi beklenenden uzun sürmüş."),
    ("Kalite kontrol beklemesi", "Kalite kontrol onayı beklenirken üretim geçici olarak durmuş."),
    ("Operasyonel aksaklık", "Operasyonel bir aksaklık devir teslim formuna not düşülmüş."),
    ("Plan değişikliği", "Üretim planında vardiya içi bir değişiklik yapılmış."),
]


def shift_notes(db: Session, plant: Plant, shift: Shift | None, kpi: Kpi | None, start: date, end: date) -> list[dict]:
    trouble = _trouble_score(db, plant, kpi) if kpi is not None else 0.1
    rng = _rng("shift_notes", plant.id, shift.code if shift else "all", start, end)
    days = (end - start).days + 1
    note_day_count = min(days, max(1, round(days * (0.15 + trouble * 0.35))))
    candidate_days = sorted(rng.sample(range(days), note_day_count))

    notes = []
    for offset in candidate_days:
        category, text = rng.choice(_SHIFT_NOTE_POOL)
        notes.append(
            {
                "date": (start + timedelta(days=offset)).isoformat(),
                "category": category, "note": text,
                "recorded_by_role": rng.choice(["Vardiya Sorumlusu", "Formen", "Tesis Şefi"]),
            }
        )
    return notes


_ROOT_CAUSE_POOL: dict[str, list[tuple[str, str, str]]] = {
    "downtime_concentration": [
        ("Tekrarlayan mekanik arıza", "Arızalı parça değiştirildi, önleyici bakım planına eklendi", "Duruş süresi %60 azaldı"),
    ],
    "shift_underperformance": [
        ("Vardiya ayar farkı", "Vardiya bazlı standart çalışma talimatı güncellendi", "Vardiyalar arası fark %70 daraldı"),
    ],
    "chronic_anomaly": [
        ("Kalıcı hale gelmiş süreç sorunu", "Kök neden analizi sonrası süreç yeniden tasarlandı", "KPI hedefe geri döndü"),
    ],
    "foreman_deviation": [
        ("Ekip deneyim farkı", "Ek eğitim ve mentorluk programı uygulandı", "Sapma önemli ölçüde azaldı"),
    ],
    "rising_trend": [
        ("Kademeli ekipman aşınması", "Planlı bakım öne çekildi", "Trend tersine döndü"),
    ],
}
_DEFAULT_ROOT_CAUSE = ("Kesin kök neden doğrulanamadı", "Saha incelemesi ve ek veri toplama başlatıldı", "İzleme devam ediyor")


def similar_historical_cases(db: Session, exclude_anomaly_id: UUID, kpi: Kpi | None, anomaly_type: str | None, factory: Factory | None, plant: Plant | None, limit: int = 5) -> list[dict]:
    candidates = list(db.scalars(select(Anomaly).where(Anomaly.id != exclude_anomaly_id)))

    # Scoring sırasında aday başına ve response mapping sırasında sonuç başına db.get()
    # çağırmak yerine tüm çağrı için tek batch yüklenir. Her adayın fabrikası iki aşamadan
    # birinde zaten gereklidir.
    candidate_plant_ids = {c.plant_id for c in candidates}
    plants_by_id = (
        {p.id: p for p in db.scalars(select(Plant).where(Plant.id.in_(candidate_plant_ids)))}
        if candidate_plant_ids else {}
    )

    scored = []
    for c in candidates:
        score = 0
        if kpi is not None and c.kpi_id == kpi.id:
            score += 2
        if anomaly_type is not None and c.anomaly_type.value == anomaly_type:
            score += 2
        if plant is not None and c.plant_id == plant.id:
            score += 2
        elif factory is not None:
            c_plant = plants_by_id.get(c.plant_id)
            if c_plant is not None and c_plant.factory_id == factory.id:
                score += 1
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda sc: (sc[0], sc[1].detected_at), reverse=True)
    top = scored[:limit]

    result_kpi_ids = {c.kpi_id for _, c in top}
    kpis_by_id = (
        {k.id: k for k in db.scalars(select(Kpi).where(Kpi.id.in_(result_kpi_ids)))}
        if result_kpi_ids else {}
    )

    results = []
    for score, c in top:
        rng = _rng("historical_case", c.code)
        pool = _ROOT_CAUSE_POOL.get(c.anomaly_type.value, [_DEFAULT_ROOT_CAUSE])
        root_cause, action, outcome = rng.choice(pool)
        c_plant = plants_by_id.get(c.plant_id)
        c_kpi = kpis_by_id.get(c.kpi_id)
        resolved = c.status.value in ("resolved", "closed")
        results.append(
            {
                "anomaly_id": str(c.id), "anomaly_code": c.code, "title": c.title,
                "plant_name": c_plant.name if c_plant else None, "kpi_name": c_kpi.name if c_kpi else None,
                "anomaly_type_label": ANOMALY_TYPE_LABELS.get(c.anomaly_type, c.anomaly_type.value),
                "similarity_reason": f"Benzerlik skoru: {score} (KPI/tür/tesis eşleşmesi)",
                "detected_at": c.detected_at.date().isoformat(),
                "resolution_status": "resolved" if resolved else "open",
                "verified_root_cause": root_cause if resolved else None,
                "action_taken": action if resolved else None,
                "action_result": outcome if resolved else None,
                "kpi_value_before": float(c.observed_value),
                "kpi_value_after": float(c.expected_value) if resolved else None,
            }
        )
    return results


def get_anomaly_details(db: Session, anomaly: Anomaly) -> dict:
    plant = db.get(Plant, anomaly.plant_id)
    factory = db.get(Factory, plant.factory_id) if plant else None
    shift = db.get(Shift, anomaly.shift_id) if anomaly.shift_id else None
    kpi = db.get(Kpi, anomaly.kpi_id)
    foreman_codes = [f.employee_number for fid in anomaly.foreman_ids if (f := db.get(Foreman, fid)) is not None]

    return {
        "anomaly_id": str(anomaly.id), "code": anomaly.code, "title": anomaly.title,
        "factory_code": factory.code if factory else None, "plant_name": plant.name if plant else None,
        "plant_id": str(anomaly.plant_id), "shift_name": shift.name if shift else None,
        "shift_code": shift.code if shift else None, "foreman_codes": foreman_codes,
        "kpi_name": kpi.name if kpi else None, "kpi_code": kpi.code if kpi else None,
        "anomaly_type": anomaly.anomaly_type.value,
        "anomaly_type_label": ANOMALY_TYPE_LABELS.get(anomaly.anomaly_type, anomaly.anomaly_type.value),
        "period_start": anomaly.period_start.isoformat(), "period_end": anomaly.period_end.isoformat(),
        "observed_value": float(anomaly.observed_value), "expected_value": float(anomaly.expected_value),
        "unit": anomaly.unit, "deviation_percent": float(anomaly.deviation_percent),
        "ml_confidence": float(anomaly.ml_confidence), "severity": anomaly.severity.value,
        "data_quality_status": anomaly.data_quality_status, "data_quality_warnings": anomaly.data_quality_warnings,
    }
