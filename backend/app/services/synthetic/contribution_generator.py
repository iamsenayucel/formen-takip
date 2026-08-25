from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models.contribution import ContributionGain, ContributionWork, ContributionWorkForeman, ContributionWorkPlant
from app.models.enums import (
    ContributionRole,
    ContributionStatus,
    ContributionWorkType,
    Currency,
    FinancialGainStatus,
    GainPeriod,
    ImpactLevel,
    OtherGainType,
    RepeatPeriod,
    SuccessDirection,
    TimeUnit,
)
from app.models.foreman import Foreman, ForemanAssignment
from app.models.organization import Plant
from app.services import contribution_calc as calc

_TITLE_TEMPLATES: dict[ContributionWorkType, list[str]] = {
    ContributionWorkType.SMED: [
        "Kalıp Değişim Süresinin Kısaltılması", "Hızlı Ürün Geçişi için SMED Uygulaması",
        "Hat Duruş Süresinin Azaltılması", "Ekipman Ayar Süresinin Standartlaştırılması",
    ],
    ContributionWorkType.KAIZEN: [
        "Hat Düzeninde Sürekli İyileştirme", "Malzeme Akışında Kaizen Çalışması",
        "İş İstasyonu Yerleşiminin Kaizen ile İyileştirilmesi", "5S Uygulamasıyla Saha Düzeninin Geliştirilmesi",
    ],
    ContributionWorkType.PROBLEM_SOLVING: [
        "Tekrarlayan Duruş Nedeninin Kök Sebep Analizi", "Kalite Şikayetinin Kalıcı Çözümü",
        "Ekipman Arıza Sıklığının Kök Sebep Analiziyle Giderilmesi", "Vardiyalar Arası Veri Tutarsızlığının Çözümü",
    ],
    ContributionWorkType.COST_REDUCTION: [
        "Yardımcı Malzeme Tüketiminin Azaltılması", "Bakım Maliyetlerinde Tasarruf",
        "Ambalaj Malzemesi Kullanımının Optimize Edilmesi", "Yedek Parça Stok Maliyetinin Azaltılması",
    ],
    ContributionWorkType.TIME_SAVING: [
        "Vardiya Devir Teslim Süresinin Kısaltılması", "Numune Alma Sürecinin Hızlandırılması",
        "Rapor Hazırlama Süresinin Kısaltılması", "Malzeme Temin Süresinin Azaltılması",
    ],
    ContributionWorkType.QUALITY_IMPROVEMENT: [
        "Iskarta Oranının Azaltılması", "Ürün Kalite Kontrol Sürecinin İyileştirilmesi",
        "Hatalı Ürün Oranının Düşürülmesi", "Ölçüm/Test Sürecinin Güvenilirliğinin Artırılması",
    ],
    ContributionWorkType.SAFETY_IMPROVEMENT: [
        "Hat Üzerinde İş Güvenliği Riskinin Giderilmesi", "Ramak Kala Bildiriminden Kalıcı Önleme",
        "Kişisel Koruyucu Ekipman Kullanımının Artırılması", "Çalışma Alanı Ergonomisinin İyileştirilmesi",
    ],
    ContributionWorkType.ENERGY_RESOURCE_SAVING: [
        "Kompresör Hava Kaçaklarının Giderilmesi", "Aydınlatma Enerji Tüketiminin Azaltılması",
        "Buhar Hattı Isı Kaybının Azaltılması", "Su Tüketiminin Optimize Edilmesi",
    ],
    ContributionWorkType.PRODUCTION_EFFICIENCY: [
        "Hat Hızının Optimize Edilmesi", "Planlanmamış Duruşların Azaltılması",
        "Ekipman Kullanılabilirlik Oranının Artırılması", "Vardiya Başına Üretim Adedinin Artırılması",
    ],
    ContributionWorkType.DIGITALIZATION: [
        "Vardiya Raporlarının Dijitalleştirilmesi", "Manuel Takip Formunun Otomasyonu",
        "Üretim Verisinin Gerçek Zamanlı İzlenmesi", "Kağıt Bazlı Kontrol Listesinin Dijitalleştirilmesi",
    ],
    ContributionWorkType.FIVE_S: [
        "Saha Düzeninde 5S Uygulaması", "İş İstasyonunda 5S ile Düzen ve Temizlik Standardı",
        "Malzeme Alanının 5S Metoduyla Yeniden Düzenlenmesi", "Görsel Yönetim Panosuyla 5S Standardının Sürdürülmesi",
    ],
    ContributionWorkType.VARIETY_CHANGEOVER_EFFICIENCY: [
        "Çeşit Dönüşü Süresinin Kısaltılması", "Ürün Geçişlerinde Ayar Kaybının Azaltılması",
        "Çeşit Değişiminde Standart İş Akışının Oluşturulması", "Reçete Değişimi Verimliliğinin Artırılması",
    ],
    ContributionWorkType.STAFF_SAVING: [
        "İş Akışının Sadeleştirilmesiyle Personel Tasarrufu", "Görev Dağılımının Yeniden Düzenlenmesi",
        "Otomasyonla Personel İhtiyacının Azaltılması", "Vardiya Başına Gerekli Personel Sayısının Optimize Edilmesi",
    ],
    ContributionWorkType.CUSTOMER_COMPLAINT: [
        "Müşteri Şikayetinin Kök Sebep Analiziyle Giderilmesi", "Tekrarlayan Müşteri Şikayetinin Kalıcı Çözümü",
        "Sevkiyat Öncesi Kontrolle Müşteri Şikayetinin Önlenmesi", "Müşteri Geri Bildiriminin Sürece Entegre Edilmesi",
    ],
    ContributionWorkType.POKA_YOKE: [
        "Hatalı Montajı Önleyen Poka Yoke Düzeneği", "Ekipmana Poka Yoke Sensörü Eklenmesi",
        "Yanlış Parça Kullanımını Engelleyen Poka Yoke Uygulaması", "Kontrol Adımının Poka Yoke ile Otomatikleştirilmesi",
    ],
    ContributionWorkType.OTHER: [
        "Saha Düzeninde İyileştirme Çalışması", "Ekip İçi İletişim Sürecinin İyileştirilmesi",
        "Vardiya Planlama Sürecinin Gözden Geçirilmesi",
    ],
}

