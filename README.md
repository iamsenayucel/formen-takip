# Formen Performans Takip Sistemi

Karaman'daki üretim tesislerinde formen (vardiya amiri) performansını KPI bazlı
izleyen, **üst yönetime yönelik salt-okunur karar destek** uygulaması. Foremen
ve tesis şefleri sistemin kullanıcısı değildir; veri girişi yalnızca ingestion
pipeline'ı (bugün sentetik veri üreticisi, ileride SAP) üzerinden gerçekleşir.

## İçindekiler

- [Mimari](#mimari)
- [Organizasyon Hiyerarşisi](#organizasyon-hiyerarşisi)
- [Veri Akışı: Sağlayıcı → Ingestion → Skor](#veri-akışı-sağlayıcı--ingestion--skor)
- [Üretim Verisi Katmanı](#üretim-verisi-katmanı)
- [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)
- [Authentication Architecture](#authentication-architecture)
  - [Yerel Geliştirme: Local Keycloak](#yerel-geliştirme-local-keycloak)
  - [Development Demo Mode](#development-demo-mode)
- [Backend API](#backend-api)
- [Tespitler Modülü (Anomali Tespiti + Yapay Zekâ Analizi)](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi)
  - [Aşama 2 — Tool Calling Destekli Analiz Ajanı](#aşama-2--tool-calling-destekli-analiz-ajanı)
- [Katkılar](#katkılar)
- [Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi)
- [Job Claiming & Concurrency](#job-claiming--concurrency)
- [Frontend](#frontend)
- [Veritabanı Şeması](#veritabanı-şeması)
- [Kurulum (Docker)](#kurulum-docker)
- [Production Deployment](#production-deployment)
  - [Prerequisites](#prerequisites)
  - [Model 1 — Tek Sunucu](#model-1--tek-sunucu)
  - [Model 2 — Frontend ve Backend Ayrı Sunucularda](#model-2--frontend-ve-backend-ayrı-sunucularda)
  - [Model 3 — External / Yönetilen PostgreSQL](#model-3--external--yönetilen-postgresql)
  - [Network / Firewall](#network--firewall)
  - [HTTPS](#https)
  - [Database Persistence Modelleri](#database-persistence-modelleri)
  - [Backup / Restore Runbook](#backup--restore-runbook)
  - [Scheduler](#scheduler)
  - [DNS](#dns)
  - [Health Checks](#health-checks)
  - [Troubleshooting](#troubleshooting)
- [Yerel Geliştirme (Docker'sız)](#yerel-geliştirme-dockersız)
- [Testler](#testler)
- [Depoyu Klonladıktan Sonra](#depoyu-klonladıktan-sonra)
- [Ortam Değişkenleri](#ortam-değişkenleri)
- [Bilinen Sınırlamalar / Kapsam Dışı](#bilinen-sınırlamalar--kapsam-dışı)

## Mimari

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI (0.115) · SQLAlchemy 2.0 (`Mapped`/`mapped_column`) · Alembic · Pydantic v2 · Python 3.11 |
| Veritabanı | PostgreSQL 16 |
| Kimlik doğrulama | Red Hat SSO / Keycloak (OIDC, Authorization Code + PKCE) — bkz. [Authentication Architecture](#authentication-architecture) |
| Raporlama | `openpyxl` (XLSX), `reportlab` (PDF), `csv` (stdlib) |
| Formen aylık rapor storage | `boto3` (S3), CloudFront (Signed URL, OAC), `smtplib` (stdlib SMTP) — bkz. [Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi) |
| Frontend | React 19 · TypeScript · Vite 8 · TanStack Query v5 · React Router v7 · Tailwind CSS v4 · Recharts 3 |
| Dağıtım | Docker Compose: `postgres` + `backend` (Uvicorn) + `frontend` (statik build, Nginx) |

Servisler arasında bind mount **yoktur** — imajlar build anında kaynağı içine
gömer. Bir dosyayı değiştirmek, ilgili servisi yeniden build etmeden
konteynerde hiçbir etki yaratmaz.

```
frontend (Nginx :80, host :8080)
   │  /api/* → proxy
   ▼
backend (Uvicorn :8000)
   │  SQLAlchemy
   ▼
postgres:16 (host :5433 → container :5432)
```

## Organizasyon Hiyerarşisi

**Karaman (tek lokasyon) → Fabrika (K1 = 1–27. tesisler, K2 = 28–50. tesisler) → Tesis → Şef → Formen.**

Bu yapı `backend/app/services/synthetic/reference_data.py` içindeki
`FACTORY_SEED` sabitiyle kodlanmış sabit bir iş kuralıdır, yapılandırılabilir
bir parametre değildir. Tesisler `"{n}. Tesis"` biçiminde adlandırılır ve
1–50 arasında benzersiz bir `sequence_number` taşır — tesisler her zaman
`sequence_number`'a göre sıralanmalı, `name`'e göre değil.

- Her tesisin tam olarak bir şefi vardır (`Plant.chief_id`), ama bir şef
  tek bir tesise değil, aynı fabrika içindeki tesislerden oluşan sabit bir
  bölgeden ("zone") sorumludur (`app/services/synthetic/reference_data.py::seed_reference_data`,
  her fabrikanın tesisleri `min_plants_per_foreman`–`max_plants_per_foreman`
  büyüklüğünde bölgelere ayrılır). Bu bölgedeki her formen (her vardiyada bir
  tane, yani bir şefin 2 formeni olur) bölgenin
  tüm tesislerinden sorumludur, bu yüzden bir formen hiçbir zaman birden
  fazla şefe bağlı olamaz.
- `Foreman` modeli organizasyon FK'sı taşımaz. Tüm yerleşim `ForemanAssignment`
  tablosunda SCD2 tarzı `start_date`/`end_date` aralıklarıyla tutulur: bir
  formenin şefi ve vardiyası görev süresi boyunca sabittir, yalnızca bölgesi
  ara dönemlerde değişebilir.
- `(plant_id, chief_id) → plants(id, chief_id)` bileşik yabancı anahtarı
  (`foreman_assignments`, `foreman_work_calendar` ve `production_records`
  üzerinde tekrarlanır), tesis/şef uyuşmazlığını veritabanı seviyesinde
  imkânsız kılar.
- Kimlikler benzersiz ve kendini açıklayan biçimde üretilir: ad/soyad çiftleri
  `FIRST_NAMES × LAST_NAMES` (80 × 70 = 5600 kombinasyon) kartezyen çarpımından
  yerine koymadan örneklenir, böylece ~1000 kişilik
  havuzda hiçbir şef veya formen aynı tam adı taşımaz. Şef sicil numaraları
  tek bir tesisi değil bölgeyi kodlar (`SEF-003`); formen sicil
  numaraları vardiyayı kodlar (`SCL-V1-014`) — ikisi de sözlüksel sıralama
  sayısal sıralamayla eşleşsin diye sıfırla doldurulur.

`docker compose exec backend python -m app.cli regenerate-personnel-identities`
komutu, mevcut şef/formen ad-soyad ve sicil numaralarını performans verisine
dokunmadan (satırlar UUID ile referans verir) yeniden üretir — isim
havuzlarını değiştirdikten sonra tam yeniden seed yerine kullanılır.

## Veri Akışı: Sağlayıcı → Ingestion → Skor

Performans verisi API yüzeyinin tamamına salt okunurdur. Ingestion
pipeline'ı dışında hiçbir yer `performance_records` / `performance_scores`
tablolarını oluşturamaz, güncelleyemez veya silemez.

1. `PerformanceDataProvider.fetch()` (`app/services/providers/base.py`),
   dahili UUID'ler yerine **kodlarla** (`plant_code`, `chief_employee_number`,
   `shift_code`, `foreman_employee_number`, `kpi_code`) `RawPerformanceRecord`
   üretir. Bugün tek implementasyon `SyntheticDataProvider` — bu sınıf
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
`pending_resync`, `reprocessed`. Bu durumlar `data_quality_issues`
tablosuna yazılır.

## Üretim Verisi Katmanı

`performance_records`'ın altında, SAP'in üretim emri/konfirmasyonu ile
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
  `uq_production_record_natural_key`). Hiçbir KPI yüzdesi burada
  tutulmaz — yalnızca ham ölçüm.

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
`kpi_targets`'tan çözer. Bu ayrım kaynak-agnostiktir: `production_records`
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
| `PLANA_UYUM` | Plana Uyum Oranı | 20 | `ASYMMETRIC_PLAN_ACHIEVEMENT` | `(gerçekleşen − planlanan) / planlanan`; **yönlü (signed)** sapma — plan üstü üretim ödüllendirilir, plan altı kalma daha güçlü cezalandırılır (aşağıda ayrıntı) |

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

`PLANA_UYUM` diğer dört KPI'dan farklı olarak **iki taraflı asimetrik**
puanlanır (`kpi_engine.py::score_plan_achievement`, seed parametreleri
`reference_data.py::DEFAULT_KPI_SEED`): plan üstü sapma `positive_log_coefficient=5.0`
ile, plan altı sapma `negative_log_coefficient=10.0` ile — yani hedefin
±%5'lik doğrusal bölgesinin (`positive_linear_limit`/`negative_linear_limit`)
dışına çıkıldığında, planın altında kalmak planın üstüne çıkmaktan **iki kat
daha sert** cezalandırılır. Bu, migration `d4f6a8b1c3e5` ("Plana Uyum v3:
asimetrik puanlama") ile önceki simetrik `PIECEWISE_LINEAR_LOGARITHMIC`
davranışının (mutlak sapma, yön farkı gözetmeksizin tek katsayı) yerini aldı
— eski sürüm hâlâ `kpi_engine.py::score_plan_compliance` içinde tanımlı
kalır ama hiçbir aktif KPI kuralı tarafından çağrılmaz.

Toplam skor **ağırlıklı geometrik ortalamayla** hesaplanır
(`app/services/analytics.py::_grouped_scores` →
`kpi_engine.py::weighted_geometric_score`):

```
100 × Π (score_i / 100) ^ (weight_i / Σ weight)
```

Geometrik ortalama, tek bir KPI'daki aşırı yüksek puanın diğer kötü
sonuçları gizlemesini engeller (aritmetik ortalamanın aksine). Kapsanan
ağırlık, aktif toplam ağırlığın `MIN_COVERED_WEIGHT_RATIO = 0.5` katından
azsa genel puan üretilmez, doğrudan 0 döner.

Skor tabanlı KPI'lar önce **dönem boyunca pay/payda toplanır**, tek bir
orandan tek bir puan üretilir — günlük puanların ortalaması alınmaz.

Performans seviyeleri (`performance_level_rules`, seed'de sabit): Kritik
(0–69.99), Geliştirilmeli (70–89.99), Başarılı (90 ve üzeri). Genel performans
puanı 105 ve üzerinde olan formenler, ana seviyeden (Başarılı) bağımsız ayrıca
"Üstün Performans" rozeti alır (`is_outstanding_performance`,
`app/services/kpi_engine.py`).

### Hedef çözümleme

`app/services/target_resolver.py` — saf fonksiyon, öncelik sırası
**FOREMAN > CHIEF > PLANT > COMPANY**. Seeder bugün yalnızca COMPANY
kapsamlı hedefler üretir, dolayısıyla tüm çözümlemeler pratikte bu katmana
düşer; daha dar katmanlar canlı bir yetenektir, canlı veri değil.

## Authentication Architecture

Kimlik doğrulama otoritesi **Red Hat SSO (Keycloak, OIDC)**'dir. Uygulama
kendi kullanıcı adı/şifre login sistemini barındırmaz, kullanıcının kurumsal
şifresini hiçbir koşulda görmez ve kendi JWT'sini üretmez — backend yalnızca
SSO'nun imzaladığı access token'ları doğrulayan bir **OIDC kaynak sunucusudur
(resource server)**.

```
Kullanıcı
   │
   ▼
Frontend (React) ──Authorization Code + PKCE──▶ Red Hat SSO / Keycloak
   │                                                    │
   │◀────────────────── access token ──────────────────┘
   │
   │  Authorization: Bearer <access_token>
   ▼
Backend (FastAPI) — app/api/deps.py::get_current_identity
   │  1) JWKS'ten (issuer'ın /.well-known/openid-configuration'ı üzerinden
   │     keşfedilir) anahtarı bulup imzayı doğrular
   │  2) issuer (iss) ve audience (aud) claim'lerini doğrular
   │  3) expiration (exp) doğrular
   │  başarısızsa → 401, hiçbir koşulda imzasız/eksik doğrulamayla devam etmez
   ▼
Identity(subject=<OIDC_USER_ID_CLAIM claim'i>, claims=<token claim'leri>)
   │
   ▼
Mevcut business logic (KPI/skor/rapor kodları değişmedi)
```

**Frontend akışı** — `src/context/AuthContext.tsx`, `oidc-client-ts` +
`react-oidc-context` üzerine ince bir sarmalayıcıdır:
`/login` sayfası kullanıcıyı Red Hat SSO'ya yönlendirir (Authorization Code +
PKCE, Implicit Flow **kullanılmaz**) → `/auth/callback`, kodu token'a çevirip
kullanıcıyı orijinal olarak istediği route'a geri döndürür → `src/api/client.ts`
her istekte güncel access token'ı `oidc-client-ts`'in kendi `UserManager`'ından
okuyup `Authorization: Bearer` header'ı olarak ekler → çıkışta
`signoutRedirect()` hem yerel oturumu hem de Red Hat SSO oturumunu sonlandırır.

**Kimlik kalıcılığı (KVKK):** Uygulama veritabanı ad/soyad/e-posta gibi SSO
profil bilgilerini **hiçbir yerde saklamaz**. `contribution_works.created_by_subject`,
`report_exports.requested_by_subject` ve `audit_logs.subject` yalnızca token'ın
stabil kimlik claim'ini (`Settings.oidc_user_id_claim`, varsayılan `sub`) düz
metin olarak tutar — `users` tablosu (email/password_hash/full_name) kaldırıldı.
Arayüzde görünen ad/e-posta (ör. sağ üstteki kullanıcı alanı), her oturumda
token claim'lerinden runtime'da okunur, hiçbir zaman DB'ye yazılmaz.

**Fail-closed:** `ENVIRONMENT=production` iken `OIDC_ISSUER_URL` /
`OIDC_AUDIENCE` eksikse backend başlamayı reddeder (bkz.
`app/core/config.py::_require_oidc_config_in_production`); production'a
taşınabilecek bir `AUTH_DISABLED`-tarzı bypass yoktur.

Bu, yalnızca **authentication** (kullanıcı kim?) kapsamındadır —
**authorization** (kullanıcı ne yapabilir?) kapsamına girilmemiştir; mevcut
sistemde ayrı bir rol/yetki modeli yoktu ve bu entegrasyon da böyle bir model
eklemez.

### Red Hat SSO tarafında yapılması gerekenler

Aşağıdaki kurumsal değerler bu repoda **bilinmiyor** ve uydurulmamıştır;
IT/DevOps ekibi tarafından sağlanmalıdır:

| Adım | Açıklama |
|---|---|
| Realm / client oluşturma | `TBD` — kurumun Keycloak realm adı |
| Client tipi | **Public client** (frontend, `client_secret` içermez — SPA + PKCE) |
| Flow | Authorization Code + PKCE (Standard Flow), Direct Access Grants **kapalı** |
| Redirect URI | `OIDC_REDIRECT_URI` ile eşleşmeli (örn. `https://<host>/auth/callback`) |
| Post-logout redirect URI | `OIDC_POST_LOGOUT_REDIRECT_URI` ile eşleşmeli (örn. `https://<host>/login`) |
| Web origins | Frontend'in gerçek origin'i (CORS/SSO cross-origin istekleri için) |
| Audience mapper | Access token'a `OIDC_AUDIENCE` ile eşleşen bir `aud` claim'i eklenmeli |
| Employee ID claim (opsiyonel) | `OIDC_USER_ID_CLAIM=employee_id` kullanılacaksa token'a bu claim'i ekleyen bir mapper gerekir; aksi halde varsayılan `sub` kullanılır |
| Production issuer URL | `TBD` — kurumsal Red Hat SSO'nun gerçek issuer adresi |
| Secret provisioning | Backend `client_secret` kullanmaz (public client + PKCE); yalnızca `OIDC_ISSUER_URL`/`OIDC_AUDIENCE` gizli değer değildir ama ortam bazlı yönetilmelidir |

### Yerel Geliştirme: Local Keycloak

Gerçek kurumsal Red Hat SSO'ya erişim gerekmeden **gerçek bir OIDC akışını**
uçtan uca çalıştırabilmek için `docker-compose.dev.yml`, `-f` ile açıkça
eklendiğinde bir Keycloak servisi tanımlar (bkz. aşağıdaki komut — otomatik
merge **olmaz**, production'a yanlışlıkla dahil edilmesin diye kasıtlı).
Bu tamamen izole, **yalnızca development** amaçlıdır — production kodunda
hiçbir değişiklik/bypass yoktur; backend'in JWKS/issuer/audience/expiry
doğrulaması olduğu gibi çalışır, yalnızca gerçek bir SSO'ya (Red Hat SSO
yerine yerel Keycloak'a) karşı doğrulanır.

**Tek manuel adım — hosts dosyası:** Tarayıcı (host makine) ve backend
container'ı aynı `keycloak` hostname'ini çözebilmeli ve token'daki `iss`
claim'i her iki taraf için de aynı olmalı (Keycloak'ın `KC_HOSTNAME` özelliği
bunu sabitler). Backend, Compose'un dahili DNS'i sayesinde `keycloak`'ı
otomatik çözer; tarayıcının da çözebilmesi için **bir kerelik** şu satırı
hosts dosyanıza eklemeniz gerekir:

```
127.0.0.1 keycloak
```

- Windows: `C:\Windows\System32\drivers\etc\hosts` (Not Defter'i **yönetici
  olarak** çalıştırıp düzenlemeniz gerekir)
- macOS/Linux: `/etc/hosts` (`sudo` ile düzenleyin)

Sonrasında:

```bash
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d
```

çalıştırın. Bu size:

- **Keycloak:** http://localhost:8081 (admin console: http://localhost:8081/admin, `admin` / `admin` — yalnızca yerel dev, gerçek bir secret değil)
- **Realm:** `formen-dev` — `keycloak/formen-dev-realm.json`'dan otomatik import edilir (`start-dev --import-realm`), Admin Console'da elle kurulum gerekmez
- **Client:** `formen-frontend` — public client, Standard Flow (Authorization Code) + PKCE (S256) açık, Implicit Flow ve Direct Access Grants kapalı, `client_secret` yok
- **Audience mapper:** access token'a `aud: formen-backend` claim'ini ekler (backend'in `OIDC_AUDIENCE` doğrulaması bunu bekler)
- **Test kullanıcısı:** `dev-user` / `DevPass123!` — parola **yalnızca** `keycloak/formen-dev-realm.json` içinde tanımlıdır; Formen Takip backend'i veya frontend'i bu parolayı hiçbir zaman görmez/saklamaz

verir. `http://localhost:8080` açtığınızda otomatik olarak Keycloak'a
yönlendirilir, `dev-user` ile giriş yaptıktan sonra `/auth/callback` üzerinden
dashboard'a dönersiniz; tüm `/api/v1/*` istekleri gerçek bir Bearer token
taşır ve backend bunu gerçek JWKS/issuer/audience/expiry doğrulamasından
geçirir. Çıkış yaptığınızda hem uygulama oturumu hem de Keycloak SSO oturumu
sonlanır.

Keycloak'a veri kalıcılığı için bir volume **tanımlanmamıştır** — bu
kasıtlıdır: her `up --build -d` çalıştırmasında `formen-dev-realm.json`'dan
tertemiz bir realm import eder, Admin Console'da elle bir şey saklamanız
gerekmez.

**Production'a geçiş:** `docker-compose.dev.yml` yalnızca yukarıdaki gibi
açıkça `-f` ile eklendiğinde devreye girer — production komutu bu dosyayı hiç
içermez (bkz. "Production Deployment"). Gerçek Red Hat SSO ile çalıştırmak
için kök `.env`'deki `OIDC_ISSUER_URL` / `OIDC_AUDIENCE` / `OIDC_CLIENT_ID` /
`OIDC_REDIRECT_URI` / `OIDC_POST_LOGOUT_REDIRECT_URI` değerlerini kurumun
gerçek Keycloak realm bilgileriyle doldurup
`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
çalıştırmanız yeterli — kod tarafında **hiçbir değişiklik gerekmez**,
`ENVIRONMENT=production` zaten fail-closed olarak bu değerleri zorunlu kılar.

### Development Demo Mode

Sentetik veriyle çalışan arayüzü, Cloudflare Tunnel gibi geçici bir linkle
başka bir bilgisayardan hızlıca gösterebilmek için — Keycloak login akışını
kurmadan/tünellemeden — `AUTH_BYPASS` adında ayrı, açıkça development-only bir
bypass modu vardır. Yukarıdaki local Keycloak akışını **değiştirmez**; ikisi
birbirinden bağımsız iki development seçeneğidir.

**Açmak** (kök `.env`):

```env
ENVIRONMENT=development
AUTH_BYPASS=true
VITE_AUTH_BYPASS=true
```

```bash
docker compose -f docker-compose.yml -f docker-compose.db.yml up --build -d
```

`docker-compose.dev.yml`'i (ve dolayısıyla local Keycloak konteynerini)
bilerek dışarıda bırakıyoruz — demo modu Keycloak'un ayakta olmasına bağımlı
değildir, yalnızca `docker-compose.db.yml` ile bir yerel Postgres gerekir.
(Keycloak'ı da isterseniz `-f docker-compose.dev.yml` ekleyerek dahil
edebilirsiniz; bu durumda Keycloak konteyneri de başlar ama demo akışı onu
hiç kullanmaz.)

`http://localhost:8080` açıldığında login ekranı/yönlendirme **olmadan**
doğrudan dashboard açılır; tüm `/api/v1/*` istekleri Authorization header'ı
olmadan gider ve backend bunları `dev-demo-user` adlı sentetik bir kimlikle
yanıtlar (hiçbir DB kaydı oluşturulmaz, hiçbir JWT/parola üretilmez).

**Kapatmak / gerçek OIDC'ye dönmek:**

```env
AUTH_BYPASS=false
VITE_AUTH_BYPASS=false
```

sonra normal `docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d`
(local Keycloak) veya `OIDC_ISSUER_URL`/`OIDC_AUDIENCE` dolu
`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
(gerçek Red Hat SSO) — her iki mod da hiç değişmeden çalışmaya devam eder.

**AUTH_BYPASS production'da asla açılamaz.** `ENVIRONMENT=production` iken
`AUTH_BYPASS=true` backend'i başlatmadan fail-closed bir config hatasıyla
durdurur (bkz. `app/core/config.py::_forbid_auth_bypass_outside_development`);
`development` dışında herhangi bir `ENVIRONMENT` değeri de aynı şekilde
reddedilir.

## Backend API

Tüm uçlar `/api/v1` altında, doğrulanmış bir OIDC access token (`Authorization:
Bearer`) ile korunur (`/auth/me` dahil — health check hariç). Backend token'ı
asla yalnızca decode ederek güvenmez; signature/issuer/audience/expiration
doğrulaması olmadan hiçbir istek işlenmez (bkz.
[Authentication Architecture](#authentication-architecture)).
OpenAPI dokümantasyonu: `http://localhost:8000/docs`.

API JSON sözleşmesi başarı/hata zarfları, camelCase alanlar, cursor sayfalama,
`X-Request-Id` ve kimlik bazlı rate limit kurallarını tek biçimde uygular. Ayrıntılı
katalog: [`docs/04-api-sozlesme-katalogu.md`](docs/04-api-sozlesme-katalogu.md).

| Router | Öne çıkan uçlar |
|---|---|
| `auth` | `GET /me` — doğrulanmış token'dan runtime kimlik bilgisi (yalnızca UI amaçlı, DB'ye yazılmaz) |
| `meta` | `GET /filters` — filtre barının kademeli (cascading) seçenekleri |
| `dashboard` | `GET /summary`, `/trend`, `/kpi-summary`, `/plant-ranking`, `/shift-comparison`, `/foreman-ranking`, `/performance-distribution` |
| `plants` | `GET /plants`, `/{id}`, `/{id}/summary`, `/{id}/kpis`, `/{id}/shifts`, `/{id}/chiefs`, `/{id}/foremen` |
| `chiefs` | `GET /chiefs`, `/{id}`, `/{id}/foremen`, `/{id}/kpis`, `/{id}/trend` |
| `foremen` | `GET /foremen`, `/{id}`, `/{id}/kpis`, `/{id}/kpis/{kpi_id}/calculation-detail`, `/{id}/trend`, `/{id}/assignment-history`, `/{id}/contribution-summary`, `/{id}/monthly-reports`, `/{id}/monthly-reports/latest`, `/{id}/monthly-reports/{y}/{m}`, `/{id}/monthly-reports/{y}/{m}/pdf`, `/{id}/monthly-reports/{y}/{m}/access` — son ikisi bkz. [Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi) |
| `kpis` | `GET /kpis`, `/{id}`, `/{id}/analysis` |
| `contributions` | `GET /contribution-works`, `/summary`, `/{id}`, `/{id}/pdf`, `POST /`, `PATCH /{id}`, `DELETE /{id}` — bkz. [Katkılar](#katkılar) |
| `anomalies` | `GET /anomalies`, `/summary`, `/{id}`, `POST /{id}/analyze`, `/{id}/reanalyze`, `GET /{id}/analysis`, `PATCH /{id}/status` — bkz. [Tespitler Modülü](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi) |
| `analyses` | `GET /analyses/{id}`, `GET /analyses/{id}/tool-calls` — Aşama 2 tool calling geçmişi |
| `shift_analysis` | `GET /shift-analysis/cards`, `/detail` — aynı tesis/KPI'da bir ayın vardiya rotasyonuna göre iki formen arasındaki belirgin performans farklarını yüzeye çıkarır |
| `reports` | `POST /generate`, `GET /`, `GET /{id}/download` |

Ortak filtreleme: `common_filters` bağımlılığı (`app/schemas/common.py`)
`date_from`, `date_to`, virgülle ayrılmış `plant_ids` / `factory_ids` /
`chief_ids` / `shift_ids` / `kpi_ids` parametrelerini tek bir `Filters`
nesnesine çözer ve `analytics._apply_filters` üzerinden tüm sorgulara
uygulanır. `factory_ids`, `PerformanceRecord`'ın `factory_id` taşımaması
nedeniyle bir `Plant.factory_id` alt sorgusu üzerinden çözülür.

Raporlama modülü mevcut `analytics.py` sorgularını yeniden kullanır;
üretilen dosya içeriği demo ölçeğinde ayrı bir obje deposu gerektirmediği
için `report_exports` tablosunda (`LargeBinary`) saklanır.

Denetlenebilir eylemler (katkı çalışması CRUD, tespit durumu/analiz
güncelleme, rapor oluşturma/indirme) `app/services/audit.py::record_audit()`
üzerinden tek noktadan `audit_logs` tablosuna yazılır — `subject` alanı OIDC
token'ının stabil kimlik claim'idir (ad/e-posta değil). Bu tabloyu görüntüleyen
ayrı bir API/ekran bulunmaz, yalnızca dahili iz kaydı olarak tutulur. Kimlik
doğrulama (login/logout) artık uygulama içinde gerçekleşmediği için bu olaylar
Red Hat SSO'nun kendi oturum/audit kayıtlarında izlenir.

## Tespitler Modülü (Anomali Tespiti + Yapay Zekâ Analizi)

**Amaç:** Üretim verilerindeki olağan dışı durumları ("Ağır Gitme", "GSF",
"Iskarta", "İnkita", "Plana Uyum" KPI'larında) yöneticilere göstermek, önem
derecesi ve durumlarını takip etmek ve her tespit için isteğe bağlı bir yapay
zekâ analizi üretmek. Modül iki kademede geliştirilmiştir:

- **Aşama 1 — Sentetik Veriyle Prototip**: tüm bağlam LLM'e tek pakette
  gönderilir (`single_context` modu, aşağıda anlatılıyor).
- **Aşama 2 — Tool Calling Destekli Analiz Ajanı**: LLM, ihtiyaç duyduğu ek
  veriyi salt-okunur backend araçlarını çağırarak kendisi toplar
  (`tool_calling` modu, [ayrı bölümde](#aşama-2--tool-calling-destekli-analiz-ajanı) anlatılıyor).

İkisinde de gerçek bir ML modeli, SAP/Ocean entegrasyonu, RAG veya vektör veri
tabanı kullanılmaz — tüm operasyonel veri sentetiktir.

### Sentetik tespit verisi

`app/services/synthetic/anomaly_generator.py`, gerçek makine öğrenmesi
tespitiymiş gibi davranan **24 sabit senaryodan** (13 farklı tespit türünü en
az bir kez kapsayan: vardiya bazlı sürekli düşük performans, yükselen trend,
formen bazlı sapma, ürün grubu sapması, duruş yoğunlaşması, art arda plan
altı kalma, tesis geçmişinden sapma, tesisler arası fark, eş zamanlı çoklu
KPI bozulması, tek günlük sıçrama, kronik anormallik, kritik üretim kaybı,
veri kalitesi şüphesi), K1/K2 fabrikaları arasında dengeli biçimde,
gerçek (seed edilmiş) tesis/vardiya/KPI referans verisine bağlı, birbiriyle
tutarlı sayısal veriler (gözlenen/beklenen değer, sapma oranı, vardiya
karşılaştırması, ilişkili KPI sinyalleri, ML güven skoru) üretir. Aynı
`--seed` ile her çalıştırma aynı sonucu verir (tekrar üretilebilirlik);
zaten var olan tespit kodları (`ANM-YYYY-NNNN`) atlanır, bu yüzden komutu
tekrar çalıştırmak güvenlidir:

```bash
docker compose exec backend python -m app.cli seed-anomalies --seed 42
```

(`seed` komutu bu adımı otomatik olarak son adım — `[5/5]` — olarak da çalıştırır.)

Şema (`app/models/anomaly.py`, `Anomaly` ve `AnomalyAnalysis` tabloları),
gelecekte gerçek bir ML tespit servisinin üreteceği çıktıyla aynı alanları
taşır — sentetik üretici ileride bu şemaya yazan gerçek bir servisle
değiştirilebilir, API ve frontend değişmeden kalır.

### Yapay zekâ analizi nasıl çalışır

1. Kullanıcı arayüzden "Yapay Zeka ile Analiz Et" butonuna basar →
   `POST /api/v1/anomalies/{id}/analyze`.
2. `app/services/anomaly_context.py::build_analysis_package()`, tespitin
   tüm sayısal verisini, KPI tanımını, vardiya/tesis/fabrika
   karşılaştırmalarını, ilişkili KPI sinyallerini ve sentetik bağlam
   öğelerini (günlük geçmiş, duruş özeti, bakım sinyalleri, ürün dağılımı,
   vardiya notları, benzer geçmiş olaylar) tek bir JSON paketinde
   toplar, LLM'nin ihtiyaç duyacağı her şey
   bu tek pakette gönderilir. Formen bilgisi isim değil sicil kodu
   (`employee_number`) ile temsil edilir.
3. `app/services/llm_service.py`, `LLM_ENABLED=true` ve `LLM_API_KEY` tanımlıysa
   OpenAI uyumlu bir `chat/completions` uç noktasına (`LLM_BASE_URL`,
   `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`) sistem promptu + JSON paketiyle istek
   atar; sağlayıcı bağımsız tek bir servis katmanıdır (ileride farklı bir
   sağlayıcıya geçmek yalnızca bu dosyanın içini değiştirmeyi gerektirir).
4. LLM cevabı (veya demo fallback çıktısı) `app/schemas/anomaly_analysis.py`
   içindeki `AnalysisResult` Pydantic şemasına karşı doğrulanır. Geçersiz
   JSON, eksik alan veya zaman aşımı durumunda en fazla bir kez otomatik
   yeniden denenir; iki deneme de başarısız olursa analiz `failed` durumuna
   geçer ve kullanıcıya jenerik bir hata mesajı gösterilir (teknik ayrıntılar
   yalnızca backend loglarında tutulur).
5. Sonuç `anomaly_analyses` tablosuna yeni bir satır olarak yazılır —
   önceki analizler silinmez, arayüzde varsayılan olarak en güncel analiz
   gösterilir (`GET /{id}/analysis` ve tespit detayındaki `latest_analysis`).

Bir tespit için aynı anda yalnızca bir analiz denemesi çalışabilir — bu,
Python seviyesinde bir `if` kontrolü değil, DB seviyesinde atomik bir
claim mekanizmasıdır; iki eşzamanlı istek/worker'ın aynı tespit için LLM'i
iki kez çağırmasını ve crash sonrası sonsuza kadar "analiz ediliyor"
görünmesini nasıl engellediği için bkz. "Job Claiming & Concurrency".

### Demo modu (LLM olmadan)

`LLM_ENABLED=false` veya `LLM_API_KEY` boşsa (varsayılan durum),
`app/services/anomaly_demo_fallback.py` gerçek çıktı şemasıyla birebir aynı
şekilde, tespitin gerçek sayısal verilerine dayanan deterministik bir analiz
üretir. Uygulama asla bozulmaz. Arayüzde bu durum küçük bir
**"Demo Yapay Zekâ Analizi"** etiketiyle; gerçek LLM kullanıldığında ise
**"Yapay Zekâ Analizi"** etiketiyle belirtilir.

### Yapılandırılmış çıktı şeması

LLM'den (veya demo üreticiden) beklenen JSON şekli (`AnalysisResult`):
`executive_summary`, `verified_findings[]` (finding/evidence), `possible_causes[]`
(cause/confidence/supporting_evidence/contradicting_evidence/verification_required),
`recommended_investigations[]`, `immediate_actions[]`, `medium_term_actions[]`,
`missing_information[]`, `risk_level`, `analysis_confidence` (0–1),
`requires_human_review` (her zaman `true`), `disclaimer`. Sistem promptu
(`anomaly_context.py::SYSTEM_PROMPT`), formenleri doğrudan suçlamamayı,
doğrulanmış bulgularla varsayımları ayırmayı, her önerinin bir sorumlu birim/
öncelik taşımasını ve tüm aksiyonların yönetici onayı gerektirdiğini açıkça
şart koşar; tespit açıklaması içine sızabilecek "talimatları yok say" türü
metinlerin komut olarak yorumlanmaması için ayrı bir güvenlik notu içerir.

### Güvenlik

`LLM_API_KEY` yalnızca backend ortam değişkeni olarak okunur, frontend'e asla
gönderilmez ve repository'ye yazılmaz (`.env` `.gitignore` ile hariç tutulur).
Tüm LLM çağrıları backend üzerinden yapılır. LLM'nin veritabanına yazma,
SAP/Ocean'a işlem gönderme veya aksiyon uygulama yetkisi yoktur — yalnızca
salt-okunur bir analiz metni üretir, kullanıcı arayüzde bunu yapılandırılmış
kartlar halinde görür (ham HTML render edilmez).

### Aşama 2 — Tool Calling Destekli Analiz Ajanı

`LLM_ANALYSIS_MODE` ayarı veya her analiz isteğinde gönderilebilen `mode` alanı 
(`single_context`, `tool_calling`) ile hangi yöntemin kullanılacağı seçilir. 
Frontend'de tespit detay ekranındaki **Hızlı Analiz / Derinlemesine Analiz** seçici 
bu iki moda karşılık gelir.

**Mimari akış** (`app/services/anomaly_orchestrator.py::AnomalyAnalysisOrchestrator`):

1. LLM'e başlangıçta yalnızca tespitin özeti (başlık, tesis, vardiya, KPI,
   sapma, ML güven skoru, kullanılabilir araçların açıklamaları) verilir —
   Aşama 1'deki gibi tüm bağlam paketi baştan gönderilmez.
2. Model önce kısa bir **iç araştırma planı** üretir (`investigation_plan`,
   kullanıcıya gösterilmez, `anomaly_analyses.investigation_plan` alanında saklanır).
3. Model, ihtiyaç duydukça `app/services/tools/definitions.py`'deki **11
   salt-okunur araçtan** (allowlist) birini çağırır; her çağrı Pydantic ile
   doğrulanır (geçersiz fabrika/tesis/vardiya/KPI/tarih aralığı → kontrollü
   hata), gerçek sentetik sağlayıcı katmanı çalıştırılır ve sonuç modele
   `tool_call_reference` koduyla geri gönderilir. Her çağrı bir
   `anomaly_tool_calls` satırı olarak kaydedilir (adım no, argümanlar, süre,
   dönen kayıt sayısı, hata kodu).
4. Döngü; `LLM_MAX_TOOL_CALLS`, `LLM_MAX_ANALYSIS_STEPS` veya
   `LLM_ANALYSIS_TIMEOUT_SECONDS` sınırlarından biri aşılınca ya da model
   kendiliğinden yeterli veri topladığına karar verince durur.
5. Modelden, topladığı bulgulara dayanan **nihai yapılandırılmış analiz**
   ayrıca istenir; `verified_findings`/`possible_causes` içindeki
   `source_refs`, gerçekten yapılmış `tool_call_reference` kodlarına karşı
   doğrulanır — LLM'nin uydurduğu bir referans varsa sessizce ayıklanır ve
   `analysis_limitations`'a not düşülür (bkz.
   `anomaly_orchestrator.py::_sanitize_source_refs`).

**Sentetik veri tutarlılığı** (`app/services/synthetic/world.py`): Aşama 2'nin
11 aracının hepsi, aynı birkaç temel fonksiyona (özellikle `_value_for_date`)
dayanır — hiçbir araç bağımsız/rastgele veri üretmez. "Zemin gerçeği", Aşama
1'de üretilip `anomalies` tablosuna yazılmış olan tespitlerdir: bir
(tesis, KPI) çifti için bir tespit varsa, o tespitin `observed_value`/
`expected_value`/`comparison` alanları tüm günlük seri, duruş, bakım ve
vardiya karşılaştırması detaylarının çıkış noktasıdır (`get_kpi_history` ile
`compare_shifts`'in aynı vardiya için ürettiği sayı **bit bit aynıdır**).
Tespit olmayan tesis/KPI kombinasyonları için "sağlıklı" (KPI hedefine yakın,
düşük varyanslı) bir seri üretilir. `find_similar_anomalies` gerçek seed
edilmiş `Anomaly` kayıtlarını sorgular.

**Veri sağlayıcı katmanı** (`app/services/data_providers/`): `base.py`'deki 7
soyut arayüz (`AnomalyDataProvider`, `KPIDataProvider`, `DowntimeDataProvider`,
`MaintenanceDataProvider`, `ProductDataProvider`, `ShiftDataProvider`,
`HistoricalCaseDataProvider`) bugün yalnızca `synthetic.py`'deki
`Synthetic*Provider` sınıflarıyla implemente edilir. Araçlar
(`tools/definitions.py`) bu arayüzlere karşı yazılmıştır ve verinin sentetik
mi Ocean mı olduğunu bilmez — `app/services/providers/base.py`'deki
`PerformanceDataProvider` deseniyle aynı mimari. `app/services/data_providers/__init__.py::get_data_providers()`
tek fabrika noktasıdır; gelecekte `OceanKPIDataProvider`/`MLAnomalyDataProvider`
gibi gerçek implementasyonlar eklendiğinde yalnızca bu fonksiyonun içi
değişir — araç adları, LLM şemaları ve frontend etkilenmez.

**Demo tool calling** (`app/services/anomaly_demo_tool_calling.py`):
`LLM_ENABLED=false` veya API anahtarı yokken (`LLM_DEMO_TOOL_CALLING_ENABLED=true`,
varsayılan), `tool_calling` modu tamamen devre dışı kalmaz — sabit bir araç
sırası (`compare_shifts → get_kpi_history → get_downtime_breakdown →
get_maintenance_signals → get_product_mix → find_similar_anomalies`)
**gerçekten çalıştırılır** (gerçek sentetik sağlayıcılara karşı), yalnızca
LLM'nin hangi aracı çağıracağına karar verme adımı atlanır. Nihai analiz metni
Aşama 1'in demo üreticisiyle üretilir ve gerçek tool-call kodlarıyla
ilişkilendirilir; arayüzde **"Demo Yapay Zekâ Analizi"** etiketiyle gösterilir.
Tool calling desteklemeyen bir model 400 hatası döndürürse
(`LLMToolCallingUnsupportedError`), sistem otomatik olarak `single_context`
moduna düşer ve bunu `analysis_limitations`'da belirtir.

**Genişletilmiş çıktı şeması**: Aşama 1'in `AnalysisResult` şeması korunur,
üstüne `tools_used[]` (tool_name/tool_call_id/purpose),
`data_scope` (start_date/end_date/record_count/data_quality_status) ve
`analysis_limitations[]` eklenir; `verified_findings`/`possible_causes`
öğeleri `source_refs[]` taşır. `single_context` modunda bu alanlar boş/`null`
bırakılabilir.

**Genişletilmiş analiz durum modeli** (`AnomalyAnalysisStatus`): Aşama 1'in
`not_analyzed`/`analyzing`/`completed`/`failed` değerlerine ek olarak
`queued`, `planning`, `collecting_data`, `generating_analysis`,
`completed_with_warnings` (sınırlara ulaşıldığında veya `tool_calling`→
`single_context` düşüşünde), `timed_out`, `cancelled` eklenmiştir. Orkestratör
bu durumları analiz sırasında ilerledikçe commit eder — aynı tespidi başka bir
sekmeden görüntüleyen bir kullanıcı kaba taneli ilerlemeyi görebilir.

**Araç çağrı sınırları ve önbellek**: `LLM_MAX_TOOL_CALLS` (varsayılan 10),
`LLM_MAX_ANALYSIS_STEPS` (12), `LLM_TOOL_TIMEOUT_SECONDS` (10),
`LLM_ANALYSIS_TIMEOUT_SECONDS` (60), `LLM_MAX_DATE_RANGE_DAYS` (365) — bir
araç bu tarih aralığını aşan bir istek alırsa `TOOL_VALIDATION_ERROR`
döndürür. Aynı analiz içinde aynı araç aynı parametrelerle tekrar çağrılırsa
bellek-içi önbellekten döner (yeni bir `anomaly_tool_calls` satırı oluşmaz,
tool-call sayacı artmaz). Hata kodları
(`TOOL_VALIDATION_ERROR`, `TOOL_NOT_FOUND`, `TOOL_TIMEOUT`,
`TOOL_DATA_NOT_FOUND`, `LLM_TOOL_LOOP_LIMIT`, `LLM_INVALID_STRUCTURED_OUTPUT`,
`LLM_TIMEOUT`, `LLM_PROVIDER_ERROR`) hem `anomaly_tool_calls.error_code`
hem de `anomaly_analyses.error_code` alanında saklanır; teknik ayrıntılar
kullanıcıya gösterilmez, yalnızca backend loglarında tutulur.

**Frontend**: Tespit detay ekranında "Derinlemesine Analiz" sonuçları için
ek bölümler gösterilir — **Analizde Kullanılan Veriler** (kaç araç
kullanıldığı, incelenen tarih aralığı/kayıt sayısı, veri kalitesi) ve
**Analiz Adımları** (her tool-call için sıra no, araç adı, durum, süre, dönen
kayıt sayısı; `GET /analyses/{id}/tool-calls`'tan gelir). Doğrulanmış
bulgu/neden kartlarında "Kaynak: <araç adı>" etiketiyle hangi araçtan
geldiği görülebilir. Analiz sürerken gerçek iç düşünce zinciri değil, sabit
bir aşama listesi gösterilir.

### Testler

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/unit/test_anomaly_demo_fallback.py tests/unit/test_anomaly_analysis_schema.py tests/unit/test_anomaly_orchestrator_helpers.py -q
.venv/Scripts/python.exe -m pytest tests/integration/test_anomalies.py tests/integration/test_anomaly_analysis_service.py tests/integration/test_anomaly_generator.py tests/integration/test_world.py tests/integration/test_tools.py tests/integration/test_anomaly_orchestrator.py -q
```

Aşama 1 kapsanan senaryolar: sentetik tespitlerin şemaya uygunluğu (≥20 tespit, 13
tür de temsil ediliyor, benzersiz kod, tutarlı sapma hesabı), liste/detay/
filtreleme/sayfalama uçları, başarılı LLM analizi, geçersiz JSON / eksik alan
/ zaman aşımı durumlarında yeniden deneme ve `failed` düşüşü, API anahtarı
olmadan demo fallback, çift tıklama koruması (`409`), analiz geçmişinin
korunması ve tespit durumu güncelleme.

Aşama 2 kapsanan senaryolar: sentetik veri sağlayıcılarının tutarlılığı
(`get_kpi_history`/`compare_shifts` aynı sayıyı üretir, anchor'sız
kombinasyonlar "sağlıklı" seri üretir, determinizm), her aracın başarılı
çağrı/eksik parametre/geçersiz parametre/tarih sınırı doğrulaması, orkestrasyon
(tek/çoklu tool çağrısı, maksimum araç sınırı, önbellekten dönme, bilinmeyen
araç adı, hatalı argüman, zaman aşımı, bir araç başarısız olsa bile analizin
tamamlanması, uydurma kaynak referanslarının ayıklanması, tool calling
desteklenmeyen modelde `single_context`'e düşüş), demo tool calling akışının
gerçek araçları çalıştırması ve `single_context` modunun bozulmadan çalışmaya
devam etmesi. Frontend tarafında
`frontend/scripts/smoke_test_anomalies.mjs` ve
`frontend/scripts/smoke_test_tool_calling.mjs` (Playwright) liste sayfası,
filtreleme, detay sayfası ve analiz akışını uçtan uca doğrular.

## Katkılar

Kullanıcı arayüzünde bu modül artık **Operational Impact+** adıyla gösterilir
(sidebar, sayfa başlıkları, formen detayı, raporlar). Backend'deki
`Contribution*`/`contribution_works` teknik isimleri isim değişikliği
uğruna değiştirilmedi — bkz. `app/services/synthetic/contribution_generator.py`
ve `ContributionWorkType` enum'ı (`app/models/enums.py`).

Formenlerin/şeflerin ürettiği iyileştirme çalışmalarını (SMED, Kaizen, sorun
çözme vb.) kaydeden, mali kazanç doğrulaması ve PDF raporu üreten bağımsız
bir modül (`app/models/contribution.py`, `app/api/v1/contributions.py`).
Performans skorlamasıyla hiçbir bağlantısı yoktur — tamamen ayrı bir takip
tablosudur.

- `contribution_works` — başlık, tür (`ContributionWorkType`: SMED, KAIZEN,
  PROBLEM_SOLVING, ...), problem/çözüm/sonuç açıklaması, `status`
  (`ContributionStatus`: DRAFT/PUBLISHED), standardizasyon bayrakları
  (`is_standardized`, `is_applicable_other_plants`, `is_permanent_solution`,
  `work_instruction_updated`) ve mali kazanç alanları
  (`financial_gain_status`, tek bir `gain_amount`, `currency`, `gain_period`).
- `contribution_work_foremen` — bir çalışmaya katkı veren formenleri
  `ContributionRole` (`LEAD` / `CONTRIBUTOR`) ile ilişkilendiren çoka-çok
  tablo; tek formenli çalışmalar migration `f2a4b8e6c9d1` ile otomatik
  `LEAD` olarak işaretlenmiştir.
- `contribution_work_plants` — bir çalışmayı birden fazla tesise (ve
  dolayısıyla birden fazla fabrikaya) bağlayan çoka-çok tablo; migration
  `f4a6c8e0b2d5` ile eski tekil `plant_id` kolonundan taşınmıştır.
- `contribution_gains` — süre/verim kazancı dışındaki diğer kazanım türlerini
  (`OtherGainType`) önceki/sonraki değer ve değişim yüzdesiyle kaydeder.

`app/services/contribution_calc.py`, süre tasarrufu gibi tekrar eden
kazançları (`previous_duration`/`new_duration`, `repeat_period`,
`repeat_count`) aylık toplam tasarruf dakikasına (`monthly_total_saving_minutes`)
çevirir. `GET /{id}/pdf`, `reportlab` ile tek bir çalışmanın özet raporunu
üretir. Sentetik örnek veri `app/services/synthetic/contribution_generator.py`
ile üretilir — `seed` komutunun katkı çalışması adımı (yalnızca en az bir
kullanıcı varsa çalışır, bkz. [Kurulum](#kurulum-docker)) veya bağımsız
olarak `docker compose exec backend python -m app.cli seed-contributions`.

## Formen Aylık Rapor Storage Mimarisi

Her formen için ayda bir üretilen bireysel performans değerlendirme raporu
(`ForemanMonthlyReport` / `foreman_monthly_reports`), ilgili formene ve
bağlı olduğu şefe e-postayla gönderilir. Bu, `report_exports` (ad-hoc
analitik export'ları, PDF binary'si DB'de) ile **aynı sistem değildir** —
o modüle bu mimari geçişi kapsamında dokunulmamıştır.

```
Report Generator (report_data JSON, mevcut hesaplama mantığı değişmedi)
      ↓
PDF render (reportlab, bellekte)
      ↓
Private S3 upload  ←── ReportStorage abstraction (app/services/storage/)
      ↓
foreman_monthly_reports.object_key + generation_status = READY
      ↓
send-monthly-report-emails (ayrı CLI komutu, PDF üretiminden bağımsız)
      ↓
Kurumsal SMTP → Formen (TO) + Şef (CC)
```

**Storage abstraction** (`app/services/storage/`): `ReportStorage` arayüzü
(`upload`/`download`/`exists`) business logic'i S3 SDK'sından ayırır.
`S3ReportStorage` (production) ve `LocalFilesystemReportStorage` (yalnızca
yerel geliştirme, `REPORT_STORAGE_PROVIDER=local` varsayılanı — AWS
gerektirmez) aynı arayüzü implemente eder; hangisinin kullanılacağı
`get_report_storage()` fabrikasında `Settings.report_storage_provider`'a
göre seçilir. `DeleteObject` IAM izni **verilmez** — uygulama bir S3
objesini asla silmez, rapor yeniden üretilirse aynı deterministik
`object_key`'e (`reports/{yıl}/{ay}/foremen/{formen_id}/{rapor_id}.pdf` —
DB'deki stabil UUID'ye dayanır, dosya adına değil) overwrite yapılır.

**Neden `ENVIRONMENT=production`'da app-wide fail-closed değil:** OIDC
(`app/core/config.py::_require_oidc_config_in_production`) tüm request'leri
etkileyen cross-cutting bir concern olduğu için `Settings()` yüklenirken
(uygulama başlangıcında) fail-closed doğrudur. Rapor storage'ı ise yalnızca
formen aylık rapor akışını etkiler; AWS henüz provizyonlanmadıysa (bkz.
"Production Setup Required" aşağıda) bu, dashboard/KPI/Tespitler gibi
tamamen ilgisiz özellikleri de aşağı çekmemelidir. Bunun yerine fail-closed
kontrolü yalnızca storage'ın gerçekten kullanıldığı çağrı noktasında
(`get_report_storage()`) yapılır: `environment=="production"` iken
`report_storage_provider != "s3"` ise `ReportStorageError` fırlatılır —
yalnızca rapor üretimi/erişimi/e-postası bundan etkilenir.

**Rapor üretim pipeline'ı** (`generate_and_store_report_pdf`,
`app/services/monthly_foreman_report.py`): `pdf_generation_status` durumu
`PENDING → GENERATING → READY | FAILED` arasında geçer. Upload başarısız
olursa DB'ye asla `READY` yazılmaz — rapor verisi (`report_data`, JSON)
kaybolmaz, yalnızca PDF teslimatı `FAILED` olur. Idempotent'tir: `READY` ve
`object_key` set edilmiş bir rapor için ikinci çağrı hiçbir S3 isteği
yapmadan döner (aynı ay için job iki kez tetiklenirse duplicate upload
olmaz — asıl duplicate-rapor koruması zaten `uq_foreman_monthly_reports_foreman_year_month`
unique constraint'idir).

**Web erişimi** (`GET /foremen/{id}/monthly-reports/{y}/{m}/access`):
Yetkilendirme, sistemin geri kalanıyla **aynı** modeldir — geçerli bir OIDC
kimliği yeterlidir, ayrı bir formen/şef rolü **icat edilmemiştir**. Bunun
nedeni mimari: bu uygulama üst yönetime yönelik salt-okunur bir karar
destek sistemidir, formen ve şefler hiçbir zaman sisteme login olmaz (bkz.
bu README'nin girişi) — dolayısıyla "raporun sahibi formen" gibi bir
yetkilendirme kontrolü zaten sistemin kullanıcı modeliyle uyuşmaz; mevcut
her endpoint aynı şekilde "herhangi bir authenticated üst yönetim kullanıcısı"
kuralını izler. CloudFront yapılandırılmışsa (`CLOUDFRONT_DOMAIN` +
`CLOUDFRONT_KEY_PAIR_ID` + `CLOUDFRONT_PRIVATE_KEY`) kısa ömürlü
(`REPORT_SIGNED_URL_TTL_SECONDS`, varsayılan 300sn) bir signed URL döner
(`requires_auth: false`, frontend yeni sekmede doğrudan açar); değilse
(IT/DevOps henüz provizyonlamadıysa) backend üzerinden authenticated bir
proxy path'ine düşer (`requires_auth: true`) — **hiçbir zaman** public/
unauthenticated bir S3 erişimine geri düşmez. Signed URL hiçbir yerde
kalıcı olarak saklanmaz (DB'de yalnızca `object_key` tutulur).

**E-posta** (`app/services/monthly_report_email.py`,
`python -m app.cli send-monthly-report-emails [--year Y --month M] [--retry-failed]`):
PDF üretiminden **bilinçli olarak ayrı** bir adımdır (aynı process/fonksiyon
içine gömülü değildir) — SMTP başarısız olsa da rapor kaybolmaz,
`email_status=FAILED` + `email_retry_count` artar, PDF/`report_data`
etkilenmez. Aynı S3 objesi hem "PDF İndir" butonunda hem e-posta ekinde
kullanılır (e-posta için PDF yeniden render edilmez). `SENT` durumundaki
bir rapor normal job tarafından asla tekrar gönderilmez; yalnızca
`--retry-failed` bayrağı, `email_retry_count < EMAIL_MAX_RETRY_COUNT` olan
`FAILED` raporları tekrar dener. Formen/şef e-postası eksikse job
crash olmaz — hangi adresin eksik olduğu loglanır (`email_last_error`),
rapor `FAILED` (formen e-postası eksikse) veya CC'siz gönderim (yalnızca
şef e-postası eksikse) olarak işaretlenir. Veri yetersiz (`is_reliable=false`)
raporlar `SKIPPED` olarak işaretlenir, hiç gönderilmeye çalışılmaz.
Kurumsal SMTP henüz aktif değilse (`SMTP_ENABLED=false` — varsayılan —
veya `SMTP_HOST`/`SMTP_FROM` eksikse, bkz. `Settings.smtp_available`) job
**hiçbir gönderim denemeden** en başta güvenli şekilde no-op yapar: `PENDING`
raporlar `PENDING` kalır, `email_retry_count` değişmez, hiçbir SMTP bağlantısı
açılmaya çalışılmaz. Bu kontrol hem CLI komutunda (raporları DB'den çekmeden
önce) hem de `send_monthly_report_email` servis fonksiyonunun başında
(herhangi bir başka çağıran için savunma amaçlı) uygulanır — SMTP yokluğu bir
*delivery failure* değildir, dolayısıyla asla `FAILED`/retry üretmez. Bu,
SMTP bağlıyken gerçekleşen gönderim hatalarından (bağlantı/timeout/auth) ayrı
tutulur; o durumda rapor normal şekilde `FAILED` olur ve `email_retry_count`
artar.

**Neden ayrı bir job kuyruğu (Celery/SQS) eklenmedi:** Mevcut sistemde
hiçbir background job/scheduler altyapısı yoktur — aylık rapor üretimi
bugün de dıştan (harici cron/scheduler) tetiklenen bir CLI komutudur
(`generate-monthly-reports`). E-posta gönderimi de aynı deseni izleyen
ayrı bir CLI komutudur (`send-monthly-report-emails`); harici scheduler
ikisini bağımsız zamanlarda tetikleyebilir. Yeni bir mesaj kuyruğu/worker
servisi eklemek bu görevin kapsamının önemli ölçüde dışına çıkardı.

**Terraform** (`infra/terraform/reports/`, henüz **deploy edilmemiştir**):
Private S3 bucket (Public Access Block açık, AES256 şifreleme,
versioning), CloudFront distribution (Origin Access Control ile, yalnızca
signed URL — `TrustedKeyGroups`), ve backend için least-privilege IAM
policy (`PutObject`/`GetObject`/`HeadObject`, `DeleteObject` **yok**).
CloudFront signing key çifti Terraform'a hiç girmez — bkz.
`infra/terraform/reports/README.md`.

### Local Development

Varsayılan `REPORT_STORAGE_PROVIDER=local` ile PDF'ler backend
container'ının `.local_reports/` dizininde (bkz. `.gitignore`) tutulur —
AWS hesabı/kimlik bilgisi gerekmez. Yerel dev stack'i bu haliyle
çalışır; rapor görüntüleme/indirme/CLI komutları AWS olmadan test
edilebilir, yalnızca gerçek CloudFront signed URL akışı devre dışı kalır
(backend proxy fallback'i kullanılır). SMTP da varsayılan olarak kapalıdır
(`SMTP_ENABLED=false`) — e-posta job'ı çalıştırılabilir ama hiçbir gerçek
gönderim denenmez, raporlar `PENDING` durumda kalır (retry sayaçları
etkilenmez).

### Production Setup Required

Aşağıdaki gerçek değerler bu repoda **kasıtlı olarak boş bırakılmıştır** —
IT/DevOps tarafından sağlanana kadar production'da rapor storage/e-posta
akışı devreye alınamaz (kod ve Terraform hazırdır, deploy edilmemiştir):

- AWS hesabı/bölgesi, `terraform apply` ile S3 bucket + CloudFront
  distribution provizyonlaması (`infra/terraform/reports/`)
- Backend'in çalıştığı ECS task role'üne (veya eşdeğerine) `terraform
  apply` çıktısındaki `backend_iam_policy_arn`'in attach edilmesi
- CloudFront signing key çifti (`infra/terraform/reports/README.md`'deki
  adımlarla üretilir) — private key merkezi sır yönetimi servisine
  yüklenir, `CLOUDFRONT_PRIVATE_KEY` olarak oradan inject edilir
- `REPORT_STORAGE_PROVIDER=s3`, `AWS_REGION`, `REPORTS_S3_BUCKET`,
  `CLOUDFRONT_DOMAIN`, `CLOUDFRONT_KEY_PAIR_ID` production ortam
  değişkenlerinin doldurulması
- Kurumsal SMTP sunucu adresi, kimlik bilgisi, gönderen adresi
  (`SMTP_ENABLED=true`, `SMTP_HOST`, `SMTP_USERNAME`/`SMTP_PASSWORD`,
  `SMTP_FROM`) — sır olan alanlar merkezi sır yönetimi servisinden inject
  edilmelidir, `.env`'e yazılmamalıdır

## Job Claiming & Concurrency

İki job türü bir DB satırını "claim" edip ardından dış sisteme (SMTP /
LLM) bir çağrı yapar: aylık rapor e-postası (`foreman_monthly_reports`) ve
tespit analizi (`anomaly_analyses`). İkisi de aynı temel deseni izler:

```
PENDING/FAILED (veya NOT_ANALYZED)
      ↓  atomic claim (conditional UPDATE / constraint-checked INSERT)
SENDING / QUEUED            ← claim burada tutulur, dış çağrı sırasında DB
      ↓  external call (SMTP / LLM) — bu adımda açık DB transaction YOKTUR
      ↓  conditional completion (claim'i hâlâ elinde tutan worker mı?)
SENT/FAILED/SKIPPED  veya  COMPLETED/FAILED
```

### Neden conditional UPDATE / constraint-checked INSERT (ve neden SELECT FOR UPDATE değil)

Her iki job da network I/O (SMTP bağlantısı, LLM isteği — saniyeler
sürebilir) yapıyor. Bir satırı `SELECT ... FOR UPDATE` ile kilitleyip bu
kilidi network çağrısı boyunca açık tutmak, o süre boyunca aynı satıra
bakan her worker'ı bloke eder ve bağlantı havuzunu network gecikmesine
bağımlı hale getirir. Bunun yerine claim, tek başına atomik ve **anlık**
bir DB işlemidir; dış çağrı bu işlemin dışında, hiçbir DB transaction'ı
açık değilken yapılır:

- **E-posta** (`app/services/monthly_report_email.py`): claim, `UPDATE
  foreman_monthly_reports SET status='SENDING', claimed_at=now(),
  claim_token=:token WHERE id=:id AND status IN ('PENDING','FAILED')`
  şeklinde koşullu bir `UPDATE`'tir — 1 satır etkilenirse worker job'ı
  almıştır, 0 satır etkilenirse başka bir worker (veya watchdog) önden
  gitmiştir ve bu worker hiçbir şey yapmaz.
- **Tespit analizi** (`app/services/anomaly_job_claim.py`): claim, yeni
  bir `AnomalyAnalysis` satırının **INSERT**'idir. Gerçek karşılıklı
  dışlama, `anomaly_analyses(anomaly_id)` üzerinde `status IN
  (in-progress)` koşuluyla tanımlı kısmi bir unique index'tir
  (`uq_anomaly_analyses_one_active_per_anomaly`) — bu repodaki
  `uq_foreman_assignments_plant_shift_active` ile aynı desen. İki worker
  aynı tespit için eşzamanlı `INSERT` denerse, ikincisi `IntegrityError`
  alır ve bu `AnalysisInProgressError`'a çevrilir. `Anomaly.analysis_status`
  üzerindeki `if status == X` kontrolü yalnızca ucuz bir *fast path*'tir —
  asıl garanti DB constraint'inden gelir, iki session'ın aynı anda aynı
  Python-level okumayı yapması bu garantiyi bozmaz.

Her iki mekanizma da izolasyon seviyesini yükseltmez (`READ COMMITTED`
yeterlidir) — satır kilidi/constraint kontrolü tek bir statement'a
sınırlıdır.

### Claim metadata ve "stale worker" koruması

- **E-posta**: `claimed_at` + `claim_token` (rastgele UUID).
  Tamamlanma (`SENDING → SENT/FAILED/SKIPPED`) her zaman `WHERE
  status='SENDING' AND claim_token=:token` koşuluyla yazılır. Bir worker
  watchdog tarafından reclaim edildikten sonra "geç" success/failure
  döndürürse, bu koşullu `UPDATE` 0 satır etkiler ve **hiçbir şey
  üzerine yazmaz** — yalnızca loglanır (`report_email_stale_completion_ignored`).
- **Tespit analizi**: `Anomaly.current_analysis_id`, o anki claim'in
  "token"ıdır — hangi `AnomalyAnalysis` satırının `analysis_status`'u
  yazma hakkına sahip olduğunu gösterir. Her ara/final durum yazımı
  (`app/services/anomaly_job_claim.py::set_anomaly_status_if_current`)
  `WHERE current_analysis_id=:this_analysis_id` koşulludur. Geç dönen bir
  worker, artık "current" olmayan bir analiz için yazmaya çalışırsa
  no-op'tur (`anomaly_status_update_stale_ignored`). `AnomalyAnalysis`
  satırının kendisi (`status`, `error_message`, `completed_at`) her zaman
  koşulsuz yazılır — bu attempt'in kendi geçmişidir, staleness'tan
  etkilenmez.

Bu iki regresyon senaryosu (`test_stale_worker_completion_does_not_overwrite_newer_claim`
/ `test_stale_worker_completing_after_reclaim_does_not_overwrite_newer_attempt`)
concurrency test paketinin en kritik parçasıdır — bkz. "Eklenen testler"
aşağıda.

### Stale-job watchdog (`app/services/job_reconciliation.py`)

```
python -m app.cli reconcile-stale-jobs
```

Cron/scheduler ile periyodik çalıştırılması önerilir (örn. her 5-10
dakikada bir — dahili bir scheduler yoktur, mevcut mimariye uygun olarak
harici tetiklenir, tıpkı `generate-monthly-reports`/`send-monthly-report-emails`
gibi). Watchdog'un kendisi de aynı koşullu-UPDATE deseniyle çalışır,
dolayısıyla aktif bir worker ile eşzamanlı çalışması güvenlidir: hangi
UPDATE (worker'ın tamamlama'sı ya da watchdog'un stale-sweep'i) önce
commit ederse o kazanır, kaybeden 0 satır etkiler ve no-op olur.

- **E-posta**: `claimed_at`'ı `EMAIL_STALE_CLAIM_TIMEOUT_SECONDS`
  (varsayılan 900sn) aşan `SENDING` kayıtlar **`RECONCILIATION_REQUIRED`**
  durumuna alınır — **asla otomatik olarak `PENDING`'e döndürülmez**. Sebep:
  SMTP'nin idempotency garantisi yoktur ("crash-before-side-effect" ve
  "crash-after-side-effect" ayrımı aşağıda) — otomatik retry, gerçek bir
  formene/şefe aynı raporun iki kez gitmesi riskini taşır. Bu, `RECONCILIATION_REQUIRED`'ın
  neden yeni bir enum değeri olarak eklendiğinin gerekçesidir (mevcut
  `FAILED`'ı kullanmak, normal retry akışıyla otomatik olarak tekrar
  denenebilir hale getirirdi — tam olarak kaçınılmak istenen şey).
- **Tespit analizi**: in-progress (`QUEUED`/`PLANNING`/`COLLECTING_DATA`/
  `GENERATING_ANALYSIS`/`ANALYZING`) durumda `started_at`'ı
  `ANOMALY_STALE_CLAIM_TIMEOUT_SECONDS`'ı (varsayılan 600sn) aşan
  `AnomalyAnalysis` satırları doğrudan **`FAILED`** yapılır (yeni bir
  ara durum yok). Sebep: bir LLM çağrısının kazara tekrarlanması yalnızca
  API maliyeti riski taşır, gerçek bir kişiye görünen duplicate bir aksiyon
  değildir — bu yüzden burada manuel onay yerine otomatik/temiz bir FAILED
  yeterli ve güvenlidir. Anomali, mevcut "Yeniden Analiz Et" butonuyla
  (veya bir sonraki zamanlanmış tarama ile) manuel olarak tekrar denenebilir.

### RECONCILIATION_REQUIRED'ı çözme

```
python -m app.cli resolve-stale-email-job --report-id <uuid> --resolution sent|retry
```

Operatör, gerçek SMTP relay/delivery loglarını kontrol edip karar verir:

- `--resolution sent`: e-postanın **gerçekten gönderildiği** doğrulandı →
  `SENT` olarak işaretlenir, bir daha denenmez.
- `--resolution retry`: e-postanın **gönderilmediği** doğrulandı → `PENDING`'e
  alınır, bir sonraki `send-monthly-report-emails` çalıştırmasında normal
  şekilde tekrar denenir.

Tespit analizi tarafında ayrı bir "resolve" komutu yoktur — `FAILED`
zaten mevcut UI'daki "Yeniden Analiz Et" akışıyla doğrudan çözülebilir bir
durumdur.

### SMTP exactly-once sınırlaması (bilinçli olarak kabul edilmiştir)

SMTP çağrısı Postgres transaction'ına dahil edilemez (harici bir
protokol çağrısıdır). Bu yüzden şu crash penceresi **tamamen ortadan
kaldırılamaz**: SMTP sunucusu maili başarıyla teslim aldıktan hemen sonra,
`SENDING → SENT` tamamlama commit'inden önce process çökerse, satır
`SENDING`'de kalır ve watchdog bunu `RECONCILIATION_REQUIRED`'a alır —
otomatik yeniden göndermez, ama sistem de "gönderilmedi" olduğunu kesin
bilemez. Bu görevin hedefi **"exactly-once garantisi"** iddia etmek
değildi; hedef şudur ve bununla sınırlıdır:

```
at-most-one aktif claim (aynı anda en fazla bir worker gönderiyor)
+ tek bir logical job (uq_foreman_monthly_reports_foreman_year_month)
+ güvenli retry (claim_token korumalı tamamlama)
+ küçük crash penceresi (network çağrısı DB lock'u dışında)
+ operasyonel reconciliation (RECONCILIATION_REQUIRED + resolve komutu)
```

Crash **öncesi** (claim alındı, SMTP/LLM çağrısı hiç yapılmadı) senaryosu
tamamen güvenlidir ve watchdog tarafından temiz şekilde kurtarılır —
side effect hiç gerçekleşmediği için hangi yöne çözülürse çözülsün risk
yoktur. Riskli olan yalnızca crash **sonrası** (side effect gerçekleşti,
commit gerçekleşmedi) penceresidir ve bunun için tasarım kasıtlı olarak
insan onayını (`resolve-stale-email-job`) devreye sokar, otomatik bir
tahminde bulunmaz.

### İlgili ayarlar

`EMAIL_STALE_CLAIM_TIMEOUT_SECONDS` (varsayılan 900) ve
`ANOMALY_STALE_CLAIM_TIMEOUT_SECONDS` (varsayılan 600) —
bkz. `app/core/config.py`. Anomali eşiği, `LLM_ANALYSIS_TIMEOUT_SECONDS`
(varsayılan 60sn) + yapılandırılmış çıktı için iki deneme payının
belirgin şekilde üzerindedir, böylece yalnızca gerçekten çökmüş bir
worker'da tetiklenir, yavaş ama hayattaki bir worker'da değil.

### Eklenen testler

`backend/tests/integration/test_monthly_report_email_concurrency.py` ve
`test_anomaly_analysis_concurrency.py` — gerçek thread'lerle iki ayrı DB
session/worker'ı eşzamanlı çalıştırarak: (a) yalnızca birinin claim
aldığını ve dış çağrının (SMTP/LLM) tam olarak bir kez yapıldığını, (b)
stale (eski) `SENDING`/in-progress kayıtların watchdog tarafından
kurtarıldığını ama taze olanların dokunulmadığını, (c) geç dönen bir
worker'ın reclaim edilmiş bir job'ın durumunu asla ezemediğini, ve (d)
crash-before-side-effect senaryosunda job'ın watchdog + manuel/otomatik
retry ile normal şekilde tamamlanabildiğini doğrular.

## Frontend

`frontend/src/App.tsx` React Router v7 ile sayfaları tanımlar; kimlik
doğrulaması olmayan istekler `/login`'e yönlendirilir (`ProtectedRoute`).

| Sayfa | Yol |
|---|---|
| Dashboard | `/` |
| Tesisler / Tesis Detayı | `/plants`, `/plants/:plantId` |
| Şef Grupları / Grup Detayı | `/groups`, `/groups/:chiefId` |
| Formenler / Formen Detayı | `/foremen`, `/foremen/:foremanId` |
| KPI Analizi | `/kpis` |
| Katkılar / Detay | `/improvement-works`, `/improvement-works/:workId` |
| Tespitler / Tespit Detayı | `/anomalies`, `/anomalies/:anomalyId` |
| Vardiya Analizi / Detay | `/shift-analysis`, `/shifts/:shiftId` |
| Raporlar | `/reports` |

Dizin yapısı: `api/` (axios client + TanStack Query hook'ları + tip
tanımları), `components/` (paylaşılan bileşenler ve `charts/` altında
Recharts sarmalayıcıları), `context/` (`AuthContext`, `ThemeContext`),
`hooks/useFilters.ts` (filtre durumunu URL query param'larında tutar),
`lib/` (`chartColors.ts`, `tableStyles.ts`, `formStyles.ts`), `pages/`.

Arayüz dili Türkçedir; tasarımda emoji kullanılmaz, ikonlar
`lucide-react`'ten gelir. Tema tamamen CSS custom property'leri üzerinden
çalışır (`index.css`, `:root[data-theme="dark"|"light"]`), `ThemeContext`
tarafından yönetilir ve varsayılan olarak koyu temadır (localStorage'da
kalıcı). Recharts renk/tooltip prop'ları CSS değişkeni kabul etmediği için
`lib/chartColors.ts` içindeki tema-duyarlı yardımcılar (`resolveChartInk`,
`accentLineColor`, `categoricalColor`) kullanılır.

Vite dev sunucusu (`vite.config.ts`) `:5173` portunda çalışır ve `/api`
isteklerini `http://127.0.0.1:8000`'e proxy'ler. Prod build'de statik
dosyalar Nginx ile sunulur ve `/api/` istekleri, container start'ta
`BACKEND_UPSTREAM` ortam değişkeninden render edilen
`frontend/default.conf.template`'e göre backend'e proxy'lenir (varsayılan
`http://backend:8000`; ayrı sunucu için `https://api.internal.company` gibi
bir değer — image yeniden build edilmez, bkz. "Production Deployment").
OIDC ayarları da benzer biçimde `frontend/config.js.template`'ten
`config.js`'e render edilip runtime'da `window.__APP_CONFIG__` olarak
okunur (`src/config/runtimeConfig.ts`) — `npm run dev` bu dosyayı hiç
görmediği için o zaman `import.meta.env.VITE_*`'a düşülür, dev deneyimi
değişmez.

`frontend/scripts/*.mjs` altında Playwright ile yazılmış smoke test
betikleri bulunur (login, filtreleme, sıralama, PDF render, logo gibi
senaryolar); `frontend/` dizininden çalıştırılmalıdır (playwright oradan
çözülür).

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
- **Entegrasyon:** `integration_runs`, `data_quality_issues` — dahili
  kullanımdadır; bunları görüntüleyen ayrı bir API/ekran bulunmaz
- **Rapor:** `report_exports` (ad-hoc analitik export'ları, PDF binary'si
  doğrudan DB'de), `foreman_monthly_reports` (formen aylık bireysel
  performans raporu — rapor verisi JSON olarak DB'de, PDF ise Private S3'te;
  bkz. [Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi))
- **Katkı ve iyileştirme çalışmaları:** `contribution_works`,
  `contribution_work_foremen`, `contribution_gains`
- **Tespitler:** `anomalies`, `anomaly_analyses`, `anomaly_tool_calls` (Aşama 2
  tool calling geçmişi)
- **Denetim:** `audit_logs` (`subject` = OIDC token'ının stabil kimlik claim'i;
  ad/e-posta gibi SSO profil bilgileri hiçbir tabloda saklanmaz — kimlik
  doğrulama otoritesi Red Hat SSO'dur, bkz.
  [Authentication Architecture](#authentication-architecture))

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
    `NotImplementedError` fırlatır)
15. `d4f6a8b1c3e5` — Plana Uyum v3: asimetrik puanlama. Plan üstü üretim
    artık cezalandırılmaz, ödüllendirilir (logaritmik olarak +%5'ten sonra
    yavaşlar); plan altı öncekinden daha güçlü cezalandırılır. Yalnızca yeni
    bir `kpi_calculation_rules` versiyonu ekler — var olan
    `performance_scores`'u yeniden hesaplamaz (bkz. `apply-scoring-model-v2`)
16. `f8a1c3e5b7d9` — `performance_records`'ın doğal anahtarına `plant_id`
    ekler — bir formenin 2-4 eşzamanlı tesisinden yalnızca ilkinin KPI
    kayıtları `ON CONFLICT DO NOTHING` ile hayatta kalıyordu, geri kalanı
    `DUPLICATE` olarak atlanıyordu (bkz. [Veri Akışı](#veri-akışı-sağlayıcı--ingestion--skor))
17. `a2c4e6f8b0d3` — `performance_records`'a da `(plant_id, chief_id) →
    plants(id, chief_id)` kompozit FK'sini ekler (`production_records`/
    `foreman_work_calendar`'da zaten vardı) — `ingestion.py`'nin
    `assignment_resolver.py` üzerinden yaptığı doğrulamaya DB seviyesinde
    bir yedek katman
18. `b3d5f7a9c1e2` — `foreman_assignments` tarih aralığı bütünlüğü: `CHECK`
    kısıtları (`start_date <= end_date`, pasif atamanın `end_date`'i
    olmalı), aynı tesis+vardiya için tarih aralığı çakışmasını engelleyen
    `EXCLUDE` kısıtı (`btree_gist`) ve bir formenin aynı anda yalnızca tek
    bir şefe bağlı olabilmesini DB seviyesinde zorunlu kılan trigger
19. `c9e2a4f6b8d0` — **Aksiyon Planları özelliği tamamen kaldırılır.**
    `action_plans` tablosu ve ilgili enum'lar (`action_plan_status`,
    `action_plan_priority`) drop edilir. Bilinçli olarak geri alınamaz
    (`downgrade()` `NotImplementedError` fırlatır)

> Not: Bu listedeki numaralandırma, `c9e2a4f6b8d0`'dan sonra eklenmiş bazı
> migration'ları (formen aylık rapor tablosu, formen/şef iletişim bilgisi,
> OIDC subject geçişi, katkı puanı, KPI ağırlık eşitleme) henüz kapsamıyor —
> bu görevin kapsamı dışında, önceden var olan bir doküman gecikmesi.
> Gerçek migration zinciri için her zaman `alembic history` çalıştırın.

20. `d6f8a0c2e4b7` — `foreman_monthly_reports`'a kalıcı PDF storage ve e-posta
    teslimat alanları ekler (`pdf_generation_status`, `object_key`,
    `email_status`, `email_retry_count` vb.) — bkz.
    [Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi).
    Yalnızca nullable/server-default kolon ekler, mevcut satırları silmez;
    `downgrade()` tam tersini yapar (HEAD)

`alembic upgrade head`, backend konteyneri her başladığında otomatik
çalışır (`backend/Dockerfile` CMD'si).


## Kurulum (Docker)

Gereksinim: Docker + Docker Compose.

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d
```

(Production kurulumu için bkz. [Production Deployment](#production-deployment) — farklı bir `-f` kombinasyonu kullanır ve local Keycloak'ı hiç başlatmaz.)

- Frontend: http://localhost:8080
- Backend / OpenAPI: http://localhost:8000/docs
- PostgreSQL (host'tan erişim): `localhost:5433`

Şema `alembic upgrade head` ile otomatik oluşur ancak **sentetik veri otomatik
seed edilmez** (kasıtlı tasarım: üst yönetim kullanıcıları arayüzden veri
giremediği gibi, demo verisi de yalnızca geliştirici tarafından kontrollü
parametrelerle üretilir). Kullanıcı hesapları artık Red Hat SSO'da
yönetildiği için (bkz. [Authentication Architecture](#authentication-architecture))
`create-admin` gibi bir komut yoktur — uygulamaya girecek kullanıcılar
Keycloak realm'ine eklenir. Konteynerler ayaktayken:

```bash
docker compose exec backend python -m app.cli seed --seed 42
```

`seed` sırasıyla şunları yapar: `[1/3]` referans veri (organizasyon +
KPI hedefleri), `[2/3]` sentetik üretim verisi
(`production_records` — bkz. [Üretim Verisi Katmanı](#üretim-verisi-katmanı)),
`[3/3]` bu üretim verisinden KPI türetme + ingestion, ardından katkı çalışması
örnekleri (`created_by_subject` sabit bir `synthetic-seed-script` değeri alır)
ve son olarak Tespitler modülü için
sentetik ML tespitleri (`seed-anomalies`). Varsayılan olarak son 12 ay için
~50–75K performans kaydı üretir (`docker compose exec backend python -m app.cli seed`
çıktısındaki `[3/3]` satırı `başarılı` sayısı) — birkaç dakika sürebilir,
arka planda çalıştırın. Bu, ham üretim kaydı sayısından belirgin düşüktür:
`performance_records`'ın doğal anahtarı (`foreman_id`, `kpi_id`, `chief_id`,
`shift_id`, `performance_date`) `plant_id` içermez, bu yüzden bir formenin
aynı gün sorumlu olduğu 2-4 tesisin ürettiği KPI kayıtlarından yalnızca
ilki eklenir, geri kalanı `DUPLICATE` olarak atlanır (bkz.
[Veri Akışı](#veri-akışı-sağlayıcı--ingestion--skor)). `seed` yalnızca boş,
migration'ları uygulanmış bir veritabanında çalışır; mevcut referans veri
algılanırsa hiçbir kayıt eklemeden kontrollü olarak durur. Sentetik veriyi
sıfırdan üretmek için yalnızca sentetik/test veritabanını deployment'ın reset
prosedürüyle yeniden oluşturun, `alembic upgrade head` çalıştırın ve ardından
`seed` komutunu çağırın. Kısmi tablo `TRUNCATE` işlemi veya force bypass
desteklenmez.

Sentetik veri üretici parametreleri (`app/cli.py`):

```bash
docker compose exec backend python -m app.cli seed \
  --seed 42 \
  --min-plants-per-foreman 2 --max-plants-per-foreman 4 \
  --start-date 2025-07-27 --end-date 2026-07-27 \
  --missing-rate 0.02 --error-rate 0.01 --anomaly-rate 0.015 --duplicate-rate 0.005
```

Aynı `--seed` ile tekrar çalıştırma aynı veri setini üretir
(deterministik). Fabrika/tesis sayısı `--plants` gibi bir bayrakla
**değiştirilemez** — 50 tesislik K1/K2 yapısı `FACTORY_SEED`'de sabittir.

Diğer CLI komutları:

```bash
docker compose exec backend python -m app.cli backfill-data-quality-issues
docker compose exec backend python -m app.cli regenerate-personnel-identities
docker compose exec backend python -m app.cli seed-anomalies --seed 42
docker compose exec backend python -m app.cli seed-contributions --seed 42 --count 40
docker compose exec backend python -m app.cli apply-scoring-model-v2
docker compose exec backend python -m app.cli generate-monthly-reports
docker compose exec backend python -m app.cli send-monthly-report-emails --retry-failed
docker compose exec backend python -m app.cli reconcile-stale-jobs
docker compose exec backend python -m app.cli resolve-stale-email-job --report-id <uuid> --resolution sent|retry
```

İlk ikisi bkz. [Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi)
— `generate-monthly-reports` en son tamamlanmış ay için her aktif formene
rapor üretir ve S3'e (veya yerel dev storage'ına) yükler; `send-monthly-report-emails`
üretilmiş raporları formen+şefe e-postayla gönderir (SMTP yapılandırılmadıysa
güvenli şekilde no-op'tur). Son ikisi bkz.
[Job Claiming & Concurrency](#job-claiming--concurrency) — `reconcile-stale-jobs`
crash sonrası takılı kalmış e-posta/analiz job'larını tarayan watchdog'tur
(periyodik cron ile çalıştırılması önerilir), `resolve-stale-email-job`
watchdog'un `RECONCILIATION_REQUIRED` işaretlediği bir e-postayı operatör
kararıyla çözer.

`apply-scoring-model-v2`, var olan performans verisini KPI'a özel yeni
puanlama formülleriyle yeniden hesaplar (AGIR_GITME'nin işaretli
türetimini düzeltir, İNKITA için geriye dönük ingestion çalıştırır ve
tüm `performance_scores`'u aktif kurallarla yeniden puanlar) — bkz.
[KPI Hesaplama Motoru](#kpi-hesaplama-motoru).

Servis bazlı yeniden build ve log inceleme (aynı `-f` kombinasyonunu stack'i
başlattığınız komutla tutarlı tutun — bkz. "Kurulum (Docker)"):

```bash
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d backend
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml logs backend --tail 50
```

> **Önemli:** İmajlar kaynağı build anında gömer, bind mount yoktur. Bir
> dosyayı düzenlemek, ilgili servisi `--build` ile yeniden oluşturmadan
> çalışan konteynerde hiçbir etki yaratmaz.

## Production Deployment

### Prerequisites

- Docker Engine + Docker Compose v2 (`docker compose version` — bu repo `!override`/`!reset` merge tag'leri ve `profiles:` kullanır, ikisi de eski Compose v1'de yoktur)
- Gerçek bir domain adı ve onu bu sunucuya (veya edge proxy'nin çalıştığı sunucuya) işaret eden bir DNS A/AAAA kaydı (bkz. [DNS](#dns)) — `edge` servisi olmadan (kendi LB'niz varsa) gerekmez
- Kurumsal Red Hat SSO / Keycloak realm'inde kayıtlı bir OIDC client (public, Authorization Code + PKCE) — bkz. [Authentication Architecture](#authentication-architecture)
- 80/443'ün genele açık olduğu bir firewall/güvenlik grubu (bkz. [Network / Firewall](#network--firewall))
- Repo'nun bir kopyası (`git clone`) — image'lar build anında kaynağı gömer, ayrıca bir artifact registry'sine ihtiyaç yoktur

### Model 1 — Tek Sunucu

```text
Sunucu A
├── Edge Proxy (Caddy, 80/443)
├── Frontend
├── Backend
└── PostgreSQL
```

```bash
git clone <repo> && cd formen-takip
cp .env.example .env   # DATABASE_URL boş bırakın (local postgres kullanılacak),
                       # SITE_DOMAIN, OIDC_*, gerçek değerlerle doldurun
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml config   # doğrula
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml up -d --build
```

### Model 2 — Frontend ve Backend Ayrı Sunucularda

```text
Sunucu A (frontend)          Sunucu B (backend)          Sunucu C (DB)
├── Edge Proxy                                            └── PostgreSQL
└── Frontend  ──BACKEND_UPSTREAM──▶  Backend  ──DATABASE_URL──▶
```

**Sunucu C** (PostgreSQL — Model 3'teki gibi, `docker-compose.db.yml` bu sunucuda çalışır ve `POSTGRES_BIND`'i Sunucu B'nin ulaşabileceği private adrese ayarlar):

```bash
# .env: POSTGRES_BIND=10.0.3.30 (bu sunucunun private-network adresi)
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml up -d postgres
```

**Sunucu B** (backend):

```bash
# .env: DATABASE_URL=postgresql+psycopg://formen:***@10.0.3.30:5432/formen_takip
#       BACKEND_BIND=10.0.2.20 (bu sunucunun private-network adresi, Sunucu A'nın ulaşacağı)
#       OIDC_ISSUER_URL / OIDC_AUDIENCE gerçek değerler
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend
```

**Sunucu A** (frontend + edge):

```bash
# .env: BACKEND_UPSTREAM=http://10.0.2.20:8000 (Sunucu B'nin private-network adresi)
#       SITE_DOMAIN=formen.example.com
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d frontend edge
```

Genel-internete açık production'da ham IP yerine internal DNS kullanımı tavsiye
edilir (bir sunucu IP'si değiştiğinde `.env`'i her yerde güncellemek yerine tek
bir DNS kaydını güncellersiniz):

```env
BACKEND_UPSTREAM=http://api.formen.internal:8000
DATABASE_URL=postgresql+psycopg://formen:***@db.formen.internal:5432/formen_takip
```

(Gerçek parola asla dokümantasyona veya `.env.example`'a yazılmaz — yukarıdaki
`***` yer tutucudur.)

### Model 3 — External / Yönetilen PostgreSQL

Sunucu A (edge+frontend+backend) + harici bir PostgreSQL (RDS, Azure Database
for PostgreSQL, vb.) — bkz. [Database Persistence Modelleri](#database-persistence-modelleri) Model B:

```bash
# docker-compose.db.yml dahil EDİLMEZ
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Network / Firewall

```text
Internet
   │
   ▼
80/443 (edge — HTTPS termination, Caddy)
   │
   ▼
Frontend (8080) ── private/same-host ──▶ Backend (8000) ── private/same-host ──▶ PostgreSQL (5432)
```

`docker-compose.prod.yml`'in `edge` servisi (Caddy) **tek genel-internete açık servistir** — yalnızca 80 (otomatik 443'e yönlendirir) ve 443'ü dinler. Diğer her şey varsayılan olarak yalnızca bu host'tan erişilebilir:

| Servis | Port | Varsayılan bind | Public mi? |
|---|---|---|---|
| `edge` (Caddy) | 80, 443 | `0.0.0.0` (kasıtlı) | **Evet** — tek genel-erişimli servis |
| `frontend` | 8080 | `${FRONTEND_BIND:-127.0.0.1}` | Hayır — `edge` bunu Compose ağı üzerinden bulur, yalnızca `FRONTEND_BIND` gerçek bir private-network adresine ayarlanırsa (ör. ayrı host'taki bir kurumsal LB) o adresten erişilebilir |
| `backend` | 8000 | `${BACKEND_BIND:-127.0.0.1}` | Hayır — yalnızca `BACKEND_BIND` gerçek bir private-network adresine ayarlanırsa (frontend ayrı host'taysa) o adresten erişilebilir |
| `postgres` | 5433→5432 | `${POSTGRES_BIND:-127.0.0.1}` | Hayır — aynı mantık, backend ayrı host'taysa `POSTGRES_BIND` |

`FRONTEND_BIND`/`BACKEND_BIND`/`POSTGRES_BIND` **asla** `0.0.0.0` yapılmamalı — bir private-network adresi (örn. `10.0.2.20`) veya varsayılan `127.0.0.1` olmalı. Tek-sunucu dağıtımda (Model 1) hiçbirini değiştirmenize gerek yok, `frontend`/`backend` birbirini zaten Compose'un dahili DNS'i üzerinden bulur; bu üç `_BIND` değişkeni yalnızca host'tan manuel erişim (`localhost:8000/docs`, `psql`) veya ayrı bir host'un doğrudan erişimi için var. Firewall kuralı özeti: sunucunun güvenlik grubunda/`ufw`'sinde yalnızca 80/443'ü (ve SSH'ı) genele açın; 8080/8000/5432/5433'ü hiç açmayın.

### HTTPS

`docker-compose.prod.yml`'deki `edge` servisi [Caddy](https://caddyserver.com/) kullanır — `SITE_DOMAIN` gerçek, DNS'i bu sunucuya işaret eden bir domain ise sertifikayı **otomatik olarak** Let's Encrypt'ten alır ve yeniler, elle hiçbir sertifika/cron işi gerekmez:

```bash
# DNS: formen.example.com -> bu sunucunun public IP'si
# .env: SITE_DOMAIN=formen.example.com
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml up -d
```

Gerçek bir domain olmadan (yerel/staging test) `SITE_DOMAIN=localhost` kullanabilirsiniz — Caddy bu durumda Let's Encrypt'e hiç gitmez, kendi dahili CA'sıyla self-signed bir sertifika üretir; `curl -k`/tarayıcıda "güvenilir değil" uyarısıyla ama gerçek HTTPS akışıyla test edilebilir.

Kurumsal bir reverse proxy/load balancer zaten varsa (`edge` servisini hiç kullanmak istemiyorsanız): `docker compose ... up -d backend frontend` ile yalnızca ilgili servisleri başlatıp kendi LB'nizi doğrudan `frontend`'in (8080) yayınlanan portuna yönlendirebilirsiniz — bu durumda `FRONTEND_BIND`'ı LB'nin erişebileceği private-network adresine ayarlamanız gerekir (varsayılan `127.0.0.1` LB'yi de dışarıda bırakır). `edge` opsiyonel bir kolaylıktır, mimarinin zorunlu bir parçası değildir.

### Database Persistence Modelleri

İki desteklenen model var — hangisini kullandığınız yalnızca hangi compose
dosyalarını `-f` ile verdiğinize bağlı, uygulama kodunda hiçbir fark yaratmaz:

**Model A — Aynı host'ta local Postgres** (`docker-compose.db.yml` dahil):

```text
Backend
   │
   ▼
Postgres container ("postgres" servisi)
   │
   ▼
Named volume (formen_pg_data) — docker compose down bunu SİLMEZ,
                                  yalnızca `docker compose down -v` siler
```

```bash
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml up -d
```

**Model B — External / yönetilen Postgres** (`docker-compose.db.yml` DAHİL EDİLMEZ):

```text
Backend
   │
   │ DATABASE_URL (kök .env)
   ▼
Uzak PostgreSQL (ayrı sunucu, RDS, vb.) — kalıcılık o servisin sorumluluğunda
```

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

`DATABASE_URL` boş bırakılırsa `docker-compose.yml`, `POSTGRES_USER/PASSWORD/DB`'den
yerel `postgres` servisine bağlanan bir varsayılan inşa eder — bu yüzden Model
B'de `DATABASE_URL`'i **mutlaka** doldurun, aksi halde backend var olmayan bir
"postgres" servisine bağlanmaya çalışır ve `docker-compose.db.yml` dahil
değilse container hiç ayağa kalkmaz.

### Backup / Restore Runbook

Aşağıdaki adımlar yalnızca Model A (local Postgres container) içindir; Model
B'de (yönetilen/external DB) yedekleme o servisin kendi mekanizmasıyla
(örn. RDS otomatik snapshot) yapılır.

**Yedek alma** (canlı sistemi durdurmadan; `pg_dump` tutarlı bir snapshot alır):

```bash
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml \
  exec -T postgres pg_dump -U formen -Fc formen_takip > formen_takip_$(date +%Y%m%d_%H%M%S).dump
sha256sum formen_takip_*.dump > formen_takip_*.dump.sha256
```

**Geri yükleme** (yeni/boş bir hedef veritabanına — var olan bir production
DB'nin üzerine **asla** doğrudan restore etmeyin, önce ayrı bir DB'de doğrulayın):

```bash
# 1) checksum doğrula
sha256sum -c formen_takip_YYYYMMDD_HHMMSS.dump.sha256

# 2) hedef (boş) veritabanına geri yükle
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml \
  exec -T postgres pg_restore -U formen -d formen_takip --clean --if-exists < formen_takip_YYYYMMDD_HHMMSS.dump

# 3) Alembic doğrulaması — restore edilen DB'nin head'de olduğunu doğrulayın
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml \
  exec backend alembic current
# beklenen: en son revision ID (bkz. `alembic heads` çıktısı)

# 4) smoke test
curl -f http://localhost:8000/health/ready
```

**S3 nesneleriyle ilişki:** Formen aylık rapor PDF'leri `REPORT_STORAGE_PROVIDER=s3`
iken veritabanı DIŞINDA S3'te tutulur; `foreman_monthly_reports.object_key`
kolonu S3 nesne anahtarını referans eder (bkz.
[Formen Aylık Rapor Storage Mimarisi](#formen-aylık-rapor-storage-mimarisi)).
Bir DB restore işleminde S3 bucket'ı **ayrıca** taşınmadıysa (`aws s3 sync` ile),
restore edilen `object_key` değerleri var olmayan nesnelere işaret eder —
bu durumda PDF indirme isteği `ReportObjectNotFoundError` alır ve backend
otomatik olarak PDF'i sıfırdan render ederek (S3'süz) yanıt verir (bkz.
`app/api/v1/foremen.py`) — istek başarısız olmaz, yalnızca CDN/kalıcı depolama
avantajı o rapor için kaybolur. Kalıcı arşivi de taşımak isterseniz DB restore
ile aynı bakım penceresinde `aws s3 sync s3://eski-bucket s3://yeni-bucket`
çalıştırın.

Bu runbook production verisi üzerinde hiçbir destructive komut içermez —
`pg_restore` adımı yalnızca boş/ayrı bir hedef veritabanına yöneliktir.

### Scheduler

Aylık rapor üretimi, e-posta gönderimi ve stale-job reconciliation için —
bkz. `backend/scheduler/README.md` (rasyonel, tek-instance kısıtı, manuel
tetikleme komutu).

### DNS

| Kayıt | Nereyi gösterir | Zorunlu mu? |
|---|---|---|
| `formen.example.com` (`SITE_DOMAIN`) | `edge` servisinin çalıştığı sunucunun **public** IP'si | Evet — Let's Encrypt bu adresi doğrulayabilmeli |
| `api.formen.internal` | Backend'in çalıştığı sunucunun **private-network** IP'si | Hayır — yalnızca Model 2 (frontend/backend ayrı sunucu) ve internal DNS kullanmak isterseniz |
| `db.formen.internal` | PostgreSQL'in çalıştığı sunucunun **private-network** IP'si | Hayır — yalnızca Model 2/3 ve internal DNS kullanmak isterseniz |

`api.formen.internal`/`db.formen.internal` **genel internetten çözülebilir
olmamalı** — yalnızca private network içinde (VPC internal DNS, `/etc/hosts`,
veya kurumsal internal resolver) çözülmelidir; genele açık bir DNS kaydı,
arkasındaki servis firewall ile korunsa bile, iç mimariyi dışarıya sızdırır.

### Health Checks

| Endpoint | Ne kontrol eder | Kullanım |
|---|---|---|
| `GET /health` , `GET /health/live` | Süreç ayakta mı (hiçbir bağımlılığı kontrol etmez) | Liveness probe |
| `GET /health/ready` | Veritabanı gerçekten erişilebilir mi (`SELECT 1`) | Readiness probe, `docker-compose.yml`'in backend `healthcheck:`'i bunu kullanır |

`/health/ready` **yalnızca** veritabanını kontrol eder — SMTP/S3/CloudFront/LLM
gibi opsiyonel entegrasyonlar zaten kendi fail-soft davranışına sahip (bkz.
[Production Setup Required](#production-setup-required)), bu yüzden onların
bir arıza durumunda backend'in tamamını "not ready" yapması yanlış olurdu.

### Troubleshooting

| Belirti | Muhtemel neden | Çözüm |
|---|---|---|
| Kod değişikliği container'da görünmüyor | Image'lar build anında kaynağı gömer, bind mount yok | İlgili servisi `--build` ile yeniden oluşturun |
| Backend `AUTH_BYPASS`/OIDC hatasıyla başlamıyor | `ENVIRONMENT=production` iken `OIDC_ISSUER_URL`/`OIDC_AUDIENCE` boş, veya `AUTH_BYPASS=true` `development` dışında | `.env`'i doldurun — bu fail-closed davranış kasıtlı, bypass edilmemeli |
| `edge` servisi başlamıyor: "SITE_DOMAIN is missing" | `.env`'de `SITE_DOMAIN` boş | Gerçek bir domain girin, veya yerel test için `SITE_DOMAIN=localhost` |
| `edge` sertifika alamıyor | DNS henüz bu sunucuyu göstermiyor, veya 80/443 firewall'da kapalı | DNS propagasyonunu ve firewall kurallarını kontrol edin (`dig SITE_DOMAIN`, `curl -I http://SITE_DOMAIN`) |
| Backend fresh DB'de `alembic upgrade head` ile başlamıyor | Migration zincirinde bir sorun | Bkz. `backend/tests/unit/test_migration_enum_safety.py` — enum `ADD VALUE` + aynı transaction'da kullanım deseni kontrol edilir |
| Bir servise `docker compose exec` "no such service" hatası veriyor | O servis `profiles:` ile kapalı (örn. `scheduler`) veya yanlış `-f` kombinasyonu kullanılıyor | Stack'i başlattığınız `-f` kombinasyonunu (ve varsa `--profile`) tutarlı kullanın |
| `docker compose config` port çakışması / beklenmedik boş `ports:` | Bir override dosyasında liste alanları (`ports`) `!reset` ile temizlenip yeni değer VERİLMEDEN bırakılmış | Listeyi tamamen değiştirmek için `!reset` değil `!override` kullanın — `!reset` yalnızca temizler, yeni değer atamaz |
| Frontend'den API isteği 404/502 | `BACKEND_UPSTREAM` yanlış, veya backend henüz `/health/ready` vermiyor | `docker compose logs frontend backend`; nginx `resolver` DNS'i periyodik yeniden çözer, backend `restart: unless-stopped` ile kendini toparlar |

## Yerel Geliştirme (Docker'sız)

### Backend

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements-dev.txt   # requirements.txt + pytest (test çalıştırmak için)
cp .env.example .env   # DATABASE_URL Compose'un host portu 5433'ü hedefler;
                       # farklı bir yerel Postgres kullanıyorsanız düzenleyin
alembic upgrade head
python -m app.cli seed --seed 42
uvicorn app.main:app --reload
```

`backend/.env.example`'daki `DATABASE_URL`, Compose'un Postgres'i host'a
map'lediği **5433** portunu kullanır; `app/core/config.py`'deki varsayılan
da aynı şekilde 5433'tür, bu yüzden `.env` dosyası hiç oluşturulmasa (veya
`DATABASE_URL` unutulsa) bile host'tan çalıştırıldığında doğru porta düşer.
`backend/.env` `.gitignore` ile hariç tutulur — her geliştirici kendi
kopyasını `.env.example`'dan türetir.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite dev sunucusu `/api` isteklerini `http://127.0.0.1:8000`'e proxy'ler,
bu yüzden backend'in ayrıca (Docker'da ya da yerelde) çalışıyor olması
gerekir.

Diğer frontend komutları:

```bash
npx tsc --noEmit    # tip kontrolü
npm run build       # tsc -b && vite build
npm run lint        # oxlint
```

## Testler

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q                      # tüm paket (712 test fonksiyonu)
.venv/Scripts/python.exe -m pytest tests/unit -q            # yalnızca unit (DB gerekmez)
.venv/Scripts/python.exe -m pytest tests/integration/test_reports.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_kpi_engine.py::TestX::test_y -q
```

- **Unit testler** (`tests/unit/`) DB gerektirmez: `test_kpi_engine.py`,
  `test_target_resolver.py`, `test_shift_utils.py`, `test_turkish_sort.py`,
  `test_reporting_pdf.py`, `test_production_kpi_derivation.py`,
  `test_contribution_calc.py`, `test_anomaly_demo_fallback.py`,
  `test_anomaly_analysis_schema.py`, `test_anomaly_orchestrator_helpers.py`,
  `test_assignment_resolver.py`, `test_shift_analysis.py`.
- **Integration testler** (`tests/integration/`) **çalışan, migrasyonu
  yapılmış ve seed edilmiş** bir Postgres bekler — gerçek DB'ye
  `SessionLocal()` üzerinden bağlanır, ayrı bir şema fixture'ı yoktur:
  `test_auth_flow.py`, `test_dashboard.py`, `test_plants_foremen.py`,
  `test_chiefs.py`, `test_data_quality.py`, `test_foreman_assignment_integrity.py`,
  `test_ingestion_idempotency.py`, `test_reports.py`, `test_contribution_works.py`,
  `test_anomalies.py`, `test_anomaly_analysis_service.py`,
  `test_anomaly_generator.py`, `test_world.py`, `test_tools.py`,
  `test_anomaly_orchestrator.py`, `test_shift_analysis.py`,
  `test_analytics_agir_gitme_display.py`,
  `test_production_kpi_derivation_plant_scoping.py`,
  `test_n_plus_one_regression.py`, `test_monthly_report_delivery.py`,
  `test_monthly_report_email_concurrency.py`,
  `test_anomaly_analysis_concurrency.py` (Tespitler'e ait olanlar için önce
  `seed-anomalies` çalıştırılmış olmalıdır). Son ikisi gerçek thread'lerle
  eşzamanlı worker'ları simüle eder — bkz.
  [Job Claiming & Concurrency](#job-claiming--concurrency).

`pytest.ini`, `testpaths = tests` ve `pythonpath = .` tanımlar; ek yapılandırma
gerekmez. Otomatik CI pipeline'ı (GitHub Actions vb.) bu depoda **tanımlı
değildir** — testler manuel çalıştırılır.

## Depoyu Klonladıktan Sonra

Aşağıdakiler kasıtlı olarak `.gitignore` ile depo dışında tutulur — çünkü
tamamen tekrar üretilebilirler ve kaynak koduna bağlı değildirler:

- `backend/.venv/` — `pip install -r requirements-dev.txt` ile yeniden kurulur
  (Docker imajı yalnızca `requirements.txt`'i kurar — `pytest`/`pytest-cov`
  production image'a hiç girmez, bkz. `backend/Dockerfile`)
- `frontend/node_modules/` — `npm install` ile yeniden kurulur
- `frontend/dist/` — `npm run build` ile yeniden üretilir
- `backend/.env`, `.env` (kök) — ilgili `.env.example` şablonlarından
  kopyalanır (bkz. [Ortam Değişkenleri](#ortam-değişkenleri))
- Python/Node önbellekleri (`__pycache__/`, `*.pyc`, `.pytest_cache/`,
  `.coverage`, `htmlcov/`) ve editör/IDE'ye özel dosyalar (`.vscode/*`,
  `.idea/`)

Bir klondan sonra sistemi çalışır hale getirmek için gereken adımlar
[Kurulum (Docker)](#kurulum-docker) veya [Yerel Geliştirme](#yerel-geliştirme-dockersız)
bölümlerinde eksiksiz olarak yer alır; ek bir adım gerekmez.

## Ortam Değişkenleri

Kök dizindeki `.env.example`, Docker Compose için referans şablondur
(`cp .env.example .env`). `backend/.env.example` ise yerelden (Docker'sız)
çalıştırma için şablondur (`cp backend/.env.example backend/.env`) —
`DATABASE_URL` doğrudan Compose'un host'a map'lediği `5433` portunu hedefler.
Her iki gerçek `.env` dosyası da `.gitignore` ile hariç tutulur; yalnızca
`.example` şablonları repoya dahildir.

**Secret = evet** olan değerler gerçek bir üretim ortamında merkezi bir sır
yönetimi servisinden inject edilmeli, `.env` dosyasına elle yazılmamalıdır.
Ayarların tam listesi ve varsayılanlar için `backend/app/core/config.py`
(pydantic-settings `Settings` sınıfı) doğrudan referans alınmalıdır — bu
tablo onun deployment açısından okunur bir özetidir.

### Runtime

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `ENVIRONMENT` | Hayır (varsayılan `production`) | Hayır | İkisi de | `development` dışındaki her değer `AUTH_BYPASS=true`'yu reddeder (fail-closed) |
| `APP_DEBUG` | Hayır (varsayılan `false`) | Hayır | İkisi de | Compose üzerinden FastAPI debug modu; production'da `true` ise backend fail-closed başlamaz |
| `AUTH_BYPASS` / `VITE_AUTH_BYPASS` | Hayır | Hayır | Yalnızca development | `ENVIRONMENT=development` dışında `true` olamaz — backend startup'ı fail-closed reddeder |
| `CORS_ORIGINS` | Hayır | Hayır | İkisi de | Backend'in kabul ettiği origin listesi (JSON array); production'da `*` fail-closed reddedilir |

### Database

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `DATABASE_URL` | Boşsa `POSTGRES_*`'ten local varsayılana düşer | **Evet** (parola içerir) | İkisi de | Externalize edilebilir tam bağlantı dizesi — bkz. [Network / Firewall](#network--firewall) |
| `POSTGRES_USER` / `POSTGRES_DB` | Yalnızca `docker-compose.db.yml` kullanılıyorsa | Hayır | İkisi de | Local Postgres servisi |
| `POSTGRES_PASSWORD` | Yalnızca `docker-compose.db.yml` kullanılıyorsa | **Evet** | İkisi de | |
| `POSTGRES_BIND` | Hayır (varsayılan `127.0.0.1`) | Hayır | Prod'da önemli | Postgres'in host'a bind edildiği adres — asla `0.0.0.0` olmamalı |

### OIDC — Backend (token doğrulama)

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `OIDC_ISSUER_URL` | **Prod'da zorunlu** (fail-closed) | Hayır | İkisi de | bkz. [Authentication Architecture](#authentication-architecture) |
| `OIDC_AUDIENCE` | **Prod'da zorunlu** | Hayır | İkisi de | Access token'ın beklenen `aud` claim'i |
| `OIDC_JWKS_URI` | Hayır | Hayır | İkisi de | JWKS keşfini override etmek için opsiyonel |
| `OIDC_USER_ID_CLAIM` | Hayır (varsayılan `sub`) | Hayır | İkisi de | |

### Frontend Runtime Config (container start'ta `config.js`'e render edilir — bkz. [Frontend](#frontend))

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `OIDC_CLIENT_ID` | Prod'da pratikte zorunlu | Hayır | İkisi de | Public client (PKCE), secret yok |
| `OIDC_REDIRECT_URI` / `OIDC_POST_LOGOUT_REDIRECT_URI` | Hayır (makul varsayılan) | Hayır | İkisi de | |
| `OIDC_SCOPE` | Hayır (varsayılan `openid profile email`) | Hayır | İkisi de | |

### Backend Upstream / Ağ

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `BACKEND_UPSTREAM` | Hayır (varsayılan `http://backend:8000`) | Hayır | Multi-server'da zorunlu | Frontend'in backend'i bulduğu adres |
| `BACKEND_BIND` | Hayır (varsayılan `127.0.0.1`) | Hayır | Prod'da önemli | Backend'in host'a bind edildiği adres — asla `0.0.0.0` olmamalı |
| `SITE_DOMAIN` | **`edge` servisi için zorunlu** | Hayır | Yalnızca prod | bkz. [HTTPS](#https) |

### S3 / CloudFront (Formen Aylık Rapor Storage — bkz. [Production Setup Required](#production-setup-required))

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `REPORT_STORAGE_PROVIDER` | Hayır (varsayılan `local`) | Hayır | `local` yalnızca dev | `s3` prod'da fiilen zorunlu (kullanılmaya çalışıldığında hata) |
| `AWS_REGION` / `REPORTS_S3_BUCKET` | `s3` iken zorunlu | Hayır | Prod | AWS credential'ı **buradan değil** IAM role/standart credential chain'den gelir |
| `LOCAL_REPORT_STORAGE_DIR` | Hayır | Hayır | Yalnızca dev | `local` sağlayıcı dizini |
| `CLOUDFRONT_DOMAIN` / `CLOUDFRONT_KEY_PAIR_ID` | Hayır | Hayır | Prod (opsiyonel) | Boşken erişim backend proxy'sine düşer |
| `CLOUDFRONT_PRIVATE_KEY` | Hayır | **Evet** (PEM private key) | Prod (opsiyonel) | |
| `REPORT_SIGNED_URL_TTL_SECONDS` | Hayır | Hayır | İkisi de | |

### SMTP

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `SMTP_ENABLED` | Hayır (varsayılan `false`) | Hayır | İkisi de | `false` iken hiç gönderim denenmez |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_FROM` / `SMTP_USE_TLS` | `SMTP_ENABLED=true` iken zorunlu | Hayır | Prod | |
| `SMTP_USERNAME` | `SMTP_ENABLED=true` iken zorunlu | Hayır | Prod | |
| `SMTP_PASSWORD` | `SMTP_ENABLED=true` iken zorunlu | **Evet** | Prod | |
| `EMAIL_MAX_RETRY_COUNT` | Hayır | Hayır | İkisi de | |

### LLM (Tespitler Modülü)

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `LLM_ENABLED` | Hayır (varsayılan `false`) | Hayır | İkisi de | `false`/anahtar yoksa demo analiz döner, uygulama bozulmaz |
| `LLM_API_KEY` | `LLM_ENABLED=true` iken zorunlu | **Evet** | Prod | Yalnızca backend'de okunur, frontend'e hiç gönderilmez |
| `LLM_MODEL` / `LLM_BASE_URL` / `LLM_TIMEOUT_SECONDS` | Hayır | Hayır | İkisi de | OpenAI uyumlu `chat/completions` uç noktası |
| `LLM_ANALYSIS_MODE` / `LLM_TOOL_CALLING_ENABLED` / `LLM_DEMO_TOOL_CALLING_ENABLED` | Hayır | Hayır | İkisi de | bkz. [Aşama 2 — Tool Calling](#aşama-2--tool-calling-destekli-analiz-ajanı) |
| `LLM_MAX_TOOL_CALLS` / `LLM_MAX_ANALYSIS_STEPS` / `LLM_TOOL_TIMEOUT_SECONDS` / `LLM_ANALYSIS_TIMEOUT_SECONDS` / `LLM_MAX_DATE_RANGE_DAYS` | Hayır | Hayır | İkisi de | |

### SAP (Faz 1'de kullanılmıyor)

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `SAP_BASE_URL` / `SAP_CLIENT_ID` | Hayır | Hayır | — | `SAPDataProvider` için yer tutucu, henüz uygulanmadı |
| `SAP_CLIENT_SECRET` | Hayır | **Evet** (kullanılınca) | — | |

### Scheduler / Reconciliation (bkz. [Scheduler](#scheduler))

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `EMAIL_STALE_CLAIM_TIMEOUT_SECONDS` | Hayır (varsayılan `900`) | Hayır | İkisi de | bkz. [Job Claiming & Concurrency](#job-claiming--concurrency) |
| `ANOMALY_STALE_CLAIM_TIMEOUT_SECONDS` | Hayır (varsayılan `600`) | Hayır | İkisi de | Aynı watchdog, tespit analizi eşiği |

### Diğer

| Değişken | Zorunlu mu? | Secret mi? | Dev/Prod | Açıklama |
|---|---|---|---|---|
| `TIMEZONE` | Hayır (varsayılan `Europe/Istanbul`) | Hayır | İkisi de | bkz. [Timezone Politikası](#timezone-politikası) |

## Timezone Politikası

Uygulamanın iş (business) zaman dilimi `settings.timezone`'dur (varsayılan
`Europe/Istanbul`). Bu politika sistemin her yerinde tek bir sözleşmeye
dayanır:

- **Business tarihler** ("bugün", anomaly gün filtreleri, contribution bonus
  90 günlük pencere, vardiya günü, rapor dönemi, CLI job tarihleri) her zaman
  `settings.timezone` içinde çözülür. Merkezi kaynak
  `backend/app/core/clock.py`'dir: `clock.today_local()`, `clock.now_local()`.
- **Kalıcı timestamp'ler** (`created_at`, `detected_at`, `started_at`,
  `imported_at` gibi mutlak zaman damgaları) veritabanında her zaman UTC
  (`DateTime(timezone=True)`) olarak saklanır — `clock.now_utc()`.
- **Timestamp kolonları üzerindeki tarih filtreleri** (ör. anomaly
  `start_date`/`end_date`), kullanıcının verdiği yerel business tarihini önce
  yarı-açık bir yerel gün/dönem aralığına, sonra UTC'ye çevirir:
  `clock.local_day_bounds_utc(day)` / `clock.local_period_bounds_utc(start, end)`
  → `[start, end)`. `23:59:59.999999` gibi gün-sonu yaklaşımları veya sabit
  `+03:00` offset aritmetiği kullanılmaz — dönüşüm her zaman
  `zoneinfo.ZoneInfo(settings.timezone)` üzerinden yapılır, bu da tarihsel
  DST kurallarına (Türkiye 2016 öncesi) karşı doğru davranır.
- **`date` tipi kolonlar** (`performance_date`, `work_date`,
  `production_date`, `report_month` gibi business tarihler) zaten timezone'suz
  takvim günleridir; bunlar üzerinde ayrıca UTC dönüşümü yapılmaz — yalnızca
  o günü temsil eden `date` değeriyle karşılaştırılır.
- Sentetik veri üretimi (`app/services/synthetic/production_generator.py`,
  `anomaly_generator.py`), vardiya başlangıç/bitiş saatleri gibi yerel fabrika
  saatlerini önce `clock.local_datetime(day, time)` ile yerel aware bir
  datetime'a çevirir, sonra `clock.to_utc(...)` ile UTC'ye dönüştürür —
  yerel saate doğrudan `tzinfo=timezone.utc` etiketi yapıştırılmaz.

Yeni bir endpoint veya job eklerken: "bugün"/"bu ay"/"son N gün" gibi bir iş
kuralı yazıyorsanız `date.today()` / `datetime.now(timezone.utc).date()`
yerine `clock.today_local()` kullanın; bir timestamp kolonunu yerel bir
tarih aralığıyla filtreliyorsanız `clock.local_day_bounds_utc` /
`clock.local_period_bounds_utc` kullanın.

## Demo Girişi

Kullanıcı hesapları Red Hat SSO / Keycloak'ta yönetilir (bkz.
[Authentication Architecture](#authentication-architecture)); bu repo bir
demo kullanıcı adı/şifresi içermez veya oluşturmaz. Yerel bir Keycloak
instance'ınız yoksa `OIDC_ISSUER_URL`/`OIDC_CLIENT_ID` boş bırakılabilir —
uygulama açılır ama "SSO yapılandırması eksik" ekranını gösterir
(fail-closed; hiçbir koşulda otomatik bypass yoktur).

## Bilinen Sınırlamalar / Kapsam Dışı

- Gerçek SAP entegrasyonu yapılmamıştır. `SAPDataProvider`
  (`app/services/providers/sap_provider.py`) yapılandırılmadığında
  `SAPNotConfiguredError`, yapılandırılsa bile `NotImplementedError`
  fırlatan bir iskelettir.
- `custom_formula` KPI hesaplama türü yalnızca sabit bir `formula_type`
  dispatch tablosu (`_CUSTOM_FORMULA_DISPATCH`) üzerinden desteklenir —
  keyfi kod veya kullanıcı tanımlı string formül çalıştırma riski
  bilinçli olarak dışarıda bırakılmıştır; jenerik motor (`calculate_raw_score`)
  tanımadığı bir hesaplama türü için hâlâ hata fırlatır (bkz.
  [KPI Hesaplama Motoru](#kpi-hesaplama-motoru)).
- `alembic downgrade` desteği `6ad63dbc115b` migration'ında bilinçli olarak
  kırıktır (`NotImplementedError`) — bu migration geri alınamaz.
- Bildirim/uyarı sistemi ve ayrı bir "Dönem Karşılaştırma" rapor türü
  uygulanmamıştır; ilgili karşılaştırmaların büyük kısmı zaten
  dashboard, tesis/formen/KPI detay ekranları ve Raporlar'daki "Vardiya
  Karşılaştırma" raporunda mevcuttur.
- Otomatik CI/CD pipeline'ı tanımlı değildir — **Doğrulanmalı**: dağıtım
  öncesi test/build adımlarının hangi süreçle (manuel, harici CI) icra
  edileceği bu depo dışında netleştirilmelidir.
- **Tespitler modülü** (bkz. [Tespitler Modülü](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi))
  bilinçli olarak Aşama 1 + Aşama 2 kapsamındadır: tespitler sabit
  senaryolardan sentetik olarak üretilir (gerçek bir ML modeli
  eğitilmemiştir/kullanılmamıştır). Aşama 2'nin tool calling'i, LLM'nin
  backend'e **serbest/dinamik** bir sorgu atmasına izin vermez — yalnızca
  önceden tanımlanmış, salt-okunur, allowlist'teki 11 aracı çağırabilir; SQL
  üretemez, veritabanına yazamaz. Gelecekte sentetik veri sağlayıcılarının
  (`app/services/data_providers/synthetic.py`) gerçek Ocean/ML servisleriyle
  değiştirilmesi planlanmıştır — bkz. bir üstteki "Veri sağlayıcı katmanı"
  bölümü; araç adları, LLM şemaları ve frontend bileşenleri bu geçişten
  etkilenmeyecek şekilde tasarlanmıştır.
- Aşama 2'nin araç çağrı geçmişi (`anomaly_tool_calls`) prototip aşamasında
  hata ayıklama kolaylığı için her aracın **tam sonucunu** saklar (yalnızca
  sentetik operasyonel veri, gizli bilgi içermez). Gerçek bir üretime geçişte
  bu, veri minimizasyonu ilkesine uygun olarak özet/hash'e indirgenmelidir.
- Analiz durum modelindeki `cancelled` değeri şema/dokümantasyon
  tamlığı için tanımlıdır ancak arayüzde bir "analizi iptal et" eylemi
  henüz yoktur.
