
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import CalculationType, TargetScopeType
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget, PerformanceLevelRule
from app.models.organization import Factory, Plant, Shift

LOCATION = "Karaman"
FACTORY_SEED = [
    dict(code="K1", name="K1 Fabrikası", plant_count=27),
    dict(code="K2", name="K2 Fabrikası", plant_count=23),
]
TOTAL_PLANTS = sum(f["plant_count"] for f in FACTORY_SEED)

FIRST_NAMES = [
    "Ahmet", "Mehmet", "Mustafa", "Ali", "Hüseyin", "Hasan", "İbrahim", "Osman", "Yusuf", "Murat",
    "Kemal", "Cengiz", "Serkan", "Onur", "Burak", "Emre", "Kaan", "Tolga", "Volkan", "Selim",
    "Barış", "Cem", "Ercan", "Fatih", "Gökhan", "Halil", "İsmail", "Kadir", "Levent", "Mert",
    "Oğuz", "Recep", "Sinan", "Tarık", "Ufuk", "Alper", "Hakan", "Kerem", "Umut", "Yavuz",
    "Fatma", "Ayşe", "Emine", "Hatice", "Zeynep", "Elif", "Meryem", "Şerife", "Sultan", "Esra",
    "Aslı", "Buse", "Ceren", "Damla", "Ebru", "Filiz", "Gamze", "Hülya", "İpek", "Kübra",
    "Leyla", "Melis", "Özlem", "Pınar", "Rabia", "Sevgi", "Tuğba", "Yasemin", "Zehra", "Aynur",
    "Berna", "Canan", "Dilek", "Emel", "Funda", "Handan", "Merve", "Nazlı", "Selin", "Tülay",
]
LAST_NAMES = [
    "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk", "Aydın", "Özdemir",
    "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara", "Koç", "Kurt", "Özkan", "Şimşek",
    "Polat", "Korkmaz", "Çakır", "Erdoğan", "Güneş", "Aksoy", "Bulut", "Yalçın", "Turan", "Avcı",
    "Şen", "Bozkurt", "Ateş", "Erdem", "Tekin", "Acar", "Karaca", "Sarı", "Uysal", "Toprak",
    "Duman", "Genç", "Tunç", "Başaran", "Fidan", "Gündüz", "Işık", "Kaplan", "Keskin", "Köse",
    "Ocak", "Sağlam", "Solmaz", "Taş", "Ünal", "Vural", "Yaman", "Akın", "Balcı", "Çiftçi",
    "Dinç", "Ergün", "Güler", "Koçak", "Öztaş", "Sezer", "Tanrıverdi", "Uçar", "Sevinç", "Zorlu",
]

EMAIL_DOMAIN = "example.com"
_TURKISH_CHAR_MAP = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "I": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_MOBILE_PREFIXES = ["501", "505", "506", "507", "530", "532", "533", "541", "542", "555"]


def _normalize_email_local_part(value: str) -> str:
    ascii_value = value.translate(_TURKISH_CHAR_MAP).lower()
    return _NON_ALNUM_RE.sub("", ascii_value)


def _make_email(first_name: str, last_name: str, used_emails: set[str]) -> str:
    base = f"{_normalize_email_local_part(first_name)}.{_normalize_email_local_part(last_name)}"
    candidate = f"{base}@{EMAIL_DOMAIN}"
    suffix = 2
    while candidate in used_emails:
        candidate = f"{base}{suffix}@{EMAIL_DOMAIN}"
        suffix += 1
    used_emails.add(candidate)
    return candidate


def _make_phone_number(rng: random.Random, used_phones: set[str]) -> str:
    while True:
        prefix = rng.choice(_MOBILE_PREFIXES)
        subscriber = "".join(str(rng.randint(0, 9)) for _ in range(7))
        candidate = f"+90{prefix}{subscriber}"
        if candidate not in used_phones:
            used_phones.add(candidate)
            return candidate

_NO_CEILING_SENTINEL = 999999.99

_NO_PLANT_TARGET_VARIANCE_KPI_CODES = frozenset({"OEE"})