_SUMMARY_TEMPLATES: dict[ContributionWorkType, list[str]] = {
    ContributionWorkType.SMED: [
        "Kalıp değişim adımları standartlaştırılarak duruş süresi kısaltıldı.",
        "Ayar işlemleri hat dururken değil, hat çalışırken hazırlanacak şekilde yeniden planlandı.",
    ],
    ContributionWorkType.KAIZEN: [
        "Saha ekibiyle birlikte küçük adımlı iyileştirmeler uygulandı.",
        "Günlük işleyişte fark edilen aksaklıklar ekip önerileriyle adım adım giderildi.",
    ],
    ContributionWorkType.PROBLEM_SOLVING: [
        "Kök sebep analiziyle tekrarlayan sorun kalıcı olarak çözüldü.",
        "Sorunun kaynağı sahada yapılan gözlem ve verilerle netleştirilip kalıcı önlem alındı.",
    ],
    ContributionWorkType.COST_REDUCTION: [
        "Süreçte gereksiz tüketim tespit edilerek maliyet azaltıldı.",
        "Malzeme kullanımı gözden geçirilerek gereksiz harcamanın önüne geçildi.",
    ],
    ContributionWorkType.TIME_SAVING: [
        "Süreç adımları sadeleştirilerek zaman kazanımı sağlandı.",
        "Gereksiz bekleme ve tekrar eden adımlar kaldırılarak süreç hızlandırıldı.",
    ],
    ContributionWorkType.QUALITY_IMPROVEMENT: [
        "Kalite kontrol noktaları güçlendirilerek hata oranı düşürüldü.",
        "Hata tespiti sürecin daha erken bir adımına taşınarak iskarta önlendi.",
    ],
    ContributionWorkType.SAFETY_IMPROVEMENT: [
        "Riskli nokta tespit edilip kalıcı güvenlik önlemi alındı.",
        "Sahada belirlenen tehlike kaynağı kalıcı bir düzenlemeyle ortadan kaldırıldı.",
    ],
    ContributionWorkType.ENERGY_RESOURCE_SAVING: [
        "Enerji kullanımı izlenerek gereksiz tüketim önlendi.",
        "Kaynak tüketimi ölçülüp gereksiz kullanım noktaları kapatıldı.",
    ],
    ContributionWorkType.PRODUCTION_EFFICIENCY: [
        "Üretim hattı verimliliği sistematik iyileştirmeyle artırıldı.",
        "Duruş nedenleri analiz edilerek hat verimliliği kalıcı şekilde yükseltildi.",
    ],
    ContributionWorkType.DIGITALIZATION: [
        "Manuel takip süreci dijital bir çözümle değiştirildi.",
        "Kağıt üzerinde yürütülen süreç dijital bir araca taşınarak hızlandırıldı.",
    ],
    ContributionWorkType.FIVE_S: [
        "Saha 5S adımlarıyla düzenlenip görsel standart oluşturuldu.",
        "Gereksiz malzemeler kaldırılıp çalışma alanı 5S ilkeleriyle yeniden düzenlendi.",
    ],
    ContributionWorkType.VARIETY_CHANGEOVER_EFFICIENCY: [
        "Çeşit dönüşü adımları standartlaştırılarak geçiş süresi kısaltıldı.",
        "Ayar parametreleri önceden hazırlanarak çeşit dönüşü verimliliği artırıldı.",
    ],
    ContributionWorkType.STAFF_SAVING: [
        "Süreç sadeleştirilerek aynı işi daha az personelle yürütmek mümkün hale geldi.",
        "Görev dağılımı yeniden planlanarak personel ihtiyacı azaltıldı.",
    ],
    ContributionWorkType.CUSTOMER_COMPLAINT: [
        "Müşteri şikayetinin kök sebebi bulunup kalıcı önlem alındı.",
        "Şikayete konu olan süreç adımı yeniden tasarlanarak tekrarı önlendi.",
    ],
    ContributionWorkType.POKA_YOKE: [
        "Hata payını ortadan kaldıran bir poka yoke düzeneği devreye alındı.",
        "Yanlış işlem yapılmasını fiziksel olarak engelleyen bir çözüm uygulandı.",
    ],
    ContributionWorkType.OTHER: [
        "Sahada tespit edilen bir iyileştirme fırsatı hayata geçirildi.",
        "Ekip tarafından fark edilen bir aksaklık kalıcı olarak giderildi.",
    ],
}

