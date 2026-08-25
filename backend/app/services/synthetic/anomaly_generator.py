from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.anomaly import Anomaly
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType
from app.models.foreman import Foreman, ForemanAssignment
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.schemas.anomaly import AnomalyCreate
from app.services.anomaly_kpi_defs import KPI_DEFINITIONS

_SCENARIOS: list[dict] = [
    dict(type=AnomalyType.SHIFT_UNDERPERFORMANCE, kpi="PLANA_UYUM", factory="K1", severity="high",
         shift_specific=True, days_ago=2, period_days=21, affected_ratio=0.76, dev_range=(-14.0, -10.0)),
    dict(type=AnomalyType.SHIFT_UNDERPERFORMANCE, kpi="ISKARTA", factory="K2", severity="medium",
         shift_specific=True, days_ago=5, period_days=14, affected_ratio=0.64, dev_range=(18.0, 26.0)),
    dict(type=AnomalyType.RISING_TREND, kpi="GSF", factory="K1", severity="high",
         shift_specific=False, days_ago=1, period_days=28, affected_ratio=0.5, dev_range=(20.0, 30.0)),
    dict(type=AnomalyType.RISING_TREND, kpi="GSF", factory="K2", severity="medium",
         shift_specific=False, days_ago=3, period_days=21, affected_ratio=0.43, dev_range=(14.0, 20.0)),
    dict(type=AnomalyType.FOREMAN_DEVIATION, kpi="ISKARTA", factory="K1", severity="high",
         shift_specific=True, days_ago=4, period_days=21, affected_ratio=0.71, dev_range=(22.0, 32.0)),
    dict(type=AnomalyType.FOREMAN_DEVIATION, kpi="AGIR_GITME", factory="K2", severity="medium",
         shift_specific=True, days_ago=6, period_days=14, affected_ratio=0.57, dev_range=(16.0, 24.0)),
    dict(type=AnomalyType.PRODUCT_GROUP_DEVIATION, kpi="AGIR_GITME", factory="K1", severity="medium",
         shift_specific=False, days_ago=7, period_days=21, affected_ratio=0.48, dev_range=(15.0, 22.0)),
    dict(type=AnomalyType.PRODUCT_GROUP_DEVIATION, kpi="AGIR_GITME", factory="K2", severity="high",
         shift_specific=False, days_ago=2, period_days=14, affected_ratio=0.64, dev_range=(24.0, 32.0)),
    dict(type=AnomalyType.DOWNTIME_CONCENTRATION, kpi="INKITA", factory="K1", severity="high",
         shift_specific=True, days_ago=1, period_days=14, affected_ratio=0.5, dev_range=(28.0, 38.0)),
    dict(type=AnomalyType.DOWNTIME_CONCENTRATION, kpi="INKITA", factory="K2", severity="critical",
         shift_specific=True, days_ago=0, period_days=10, affected_ratio=0.6, dev_range=(40.0, 55.0)),
    dict(type=AnomalyType.PLAN_ADHERENCE_STREAK, kpi="PLANA_UYUM", factory="K1", severity="medium",
         shift_specific=False, days_ago=3, period_days=10, affected_ratio=0.7, dev_range=(-11.0, -7.0)),
    dict(type=AnomalyType.PLAN_ADHERENCE_STREAK, kpi="PLANA_UYUM", factory="K2", severity="high",
         shift_specific=False, days_ago=1, period_days=7, affected_ratio=1.0, dev_range=(-16.0, -12.0)),
    dict(type=AnomalyType.PLANT_HISTORICAL_DEVIATION, kpi="GSF", factory="K1", severity="medium",
         shift_specific=False, days_ago=9, period_days=30, affected_ratio=0.4, dev_range=(18.0, 25.0)),
    dict(type=AnomalyType.PLANT_HISTORICAL_DEVIATION, kpi="ISKARTA", factory="K2", severity="low",
         shift_specific=False, days_ago=12, period_days=30, affected_ratio=0.33, dev_range=(10.0, 15.0)),
    dict(type=AnomalyType.CROSS_PLANT_GAP, kpi="AGIR_GITME", factory="K1", severity="medium",
         shift_specific=False, days_ago=5, period_days=21, affected_ratio=0.52, dev_range=(17.0, 23.0)),
    dict(type=AnomalyType.CROSS_PLANT_GAP, kpi="PLANA_UYUM", factory="K2", severity="medium",
         shift_specific=False, days_ago=8, period_days=21, affected_ratio=0.48, dev_range=(-13.0, -9.0)),
    dict(type=AnomalyType.MULTI_KPI_SIMULTANEOUS, kpi="INKITA", factory="K1", severity="critical",
         shift_specific=True, days_ago=0, period_days=7, affected_ratio=0.86, dev_range=(35.0, 48.0)),
    dict(type=AnomalyType.MULTI_KPI_SIMULTANEOUS, kpi="GSF", factory="K2", severity="high",
         shift_specific=True, days_ago=2, period_days=10, affected_ratio=0.7, dev_range=(26.0, 34.0)),
    dict(type=AnomalyType.SINGLE_DAY_SPIKE, kpi="ISKARTA", factory="K1", severity="high",
         shift_specific=True, days_ago=1, period_days=1, affected_ratio=1.0, dev_range=(45.0, 60.0)),
    dict(type=AnomalyType.SINGLE_DAY_SPIKE, kpi="AGIR_GITME", factory="K2", severity="medium",
         shift_specific=True, days_ago=4, period_days=1, affected_ratio=1.0, dev_range=(30.0, 42.0)),
    dict(type=AnomalyType.CHRONIC_ANOMALY, kpi="INKITA", factory="K1", severity="critical",
         shift_specific=False, days_ago=1, period_days=60, affected_ratio=0.8, dev_range=(24.0, 32.0)),
    dict(type=AnomalyType.CHRONIC_ANOMALY, kpi="GSF", factory="K2", severity="high",
         shift_specific=False, days_ago=2, period_days=45, affected_ratio=0.71, dev_range=(19.0, 27.0)),
    dict(type=AnomalyType.CRITICAL_PRODUCTION_LOSS, kpi="PLANA_UYUM", factory="K1", severity="critical",
         shift_specific=True, days_ago=0, period_days=5, affected_ratio=1.0, dev_range=(-30.0, -22.0)),
    dict(type=AnomalyType.DATA_QUALITY_SUSPECT, kpi="ISKARTA", factory="K2", severity="low",
         shift_specific=False, days_ago=10, period_days=14, affected_ratio=0.3, dev_range=(12.0, 18.0)),
    dict(type=AnomalyType.SINGLE_DAY_SPIKE, kpi="OEE", factory="K1", severity="high",
         shift_specific=False, days_ago=2, period_days=1, affected_ratio=1.0, dev_range=(-38.0, -25.0)),
    dict(type=AnomalyType.CHRONIC_ANOMALY, kpi="OEE", factory="K2", severity="critical",
         shift_specific=False, days_ago=1, period_days=30, affected_ratio=0.63, dev_range=(-22.0, -14.0)),
    dict(type=AnomalyType.PLANT_HISTORICAL_DEVIATION, kpi="OEE", factory="K1", severity="medium",
         shift_specific=False, days_ago=6, period_days=21, affected_ratio=0.45, dev_range=(-16.0, -11.0)),
]