def kpis_needing_plant_target_variance(kpis: list[Kpi]) -> list[Kpi]:
    return [k for k in kpis if k.code not in _NO_PLANT_TARGET_VARIANCE_KPI_CODES]

DEFAULT_KPI_SEED = [
    dict(
        code="AGIR_GITME", name="Ağır Gitme Oranı",
        description="Üretilen ürünlerin kabul edilen gramaj aralığının (alt/üst limit) dışına çıkan işaretli sapmasının, standart üretim gramajına oranı.",
        unit="%", calculation_type=CalculationType.CUSTOM_FORMULA, success_direction_higher=False,
        default_target_value=1.5, min_valid_value=-100, max_valid_value=100,
        min_score=0, max_score=_NO_CEILING_SENTINEL, weight=13, is_critical=True, display_order=1,
        rule_params={"formula_type": "SIGNED_ABSOLUTE_PIECEWISE", "good_coefficient": 9, "bad_coefficient": 12},
    ),
    dict(
        code="GSF", name="GSF Oranı",
        description="Tekrar üretimde kullanılamayan, geri kazanılamayan ve çöp veya hayvan yemi olarak değerlendirilen nihai fire miktarının toplam brüt üretim miktarına oranı.",
        unit="%", calculation_type=CalculationType.CUSTOM_FORMULA, success_direction_higher=False,
        default_target_value=3.0, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=_NO_CEILING_SENTINEL, weight=20, is_critical=True, display_order=2,
        rule_params={
            "formula_type": "HYBRID_BASE_PIECEWISE_LOG", "minimum_normalization_base": 0.05,
            "good_coefficient": 10, "bad_coefficient": 16,
        },
    ),
    dict(
        code="ISKARTA", name="Iskarta Oranı",
        description="Şekil veya yapı bozukluğu nedeniyle paketlenemeyen ancak ürün hamurlarına katılarak yeniden üretimde kullanılabilen geri dönüştürülebilir ürün miktarının toplam brüt üretim miktarına oranı.",
        unit="%", calculation_type=CalculationType.CUSTOM_FORMULA, success_direction_higher=False,
        default_target_value=2.0, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=_NO_CEILING_SENTINEL, weight=12, is_critical=True, display_order=3,
        rule_params={"formula_type": "TARGET_RATIO_PIECEWISE", "good_coefficient": 12, "bad_coefficient": 12},
    ),
    dict(
        code="INKITA", name="İnkita Oranı",
        description="Teknik ve imalat kaynaklı duruş sürelerinin planlanan üretim süresine oranı (Diğer duruşlar puana dahil edilmez).",
        unit="%", calculation_type=CalculationType.CUSTOM_FORMULA, success_direction_higher=False,
        default_target_value=10.0, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=_NO_CEILING_SENTINEL, weight=22, is_critical=True, display_order=4,
        rule_params={
            "formula_type": "HYBRID_BASE_PIECEWISE_LOG",
            "included_components": ["TECHNICAL", "MANUFACTURING"], "excluded_components": ["OTHER"],
            "minimum_normalization_base": 0.50, "good_coefficient": 6, "bad_coefficient": 10,
        },
    ),
    dict(
        code="PLANA_UYUM", name="Plana Uyum Oranı",
        description="Gerçekleşen üretimin, güncel (revize) üretim planına göre yönlü sapması (planın üzerinde üretim ödüllendirilir, planın altında üretim daha güçlü cezalandırılır).",
        unit="%", calculation_type=CalculationType.CUSTOM_FORMULA, success_direction_higher=True,
        default_target_value=100.0, min_valid_value=0, max_valid_value=300,
        min_score=0, max_score=_NO_CEILING_SENTINEL, weight=12, is_critical=True, display_order=5,
        rule_params={
            "formula_type": "ASYMMETRIC_PLAN_ACHIEVEMENT",
            "target_score": 100, "positive_linear_limit": 5.0,
            "positive_points_per_percentage_point": 1.0, "positive_log_coefficient": 5.0,
            "negative_linear_limit": 5.0, "negative_points_per_percentage_point": 1.0,
            "negative_log_coefficient": 10.0, "minimum_score": 0, "maximum_score": None,
        },
    ),
    dict(
        code="OEE", name="OEE",
        description=(
            "Bir vardiyanın (720 dk) ya da tesis/dönem toplamının gerçekleşen çalışma süresinin, "
            "ilgili toplam süreye oranı. Formen düzeyinde kendi vardiyasını, tesis/dönem düzeyinde "
            "vardiyaların toplamını kapsar."
        ),
        unit="%", calculation_type=CalculationType.CUSTOM_FORMULA, success_direction_higher=True,
        default_target_value=100.0, min_valid_value=0, max_valid_value=100,
        min_score=0, max_score=105, weight=21, is_critical=True, display_order=6,
        rule_params={"formula_type": "TARGET_RATIO_LINEAR_BONUS", "ratio_multiplier": 1.05, "max_score": 105},
    ),
]

