# Formen Performans Takip Sistemi — İş Analizi Raporu

| | |
|---|---|
| **Doküman türü** | Uçtan uca iş analizi / sistem analizi raporu |
| **Sistem** | Formen Performans Takip Sistemi (Faz 1 — çekirdek platform) |
| **Birincil hedef kitle** | Bilgi İşlem / IT birimi |
| **İkincil hedef kitle** | SAP/ERP ekibi, Üretim Yönetimi, Kalite, Bakım, İş Güvenliği, diğer süreç sahipleri |
| **Kaynak** | Depo kök dizinindeki backend/frontend kodu, veri modeli, servis katmanı ve `README.md` üzerinden statik analiz |
| **Kapsam notu** | Bu rapor mevcut kodun ne yaptığını belgeler; hiçbir yerde kodda karşılığı olmayan bir yetenek "mevcut" olarak sunulmamıştır. Planlanan ama uygulanmamış konular ayrı bir bölümde ("Yol Haritası") işaretlenmiştir. |

---

## 1. Yönetici Özeti

Formen Performans Takip Sistemi, Karaman'daki üretim tesislerinde görev yapan **formenlerin (vardiya amirlerinin)** KPI bazlı performansını **üst yönetime** sunan salt-okunur bir karar destek uygulamasıdır. Sistem; formen, şef (foreman'ların bağlı olduğu ilk kademe yönetici) ve tesis müdürlerini **kullanıcı olarak kapsamaz** — bu roller sistemde yalnızca birer *veri öznesi*dir, arayüze giriş yapmazlar. Tek kullanıcı kitlesi genel müdürlük/üst yönetim seviyesindeki karar vericilerdir.

Sistemin en kritik mimari kararı şudur: **performans verisi API yüzeyinin tamamına salt okunurdur.** Hiçbir ekran, formen/şef/tesis performans verisini oluşturmaz, güncellemez veya silmez. Veri yalnızca bir **ingestion (veri alım) pipeline'ı** üzerinden sisteme girer. Bugün bu pipeline'ın tek beslediği kaynak, üretim verisini istatistiksel olarak taklit eden bir **sentetik veri üreticisidir**; gelecekte gerçek SAP/ERP entegrasyonuyla değiştirilmesi mimari olarak öngörülmüş, ancak **henüz uygulanmamıştır** (bkz. Bölüm 10).

Sistem; 1 lokasyon (Karaman) → 2 fabrika (K1, K2) → 50 tesis → şef → formen hiyerarşisi üzerinde, 5 varsayılan KPI ile ~1000 personel ve (12 aylık varsayılan üretim döneminde) ~1,3 milyon performans kaydı ölçeğinde çalışacak şekilde tasarlanmıştır. KPI ağırlıklandırma, hedef çözümleme, veri kalitesi izleme, aksiyon planı takibi ve çok formatlı raporlama (CSV/XLSX/PDF) yetenekleri **uygulanmış ve test edilmiş** durumdadır (142 backend test fonksiyonu; ayrıca Playwright smoke testleri).

Bu raporun amacı, IT biriminin sistemi mimari/güvenlik/işletim açısından değerlendirmesini; ardından SAP/ERP ekibinin gerçek entegrasyon için gereken çalışmayı, üretim/kalite/bakım/iş güvenliği süreç sahiplerinin ise kendi alanlarına dokunan KPI'ları ve raporları doğrulayabilmesini sağlamaktır.

---

## 2. Amaç, Kapsam ve Hedef Kitle

### 2.1 Amaç

Karaman'daki formen performansının;
- standart, tartışmasız bir KPI formülüyle **objektif olarak** ölçülmesi,
- fabrika/tesis/şef/vardiya/formen kırılımında **karşılaştırılabilir** olması,
- veri eksikliği/hatası durumunda **güvenilirlik etiketiyle** şeffaf sunulması,
- düşük performans alanlarında **aksiyon planı** ile izlenebilir olması,
- düzenli **rapor** üretimiyle yönetim toplantılarına hazır hale getirilmesi

hedeflenmektedir.

### 2.2 Kapsam

**Kapsam dahilinde (Faz 1 — mevcut kod tabanında uygulanmış):**
- Organizasyon hiyerarşisi yönetimi (fabrika/tesis/şef/formen/vardiya)
- Sentetik veri üretimi + ingestion pipeline'ı (idempotent, veri kalitesi etiketli)
- 5 hesaplama türünü destekleyen KPI motoru ve kapsam bazlı hedef çözümleme
- Yönetim panosu, tesis/şef/formen detay ekranları, KPI analiz ekranı
- Aksiyon planı takibi (performans verisinden bağımsız)
- CSV/XLSX/PDF rapor üretimi ve indirme geçmişi
- Veri kalitesi ve entegrasyon durumu izleme ekranları
- JWT tabanlı kimlik doğrulama, hesap kilitleme, denetim kaydı (audit log)

**Kapsam dışında (bu depoda bilinçli olarak uygulanmamış — bkz. Bölüm 12):**
- Gerçek SAP/ERP bağlantısı (`SAPDataProvider` bir iskelettir)
- `custom_formula` KPI hesaplama türü (güvenlik nedeniyle bilinçli olarak engellenmiştir)
- Bildirim/uyarı (alerting) sistemi
- Otomatik CI/CD pipeline'ı
- Karaman dışında başka bir lokasyon (organizasyon yapısı kodda sabittir)

### 2.3 Hedef Kitle ve Bu Raporun Kullanımı

| Paydaş | Bu raporda öncelikli ilgi alanı |
|---|---|
| **IT / Bilgi İşlem** | Mimari, teknoloji yığını, dağıtım modeli, güvenlik, veritabanı şeması, test kapsamı, işletimsel kısıtlar (Bölüm 5, 6, 9, 11, 13) |
| **SAP/ERP Ekibi** | Sağlayıcı (provider) mimarisi, kod tabanlı eşleştirme, entegrasyon hazırlık/gap analizi (Bölüm 7, 10) |
| **Üretim Yönetimi** | Üretim gerçekleşme ve fire KPI'ları, tesis/vardiya karşılaştırması, formen sıralaması (Bölüm 8.3, 9.1) |
| **Kalite** | Kalite uygunluk KPI'sı, aralık bazlı hedef mantığı, veri kalitesi modülü (Bölüm 8.3, 9.6) |
| **Bakım** | Plansız duruş KPI'sı, orantısal ceza mantığı (Bölüm 8.3) |
| **İş Güvenliği** | İş güvenliği/süreç uyum puanı, doğrudan skor mantığı (Bölüm 8.3) |
| **Süreç Sahipleri (genel)** | Aksiyon planı süreci, raporlama, denetim izlenebilirliği (Bölüm 9.7, 9.8, 11) |