_STATUS_CYCLE = [
    AnomalyStatus.NEW, AnomalyStatus.NEW, AnomalyStatus.IN_REVIEW, AnomalyStatus.NEW,
    AnomalyStatus.ACTION_PENDING, AnomalyStatus.IN_REVIEW, AnomalyStatus.NEW, AnomalyStatus.RESOLVED,
    AnomalyStatus.NEW, AnomalyStatus.ACTION_PENDING, AnomalyStatus.IN_REVIEW, AnomalyStatus.NEW,
    AnomalyStatus.CLOSED, AnomalyStatus.NEW, AnomalyStatus.IN_REVIEW, AnomalyStatus.ACTION_PENDING,
    AnomalyStatus.NEW, AnomalyStatus.NEW, AnomalyStatus.RESOLVED, AnomalyStatus.IN_REVIEW,
    AnomalyStatus.NEW, AnomalyStatus.ACTION_PENDING, AnomalyStatus.NEW, AnomalyStatus.CLOSED,
]

_RELATED_SIGNAL_POOL: dict[str, list[str]] = {
    "PLANA_UYUM": ["AGIR_GITME", "INKITA"],
    "GSF": ["ISKARTA", "AGIR_GITME"],
    "ISKARTA": ["GSF", "AGIR_GITME"],
    "INKITA": ["PLANA_UYUM", "ISKARTA", "OEE"],
    "AGIR_GITME": ["GSF", "PLANA_UYUM"],
    "OEE": ["INKITA", "PLANA_UYUM"],
}