PERFORMANCE_LEVEL_SEED = [
    dict(name="Kritik", min_score=0, max_score=69.99, description="Acil aksiyon gerektiren kritik performans.", color="#DC2626", icon="alert-triangle", sort_order=1),
    dict(name="Geliştirilmeli", min_score=70, max_score=89.99, description="Hedefin altında, iyileştirme gerekiyor.", color="#EA580C", icon="trending-down", sort_order=2),
    dict(name="Başarılı", min_score=90, max_score=9999.99, description="Hedef seviyesinde veya üzerinde başarılı performans.", color="#16A34A", icon="check-circle", sort_order=3),
]

SHIFT_SEED = [
    dict(code="V1", name="1. Vardiya", start="07:00", end="19:00", sequence=1),
    dict(code="V2", name="2. Vardiya", start="19:00", end="07:00", sequence=2),
]


@dataclass
class ReferenceData:
    factories: list[Factory] = field(default_factory=list)
    plants: list[Plant] = field(default_factory=list)
    shifts: list[Shift] = field(default_factory=list)
    chiefs: list[Chief] = field(default_factory=list)
    foremen: list[Foreman] = field(default_factory=list)
    assignments: list[ForemanAssignment] = field(default_factory=list)
    kpis: list[Kpi] = field(default_factory=list)
    calculation_rules: dict[str, KpiCalculationRule] = field(default_factory=dict)
    targets: list[KpiTarget] = field(default_factory=list)
    performance_levels: list[PerformanceLevelRule] = field(default_factory=list)


def _parse_time(value: str):
    from datetime import time

    h, m = value.split(":")
    return time(int(h), int(m))


def _build_unique_name_pool(rng: random.Random) -> list[tuple[str, str]]:
    combos = [(first, last) for first in FIRST_NAMES for last in LAST_NAMES]
    rng.shuffle(combos)
    return combos


def _take_name(pool: list[tuple[str, str]]) -> tuple[str, str]:
    if not pool:
        raise ValueError(
            "Benzersiz ad-soyad havuzu tükendi — FIRST_NAMES/LAST_NAMES listelerini genişletin."
        )
    return pool.pop()


def _partition_into_groups(rng: random.Random, items: list, min_size: int, max_size: int) -> list[list]:
    pool = list(items)
    rng.shuffle(pool)
    groups: list[list] = []
    i = 0
    n = len(pool)
    while i < n:
        remaining = n - i
        if remaining <= max_size:
            size = remaining
        else:
            size = rng.randint(min_size, max_size)
            if remaining - size < min_size:
                size -= min_size - (remaining - size)
        groups.append(pool[i : i + size])
        i += size
    return groups


