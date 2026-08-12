# Veri Şeması ve İş Kuralları

## Veritabanı Şeması

Ana tablo grupları (SQLAlchemy 2.0 `Mapped`/`mapped_column`, `app/models/`):

- **Organizasyon:** `factories`, `plants`, `shifts`
- **Personel:** `chiefs`, `foremen`, `foreman_assignments` (SCD2)
- **Üretim (ham veri katmanı):** `products`, `production_lines`,
  `company_calendar`, `foreman_work_calendar`, `production_records` —
  bkz. [Üretim Verisi Katmanı](#üretim-verisi-katmanı)
- **KPI:** `kpis`, `kpi_calculation_rules` (versiyonlu), `kpi_targets`
  (kapsam bazlı), `performance_level_rules`
- **Performans (salt okunur, üretim verisinden türetilir):**
  `performance_records`, `performance_scores`
- **Entegrasyon:** `integration_runs`, `data_quality_issues`
- **Aksiyon/rapor:** `action_plans`, `report_exports`
- **Katkı ve iyileştirme çalışmaları:** `contribution_works`,
  `contribution_work_foremen`, `contribution_gains`
- **Tespitler:** `anomalies`, `anomaly_analyses`, `anomaly_tool_calls` (Aşama 2
  tool calling geçmişi)
- **Kimlik/denetim:** `users`, `audit_logs`

Alembic migration geçmişi (`backend/alembic/versions/`, `down_revision`
zincirine göre sıralı):

1. `afa71ec04497` — ilk şema
2. `55082513f1be` — audit log `ip_address` alanını string'e çevirir
3. `ef3f90d743f8` — aksiyon planları ve rapor export tabloları
4. `6ad63dbc115b` — **Karaman fabrika/şef hiyerarşisi restrukturasyonu.**
   Bilinçli olarak yıkıcıdır: organizasyon ve performans verisini
   `TRUNCATE` eder, `downgrade()` çağrısı `NotImplementedError` fırlatır.
   Postgres enum'ları değer silemediği için bu migration'da
   rename → yeni enum oluştur → `ALTER COLUMN ... USING` → eski enum'u
   sil sırası izlenmiştir.
5. `9f3a2c7b1e44` — tavansız (uncapped) KPI'lar için skor kolonlarının
   hassasiyetini genişletir
6. `c7a1f9d0b2e3` — üretim verisi katmanını ekler (`products`,
   `production_lines`, `company_calendar`, `foreman_work_calendar`,
   `production_records`) ve `performance_records.production_record_id`'yi
   tanıtır
7. `b6d4f8a2c1e7` — KPI'a özel puanlama formülleri (`custom_formula`
   dispatch tablosu) — bkz. [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)
8. `d3e5a7c9f102` — katkı ve iyileştirme çalışmaları tabloları
9. `e1b2c4d6f8a0` — tespitler (anomali) tabloları
10. `f2a4b8e6c9d1` — katkı çalışmalarına formen rolü (`LEAD`/`CONTRIBUTOR`)
    ekler
11. `a4c8e0b2d6f1` — tool calling destekli analiz ajanı: `anomaly_tool_calls`
    tablosu, `anomaly_analyses.mode`/`investigation_plan`/`error_code`
    kolonları, genişletilmiş analiz durumları — bkz.
    [Aşama 2 — Tool Calling Destekli Analiz Ajanı](#aşama-2--tool-calling-destekli-analiz-ajanı)
12. `b7c9e1a3d5f2` — `foreman_assignments(plant_id, shift_id) WHERE is_active`
    üzerinde kısmi benzersiz indeks: bir tesisin bir vardiyasından aynı anda
    yalnızca bir formen sorumlu olabilir
13. `c3e5f7a9b1d4` — `foreman_work_calendar`/`production_records` doğal
    anahtarlarına `plant_id` ekler (formen 2-4 eşzamanlı tesise bağlı
    olabildiğinden gerekli)
14. `a1b3c5d7e9f2` — **şef artık tek tesise değil bölgeye (zone) sorumlu.**
    `chiefs.plant_id` kaldırılır, `plants.chief_id` eklenir (yön tersine
    döner); `(plant_id, chief_id) → plants(id, chief_id)` kompozit FK'si
    `foreman_assignments`/`foreman_work_calendar`/`production_records`'a
    eklenir. Karaman migration'ıyla aynı gerekçeyle yıkıcıdır (organizasyon
    kimlikleri kökten değiştiği için `TRUNCATE` eder, `downgrade()`
    `NotImplementedError` fırlatır) (HEAD)