_SHIFT_NOTE_POOL = [
    "Vardiya devir teslim formunda özel bir not girilmemiş.",
    "Vardiya sorumlusu, hat ayarlarında sık değişiklik yapıldığını not etmiş.",
    "Devir teslimde hammadde parti değişikliğine dikkat çekilmiş.",
    "Vardiya başında kısa süreli bir elektrik dalgalanması raporlanmış.",
    "Yeni başlayan personel için oryantasyon notu düşülmüş.",
]


@dataclass
class AnomalySeedResult:
    anomalies_created: int = 0
    codes: list[str] = field(default_factory=list)


def _load_reference(db: Session) -> dict:
    plants = list(db.scalars(select(Plant).where(Plant.is_active.is_(True)).order_by(Plant.sequence_number)))
    factories_by_id = {f.id: f for f in db.scalars(select(Factory))}
    plants_by_factory: dict[str, list[Plant]] = {}
    for p in plants:
        code = factories_by_id[p.factory_id].code
        plants_by_factory.setdefault(code, []).append(p)

    shifts = list(db.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence)))
    kpis_by_code = {k.code: k for k in db.scalars(select(Kpi))}

    return {
        "plants_by_factory": plants_by_factory,
        "factories_by_id": factories_by_id,
        "shifts": shifts,
        "kpis_by_code": kpis_by_code,
    }


def _pick_foreman(db: Session, plant_id, rng: random.Random) -> Foreman | None:
    assignments = list(
        db.scalars(
            select(ForemanAssignment)
            .where(ForemanAssignment.plant_id == plant_id, ForemanAssignment.is_active.is_(True))
        )
    )
    if not assignments:
        return None
    chosen = rng.choice(assignments)
    return db.get(Foreman, chosen.foreman_id)


def _shift_averages(rng: random.Random, worst_index: int, plant_average: float, spread: float) -> dict:
    values = {}
    for i in range(3):
        if i == worst_index:
            continue
        values[i] = round(plant_average + rng.uniform(-spread * 0.3, spread * 0.5), 1)
    return values