def seed_reference_data(
    db: Session,
    rng: random.Random,
    min_plants_per_foreman: int,
    max_plants_per_foreman: int,
    period_start: date,
    period_end: date,
) -> ReferenceData:
    ref = ReferenceData()

    for s in SHIFT_SEED:
        shift = Shift(
            code=s["code"], name=s["name"],
            start_time=_parse_time(s["start"]), end_time=_parse_time(s["end"]),
            sequence=s["sequence"], crosses_midnight=_parse_time(s["end"]) <= _parse_time(s["start"]),
            is_active=True,
        )
        db.add(shift)
        ref.shifts.append(shift)
    db.flush()

    for spec in DEFAULT_KPI_SEED:
        kpi = Kpi(
            code=spec["code"], name=spec["name"], description=spec["description"], unit=spec["unit"],
            calculation_type=spec["calculation_type"], success_direction_higher=spec["success_direction_higher"],
            default_target_value=spec["default_target_value"], min_valid_value=spec["min_valid_value"],
            max_valid_value=spec["max_valid_value"], min_score=spec["min_score"], max_score=spec["max_score"],
            weight=spec["weight"], valid_from=date(2020, 1, 1), is_active=True,
            aggregation_method=_default_aggregation_for(spec["calculation_type"]),
            decimal_places=2, is_critical=spec["is_critical"], display_order=spec["display_order"],
        )
        db.add(kpi)
        db.flush()
        rule = KpiCalculationRule(
            kpi_id=kpi.id, version=1, calculation_type=spec["calculation_type"],
            parameters=spec["rule_params"], valid_from=date(2020, 1, 1), is_active=True,
        )
        db.add(rule)
        ref.kpis.append(kpi)
        ref.calculation_rules[kpi.code] = rule
    db.flush()

    weights = [k.weight for k in ref.kpis]
    from app.services.kpi_engine import validate_kpi_weights

    ok, msg = validate_kpi_weights([float(w) for w in weights])
    if not ok:
        raise ValueError(f"Sentetik KPI seed verisi geçersiz ağırlıkla tanımlandı: {msg}")

    for lv in PERFORMANCE_LEVEL_SEED:
        level = PerformanceLevelRule(**lv)
        db.add(level)
        ref.performance_levels.append(level)
    db.flush()

    for kpi in ref.kpis:
        target = KpiTarget(
            kpi_id=kpi.id, scope_type=TargetScopeType.COMPANY, scope_id=None,
            target_value=kpi.default_target_value, valid_from=date(2020, 1, 1), is_active=True,
        )
        db.add(target)
        ref.targets.append(target)
    db.flush()

    factories_by_code: dict[str, Factory] = {}
    for spec in FACTORY_SEED:
        factory = Factory(code=spec["code"], name=spec["name"], location=LOCATION, is_active=True)
        db.add(factory)
        db.flush()
        ref.factories.append(factory)
        factories_by_code[spec["code"]] = factory

    name_pool = _build_unique_name_pool(rng)
    used_chief_emails: set[str] = set()
    used_chief_phones: set[str] = set()
    used_foreman_emails: set[str] = set()
    used_foreman_phones: set[str] = set()

    zones: list[tuple[Chief, list[Plant]]] = []
    sequence_number = 0
    for spec in FACTORY_SEED:
        factory = factories_by_code[spec["code"]]
        factory_plant_specs = []
        for _ in range(spec["plant_count"]):
            sequence_number += 1
            factory_plant_specs.append(
                dict(
                    code=f"PLT{sequence_number:02d}",
                    name=f"{sequence_number}. Tesis",
                    sequence_number=sequence_number,
                    factory_id=factory.id,
                    factory_name=factory.name,
                )
            )

        for group in _partition_into_groups(rng, factory_plant_specs, min_plants_per_foreman, max_plants_per_foreman):
            chief_hire = _random_date(
                rng, period_start - timedelta(days=365 * 5), period_end - timedelta(days=1)
            )
            chief_first, chief_last = _take_name(name_pool)
            zone_idx = len(zones) + 1
            chief = Chief(
                employee_number=f"SEF-{zone_idx:03d}",
                first_name=chief_first, last_name=chief_last,
                hire_date=chief_hire, is_active=True,
                sap_personnel_number=f"SAP-S-{zone_idx:03d}",
                phone_number=_make_phone_number(rng, used_chief_phones),
                email=_make_email(chief_first, chief_last, used_chief_emails),
            )
            db.add(chief)
            db.flush()
            ref.chiefs.append(chief)

            zone_plants: list[Plant] = []
            for pspec in sorted(group, key=lambda p: p["sequence_number"]):
                plant = Plant(
                    code=pspec["code"], name=pspec["name"], sequence_number=pspec["sequence_number"],
                    factory_id=pspec["factory_id"], chief_id=chief.id,
                    description=f"{pspec['factory_name']} bünyesindeki {pspec['sequence_number']}. Tesis.",
                    is_active=True, sap_plant_code=f"SAP-{pspec['sequence_number']:04d}",
                )
                db.add(plant)
                db.flush()
                ref.plants.append(plant)
                zone_plants.append(plant)
            zones.append((chief, zone_plants))

    ref.plants.sort(key=lambda p: p.sequence_number)

    foreman_idx_by_shift: dict[str, int] = {}
    for shift in ref.shifts:
        for chief, zone_plants in zones:
            hire_earliest = period_start - timedelta(days=365 * 3)
            hire_latest = period_end - timedelta(days=1)
            hire_date = _random_date(rng, hire_earliest, hire_latest)

            is_terminated = rng.random() < 0.04
            termination_date = None
            is_active = True
            if is_terminated:
                term_earliest = max(hire_date, period_start) + timedelta(days=30)
                if term_earliest < period_end:
                    termination_date = _random_date(rng, term_earliest, period_end)
                    is_active = termination_date < period_end

            foreman_idx = foreman_idx_by_shift.get(shift.code, 0) + 1
            foreman_idx_by_shift[shift.code] = foreman_idx

            foreman_first, foreman_last = _take_name(name_pool)
            foreman = Foreman(
                employee_number=f"SCL-{shift.code}-{foreman_idx:03d}",
                first_name=foreman_first, last_name=foreman_last,
                hire_date=hire_date, termination_date=termination_date, is_active=is_active,
                sap_personnel_number=f"SAP-P-{shift.code}{foreman_idx:03d}",
                phone_number=_make_phone_number(rng, used_foreman_phones),
                email=_make_email(foreman_first, foreman_last, used_foreman_emails),
            )
            db.add(foreman)
            db.flush()
            ref.foremen.append(foreman)

            for plant in zone_plants:
                assignment = ForemanAssignment(
                    foreman_id=foreman.id, plant_id=plant.id, chief_id=chief.id,
                    shift_id=shift.id,
                    start_date=hire_date, end_date=termination_date, is_active=is_active,
                )
                db.add(assignment)
                ref.assignments.append(assignment)

    kpis_with_plant_variance = kpis_needing_plant_target_variance(ref.kpis)
    for plant in ref.plants:
        for kpi in kpis_with_plant_variance:
            base = float(kpi.default_target_value)
            variation = rng.uniform(-0.15, 0.15)
            target_value = max(0.01, min(float(kpi.max_valid_value), base * (1 + variation)))
            plant_target = KpiTarget(
                kpi_id=kpi.id, scope_type=TargetScopeType.PLANT, scope_id=plant.id,
                target_value=target_value,
                valid_from=date(2020, 1, 1), is_active=True,
            )
            db.add(plant_target)
            ref.targets.append(plant_target)
    db.flush()

    plant_target_count = sum(1 for t in ref.targets if t.scope_type == TargetScopeType.PLANT)
    expected_plant_target_count = len(ref.plants) * len(kpis_with_plant_variance)
    if plant_target_count != expected_plant_target_count:
        raise ValueError(
            f"Tesis bazlı KPI hedef kapsamı eksik: {plant_target_count}/{expected_plant_target_count} "
            "(her aktif tesis, plant-varyasyonu üretilen her KPI için ayrı bir hedefe sahip olmalı)."
        )

    db.commit()
    return ref