_PROBLEM_TEMPLATES = [
    "Mevcut süreçte tekrarlayan bir verimsizlik/duruş tespit edildi.",
    "Saha gözlemlerinde standart dışı bir uygulama fark edildi.",
    "Vardiyalar arası veri toplama sırasında tutarsızlık yaşanıyordu.",
]
_SOLUTION_TEMPLATES = [
    "Formen ve ekibi birlikte adım adım bir iyileştirme planı uyguladı.",
    "Süreç standart hale getirilip görsel yönetim panosu eklendi.",
    "Ekipman/yöntem küçük bir değişiklikle yeniden düzenlendi.",
]
_RESULT_TEMPLATES = [
    "Uygulama sonrası ölçülebilir bir iyileşme gözlemlendi ve sahada kalıcı hale getirildi.",
    "Sonuçlar bir sonraki vardiyalarda da doğrulandı.",
    "İyileştirme, ilgili tesis yönetimiyle paylaşılarak onaylandı.",
]

_TIME_SAVING_TYPES = {
    ContributionWorkType.SMED, ContributionWorkType.TIME_SAVING, ContributionWorkType.PRODUCTION_EFFICIENCY,
    ContributionWorkType.VARIETY_CHANGEOVER_EFFICIENCY,
}
_OTHER_GAIN_BY_TYPE: dict[ContributionWorkType, list[OtherGainType]] = {
    ContributionWorkType.QUALITY_IMPROVEMENT: [OtherGainType.QUALITY_DEFECT_REDUCTION],
    ContributionWorkType.SAFETY_IMPROVEMENT: [OtherGainType.SAFETY_RISK_REDUCTION],
    ContributionWorkType.ENERGY_RESOURCE_SAVING: [OtherGainType.ENERGY_REDUCTION],
    ContributionWorkType.PRODUCTION_EFFICIENCY: [OtherGainType.CAPACITY_INCREASE, OtherGainType.DOWNTIME_REDUCTION],
    ContributionWorkType.COST_REDUCTION: [OtherGainType.SCRAP_REDUCTION, OtherGainType.LABOR_SAVING],
    ContributionWorkType.KAIZEN: [OtherGainType.GSF_REDUCTION, OtherGainType.SLOW_RUNNING_REDUCTION],
    ContributionWorkType.STAFF_SAVING: [OtherGainType.LABOR_SAVING],
    ContributionWorkType.CUSTOMER_COMPLAINT: [OtherGainType.QUALITY_DEFECT_REDUCTION],
    ContributionWorkType.POKA_YOKE: [OtherGainType.QUALITY_DEFECT_REDUCTION, OtherGainType.SCRAP_REDUCTION],
}


