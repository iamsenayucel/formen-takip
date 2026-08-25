from __future__ import annotations

from app.models.enums import AnomalyType

KPI_DEFINITIONS: dict[str, dict] = {
    "AGIR_GITME": {
        "name": "Ağır Gitme Oranı",
        "description": (
            "Üretilen ürünlerin kabul edilen gramaj aralığının (alt/üst limit) dışına çıkan "
            "işaretli sapmasının, standart üretim gramajına oranı."
        ),
        "desired_direction": "low",
        "warning_threshold": 6.0,
        "critical_threshold": 9.0,
    },
    "GSF": {
        "name": "GSF Oranı",
        "description": (
            "Tekrar üretimde kullanılamayan, geri kazanılamayan ve çöp veya hayvan yemi olarak "
            "değerlendirilen nihai fire miktarının toplam brüt üretim miktarına oranı."
        ),
        "desired_direction": "low",
        "warning_threshold": 5.0,
        "critical_threshold": 8.0,
    },
    "ISKARTA": {
        "name": "Iskarta Oranı",
        "description": (
            "Şekil veya yapı bozukluğu nedeniyle paketlenemeyen ancak ürün hamurlarına katılarak "
            "yeniden üretimde kullanılabilen geri dönüştürülebilir ürün miktarının toplam brüt "
            "üretim miktarına oranı."
        ),
        "desired_direction": "low",
        "warning_threshold": 8.0,
        "critical_threshold": 12.0,
    },
    "INKITA": {
        "name": "İnkita Oranı",
        "description": (
            "Teknik ve imalat kaynaklı duruş sürelerinin planlanan üretim süresine oranı "
            "(diğer duruşlar puana dahil edilmez)."
        ),
        "desired_direction": "low",
        "warning_threshold": 10.0,
        "critical_threshold": 15.0,
    },
    "PLANA_UYUM": {
        "name": "Plana Uyum Oranı",
        "description": (
            "Gerçekleşen üretimin, güncel (revize) üretim planına göre yönlü sapması "
            "(planın üzerinde üretim ödüllendirilir, planın altında üretim daha güçlü cezalandırılır)."
        ),
        "desired_direction": "high",
        "warning_threshold": 90.0,
        "critical_threshold": 80.0,
    },
    "OEE": {
        "name": "OEE",
        "description": (
            "Bir vardiyanın (720 dk) ya da tesis/dönem toplamının gerçekleşen çalışma süresinin, "
            "ilgili toplam süreye oranı."
        ),
        "desired_direction": "high",
        "warning_threshold": 85.0,
        "critical_threshold": 70.0,
    },
}

ANOMALY_TYPE_LABELS: dict[AnomalyType, str] = {
    AnomalyType.SHIFT_UNDERPERFORMANCE: "Vardiya Bazlı Sürekli Düşük Performans",
    AnomalyType.RISING_TREND: "Yükselen Trend",
    AnomalyType.FOREMAN_DEVIATION: "Formen Bazlı Sapma",
    AnomalyType.PRODUCT_GROUP_DEVIATION: "Ürün Grubu Bazlı Sapma",
    AnomalyType.DOWNTIME_CONCENTRATION: "Duruş Yoğunlaşması",
    AnomalyType.PLAN_ADHERENCE_STREAK: "Art Arda Plan Altı Kalma",
    AnomalyType.PLANT_HISTORICAL_DEVIATION: "Tesis Geçmiş Ortalamasından Sapma",
    AnomalyType.CROSS_PLANT_GAP: "Tesisler Arası Performans Farkı",
    AnomalyType.MULTI_KPI_SIMULTANEOUS: "Eş Zamanlı Çoklu KPI Bozulması",
    AnomalyType.SINGLE_DAY_SPIKE: "Tek Günlük Ani Anormallik",
    AnomalyType.CHRONIC_ANOMALY: "Kronik Anormallik",
    AnomalyType.CRITICAL_PRODUCTION_LOSS: "Kritik Üretim Kaybı",
    AnomalyType.DATA_QUALITY_SUSPECT: "Veri Kalitesi Şüphesi",
}

SEVERITY_LABELS = {"low": "Düşük", "medium": "Orta", "high": "Yüksek", "critical": "Kritik"}
STATUS_LABELS = {
    "new": "Yeni",
    "in_review": "İnceleniyor",
    "action_pending": "Aksiyon Bekliyor",
    "resolved": "Çözüldü",
    "closed": "Kapatıldı",
}
ANALYSIS_STATUS_LABELS = {
    "not_analyzed": "Analiz Edilmedi",
    "analyzing": "Analiz Ediliyor",
    "queued": "Sırada",
    "planning": "Analiz Planlanıyor",
    "collecting_data": "Veriler Toplanıyor",
    "generating_analysis": "Sonuç Hazırlanıyor",
    "completed": "Analiz Tamamlandı",
    "completed_with_warnings": "Uyarılarla Tamamlandı",
    "failed": "Analiz Başarısız",
    "timed_out": "Zaman Aşımına Uğradı",
    "cancelled": "İptal Edildi",
}