def validate_plant_kpi_target_coverage(db: Session) -> tuple[bool, list[str]]:
    active_plant_ids = {p.id for p in db.scalars(select(Plant).where(Plant.is_active.is_(True)))}
    active_kpis = [
        k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))
        if k.code not in _NO_PLANT_TARGET_VARIANCE_KPI_CODES
    ]
    covered: dict[uuid.UUID, set[uuid.UUID]] = {}
    for target in db.scalars(
        select(KpiTarget).where(KpiTarget.scope_type == TargetScopeType.PLANT, KpiTarget.is_active.is_(True))
    ):
        covered.setdefault(target.scope_id, set()).add(target.kpi_id)

    missing: list[str] = []
    for plant in db.scalars(select(Plant).where(Plant.id.in_(active_plant_ids)).order_by(Plant.sequence_number)):
        plant_covered = covered.get(plant.id, set())
        for kpi in active_kpis:
            if kpi.id not in plant_covered:
                missing.append(f"{plant.code} / {kpi.code}")

    return (len(missing) == 0), missing


def load_existing_reference_data(db: Session) -> ReferenceData:
    ref = ReferenceData()
    ref.plants = list(db.scalars(select(Plant).order_by(Plant.sequence_number)))
    ref.foremen = list(db.scalars(select(Foreman)))
    ref.shifts = list(db.scalars(select(Shift).order_by(Shift.sequence)))
    ref.assignments = list(db.scalars(select(ForemanAssignment)))
    return ref