@dataclass
class ContributionSeedResult:
    works_created: int = 0
    published_count: int = 0
    draft_count: int = 0
    foreman_ids: list[UUID] = field(default_factory=list)


def _foremen_by_plant(db: Session) -> dict[UUID, list[Foreman]]:
    result: dict[UUID, list[Foreman]] = {}
    rows = db.execute(
        select(ForemanAssignment.plant_id, Foreman)
        .join(Foreman, Foreman.id == ForemanAssignment.foreman_id)
        .where(ForemanAssignment.is_active.is_(True))
    ).all()
    for plant_id, foreman in rows:
        result.setdefault(plant_id, []).append(foreman)
    return result


def _plants_by_foreman(db: Session) -> dict[UUID, list[UUID]]:
    result: dict[UUID, list[UUID]] = {}
    rows = db.execute(
        select(ForemanAssignment.foreman_id, ForemanAssignment.plant_id).where(ForemanAssignment.is_active.is_(True))
    ).all()
    for foreman_id, plant_id in rows:
        result.setdefault(foreman_id, []).append(plant_id)
    return result


def seed_contribution_works(
    db: Session, rng: random.Random, creator_subject: str, count: int = 40
) -> ContributionSeedResult:
    plants = list(db.scalars(select(Plant).where(Plant.is_active.is_(True))))
    foremen_by_plant = _foremen_by_plant(db)
    plants_by_foreman = _plants_by_foreman(db)
    eligible_plants = [p for p in plants if foremen_by_plant.get(p.id)]
    if not eligible_plants:
        return ContributionSeedResult()

    result = ContributionSeedResult()
    work_types = list(ContributionWorkType)
    today = clock.today_local()
    used_title_summary: set[tuple[str, str]] = set()

    for _ in range(count):
        plant = rng.choice(eligible_plants)
        plant_foremen = foremen_by_plant[plant.id]
        chosen_foremen = rng.sample(plant_foremen, k=min(len(plant_foremen), rng.randint(1, 3)))

        zone_plant_ids = {plant.id}
        for foreman in chosen_foremen:
            zone_plant_ids.update(plants_by_foreman.get(foreman.id, []))
        work_plant_ids = [plant.id] + rng.sample(
            sorted(zone_plant_ids - {plant.id}, key=str),
            k=min(len(zone_plant_ids) - 1, rng.randint(0, 2)),
        )
        work_type = rng.choice(work_types)
        is_published = rng.random() < 0.8
        work_date = today - timedelta(days=rng.randint(1, 300))
        impact_level = rng.choices(list(ImpactLevel), weights=[0.3, 0.45, 0.25])[0]

        title_options = _TITLE_TEMPLATES[work_type]
        summary_options = _SUMMARY_TEMPLATES[work_type]
        all_combos = [(t, s) for t in title_options for s in summary_options]
        available_combos = [c for c in all_combos if c not in used_title_summary] or all_combos
        title, summary = rng.choice(available_combos)
        used_title_summary.add((title, summary))

        has_financial = rng.random() < 0.6
        financial_gain_status = FinancialGainStatus.NOT_CALCULATED
        gain_amount = None
        currency = gain_period = None
        if has_financial:
            financial_gain_status = FinancialGainStatus.YES
            gain_amount = round(rng.uniform(5_000, 300_000), 2)
            currency = Currency.TRY
            gain_period = rng.choice(list(GainPeriod))

        previous_duration = new_duration = duration_unit = repeat_period = repeat_count = None
        per_occurrence_saving = monthly_total_saving_minutes = None
        if work_type in _TIME_SAVING_TYPES and rng.random() < 0.7:
            duration_unit = TimeUnit.MINUTE
            previous_duration = round(rng.uniform(20, 90), 1)
            new_duration = round(previous_duration * rng.uniform(0.4, 0.8), 1)
            repeat_period = rng.choice(list(RepeatPeriod))
            repeat_count = float(rng.randint(1, 30))
            per_occurrence_saving = calc.compute_time_saving(previous_duration, new_duration)
            per_occurrence_minutes = calc.duration_to_minutes(per_occurrence_saving, duration_unit)
            monthly_total_saving_minutes = calc.compute_monthly_total(per_occurrence_minutes, repeat_period, repeat_count)

        work = ContributionWork(
            title=title, status=ContributionStatus.PUBLISHED if is_published else ContributionStatus.DRAFT,
            work_type=work_type, summary=summary,
            detailed_description=f"{summary} {rng.choice(_RESULT_TEMPLATES)}",
            problem_description=rng.choice(_PROBLEM_TEMPLATES),
            solution_description=rng.choice(_SOLUTION_TEMPLATES),
            result_description=rng.choice(_RESULT_TEMPLATES),
            work_date=work_date,
            impact_level=impact_level, created_by_subject=creator_subject,
            is_standardized=rng.random() < 0.35, is_applicable_other_plants=rng.random() < 0.3,
            is_permanent_solution=rng.random() < 0.5, work_instruction_updated=rng.random() < 0.25,
            financial_gain_status=financial_gain_status, gain_amount=gain_amount,
            currency=currency, gain_period=gain_period,
            previous_duration=previous_duration, new_duration=new_duration, duration_unit=duration_unit,
            repeat_period=repeat_period, repeat_count=repeat_count,
            per_occurrence_saving=per_occurrence_saving, monthly_total_saving_minutes=monthly_total_saving_minutes,
            published_at=clock.now_utc() if is_published else None,
        )
        db.add(work)
        db.flush()

        work_gains: list[ContributionGain] = []

        lead_foreman_id = chosen_foremen[0].id if chosen_foremen else None
        if len(chosen_foremen) > 1:
            lead_foreman_id = rng.choice(chosen_foremen).id
        for foreman in chosen_foremen:
            role = ContributionRole.LEAD if foreman.id == lead_foreman_id else ContributionRole.CONTRIBUTOR
            db.add(ContributionWorkForeman(work_id=work.id, foreman_id=foreman.id, role=role))

        for plant_id in work_plant_ids:
            db.add(ContributionWorkPlant(work_id=work.id, plant_id=plant_id))

        gain_type_options = _OTHER_GAIN_BY_TYPE.get(work_type)
        if gain_type_options and rng.random() < 0.7:
            gain_type = rng.choice(gain_type_options)
            previous_value = round(rng.uniform(2, 20), 2)
            direction = calc.GAIN_TYPE_DIRECTION.get(gain_type)
            if direction == SuccessDirection.HIGHER_IS_BETTER:
                next_value = round(previous_value * rng.uniform(1.1, 1.4), 2)
            else:
                next_value = round(previous_value * rng.uniform(0.5, 0.85), 2)
            amount, percent = calc.compute_change(previous_value, next_value)
            gain = ContributionGain(
                work_id=work.id, gain_type=gain_type, previous_value=previous_value, next_value=next_value,
                change_amount=amount, change_percent=percent, unit="%", measurement_period="Aylık",
            )
            db.add(gain)
            work_gains.append(gain)

        work.contribution_score = calc.compute_contribution_score(work, work_gains)[0]

        result.works_created += 1
        if is_published:
            result.published_count += 1
        else:
            result.draft_count += 1
        result.foreman_ids.extend(f.id for f in chosen_foremen)

    db.commit()
    return result
