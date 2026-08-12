# Test Stratejisi

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
  (`financial_gain_status`, `estimated_amount`/`verified_amount`, `currency`,
  doğrulayan departman, doğrulama tarihi/notu).
- `contribution_work_foremen` — bir çalışmaya katkı veren formenleri
  `ContributionRole` (`LEAD` / `CONTRIBUTOR`) ile ilişkilendiren çoka-çok
  tablo; tek formenli çalışmalar migration `f2a4b8e6c9d1` ile otomatik
  `LEAD` olarak işaretlenmiştir.
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
| Aksiyon Planları | `/action-plans` |
| Katkılar / Detay | `/improvement-works`, `/improvement-works/:workId` |
| Tespitler / Tespit Detayı | `/anomalies`, `/anomalies/:anomalyId` |
| Raporlar | `/reports` |
| Veri Kalitesi | `/data-quality` |
| Entegrasyon Durumu | `/integration-status` |
| Denetim Kayıtları | `/audit-log` |

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
dosyalar Nginx ile sunulur ve `/api/` istekleri `nginx.conf` üzerinden
`http://backend:8000/api/`'ye proxy'lenir.

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

## Kurulum (Docker)

Gereksinim: Docker + Docker Compose.

```bash
cp .env.example .env
docker compose up --build -d
```