def regenerate_personnel_identities(db: Session, rng: random.Random) -> tuple[int, int]:
    plants = {p.id: p for p in db.scalars(select(Plant))}
    name_pool = _build_unique_name_pool(rng)

    plants_by_chief: dict = {}
    for p in plants.values():
        plants_by_chief.setdefault(p.chief_id, []).append(p)

    chiefs = list(db.scalars(select(Chief)))
    chiefs.sort(
        key=lambda c: (
            min((p.sequence_number for p in plants_by_chief.get(c.id, [])), default=0),
            c.employee_number,
        )
    )

    shifts = {s.id: s for s in db.scalars(select(Shift))}
    shift_code_by_foreman: dict = {}
    primary_seq_by_foreman: dict = {}
    for assignment in db.scalars(select(ForemanAssignment).order_by(ForemanAssignment.start_date)):
        shift_code_by_foreman.setdefault(assignment.foreman_id, shifts[assignment.shift_id].code)
        seq = plants[assignment.plant_id].sequence_number
        primary_seq_by_foreman[assignment.foreman_id] = min(
            seq, primary_seq_by_foreman.get(assignment.foreman_id, seq)
        )

    foremen = [f for f in db.scalars(select(Foreman)) if f.id in shift_code_by_foreman]
    foremen.sort(key=lambda f: (shift_code_by_foreman[f.id], primary_seq_by_foreman[f.id], f.employee_number))

    used_chief_emails: set[str] = set()
    used_chief_phones: set[str] = set()
    used_foreman_emails: set[str] = set()
    used_foreman_phones: set[str] = set()

    for zone_idx, chief in enumerate(chiefs, start=1):
        chief.first_name, chief.last_name = _take_name(name_pool)
        chief.employee_number = f"SEF-{zone_idx:03d}"
        chief.sap_personnel_number = f"SAP-S-{zone_idx:03d}"
        chief.phone_number = _make_phone_number(rng, used_chief_phones)
        chief.email = _make_email(chief.first_name, chief.last_name, used_chief_emails)

    foreman_idx_by_shift: dict[str, int] = {}
    for foreman in foremen:
        shift_code = shift_code_by_foreman[foreman.id]
        idx = foreman_idx_by_shift.get(shift_code, 0) + 1
        foreman_idx_by_shift[shift_code] = idx
        foreman.first_name, foreman.last_name = _take_name(name_pool)
        foreman.employee_number = f"SCL-{shift_code}-{idx:03d}"
        foreman.sap_personnel_number = f"SAP-P-{shift_code}{idx:03d}"
        foreman.phone_number = _make_phone_number(rng, used_foreman_phones)
        foreman.email = _make_email(foreman.first_name, foreman.last_name, used_foreman_emails)

    db.commit()
    return len(chiefs), len(foremen)


def _default_aggregation_for(calc_type: CalculationType):
    from app.models.enums import AggregationMethod

    if calc_type in (
        CalculationType.HIGHER_IS_BETTER, CalculationType.LOWER_IS_BETTER, CalculationType.RANGE_TARGET,
        CalculationType.CUSTOM_FORMULA,
    ):
        return AggregationMethod.RATIO_RECOMPUTE
    if calc_type == CalculationType.PROPORTIONAL_PENALTY:
        return AggregationMethod.SUM
    return AggregationMethod.AVERAGE


def _random_date(rng: random.Random, start: date, end: date) -> date:
    if end <= start:
        return start
    delta_days = (end - start).days
    return start + timedelta(days=rng.randint(0, delta_days))