def _build_case(spec: dict, index: int, ref: dict, rng: random.Random, today: date, admin_note: str) -> dict | None:
    kpi = ref["kpis_by_code"].get(spec["kpi"])
    plants = ref["plants_by_factory"].get(spec["factory"])
    if kpi is None or not plants:
        return None

    plant = plants[index % len(plants)]
    higher_is_better = kpi.success_direction_higher

    dev_low, dev_high = spec["dev_range"]
    deviation_percent = round(rng.uniform(dev_low, dev_high), 2)
    kpi_def = KPI_DEFINITIONS[spec["kpi"]]
    baseline = kpi_def["critical_threshold"] if higher_is_better else kpi_def["warning_threshold"] * 0.6
    expected_value = round(baseline + rng.uniform(-1.5, 1.5), 2) if higher_is_better else round(
        max(0.5, baseline + rng.uniform(-0.8, 0.8)), 2
    )
    observed_value = round(expected_value * (1 + deviation_percent / 100), 2)

    shift = None
    worst_shift_idx = None
    if spec["shift_specific"] and ref["shifts"]:
        worst_shift_idx = index % len(ref["shifts"])
        shift = ref["shifts"][worst_shift_idx]

    plant_average = expected_value
    factory_average = round(plant_average + rng.uniform(-1.0, 1.0), 2)
    comparison: dict = {"plant_average": plant_average, "factory_average": factory_average}
    if shift is not None:
        others = _shift_averages(rng, worst_shift_idx, plant_average, abs(deviation_percent) / 100 * plant_average)
        for i, s in enumerate(ref["shifts"]):
            comparison[f"{s.code.lower()}_average"] = observed_value if i == worst_shift_idx else others.get(i, plant_average)

    total_days = spec["period_days"]
    affected_days = max(1, round(total_days * spec["affected_ratio"]))
    period_end = today - timedelta(days=spec["days_ago"])
    period_start = period_end - timedelta(days=total_days - 1)
    detected_at = clock.to_utc(datetime.combine(period_end, time(7, 30)))

    related_codes = _RELATED_SIGNAL_POOL.get(spec["kpi"], [])
    related_signals = []
    for code in related_codes[: 1 if spec["type"] != AnomalyType.MULTI_KPI_SIMULTANEOUS else 2]:
        related_kpi = ref["kpis_by_code"].get(code)
        if related_kpi is None:
            continue
        change = round(rng.uniform(8.0, 22.0) * (1 if rng.random() > 0.2 else -1), 1)
        related_signals.append(
            {
                "kpi": related_kpi.name,
                "kpi_code": code,
                "value": round(rng.uniform(2.0, 12.0), 2),
                "change_percent": change,
                "direction": "increase" if change > 0 else "decrease",
            }
        )

    evidence = [
        {"type": "metric", "label": f"{plant.name} dönem gözlenen değeri", "value": observed_value, "unit": "%"},
        {"type": "metric", "label": f"{plant.name} dönem beklenen değeri", "value": expected_value, "unit": "%"},
        {
            "type": "metric",
            "label": "Anormalliğin görüldüğü gün sayısı",
            "value": affected_days,
            "unit": f"/ {total_days} gün",
        },
    ]
    if shift is not None:
        evidence.append({"type": "metric", "label": f"{shift.name} ortalaması", "value": observed_value, "unit": "%"})

    foreman_ids: list[str] = []

    ml_confidence = round(min(0.99, 0.72 + spec["affected_ratio"] * 0.2 + rng.uniform(-0.03, 0.05)), 3)

    data_quality_status = "suspicious" if spec["type"] == AnomalyType.DATA_QUALITY_SUSPECT else "valid"
    data_quality_warnings = (
        ["Dönem içinde 2 gün için kaynak sistemden gecikmeli veri geldi.", "1 kayıt için formen ataması geriye dönük düzeltildi."]
        if data_quality_status == "suspicious"
        else []
    )

    shift_txt = f" {shift.name}" if shift is not None else ""
    direction_word = "altında" if (deviation_percent < 0) == higher_is_better else "üzerinde"
    title = f"{plant.name}{shift_txt}"
    if spec["type"] == AnomalyType.SHIFT_UNDERPERFORMANCE:
        title = f"{plant.name} {shift.name if shift else ''} sürekli düşük {kpi.name}".strip()
    elif spec["type"] == AnomalyType.RISING_TREND:
        title = f"{plant.name} tesisinde {kpi.name} son haftalarda yükseliyor"
    elif spec["type"] == AnomalyType.CRITICAL_PRODUCTION_LOSS:
        title = f"{plant.name} — Kritik seviyede üretim kaybı ({kpi.name})"
    elif spec["type"] == AnomalyType.DATA_QUALITY_SUSPECT:
        title = f"{plant.name} — {kpi.name} verisinde kalite şüphesi"
    elif spec["type"] == AnomalyType.CHRONIC_ANOMALY:
        title = f"{plant.name} — {kpi.name} kronik olarak {direction_word} hedefin"
    elif spec["type"] == AnomalyType.SINGLE_DAY_SPIKE:
        title = f"{plant.name}{shift_txt} — {kpi.name} tek günlük ani sıçrama"
    elif spec["type"] == AnomalyType.FOREMAN_DEVIATION:
        title = f"{plant.name} — formen bazlı {kpi.name} sapması"
    elif spec["type"] == AnomalyType.PRODUCT_GROUP_DEVIATION:
        title = f"{plant.name} — ürün grubu bazlı {kpi.name} sapması"
    elif spec["type"] == AnomalyType.DOWNTIME_CONCENTRATION:
        title = f"{plant.name}{shift_txt} — duruş süresi yoğunlaşması ({kpi.name})"
    elif spec["type"] == AnomalyType.PLAN_ADHERENCE_STREAK:
        title = f"{plant.name} — art arda {affected_days} gün plan altı"
    elif spec["type"] == AnomalyType.PLANT_HISTORICAL_DEVIATION:
        title = f"{plant.name} — kendi geçmiş ortalamasından sapma ({kpi.name})"
    elif spec["type"] == AnomalyType.CROSS_PLANT_GAP:
        title = f"{plant.name} — fabrika ortalamasının gerisinde ({kpi.name})"
    elif spec["type"] == AnomalyType.MULTI_KPI_SIMULTANEOUS:
        title = f"{plant.name}{shift_txt} — eş zamanlı çoklu KPI bozulması"

    description = (
        f"{plant.name} tesisinde{shift_txt} {kpi.name}, {period_start.isoformat()} - {period_end.isoformat()} "
        f"döneminde incelenen {total_days} günün {affected_days}'inde beklenen değerin {direction_word} kalmıştır "
        f"(gözlenen %{observed_value}, beklenen %{expected_value}, sapma %{deviation_percent}). "
        f"{admin_note}"
    ).strip()

    return dict(
        code=f"ANM-{today.year}-{index + 1:04d}",
        title=title,
        description=description,
        anomaly_type=spec["type"],
        severity=AnomalySeverity(spec["severity"]),
        status=_STATUS_CYCLE[index % len(_STATUS_CYCLE)],
        analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED,
        detected_at=detected_at,
        plant_id=plant.id,
        shift_id=shift.id if shift else None,
        kpi_id=kpi.id,
        period_start=period_start,
        period_end=period_end,
        observed_value=observed_value,
        expected_value=expected_value,
        unit="%",
        deviation_percent=deviation_percent,
        ml_confidence=ml_confidence,
        affected_days=affected_days,
        total_days=total_days,
        comparison=comparison,
        related_signals=related_signals,
        evidence=evidence,
        foreman_ids=foreman_ids,
        data_quality_status=data_quality_status,
        data_quality_warnings=data_quality_warnings,
    )


def generate_anomaly_fixtures(db: Session, rng: random.Random, today: date | None = None) -> list[dict]:
    ref = _load_reference(db)
    today = today or clock.today_local()
    cases = []
    for i, spec in enumerate(_SCENARIOS):
        note = rng.choice(_SHIFT_NOTE_POOL) if rng.random() < 0.3 else ""
        case = _build_case(spec, i, ref, rng, today, note)
        if case is None:
            continue
        if spec["type"] == AnomalyType.FOREMAN_DEVIATION:
            foreman = _pick_foreman(db, case["plant_id"], rng)
            if foreman is not None:
                case["foreman_ids"] = [str(foreman.id)]
        cases.append(case)
    return cases


def seed_anomalies(db: Session, rng: random.Random) -> AnomalySeedResult:
    result = AnomalySeedResult()
    for case in generate_anomaly_fixtures(db, rng):
        existing = db.scalar(select(Anomaly).where(Anomaly.code == case["code"]))
        if existing is not None:
            continue
        AnomalyCreate(**case)
        db.add(Anomaly(**case))
        result.anomalies_created += 1
        result.codes.append(case["code"])
    db.commit()
    return result