---

## 3. Mevcut Durum ve İş Problemi

Formen performansının değerlendirilmesi, KPI tanımının, hedefin ve hesaplama yönteminin sistemsel ve tutarlı olmasını gerektirir. Bu sistem olmadan tipik olarak karşılaşılan sorunlar:

- Tesisler/vardiyalar arasında farklı ölçüm yöntemleri kullanılması → karşılaştırılamazlık,
- Eksik/hatalı veri girişinin skor hesaplamasına sessizce karışması → yanıltıcı sonuçlar,
- Hedeflerin (tesis/şef/formen özelinde) nerede tanımlı olduğunun izlenememesi,
- Düşük performans tespit edilse dahi bunun bir aksiyona bağlanmaması,
- Yönetim raporlarının manuel, tekrarlanabilir olmayan şekilde hazırlanması.

Sistem bu sorunları; **tek bir toplam skor formülü** (Bölüm 8.2), **veri kalitesi durum makinesi** (Bölüm 9.6), **kapsam öncelikli hedef çözümleme** (Bölüm 8.4), **aksiyon planı modülü** (Bölüm 9.7) ve **standart rapor şablonları** (Bölüm 9.8) ile ele alır.

---

## 4. Organizasyonel Model

```
Karaman (tek lokasyon)
 └─ Fabrika  (K1 = 1–27. Tesisler · K2 = 28–50. Tesisler)
     └─ Tesis  (50 adet, "{n}. Tesis", benzersiz sequence_number 1–50)
         └─ Şef (Chief)
             └─ Formen (Foreman) — vardiya bazında (V1/V2/V3)
```

**İş kuralları (kodda sabit, parametrik değil):**

1. Bu hiyerarşi `backend/app/services/synthetic/reference_data.py` içindeki `FACTORY_SEED` sabitiyle tanımlıdır. Fabrika/tesis sayısı bir komut satırı parametresiyle değiştirilemez.
2. Tesisler **her zaman `sequence_number`'a göre sıralanmalıdır** — isme göre sıralama "10. Tesis"i "2. Tesis"ten önce gösterir (lexicographic hata). Bu kural hem backend sorgularında hem frontend listelerinde tutarlı uygulanmıştır.
3. `Foreman` tablosu organizasyon FK'sı taşımaz. Yerleşim tamamen `ForemanAssignment` tablosunda SCD2 (start_date/end_date) mantığıyla tutulur — bir formenin **şefi ve tesisi görev süresi boyunca sabittir**, yalnızca vardiyası dönem içinde değişebilir.
4. `(chief_id, plant_id) → chiefs(id, plant_id)` bileşik yabancı anahtar kısıtı, "bir şefin, kendi tesisi dışında bir formen'e atanması" durumunu **veritabanı seviyesinde imkânsız** kılar — bu, uygulama katmanında ayrıca doğrulanması gerekmeyen güçlü bir bütünlük garantisidir.
5. Personel kimlikleri (ad-soyad) 80×70 = 5600 kombinasyonluk havuzdan **yerine koymadan** örneklenir; ~1000 kişilik veri setinde iki kişi asla aynı adı taşımaz. Sicil numaraları tesisi kodlar ve sıfırla doldurulur (`SCL-29-004`, `SEF-29-01`) — bu, IT ve SAP ekipleri için doğal anahtar/kod eşleştirme tasarımının bir örneğidir (bkz. Bölüm 7).

---

## 5. Sistem Mimarisi

### 5.1 Teknoloji Yığını

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI 0.115 · SQLAlchemy 2.0 (Mapped/mapped_column) · Alembic · Pydantic v2 · Python 3.11 |
| Veritabanı | PostgreSQL 16 |
| Kimlik doğrulama | Red Hat SSO / Keycloak (OIDC, Authorization Code + PKCE) — bkz. §5.4 |
| Raporlama | openpyxl (XLSX), reportlab (PDF), stdlib csv |
| Frontend | React 19 · TypeScript · Vite 8 · TanStack Query v5 · React Router v7 · Tailwind CSS v4 · Recharts 3 |
| Dağıtım | Docker Compose: `postgres` + `backend` (Uvicorn) + `frontend` (statik build, Nginx) |

### 5.2 Dağıtım Topolojisi

```mermaid
flowchart LR
    subgraph Docker Compose
        FE["frontend (Nginx :80 → host :8080)"] -->|"/api/*"| BE["backend (Uvicorn :8000)"]
        BE -->|SQLAlchemy| PG[("postgres:16 (host :5433)")]
    end
    User["Üst yönetim kullanıcısı (tarayıcı)"] --> FE
```

**Önemli işletim kısıtı:** Servisler arasında bind mount yoktur — Docker imajları kaynağı **build anında** içine gömer. Bir dosya değişikliği, ilgili servis `--build` ile yeniden oluşturulmadan çalışan konteynerde hiçbir etki yaratmaz. IT/DevOps ekibinin dağıtım prosedürüne bu davranışı dahil etmesi gerekir.

### 5.3 Katmanlı Backend Mimarisi

```
app/api/v1/*      → HTTP uçları (FastAPI router'ları), yalnızca I/O ve yetkilendirme
app/schemas/*      → Pydantic/dataclass giriş-çıkış şemaları (ör. ortak Filters)
app/services/*     → İş mantığı (kpi_engine, analytics, target_resolver, ingestion, reporting, audit)
app/models/*       → SQLAlchemy ORM varlıkları (organizasyon, personel, KPI, performans, entegrasyon, aksiyon/rapor, kimlik)
app/services/providers/* → Dış veri kaynağı soyutlaması (SyntheticDataProvider, SAPDataProvider iskeleti)
```

Bu ayrım, iş mantığının (`kpi_engine.py`, `analytics.py`, `target_resolver.py`) HTTP katmanından bağımsız, saf fonksiyonlar halinde test edilebilir olmasını sağlar — nitekim bu üç modül unit test kapsamındadır (DB gerektirmez).

### 5.4 Güvenlik Modeli

