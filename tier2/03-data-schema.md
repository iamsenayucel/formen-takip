# Veri Şeması ve İş Kuralları

## Veritabanı Şeması

PostgreSQL şeması SQLAlchemy modelleri ve tek Alembic zinciriyle yönetilir.
Güncel tek head (`alembic heads` ile doğrulandı):

```text
3dd3d7f35759 — RBAC role/scope tabloları (user_role_assignments, user_scope_assignments)
```

OEE zinciri `f1a3c5e7b9d2` (KPI ekleme) → `c4a99f861289` (vardiya seviyesinde
720 dakika semantiği) → `3b43eeec9028` (güncel ağırlıklar) → `3dd3d7f35759`
(RBAC, salt-additive: mevcut tablolara ALTER/lock/backfill yok, tam geri
alınabilir) şeklindedir.

Ana tablo grupları:

| Grup | Tablolar | Temel ilişkiler |
|---|---|---|
| Organizasyon | `factories`, `plants`, `shifts` | Tesis → fabrika ve şef; V1/V2 vardiya tanımı |
| Personel | `chiefs`, `foremen`, `foreman_assignments` | Assignment → formen, tesis, şef, vardiya ve tarih aralığı |
| Üretim | `products`, `production_lines`, `company_calendar`, `foreman_work_calendar`, `production_records` | Ham vardiya/üretim/duruş verisi |
| KPI | `kpis`, `kpi_calculation_rules`, `kpi_targets`, `performance_level_rules` | Tarihsel kural, kapsam hedefi ve seviye tanımı |
| Performans | `performance_records`, `performance_scores` | Türetilmiş actual/pay/payda ve bire-bir skor |
| Entegrasyon | `integration_runs`, `data_quality_issues` | Ingestion koşusu ve veri kalitesi |
| Katkı | `contribution_works`, `contribution_work_foremen`, `contribution_work_plants`, `contribution_gains` | Çok formen/çok tesis iyileştirme çalışması |
| Anomali | `anomalies`, `anomaly_analyses`, `anomaly_tool_calls` | Tespit, analiz denemesi ve araç izi |
| Rapor | `report_exports`, `foreman_monthly_reports` | Genel export ve aylık formen snapshot/teslim metadata'sı |
| Yetkilendirme | `user_role_assignments`, `user_scope_assignments` | Subject → rol (PK=subject) ve subject → ALL/FACTORY/PLANT scope satırları; PII içermez |
| Denetim | `audit_logs` | OIDC subject tabanlı mutasyon izi |

Tüm ana varlıklar UUID PK kullanır. Öne çıkan DB bütünlük kuralları:

- Fabrika, tesis, vardiya, şef ve formen kod/sicilleri benzersizdir.
- `plants.sequence_number` benzersizdir; `(plants.id, plants.chief_id)` bileşik
  anahtarı assignment/üretim/performance katmanındaki tesis–şef FK'larını destekler.
- `uq_foreman_assignments_plant_shift_active`, aktif `plant_id + shift_id`
  slotunda tek assignment uygular.
- `excl_foreman_assignments_plant_shift_daterange`, aynı slotta çakışan kapalı
  tarih aralıklarını PostgreSQL GiST exclusion constraint ile reddeder.
- Assignment tarih kontrolü `end_date >= start_date`; inactive kayıt için
  `end_date` zorunludur. Trigger bir formenin farklı şeflere bağlanmasını reddeder.
- `production_records` kaynak anahtarı ve doğal anahtarı benzersizdir;
  `working_time_minutes` nullable'dır ve doluysa `0..720` aralığındadır.
- `performance_records` kaynak/doğal anahtarları benzersizdir ve plant/chief
  bileşik FK'sı taşır. `performance_scores.performance_record_id` bire-bir
  benzersizdir.
- KPI target ve calculation rule tarih aralıkları geçerli olmak zorundadır;
  aynı KPI/kapsam için çakışan aralıklar exclusion constraint ile engellenir.
- Aylık rapor `(foreman_id, year, month)` ile benzersizdir.
- Katkı/anomali check constraint'leri skor, tarih, yüzde, güven ve gün sayılarını
  geçerli aralıkta tutar.

Development/test dataset sentetiktir. Eski sentetik dump production migration
gereksinimi değildir. Production veri yaklaşımı:

```text
boş PostgreSQL → alembic upgrade head → gerçek master/veri entegrasyonu
```

## Veri Akışı

```text
production_records
  → KPI bileşeni türetme
  → kod/FK + assignment + target/rule çözümleme
  → performance_records + performance_scores
  → dönemsel pay/payda agregasyonu
  → KPI skorları
  → ağırlıklı geometrik toplam
  → tesis/formen/şef/vardiya/dashboard/rapor
```

`SyntheticDataProvider`, ham `production_records` kayıtlarını
`RawPerformanceRecord` akışına dönüştürür. `ingestion.py`; entity kodlarını
FK'lara, tarihi geçerli assignment'a, hedefi ve calculation rule'u ilgili
geçerlilik aralığına çözer. Duplicate doğal anahtarlar tekrar insert edilmez;
kalite sorunları `data_quality_issues` içinde izlenir.