`alembic upgrade head`, backend konteyneri her başladığında otomatik
çalışır (`backend/Dockerfile` CMD'si).

> `README.md`'nin önceki sürümü Türkçe bölge/il, `Department`,
> `ProductionLine` ve `--plants` bayrağına dayanan eski bir modeli
> tanımlıyordu. Bu kavramlar Karaman restrukturasyonuyla tamamen
> kaldırıldı; bu belge yalnızca mevcut kodu yansıtır.

## Veri Akışı

Performans verisi **API yüzeyinin tamamına salt okunurdur**. Ingestion
pipeline'ı dışında hiçbir yer `performance_records` / `performance_scores`
tablolarını oluşturamaz, güncelleyemez veya silemez.

1. `PerformanceDataProvider.fetch()` (`app/services/providers/base.py`),
   dahili UUID'ler yerine **kodlarla** (`plant_code`, `chief_employee_number`,
   `shift_code`, `foreman_employee_number`, `kpi_code`) `RawPerformanceRecord`
   üretir. Bugün tek implementasyon `SyntheticDataProvider` — bu sınıf artık
   **rastgele KPI değeri üretmez**: `app/services/production_kpi_derivation.py`
   üzerinden yalnızca önceden seed edilmiş `production_records` tablosunu okur
   ve ham üretim/kayıp verisinden KPI değerlerini türetir (bkz.
   [Üretim Verisi Katmanı](#üretim-verisi-katmanı)). `SAPDataProvider`
   iskeleti (`app/services/providers/sap_provider.py`) `SAP_BASE_URL` ayarlı
   değilse `SAPNotConfiguredError`, ayarlıysa `NotImplementedError` fırlatır.
2. `run_ingestion()` (`app/services/ingestion.py`) kodları FK'lere çözer
   (`_Lookups`), hedef değeri `target_resolver` ile bulur, `kpi_engine` ile
   skoru hesaplar ve `BATCH_SIZE = 1000` satırlık gruplar halinde toplu insert
   eder — psycopg'nin bir statement başına 65535 bound parametre limiti ve
   ~20 kolonluk satır boyutu bu sabiti belirler.
3. Idempotency iki benzersiz kısıtla sağlanır: `uq_perf_record_source`
   (source_system, source_record_id) ve `uq_perf_record_natural_key`
   (foreman, kpi, chief, shift, date). Çakışan satırlar
   `ON CONFLICT DO NOTHING ... RETURNING` ile sessizce atlanır ve
   `data_quality_issues` tablosuna `DUPLICATE` olarak kaydedilir.

Veri kalitesi durumları (`DataQualityStatus`): `complete`, `missing`,
`invalid`, `suspicious`, `duplicate`, `needs_source_correction`,
`pending_resync`, `reprocessed`.

### Manuel yeniden senkronizasyon

`POST /api/v1/integration/resync` (Entegrasyon Durumu ekranından tetiklenir),
mevcut sağlayıcıyı (bu ortamda sentetik) belirtilen tarih aralığı için
yeniden çalıştırır — kullanıcının performans verisi girmesi anlamına GELMEZ.
Aralık en fazla **31 gün** (`MAX_RESYNC_DAYS`) ile sınırlıdır. Zaten yüklenmiş
bir dönemi yeniden senkronize etmek, tüm satırların doğal anahtar
çakışmasıyla atlanması nedeniyle idempotent biçimde no-op'tur.

## Üretim Verisi Katmanı

`performance_records`'ın **altında**, SAP'in üretim emri/konfirmasyonu ile
göndereceği ham veriyi taklit eden salt okunur bir "ham veri" katmanı bulunur
(`app/models/production.py`):

- `products` — ürün master verisi. `standard_gram`/`lower_gram_limit`/
  `upper_gram_limit` bilinçli olarak nullable — tanımsızsa o ürün için
  Ağır Gitme KPI'sı hiç hesaplanmaz (değer uydurulmaz).
- `production_lines` — tesis içi üretim hattı / iş merkezi.
- `company_calendar` — şirket geneli tatil takvimi.
- `foreman_work_calendar` — formenin hangi tarihte fiilen hangi tesis/şef/
  vardiya/hatta çalıştığı; `ForemanAssignment`'ın (yapısal, nadiren değişen
  atama) gün bazlı somutlaşmış hali. Bir üretim kaydı yalnızca burada
  `is_working=true` bir satır varsa formene bağlanabilir.
- `production_records` — ham üretim/kayıp kaydı: planlanan/gerçekleşen
  miktar, ölçülen ortalama gramaj, GSF/Iskarta miktarı, Teknik/İmalat/Diğer
  duruş dakikaları, plan revizyon no'su. `performance_records`'la aynı
  idempotency deseni uygulanır (`uq_production_record_source`,
  `uq_production_record_natural_key`). **Hiçbir KPI yüzdesi burada
  tutulmaz** — yalnızca ham ölçüm.

`app/services/production_kpi_derivation.py::derive_raw_performance_records()`
bu tabloları okuyup her üretim kaydından sıfır veya daha fazla
`(kpi_code, actual, numerator, denominator)` bileşeni türetir:

| KPI | Türetildiği ham veri |
|---|---|
| `AGIR_GITME` | `measured_avg_gram`'ın ürünün `lower_gram_limit`/`upper_gram_limit` aralığı dışına taşan işaretli sapması |
| `GSF` | `gsf_qty / actual_qty` |
| `ISKARTA` | `iskarta_qty / actual_qty` |
| `PLANA_UYUM` | `actual_qty / planned_qty` |
| `INKITA` | `(technical_downtime_minutes + manufacturing_downtime_minutes) / planlanan vardiya süresi` — `other_downtime_minutes` puanlamaya hiç dahil edilmez |

`target_value` bu katmandan bilinçli olarak `None` gelir; `ingestion.py`
her zaman olduğu gibi hedefi `target_resolver.resolve_target()` ile
`kpi_targets`'tan çözer. Bu ayrım **kaynak-agnostiktir**: `production_records`
tablosunu sentetik üretici (`app/services/synthetic/production_generator.py`)
yerine gerçek bir SAP sağlayıcısı doldursa bile `ingestion.py` /
`kpi_engine.py` / `analytics.py` hiçbir değişiklik gerektirmez — yalnızca
`production_records`'ı dolduran katman değişir.

`performance_records.production_record_id` (nullable), her KPI sonucunu
kaynak üretim kaydına geri izlenebilir kılar.

## KPI Hesaplama Motoru

`app/services/kpi_engine.py` iki katmanlı bir modeldir:

- **Jenerik motor** (`calculate_score` / `calculate_raw_score`), `KPI.calculation_type`
  alanına göre 4 klasik hesaplama türü uygular ve gelecekteki veri odaklı
  KPI'lar için kullanılabilir kalır: `higher_is_better`, `lower_is_better`,
  `range_target`, `direct_score`, `proportional_penalty`. Bu türlerin
  dışındaki (tanınmayan) bir `calculation_type` için hâlâ hata fırlatır —
  keyfi kod veya string formül çalıştırma yoktur.
- **Bugün seed edilen 5 KPI'nın tamamı** `calculation_type=CUSTOM_FORMULA`'dır
  ve sabit bir `formula_type` dispatch tablosuna (`_CUSTOM_FORMULA_DISPATCH`)
  yönlendirilerek KPI'a özel, elle yazılmış formüllerle puanlanır — yalnızca
  burada tanımlı 4 formül türünden birine yönlenebilir, keyfi kod
  çalıştırılamaz.

Varsayılan 5 KPI (`DEFAULT_KPI_SEED`, ağırlıkları toplamda 100):

| Kod | Ad | Ağırlık | `formula_type` | Mantık |
|---|---|---|---|---|
| `AGIR_GITME` | Ağır Gitme Oranı | 20 | `SIGNED_ABSOLUTE_PIECEWISE` | Kabul aralığı dışına taşan işaretli sapmanın mutlak büyüklüğü; hedefi tutturursa 100, sapma arttıkça `good_coefficient`/`bad_coefficient` (log2) ile ceza |
| `GSF` | GSF Oranı | 25 | `HYBRID_BASE_PIECEWISE_LOG` | Geri kazanılamayan nihai kayıp oranı; Iskarta'dan daha sert (log tabanlı) cezalandırılır |
| `ISKARTA` | Iskarta Oranı | 15 | `TARGET_RATIO_PIECEWISE` | Geri dönüştürülebilir kayıp oranı; GSF'ye göre daha yumuşak cezalandırılır |
| `INKITA` | İnkita Oranı | 20 | `HYBRID_BASE_PIECEWISE_LOG` | Yalnızca Teknik + İmalat duruş süresi / planlanan süre — Diğer duruşlar hariç |
| `PLANA_UYUM` | Plana Uyum Oranı | 20 | `PIECEWISE_LINEAR_LOGARITHMIC` | `\|gerçekleşen − planlanan\| / planlanan`; plan altı ve plan üstü sapma eşit ağırlıkta cezalandırılır |

Ortak mantık: hedef tam tutturulduğunda **100**, daha iyi performansta
doğrusal olarak **100'ün üzerine** çıkar, daha kötüde logaritmik olarak
**100'ün altına** düşer — `min_score=0` dışında **manuel bir üst sınır
(tavan) uygulanmaz** (`kpis.max_score` sütunundaki `999999.99`, yalnızca
NOT NULL kısıtı içindir; CUSTOM_FORMULA bu değeri hiç okumaz). Bu model
`9f3a2c7b1e44` (skor kolonlarının hassasiyetini genişletme) ve `b6d4f8a2c1e7`
(KPI'a özel formüller) migration'larıyla geldi; eski 5 KPI'lık jenerik model
(`URETIM_GERCEKLESME`, `FIRE_ORANI`, `PLANSIZ_DURUS`, `KALITE_UYGUNLUK`,
`IS_GUVENLIGI`) tamamen kaldırıldı. Var olan performans verisini yeni
formüllerle yeniden hesaplamak için:
`docker compose exec backend python -m app.cli apply-scoring-model-v2`.

Toplam (aggregate) skor **ağırlıklı geometrik ortalamayla** hesaplanır
(`app/services/analytics.py::_grouped_scores` →
`kpi_engine.py::weighted_geometric_score`):

```
100 × Π (score_i / 100) ^ (weight_i / Σ weight)
```

Geometrik ortalama, tek bir KPI'daki aşırı yüksek puanın diğer kötü
sonuçları gizlemesini engeller (aritmetik ortalamanın aksine). Kapsanan
ağırlık, aktif toplam ağırlığın `MIN_COVERED_WEIGHT_RATIO = 0.5` katından
azsa genel puan **üretilmez, doğrudan 0 döner** — eksik KPI'larda otomatik
yeniden normalize eden eski davranış (`compute_weighted_total`, hâlâ
`kpi_engine.py` içinde tanımlı ama artık hiçbir canlı yoldan çağrılmıyor)
bu formülün yerini aldı. `is_reliable`, kapsanan ağırlığın aktif toplam
ağırlıktan `WEIGHT_TOLERANCE` kadar bile eksik olduğu satırları işaretler.

Skor tabanlı KPI'lar önce **dönem boyunca pay/payda toplanır**, tek bir
orandan tek bir puan üretilir — günlük puanların ortalaması alınmaz.

Performans seviyeleri (`performance_level_rules`, seed'de sabit): Kritik
(0–69.99), Geliştirilmeli (70–79.99), İyi (80–89.99), Çok İyi (90–99.99),
Mükemmel (100–120).

### Hedef çözümleme

`app/services/target_resolver.py` — saf fonksiyon, öncelik sırası
**FOREMAN > CHIEF > PLANT > COMPANY**. Seeder bugün yalnızca COMPANY
kapsamlı hedefler üretir, dolayısıyla tüm çözümlemeler pratikte bu katmana
düşer; daha dar katmanlar canlı bir yetenektir, canlı veri değil.