- **Kimlik doğrulama:** Yerel kullanıcı adı/şifre veya backend tarafından üretilen bir JWT **yoktur**. Kimlik doğrulama otoritesi Red Hat SSO / Keycloak'tur (OIDC, Authorization Code + PKCE); backend yalnızca SSO'nun imzaladığı access token'ı JWKS/issuer/audience/expiry açısından doğrulayan bir kaynak sunucusudur (`app/core/oidc.py`, `app/api/deps.py::get_current_identity`). Eski yerel JWT (access+refresh)/bcrypt mekanizması ve `app/services/auth_service.py` kod tabanından kaldırılmıştır.
- **Hesap kilitleme:** Uygulanmaz — hesap yönetimi (parola politikası, başarısız giriş kilidi vb.) tamamen Red Hat SSO/Keycloak tarafında yürütülür.
- **Yetkilendirme modeli:** Tüm API uçları (health check hariç) doğrulanmış bir OIDC access token ister; rol bazlı yetkilendirme (RBAC) **uygulanmamıştır** — doğrulanmış her kullanıcı aynı yetki seviyesindedir (sistemin tek kullanıcı kitlesi zaten üst yönetimdir, foremen/şefler kullanıcı değildir).
- **Denetim izi:** Katkı çalışması CRUD, tespit durumu/analiz güncelleme, rapor oluşturma/indirme gibi eylemler `record_audit()` üzerinden tek noktadan `audit_logs` tablosuna yazılır; `subject` alanı OIDC token'ının stabil kimlik claim'idir (ad/e-posta değil, KVKK gereği DB'ye yazılmaz). Giriş/çıkış olayları artık uygulama içinde gerçekleşmediği için Red Hat SSO'nun kendi oturum kayıtlarında izlenir. Bu tabloyu görüntüleyen ayrı bir ekran yoktur.
- **CORS:** `CORS_ORIGINS` ayarıyla sınırlıdır (Compose'da `http://localhost:5173` ve `http://localhost:8080`).
- **Development-only bypass:** `ENVIRONMENT=development` + `AUTH_BYPASS=true` iken backend sabit bir demo kimlikle yanıt verir; `ENVIRONMENT=production` bunu ve eksik `OIDC_ISSUER_URL`/`OIDC_AUDIENCE`'ı fail-closed olarak reddeder (`app/core/config.py`).

**IT için doğrulanması gereken açık nokta:** RBAC olmaması, sistemin yalnızca "üst yönetim = tek güven seviyesi" varsayımıyla tasarlandığını gösterir. Genel müdürlük dışında farklı yetki seviyeleri (ör. sadece görüntüleme, bölge bazlı kısıtlama) ileride gerekirse bu, mevcut yetkilendirme modelinde bir mimari değişiklik gerektirir.

---

## 6. Veri Modeli

### 6.1 Varlık İlişki Diyagramı (özet)

```mermaid
erDiagram
    FACTORY ||--o{ PLANT : "1 fabrika - N tesis"
    PLANT ||--o{ CHIEF : "1 tesis - N şef"
    PLANT ||--o{ FOREMAN_ASSIGNMENT : "tesis ataması"
    CHIEF ||--o{ FOREMAN_ASSIGNMENT : "şef ataması"
    SHIFT ||--o{ FOREMAN_ASSIGNMENT : "vardiya ataması"
    FOREMAN ||--o{ FOREMAN_ASSIGNMENT : "1 formen - N atama (SCD2)"
    FOREMAN ||--o{ PERFORMANCE_RECORD : ""
    CHIEF ||--o{ PERFORMANCE_RECORD : ""
    PLANT ||--o{ PERFORMANCE_RECORD : ""
    SHIFT ||--o{ PERFORMANCE_RECORD : ""
    KPI ||--o{ PERFORMANCE_RECORD : ""
    KPI ||--o{ KPI_CALCULATION_RULE : "versiyonlu kural"
    KPI ||--o{ KPI_TARGET : "kapsam bazlı hedef"
    PERFORMANCE_RECORD ||--|| PERFORMANCE_SCORE : "1-1 skor"
    PERFORMANCE_RECORD }o--|| INTEGRATION_RUN : "hangi koşuda geldi"
    PERFORMANCE_RECORD ||--o{ DATA_QUALITY_ISSUE : ""
    USER ||--o{ ACTION_PLAN : "oluşturan"
    USER ||--o{ REPORT_EXPORT : "talep eden"
    USER ||--o{ AUDIT_LOG : ""
```

### 6.2 Tablo Grupları ve Veri Sözlüğü

**Organizasyon**

| Tablo | Amaç | Dikkat çeken alanlar |
|---|---|---|
| `factories` | K1/K2 fabrikaları | `code` (benzersiz), `location="Karaman"` |
| `plants` | 50 tesis | `sequence_number` (1–50, benzersiz, **sıralama anahtarı**), `sap_plant_code` (SAP eşleştirme alanı — bugün yalnızca sentetik `SAP-0029` biçiminde dolduruluyor) |
| `shifts` | V1 (08–16), V2 (16–00), V3 (00–08) | `crosses_midnight`, `sequence` |

**Personel**

| Tablo | Amaç | Dikkat çeken alanlar |
|---|---|---|
| `chiefs` | Tesis şefleri | `(id, plant_id)` bileşik benzersiz kısıt; `sap_personnel_number` |
| `foremen` | Formenler | Organizasyon FK'sı **yok**; `termination_date`/`is_active` |
| `foreman_assignments` | SCD2 yerleşim geçmişi | `(chief_id, plant_id)` bileşik FK ile şef/tesis tutarlılığı garantili |

**KPI**

| Tablo | Amaç | Dikkat çeken alanlar |
|---|---|---|
| `kpis` | KPI tanımı | `calculation_type`, `weight`, `min_valid_value`/`max_valid_value` (veri kalitesi sınırı), `min_score`/`max_score` (skor clip sınırı), `is_critical`, `display_order` |
| `kpi_calculation_rules` | Versiyonlu hesaplama parametreleri | `parameters` (JSON — ör. `lower_bound`/`upper_bound`/`tolerance`/`penalty_rate`), `version` |
| `kpi_targets` | Kapsam bazlı hedef | `scope_type` (FOREMAN/CHIEF/PLANT/COMPANY), `scope_id`, `valid_from`/`valid_to` |
| `performance_level_rules` | 5 kademeli performans seviyesi | `min_score`/`max_score`, `color`, `icon`, `sort_order` |

**Performans (salt okunur)**

| Tablo | Amaç | Dikkat çeken alanlar |
|---|---|---|
| `performance_records` | Ham gerçekleşen/hedef değer | İki benzersiz kısıt: `uq_perf_record_source` (kaynak idempotency) ve `uq_perf_record_natural_key` (foreman+kpi+chief+shift+tarih iş anahtarı); `data_quality_status` |
| `performance_scores` | Hesaplanmış skor | `raw_score` (clip öncesi), `capped_score`, `kpi_weight`, `weighted_contribution`, `calculation_version` |

**Entegrasyon**

| Tablo | Amaç |
|---|---|
| `integration_runs` | Her ingestion koşusunun durumu (RUNNING/SUCCESS/PARTIAL_SUCCESS/FAILED) ve sayaçları |
| `data_quality_issues` | Her sorunlu kaydın açıklaması, tipi, durumu |

**Aksiyon/Rapor/Kimlik**

| Tablo | Amaç |
|---|---|
| `action_plans` | Performans verisinden **bağımsız**, tamamen ayrı takip tablosu |
| `report_exports` | Üretilen rapor dosyası içeriği (`LargeBinary`), talep eden kullanıcı, filtre özeti |
| `users` / `audit_logs` | Kimlik doğrulama ve denetim izi |

### 6.3 Veri Hacmi

Varsayılan sentetik üretim: 12 aylık dönem × ~1000 formen × 5 KPI/gün ≈ **~1,3 milyon `performance_records` satırı**. Bu ölçek, PostgreSQL `shm_size`'ının Compose dosyasında bilinçli olarak 1 GB'a çıkarılmasını gerektirmiştir (varsayılan 64 MB, paralel sorgu worker'larında `DiskFull` hatasına yol açıyordu — host diskiyle ilgisi yok, tamamen Postgres'in paylaşımlı bellek segmenti sınırı).

---

## 7. Veri Akışı: Sağlayıcı → Ingestion → Skor

Bu, sistemin en kritik iş sürecidir ve SAP/ERP entegrasyonunun tam olarak nereye oturacağını tanımlar.

```mermaid
sequenceDiagram
    participant Kaynak as Veri Kaynağı (bugün: Sentetik / gelecek: SAP)
    participant Provider as PerformanceDataProvider.fetch()
    participant Ingestion as run_ingestion()
    participant Lookups as _Lookups (kod → FK çözümleme)
    participant Target as target_resolver
    participant Engine as kpi_engine
    participant DB as PostgreSQL

    Kaynak->>Provider: ham veri
    Provider->>Ingestion: RawPerformanceRecord (kodlarla: plant_code, chief_employee_number, shift_code, foreman_employee_number, kpi_code)
    Ingestion->>Lookups: kodları FK'lere çözer
    alt kod bulunamadı
        Ingestion->>Ingestion: errors += 1, kayıt atlanır
    end
    Ingestion->>Ingestion: veri kalitesi durumu belirlenir (COMPLETE/MISSING/INVALID)
    opt hedef değer kaynaktan gelmemiş
        Ingestion->>Target: resolve_target(FOREMAN>CHIEF>PLANT>COMPANY)
        Target-->>Ingestion: hedef değer veya NoTargetFoundError → NEEDS_SOURCE_CORRECTION
    end
    opt durum = COMPLETE
        Ingestion->>Engine: calculate_score(actual, target, rule)
        Engine-->>Ingestion: raw_score, capped_score
    end
    Ingestion->>DB: 1000'lik batch'ler halinde ON CONFLICT DO NOTHING ile toplu insert
    DB-->>Ingestion: eklenen kayıt ID'leri (RETURNING)
    Ingestion->>DB: atlanan/sorunlu kayıtlar için data_quality_issues yazılır
```

### 7.1 Neden Kod Bazlı Eşleştirme?

`RawPerformanceRecord`, dahili UUID'ler yerine **iş kodlarıyla** (`plant_code`, `chief_employee_number`, `shift_code`, `foreman_employee_number`, `kpi_code`) tanımlanır. Bu, `PerformanceDataProvider` arayüzünü uygulayan yeni bir sağlayıcının (ör. `SAPDataProvider`) hiçbir UUID bilgisine ihtiyaç duymadan, yalnızca SAP tarafındaki doğal kodları (tesis kodu, personel sicil no, vardiya kodu, KPI kodu) üretmesi yeterli olacak şekilde tasarlandığı anlamına gelir — **provider değişikliği, `ingestion.py`, `kpi_engine.py`, `analytics.py` veya API katmanında hiçbir değişiklik gerektirmez.**

### 7.2 Idempotency

İki benzersiz kısıt garantör:
- `uq_perf_record_source` (source_system, source_record_id) — aynı kaynak sisteminden aynı kayıt ID'siyle tekrar gelen veri.
- `uq_perf_record_natural_key` (foreman, kpi, chief, shift, performance_date) — iş anlamında aynı olay.

Çakışan satırlar `ON CONFLICT DO NOTHING ... RETURNING` ile sessizce atlanır ve `DUPLICATE` tipinde bir veri kalitesi kaydı oluşturulur. Bu tasarım, **aynı dönemin yanlışlıkla iki kez yüklenmesini zararsız (no-op) hale getirir** — SAP tarafında olası tekrar gönderimler (retry, replay) için ek bir de-duplikasyon mekanizması gerekmez.

### 7.3 Toplu İşlem Boyutu

`BATCH_SIZE = 1000` — psycopg'nin bir SQL ifadesi başına 65.535 bound parametre sınırı ve performans kayıtlarının ~20 kolon taşıması bu sabiti belirler (1000 × 20 = 20.000 < 65.535, güvenli marj). SAP entegrasyonunda kayıt şeması genişletilirse bu sabitin yeniden hesaplanması gerekir.

### 7.4 Manuel Yeniden Senkronizasyon

`POST /api/v1/integration/resync` ekranı (Entegrasyon Durumu sayfası) mevcut sağlayıcıyı belirtilen tarih aralığı için yeniden çalıştırır. **Bu, kullanıcının performans verisi girmesi anlamına gelmez** — yalnızca ingestion'ı yeniden tetikler. Aralık en fazla 31 gün (`MAX_RESYNC_DAYS`) ile sınırlıdır; zaten yüklenmiş bir dönem için no-op'tur (idempotency nedeniyle).

---

## 8. KPI Yönetimi ve Hesaplama Motoru

### 8.1 Hesaplama Türleri

`app/services/kpi_engine.py`, 5 hesaplama türünü uygular (6. tür olan `custom_formula`, keyfi kod çalıştırma riski nedeniyle **bilinçli olarak desteklenmez** — çağrıldığında hata fırlatır):

| Tür | Formül | Kullanım örneği (varsayılan seed) |
|---|---|---|
| `higher_is_better` | `(gerçekleşen / hedef) × 100`, min/max skora clip | Üretim Hedef Gerçekleşme Oranı |
| `lower_is_better` | `(hedef / gerçekleşen) × 100`, min/max skora clip | Fire Oranı |
| `range_target` | Aralık içindeyse taban skor (100); dışındaysa tolerans düşülmüş mesafe × ceza oranı kadar düşüş | Kalite Uygunluk Oranı |
| `direct_score` | Gerçekleşen değer doğrudan skor (clip'lenir) | İş Güvenliği ve Süreç Uyum Puanı |
| `proportional_penalty` | Hedefi aşan miktar başına birim ceza uygulanır | Plansız Duruş Süresi |

Her KPI için `min_score`/`max_score` (skor kırpma sınırları) ve `min_valid_value`/`max_valid_value` (veri kalitesi geçerlilik sınırları) **ayrı ayrı** tanımlıdır — bir değerin "geçersiz" (INVALID) sayılması ile "düşük skorlu" sayılması birbirinden bağımsız kavramlardır.

### 8.2 Toplam Skor Formülü

Her düzeyde (formen, şef, tesis, vardiya, şirket) **aynı formül** kullanılır:

```
Toplam Skor = SUM(weighted_contribution) / SUM(kpi_weight) × 100
```

Bu formülün iki önemli özelliği vardır:
1. **Otomatik yeniden normalize etme:** Bir KPI'nın verisi eksikse, mevcut KPI'ların ağırlıkları kendi aralarında yeniden ölçeklenir — toplam skor her zaman 0-120+ aralığında anlamlı kalır (KPI eksikliği yapay olarak skoru düşürmez veya yükseltmez).
2. **Güvenilirlik etiketi (`is_reliable`):** Kapsanan ağırlık toplamı, aktif KPI ağırlık toplamının `WEIGHT_TOLERANCE` (0.5 puan) altına düşerse satır **güvenilmez** olarak işaretlenir. Bu, "5 KPI'dan sadece 1'i girildi ama skor 100 çıktı" gibi yanıltıcı sonuçların şeffaf şekilde etiketlenmesini sağlar — **veri gizlenmez, ama okuyucuya uyarı verilir.**

### 8.3 Varsayılan KPI Seti (Faz 1 seed verisi)

| Kod | Ad | Tür | Ağırlık | İlgili süreç sahibi |
|---|---|---|---|---|
| `URETIM_GERCEKLESME` | Üretim Hedef Gerçekleşme Oranı | higher_is_better | 30 | Üretim Yönetimi |
| `FIRE_ORANI` | Fire Oranı | lower_is_better | 20 | Üretim Yönetimi / Kalite |
| `PLANSIZ_DURUS` | Plansız Duruş Süresi | proportional_penalty | 20 | Bakım |
| `KALITE_UYGUNLUK` | Kalite Uygunluk Oranı | range_target (95–100 arası hedef, %2 tolerans) | 20 | Kalite |
| `IS_GUVENLIGI` | İş Güvenliği ve Süreç Uyum Puanı | direct_score | 10 | İş Güvenliği |

Ağırlıklar toplamda **100** olacak şekilde doğrulanır (`validate_kpi_weights`) — seed verisi bu doğrulamayı geçmezse sistem hata fırlatır. **Bu 5 KPI, iş kuralı olarak sabit değildir** — `kpis`/`kpi_calculation_rules` tabloları üzerinden yeni KPI eklenebilir; ancak Faz 1'de bunu yapan bir yönetim ekranı (KPI CRUD arayüzü) **yoktur**, değişiklik doğrudan veritabanı/seed katmanında yapılır.

### 8.4 Hedef Çözümleme (Target Resolution)

`app/services/target_resolver.py` saf bir fonksiyondur; öncelik sırası:

```
FOREMAN > CHIEF > PLANT > COMPANY
```

Yani bir formen için özel bir hedef tanımlıysa o kullanılır; yoksa şefinin hedefi, o da yoksa tesisin, o da yoksa şirket genelinin hedefi kullanılır. **Önemli gerçek durum notu:** Seed verisi bugün **yalnızca COMPANY kapsamlı hedefler** üretir — dolayısıyla üretim/test ortamında tüm hedef çözümlemeleri pratikte COMPANY katmanına düşer. Daha dar kapsamlı hedefler (tesis/şef/formen özel hedefleri) **canlı bir yetenektir, canlı veri değildir** — yani kod bunu destekler ama bugünkü veri setinde kullanılmamaktadır. Hedefi kaynak veriden gelmeyen ve hiçbir kapsamda hedef bulunamayan kayıtlar `NEEDS_SOURCE_CORRECTION` durumuna düşer.

### 8.5 Performans Seviyeleri

| Seviye | Aralık | Renk |
|---|---|---|
| Kritik | 0 – 69.99 | Kırmızı |
| Geliştirilmeli | 70 – 79.99 | Turuncu |
| İyi | 80 – 89.99 | Sarı |
| Çok İyi | 90 – 99.99 | Mavi |
| Mükemmel | 100 – 120 | Yeşil |

Skorun 100'ü aşabilmesi (maksimum 120), hedefi aşan performansın ödüllendirilmesi tasarım kararıdır.

---

## 9. Fonksiyonel Kapsam (Ekran Bazlı)

| Ekran | Yol | Temel işlev |
|---|---|---|
| Giriş | `/login` | JWT ile kimlik doğrulama |
| **9.1 Yönetim Panosu** | `/` | Şirket geneli özet: ortalama skor, hedef üstü/altı formen sayısı, kritik/mükemmel sayısı, en iyi/kötü tesis-vardiya-formen, en zayıf KPI, eksik veri olan tesis sayısı, son senkronizasyon zamanı |
| **9.2 Tesisler** | `/plants`, `/plants/:id` | Tesis listesi + skor/seviye; tesis detayında KPI kırılımı, vardiya karşılaştırması, şef listesi, formen sıralaması |
| **9.3 Şef Grupları** | `/groups`, `/groups/:chiefId` | Şef bazlı ekip skorları (formen skorlarının ortalaması), şirket/tesis içi sıralama |
| **9.4 Formenler** | `/foremen`, `/foremen/:id` | Arama/sıralama/filtreleme destekli formen listesi; formen detayında KPI kırılımı, **hesaplama detayı** (ham/kırpılmış skor, kural parametreleri, ağırlık), trend grafiği, atama geçmişi |
| **9.5 KPI Analizi** | `/kpis` | KPI bazlı şirket ortalaması, en iyi/kötü 5 tesis, vardiya karşılaştırması, en iyi/kötü 5 formen, haftalık trend |
| **9.6 Veri Kalitesi** | `/data-quality` | Sorun tipine ve tesise göre kırılımlı veri kalitesi sorun listesi + özet |
| **9.7 Aksiyon Planları** | `/action-plans` | Performans verisinden bağımsız CRUD; öncelik (düşük/normal/yüksek/kritik), durum (açık/devam ediyor/beklemede/tamamlandı/iptal/gecikti), tamamlanma yüzdesi |
| **9.8 Raporlar** | `/reports` | 7 rapor türü × 3 format (CSV/XLSX/PDF), geçmiş liste + indirme |
| **9.9 Entegrasyon Durumu** | `/integration-status` | Ingestion koşu geçmişi + manuel resync tetikleme |
| **9.10 Denetim Kayıtları** | `/audit-log` | Tüm denetlenebilir eylemlerin listesi |

### 9.1 Filtreleme Modeli

Tüm ekranlarda ortak bir `Filters` nesnesi (`date_from`, `date_to`, `plant_ids`, `factory_ids`, `chief_ids`, `shift_ids`, `kpi_ids`) kullanılır; frontend'de bu durum URL query parametrelerinde tutulur (`useFilters.ts`) — yani **her filtrelenmiş görünüm paylaşılabilir bir bağlantıdır.** Filtre çubuğu sırası **Lokasyon (sabit "Karaman") → Fabrika → Tesis → Şef → Vardiya → KPI** şeklinde kademelidir: fabrika seçimi tesis/şef seçimini daraltır, tesis seçimi şef seçimini daraltır (`/meta/filters` ucu bu kademelemeyi sunar). Formen bazlı filtreleme **bilinçli olarak** global bir filtre değildir — formen seviyesine yalnızca Formenler listesinden "drill-down" ile inilir.

### 9.2 Raporlama

| Rapor Türü | İçerik |
|---|---|
| Şirket Genel Performans | Performans seviyesine göre formen sayısı ve ortalama puan |
| Tesis Karşılaştırma | Tesis bazlı toplam puan, güvenilirlik, kayıt sayısı |
| Vardiya Karşılaştırma | Vardiya bazlı toplam puan ve kayıt sayısı |
| Formen Performans | Tüm formenlerin puan/seviye/güvenilirlik listesi |
| KPI Analiz | KPI bazlı ortalama hedef/gerçekleşen/puan |
| Kritik Performans | Yalnızca "Kritik" seviyedeki formenler |
| Eksik Veri | Veri kalitesi sorunu olan kayıtların dökümü |

Raporlar CSV (UTF-8 BOM ile, Excel Türkçe karakter uyumu için), XLSX (openpyxl) veya PDF (reportlab, Türkçe karakter desteği için Vera font ailesi gömülü) olarak üretilir ve `report_exports` tablosunda ikili içerik olarak saklanır; her üretim/indirme denetim kaydına yazılır.

---

## 10. SAP/ERP Entegrasyon Hazırlığı ve Boşluk (Gap) Analizi

Bu bölüm özellikle **SAP/ERP ekibi** için hazırlanmıştır.

### 10.1 Mevcut Durum

`app/services/providers/sap_provider.py` içinde bir `SAPDataProvider` sınıfı **mevcuttur** ancak işlevsel değildir:

```python
class SAPDataProvider(PerformanceDataProvider):
    source_system = SourceSystem.SAP
    def fetch(self, date_from, date_to, plant_codes=None):
        if not self._base_url:
            raise SAPNotConfiguredError(...)
        raise NotImplementedError("SAP entegrasyonu henüz implement edilmedi.")
```

Yani bugün: (a) `SAP_BASE_URL`/`SAP_CLIENT_ID`/`SAP_CLIENT_SECRET` ortam değişkenleri tanımlıdır ama boştur, (b) yapılandırılmamışsa net bir hata (`SAPNotConfiguredError`) fırlatılır, (c) yapılandırılsa dahi gerçek çağrı mantığı **yazılmamıştır** (`NotImplementedError`). Bu, "entegrasyon var ama çalışmıyor" değil, **"entegrasyon noktası tanımlı ama içi boş"** demektir — kasıtlı ve dürüst bir iskelet.

Buna karşılık, entegrasyonu kolaylaştıracak şu alanlar **zaten veri modelinde mevcuttur**:
- `plants.sap_plant_code`
- `chiefs.sap_personnel_number`
- `foremen.sap_personnel_number`
- `SourceSystem.SAP` enum değeri (ingestion, `source_system` alanına zaten yazılabilir durumda)

### 10.2 SAP Entegrasyonu İçin Gerekli Çalışma (Yapılacaklar)

| Adım | Açıklama | Etki alanı |
|---|---|---|
| 1. Bağlantı protokolü seçimi | OData servisi / BAPI çağrısı / IDoc / SAP Integration Suite (CPI) — hangisi kullanılacağına SAP/ERP ekibi ve IT birlikte karar vermeli | `sap_provider.py` |
| 2. Kimlik doğrulama | OAuth2 client-credentials (mevcut `sap_client_id`/`sap_client_secret` alanları buna hazır görünüyor) ya da SAP kullanıcı/sertifika modeli | `config.py`, `sap_provider.py` |
| 3. Alan eşleştirme | SAP tarafındaki üretim/kalite/duruş/güvenlik verisinin `RawPerformanceRecord` alanlarına (plant_code, chief_employee_number, shift_code, foreman_employee_number, kpi_code, actual_value, unit, numerator/denominator) eşlenmesi | Yeni bir mapping katmanı |
| 4. Kod eşleştirme tablosu doğrulaması | `sap_plant_code`/`sap_personnel_number` alanlarının gerçek SAP master data ile birebir örtüştüğünün doğrulanması (bugünkü değerler sentetiktir: `SAP-0029`, `SAP-S-2901`) | Master data senkronizasyonu |
| 5. Hata/kısmi başarı stratejisi | `run_ingestion()` zaten kod bulunamayan kayıtları `errors` sayacına yazıp atlıyor — SAP tarafında sık karşılaşılacak senaryoların (yeni tesis, henüz eşlenmemiş personel) nasıl ele alınacağı netleşmeli | İşletimsel prosedür |
| 6. Zamanlama | Ingestion bugün manuel (`resync` ucu) veya CLI (`seed`) ile tetikleniyor; gerçek SAP entegrasyonunda periyodik/zamanlanmış çalıştırma (cron, SAP job, veya orkestrasyon aracı) gerekecek | Yeni bir zamanlayıcı bileşeni |
| 7. Hacim/performans testi | `BATCH_SIZE = 1000` varsayımı SAP veri hacmine göre yeniden değerlendirilmeli | `ingestion.py` |
| 8. Veri kalitesi eşiklerinin gözden geçirilmesi | `min_valid_value`/`max_valid_value` sınırları sentetik veri için ayarlanmıştır; gerçek SAP verisinin dağılımına göre yeniden kalibre edilmesi gerekir | `kpis` tablosu |

### 10.3 Mimari Güvence

`PerformanceDataProvider` soyutlaması sayesinde, yukarıdaki çalışma **yalnızca `sap_provider.py` içinde ve yeni bir mapping/config katmanında** yapılır — `ingestion.py`, `kpi_engine.py`, `analytics.py`, hiçbir API ucu veya frontend ekranı **değişmeden** SAP verisiyle çalışmaya devam eder. Bu, sistemin en güçlü mimari yatırımıdır ve entegrasyon riskini büyük ölçüde `sap_provider.py` dosyasına izole eder.

---

## 11. Veri Kalitesi Yönetimi

Veri kalitesi, sisteme "sonradan eklenmiş" bir modül değil, ingestion'ın **ayrılmaz parçasıdır.**

| Durum (`DataQualityStatus`) | Ne zaman oluşur |
|---|---|
| `complete` | Değer geçerli aralıkta ve hedef bulunabildi |
| `missing` | Kaynaktan gerçekleşen değer gelmedi (boş) |
| `invalid` | Gerçekleşen değer, KPI'nın `min_valid_value`/`max_valid_value` aralığı dışında |
| `duplicate` | Doğal anahtar (foreman+kpi+chief+shift+tarih) zaten işlenmiş bir kayıtla çakışıyor |
| `needs_source_correction` | Bu KPI/tarih/kapsam için geçerli hedef bulunamadı |
| `suspicious`, `pending_resync`, `reprocessed` | Enum'da tanımlı ama Faz 1 ingestion mantığında henüz üretilmiyor — ileri kullanım için ayrılmış |

Sadece `complete` durumundaki kayıtlar için skor hesaplanır (`performance_scores` tablosuna yazılır); diğerleri `data_quality_issues` tablosuna açıklamalı olarak kaydedilir ve `/data-quality` ekranından (tesis, tarih, sorun tipi filtreli) izlenebilir. `backfill-data-quality-issues` CLI komutu, geçmişte üretilmiş ama henüz issue kaydı oluşturulmamış satırlar için bu kayıtları geriye dönük tamamlar.

---

## 12. Kısıtlar, Varsayımlar ve Bilinçli Kapsam Dışılıklar

Bu bölüm, kodda ve `README.md`'de açıkça belirtilmiş sınırları listeler — bunlar "eksiklik" değil, **kayıtlı tasarım kararlarıdır**:

1. **Gerçek SAP entegrasyonu yoktur** — bkz. Bölüm 10.
2. **`custom_formula` KPI türü desteklenmez** — keyfi kod çalıştırma güvenlik riski nedeniyle bilinçli olarak engellenmiştir.
3. **`alembic downgrade` desteği kırıktır** (`6ad63dbc115b` migration'ında `NotImplementedError`) — Karaman restrukturasyon migration'ı **geri alınamaz**. IT bu migration'ı prod'a almadan önce tam yedek stratejisi belirlemelidir.
4. **Bildirim/uyarı (alerting) sistemi yoktur** — kritik performans tespiti sistem içinde görülebilir ama otomatik e-posta/SMS/push bildirimi tetiklenmez.
5. **Ayrı bir "Dönem Karşılaştırma" rapor türü yoktur** — ilgili karşılaştırmaların büyük kısmı dashboard, detay ekranları ve "Vardiya Karşılaştırma" raporunda zaten karşılanmaktadır.
6. **Otomatik CI/CD pipeline'ı tanımlı değildir** — testler manuel çalıştırılır. **Doğrulanmalı:** Dağıtım öncesi test/build adımlarının hangi süreçle (manuel, harici CI) icra edileceği bu depo dışında netleştirilmelidir.
7. **RBAC (rol bazlı yetkilendirme) yoktur** — tüm kullanıcılar eşit yetkiye sahiptir (bkz. Bölüm 5.4).
8. **KPI tanımı için yönetim arayüzü yoktur** — yeni KPI eklemek veritabanı/seed katmanında yapılır, ekrandan değil.
9. **Organizasyon yapısı (1 lokasyon, 2 fabrika, 50 tesis) kod seviyesinde sabittir** — yeni bir lokasyon/fabrika eklemek `FACTORY_SEED` sabitinin ve muhtemelen ilişkili migration'ların değiştirilmesini gerektirir.
10. **`README.md`'nin önceki bir sürümü** Türkçe bölge/il, `Department`, `ProductionLine` ve `--plants` bayrağına dayanan **eski bir modeli** tanımlıyordu; bu kavramlar Karaman restrukturasyonuyla tamamen kaldırılmıştır. Bu analiz yalnızca mevcut kodu yansıtır.

---

## 13. Test Kapsamı ve Kalite Güvencesi

| Katman | Kapsam |
|---|---|
| Unit testler (`tests/unit/`, DB gerektirmez) | `kpi_engine`, `target_resolver`, `shift_utils`, `turkish_sort`, `reporting_pdf` |
| Integration testler (`tests/integration/`, canlı seed'li Postgres gerektirir) | auth akışı, dashboard, tesis/formen, şefler, veri kalitesi, entegrasyon durumu, ingestion idempotency, aksiyon planları, denetim kayıtları, raporlar |
| Toplam | 142 test fonksiyonu (README'de belirtilen sayı) |
| Frontend | Playwright smoke script'leri (`frontend/scripts/*.mjs`): giriş, filtreleme, sıralama, PDF render, logo gibi senaryolar; ekran görüntüsü + konsol hatası yakalama |
| CI/CD | **Tanımlı değil** — bkz. Bölüm 12, madde 6 |

Integration testlerin gerçek DB'ye bağlanması (mock veritabanı değil), test/prod paritesini artıran bilinçli bir tercih olarak değerlendirilebilir; ancak bu, testlerin **her zaman migrasyonu yapılmış ve seed edilmiş bir ortam gerektirdiği** anlamına gelir — CI'a taşınırsa pipeline'ın bu ön koşulu sağlaması gerekir.

---

## 14. Riskler ve Öneriler

| # | Risk | Etki | Öneri |
|---|---|---|---|
| R1 | `JWT_SECRET_KEY` varsayımı üretime taşınırsa değiştirilmeden kalabilir | Yüksek — token sahteciliği | Dağıtım kontrol listesine (checklist) zorunlu madde olarak eklenmeli |
| R2 | RBAC olmaması, ileride farklı yetki seviyesi ihtiyacı doğduğunda mimari değişiklik gerektirir | Orta | İhtiyaç netleşirse erken planlanmalı; retrofit maliyeti yüksektir |
| R3 | `alembic downgrade` kırık olduğu için Karaman migration'ı sonrası geri dönüş yoktur | Yüksek (geri dönülemez veri kaybı riski) | Prod migration öncesi tam DB yedeği zorunlu tutulmalı |
| R4 | SAP entegrasyonu olmadan sistem yalnızca sentetik veriyle "demo" niteliğindedir | Yüksek (iş değeri gerçek veri olmadan sınırlı) | Bölüm 10'daki adımlar için SAP/ERP ekibiyle erken çalışma başlatılmalı |
| R5 | Bildirim sistemi yokluğunda kritik performans, kullanıcı sisteme giriş yapmadıkça fark edilmeyebilir | Orta | Faz 2 kapsamına alınabilir (bkz. Bölüm 15) |
| R6 | Docker imajlarının bind-mount içermemesi, geliştirme sürecinde "değişiklik etkisiz" yanılgısına yol açabilir | Düşük (operasyonel sürtünme) | Dağıtım/geliştirme dokümantasyonunda vurgulanmalı (zaten `README.md`'de var) |
| R7 | CI/CD tanımlı değil — manuel test disiplinine bağımlılık | Orta | Prod'a geçiş öncesi en azından backend unit testlerini çalıştıran minimal bir pipeline önerilir |

---

## 15. Yol Haritası Önerileri (Faz 2+)

Aşağıdakiler **mevcut kodda uygulanmamıştır**; yalnızca bu analizin doğal uzantısı olarak öneridir:

1. Gerçek SAP/ERP entegrasyonunun uçtan uca hayata geçirilmesi (Bölüm 10.2).
2. Kritik performans / veri kalitesi eşiği aşıldığında otomatik bildirim (e-posta) mekanizması.
3. KPI tanımı, ağırlık ve hedef yönetimi için bir yönetim ekranı (bugün yalnızca veritabanı/seed seviyesinde mümkün).
4. Rol bazlı yetkilendirme, farklı üst yönetim kademeleri arasında görüntüleme kapsamını ayırmak gerekirse.
5. Otomatik CI/CD pipeline'ı (test + build + dağıtım).
6. Tesis/şef/formen özelinde hedef tanımlarının operasyonel olarak kullanılmaya başlanması (kod zaten destekliyor, veri henüz yok).

---

## 16. Sözlük

| Terim | Açıklama |
|---|---|
| Formen | Vardiya amiri; performansı izlenen temel personel birimi |
| Şef (Chief) | Formenlerin bağlı olduğu, tesis bazlı ilk kademe yönetici |
| Tesis (Plant) | Fabrika altında, `sequence_number` ile sıralı 50 üretim birimi |
| Fabrika (Factory) | K1/K2 — tesislerin gruplandığı üst birim |
| KPI | Anahtar performans göstergesi; hesaplama türü, ağırlık ve hedefle tanımlı |
| Ağırlıklı Katkı (weighted_contribution) | `capped_score × (kpi_weight / 100)` |
| Güvenilirlik (`is_reliable`) | Kapsanan KPI ağırlığının aktif toplam ağırlığa yeterince yakın olup olmadığını gösteren etiket |
| İngestion | Ham verinin sağlayıcıdan okunup FK'lere çözülerek, skorlanarak veritabanına yazıldığı süreç |
| Idempotency | Aynı verinin birden fazla kez işlenmesinin veri tekrarına yol açmaması |
| SCD2 | Slowly Changing Dimension Type 2 — `start_date`/`end_date` ile geçmişi koruyan veri modeli deseni |
| Veri Kalitesi Durumu | Bir performans kaydının işlenebilirlik/geçerlilik durumu (complete, missing, invalid, vb.) |

---

## Ek A — API Uç Noktaları Özeti

Tüm uçlar `/api/v1` altında, JWT bearer token ile korunur (`/auth/*` hariç). OpenAPI dokümantasyonu: `http://localhost:8000/docs`.

| Router | Uçlar |
|---|---|
| `auth` | `POST /login`, `POST /refresh`, `POST /logout`, `GET /me` |
| `meta` | `GET /filters` |
| `dashboard` | `GET /summary`, `/trend`, `/kpi-summary`, `/plant-ranking`, `/shift-comparison`, `/foreman-ranking`, `/performance-distribution` |
| `plants` | `GET /plants`, `/{id}`, `/{id}/summary`, `/{id}/kpis`, `/{id}/shifts`, `/{id}/chiefs`, `/{id}/foremen` |
| `chiefs` | `GET /chiefs`, `/{id}`, `/{id}/foremen`, `/{id}/kpis`, `/{id}/trend` |
| `foremen` | `GET /foremen`, `/{id}`, `/{id}/kpis`, `/{id}/kpis/{kpi_id}/calculation-detail`, `/{id}/trend`, `/{id}/assignment-history` |
| `kpis` | `GET /kpis`, `/{id}`, `/{id}/analysis` |
| `data_quality` | `GET /issues`, `/summary` |
| `integration` | `GET /runs`, `/runs/{id}`, `POST /resync` |
| `action_plans` | `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}` |
| `reports` | `POST /generate`, `GET /`, `GET /{id}/download` |
| `audit_logs` | `GET /` |

## Ek B — Ortam Değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` | `formen`/`formen`/`formen_takip` | Compose Postgres servisi |
| `DATABASE_URL` | `postgresql+psycopg://formen:formen@localhost:5433/formen_takip` | Compose'da `postgres:5432` olarak override edilir |
| `JWT_SECRET_KEY` | `change-me-in-production` | **Production'da mutlaka değiştirilmeli** |
| `ACCESS_TOKEN_EXPIRE_MINUTES`/`REFRESH_TOKEN_EXPIRE_DAYS` | 30 / 7 | JWT ömürleri |
| `MAX_FAILED_LOGIN_ATTEMPTS`/`ACCOUNT_LOCKOUT_MINUTES` | 5 / 15 | Hesap kilitleme eşiği/süresi |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Compose'da `["http://localhost:5173","http://localhost:8080"]` |
| `SAP_BASE_URL`/`SAP_CLIENT_ID`/`SAP_CLIENT_SECRET` | boş | `SAPDataProvider` için yer tutucu — bugün kullanılmıyor |

## Ek C — Alembic Migration Geçmişi

1. `afa71ec04497` — ilk şema
2. `ef3f90d743f8` — aksiyon planları ve rapor export tabloları
3. `6ad63dbc115b` — Karaman fabrika/şef hiyerarşisi restrukturasyonu (**yıkıcı, geri alınamaz**: organizasyon ve performans verisini `TRUNCATE` eder)
4. `55082513f1be` — audit log `ip_address` alanını string'e çevirir

---

*Bu rapor, `formen-takip` deposundaki kod tabanının statik incelemesine dayanılarak hazırlanmıştır (backend/app, frontend/src, alembic/versions, README.md, docker-compose.yml). Kodda karşılığı bulunmayan hiçbir yetenek "mevcut" olarak sunulmamıştır; planlanan ama uygulanmamış konular Bölüm 12 ve 15'te açıkça işaretlenmiştir.*