Analitik dönem sonuçları günlük skorların basit ortalaması değildir. Önce KPI
pay ve paydaları dönem/kapsam için toplanır, actual yeniden hesaplanır ve aktif
kural uygulanır. Formen birden çok tesisten sorumluysa aynı KPI'nın tesis
skorları tesis başına eşit ağırlıkla ortalanır.

### Manuel yeniden senkronizasyon

Sentetik seed yalnızca boş, migration uygulanmış veritabanında çalışır:

```bash
docker compose exec backend python -m app.cli seed --seed 42
```

Referans veri varsa komut mutasyon yapmadan hata ile çıkar. Sentetik dünyayı
yeniden üretmek için DB sıfırlanır, `alembic upgrade head` uygulanır ve seed
yeniden çalıştırılır. Seed guard'ını bypass eden bir seçenek yoktur.

Mevcut veriye yönelik bağımsız bakım/backfill komutları `python -m app.cli
--help` üzerinden görülmelidir; seed yerine kısmi tablo temizliği önerilmez.

## Üretim Verisi Katmanı

`production_records` vardiya seviyesinde şu temel kaynak alanlarını tutar:
planlanan/gerçekleşen miktar, ürün/hat, ortalama gramaj, GSF ve Iskarta
miktarı, teknik/imalat/diğer duruş dakikaları ve `working_time_minutes`.

`production_kpi_derivation.py` aşağıdaki actual/pay/payda değerlerini üretir:

| KPI | Actual bileşeni |
|---|---|
| Ağır Gitme | Ortalama gramajın kabul aralığı dışındaki işaretli sapması / standart gramaj |
| GSF | Geri kazanılamayan nihai kayıp miktarı / gerçekleşen brüt üretim |
| Iskarta | Hamura geri katılabilen, paketlenemeyen ürün miktarı / gerçekleşen brüt üretim |
| İnkita | `(teknik + imalat duruş dakikası) / 720`; diğer duruş hariç |
| Plana Uyum | Gerçekleşen üretim / güncel planlanan üretim |
| OEE | Vardiya çalışma dakikası / `720` |

V1 `07:00–19:00`, V2 `19:00–07:00` çalışır; V2 geceyi aşar. Tarih ve haftalık
rotasyon hesapları `Europe/Istanbul` iş günü bağlamında yapılır, saklanan
timestamp'ler UTC'dir.

OEE aggregation:

- Tek formen/vardiya kaydı: `working_time_minutes / 720 × 100`.
- Tam tesis günü: V1+V2 çalışma dakikaları / `1440 × 100`.
- Daha uzun dönem: kapsam içindeki çalışma dakika toplamı / ilgili vardiya
  paydalarının toplamı × 100.

## KPI Hesaplama Motoru

Altı aktif KPI'nın seed ve head migration ile doğrulanan ağırlıkları:

| Kod | Ad | Ağırlık | Kural | İş anlamı |
|---|---|---:|---|---|
| `INKITA` | İnkita Oranı | 22 | `HYBRID_BASE_PIECEWISE_LOG` | Teknik+imalat duruşu; düşük değer iyidir, diğer duruş dahil değildir |
| `OEE` | OEE | 21 | `TARGET_RATIO_LINEAR_BONUS` | Çalışma süresi oranı; skor `actual/target × 100 × 1.05`, `0..105` ile sınırlandırılır |
| `GSF` | GSF Oranı | 20 | `HYBRID_BASE_PIECEWISE_LOG` | Tekrar üretimde kullanılamayan nihai kayıp; düşük değer iyidir |
| `AGIR_GITME` | Ağır Gitme Oranı | 13 | `SIGNED_ABSOLUTE_PIECEWISE` | Kabul aralığı dışındaki işaretli gramaj sapmasının mutlak büyüklüğü |
| `ISKARTA` | Iskarta Oranı | 12 | `TARGET_RATIO_PIECEWISE` | Paketlenemeyen fakat hamura geri katılabilen ürün; düşük değer iyidir |
| `PLANA_UYUM` | Plana Uyum Oranı | 12 | `ASYMMETRIC_PLAN_ACHIEVEMENT` | Plan üstü olumlu, plan altı daha güçlü olumsuz skorlanır |

```text
Toplam ağırlık = 100
```

Toplam performans skoru aktif ve yeterli kapsamlı KPI skorlarının ağırlıklı
geometrik ortalamasıdır:

```text
100 × Π (score_i / 100) ^ (weight_i / toplam_ağırlık)
```

Kapsanan ağırlık aktif toplamın `%50` altındaysa toplam skor `0` döner.
`isReliable`, tüm aktif KPI ağırlığının kapsanıp kapsanmadığını ayrıca belirtir.

### Hedef çözümleme

Hedef önceliği:

```text
FOREMAN → CHIEF → PLANT → COMPANY
```

Resolver, performance tarihiyle target'ın `valid_from`/`valid_to` aralığını
eşleştirir. Seed; tüm KPI'lar için company fallback hedefi, OEE dışındaki
KPI'lar için plant varyasyon hedefleri üretir. OEE company hedefi `%100`dür;
plant/shift/dönem gerçek değeri pay/payda agregasyonundan gelir.