- Frontend: http://localhost:8080
- Backend / OpenAPI: http://localhost:8000/docs
- PostgreSQL (host'tan erişim): `localhost:5433`

Şema `alembic upgrade head` ile otomatik oluşur ancak **sentetik veri ve
demo kullanıcı otomatik seed edilmez** (kasıtlı tasarım: üst yönetim
kullanıcıları arayüzden veri giremediği gibi, demo verisi de yalnızca
geliştirici tarafından kontrollü parametrelerle üretilir). Konteynerler
ayaktayken:

```bash
docker compose exec backend python -m app.cli create-admin \
  --email genel.mudur@formen-demo.com --password "Demo!2026" --full-name "Demo Genel Müdür"
docker compose exec backend python -m app.cli seed --seed 42
```

> **Sıra önemli:** `seed`'in katkı/iyileştirme çalışması örnek verisi
> üretme adımı (`[4/5]`), çalıştığı anda **en az bir kullanıcı** olmasını
> gerektirir — yoksa bu adımı sessizce atlar (hata vermez). `create-admin`'i
> `seed`'den önce çalıştırmazsanız, örnek katkı verisini daha sonra ayrıca
> `docker compose exec backend python -m app.cli seed-contributions`
> ile üretebilirsiniz.

`seed` sırasıyla şunları yapar: `[1/3]` referans veri (organizasyon +
KPI hedefleri), `[2/3]` sentetik üretim verisi
(`production_records` — bkz. [Üretim Verisi Katmanı](#üretim-verisi-katmanı)),
`[3/3]` bu üretim verisinden KPI türetme + ingestion, ardından (admin
varsa) katkı çalışması örnekleri ve son olarak Tespitler modülü için
sentetik ML tespitleri (`seed-anomalies`). Varsayılan olarak son 12 ay için
~50–75K performans kaydı üretir (`docker compose exec backend python -m app.cli seed`
çıktısındaki `[3/3]` satırı `başarılı` sayısı) — birkaç dakika sürebilir,
arka planda çalıştırın. Bu, ham üretim kaydı sayısından belirgin düşüktür:
`performance_records`'ın doğal anahtarı (`foreman_id`, `kpi_id`, `chief_id`,
`shift_id`, `performance_date`) `plant_id` içermez, bu yüzden bir formenin
aynı gün sorumlu olduğu 2-4 tesisin ürettiği KPI kayıtlarından yalnızca
ilki eklenir, geri kalanı `DUPLICATE` olarak atlanır (bkz.
[Veri Akışı](#veri-akışı-sağlayıcı--ingestion--skor)). Yalnızca boş bir
veritabanında (veya `--force` ile) çalışır ve mevcut referans veriyi
üzerine yazmaz. Sıfırdan yeniden üretmek için önce ilgili tabloları
temizleyin:

```bash
docker compose exec -T postgres psql -U formen -d formen_takip -c \
  "TRUNCATE factories, plants, chiefs, foremen, kpi_targets, integration_runs, shifts, kpis, performance_level_rules, products, company_calendar CASCADE;"
```

Sentetik veri üretici parametreleri (`app/cli.py`):

```bash
docker compose exec backend python -m app.cli seed \
  --seed 42 \
  --min-foremen 8 --max-foremen 25 \
  --start-date 2025-07-27 --end-date 2026-07-27 \
  --missing-rate 0.02 --error-rate 0.01 --anomaly-rate 0.015 --duplicate-rate 0.005 \
  --force
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
```

`apply-scoring-model-v2`, var olan performans verisini KPI'a özel yeni
puanlama formülleriyle yeniden hesaplar (AGIR_GITME'nin işaretli
türetimini düzeltir, İNKITA için geriye dönük ingestion çalıştırır ve
tüm `performance_scores`'u aktif kurallarla yeniden puanlar) — bkz.
[KPI Hesaplama Motoru](#kpi-hesaplama-motoru).

Servis bazlı yeniden build ve log inceleme:

```bash
docker compose up --build -d backend
docker compose logs backend --tail 50
```

> **Önemli:** İmajlar kaynağı build anında gömer, bind mount yoktur. Bir
> dosyayı düzenlemek, ilgili servisi `--build` ile yeniden oluşturmadan
> çalışan konteynerde hiçbir etki yaratmaz.

## Yerel Geliştirme (Docker'sız)

### Backend

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env   # DATABASE_URL Compose'un host portu 5433'ü hedefler;
                       # farklı bir yerel Postgres kullanıyorsanız düzenleyin
alembic upgrade head
python -m app.cli seed --seed 42
python -m app.cli create-admin --email genel.mudur@formen-demo.com --password "Demo!2026" --full-name "Demo Genel Müdür"
uvicorn app.main:app --reload
```

`backend/.env.example`'daki `DATABASE_URL`, Compose'un Postgres'i host'a
map'lediği **5433** portunu kullanır; `app/core/config.py`'deki varsayılan
5432, host'tan doğrudan çalıştırıldığında işe yaramaz. `backend/.env`
`.gitignore` ile hariç tutulur — her geliştirici kendi kopyasını
`.env.example`'dan türetir.

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
.venv/Scripts/python.exe -m pytest -q                      # tüm paket (365 test fonksiyonu)
.venv/Scripts/python.exe -m pytest tests/unit -q            # yalnızca unit (DB gerekmez)
.venv/Scripts/python.exe -m pytest tests/integration/test_reports.py -q
.venv/Scripts/python.exe -m pytest tests/unit/test_kpi_engine.py::TestX::test_y -q
```

- **Unit testler** (`tests/unit/`) DB gerektirmez: `test_kpi_engine.py`,
  `test_target_resolver.py`, `test_shift_utils.py`, `test_turkish_sort.py`,
  `test_reporting_pdf.py`, `test_production_kpi_derivation.py`,
  `test_contribution_calc.py`, `test_anomaly_demo_fallback.py`,
  `test_anomaly_analysis_schema.py`, `test_anomaly_orchestrator_helpers.py`.
- **Integration testler** (`tests/integration/`) **çalışan, migrasyonu
  yapılmış ve seed edilmiş** bir Postgres bekler — gerçek DB'ye
  `SessionLocal()` üzerinden bağlanır, ayrı bir şema fixture'ı yoktur:
  `test_auth_flow.py`, `test_dashboard.py`, `test_plants_foremen.py`,
  `test_chiefs.py`, `test_data_quality.py`, `test_integration_status.py`,
  `test_ingestion_idempotency.py`, `test_action_plans.py`,
  `test_audit_logs.py`, `test_reports.py`, `test_contribution_works.py`,
  `test_anomalies.py`, `test_anomaly_analysis_service.py`,
  `test_anomaly_generator.py`, `test_world.py`, `test_tools.py`,
  `test_anomaly_orchestrator.py` (Tespitler'e ait olanlar için önce
  `seed-anomalies` çalıştırılmış olmalıdır).

`pytest.ini`, `testpaths = tests` ve `pythonpath = .` tanımlar; ek yapılandırma
gerekmez. Otomatik CI pipeline'ı (GitHub Actions vb.) bu depoda **tanımlı
değildir** — testler manuel çalıştırılır.