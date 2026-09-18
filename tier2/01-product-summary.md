# CORVUS Ürün Özeti

CORVUS; Karaman lokasyonundaki K1/K2 fabrikaları ve 50 tesis için tesis, şef/grup,
formen ve vardiya performansını izleyen üst yönetim karar destek uygulamasıdır.
Mevcut geliştirme/test veri seti tamamen sentetiktir; gerçek SAP/Ocean/ML kaynakları
henüz bağlı değildir.

Ürün; Genel Bakış, tesis/formen/şef detayları, KPI analizi, performans liderleri,
vardiya analizi, Tespitler, Operational Impact+ ve genel/aylık raporlama modüllerini
içerir. Resmî KPI seti altı adettir: İnkita, OEE, GSF, Ağır Gitme, Plana Uyum ve
Iskarta. Üretim ve KPI kayıtları API üzerinden salt okunur; sınırlı mutasyonlar
katkı çalışması, anomali analizi/durumu ve rapor üretimiyle ilgilidir.

Frontend React/Vite, backend FastAPI/SQLAlchemy/PostgreSQL, edge katmanı Caddy,
statik sunum Nginx ve periyodik işler tek-instance cron scheduler ile çalışır.
Kimlik doğrulama OIDC Authorization Code + PKCE ve backend JWT doğrulamasıyla
sağlanır. Fine-grained backend RBAC uygulanmıştır: üç rol (`FOREMAN`,
`SUPERVISOR`, `OPERATIONS_MANAGER`), sabit permission paketleri ve
ALL/FACTORY/PLANT veri kapsamı — bkz. [Güvenlik ve Uyum](06-security.md).

## Kurulum (Docker)

Gereksinim: Docker ve Docker Compose.

Yerel Keycloak ve aynı-host PostgreSQL içeren geliştirme kurulumu:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.dev.yml up --build -d
docker compose exec backend python -m app.cli seed --seed 42
```

- Frontend: `http://localhost:8080`
- Backend/OpenAPI: `http://localhost:8000/docs`
- PostgreSQL host portu: `localhost:5433`

Backend başlangıcında `alembic upgrade head` otomatik çalışır. Sentetik seed
otomatik çalışmaz ve yalnızca migration uygulanmış, referans verisi bulunmayan
boş veritabanında kabul edilir. Veriyi yeniden üretmek için veritabanı tamamen
sıfırlanır, migration yeniden uygulanır ve seed tekrar çalıştırılır; kısmi
tablo temizliği veya seed guard bypass akışı yoktur.

Seed; organizasyon/KPI referanslarını, ham üretim kayıtlarını, türetilmiş
performans kayıtlarını, örnek Operational Impact+ çalışmalarını ve sentetik
anomalileri üretir. Desteklenen ana parametreler:

```bash
docker compose exec backend python -m app.cli seed \
  --seed 42 \
  --min-plants-per-foreman 2 \
  --max-plants-per-foreman 4 \
  --start-date 2025-08-19 \
  --end-date 2026-08-19
```

Production dağıtımı `docker-compose.yml` ile `docker-compose.prod.yml`
overlay'ini kullanır; aynı-host DB gerekiyorsa `docker-compose.db.yml` ayrıca
eklenir. Production edge için `SITE_DOMAIN`, OIDC ve deployment'a bağlı
storage/SMTP ayarları `.env` üzerinden sağlanır.

## Yerel Geliştirme

### Backend

```bash
cd backend
python -m venv .venv
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.cli seed --seed 42
uvicorn app.main:app --reload
```

Windows PowerShell'de sanal ortam `.venv\Scripts\Activate.ps1` ile
etkinleştirilebilir. `backend/.env.example`, Docker dışı backend ayarlarının
şablonudur.

### Frontend

```bash
cd frontend
npm install
npm run dev
npm run lint
npx tsc -b
npm run build
npm audit
```

Vite `:5173` üzerinde çalışır ve `/api` isteklerini yerel backend `:8000`
adresine proxy'ler. Production imajı aynı build'i non-root Nginx ile `:8080`
üzerinde sunar; backend upstream ve OIDC değerleri container başlangıcında
runtime config olarak üretilir.

## Ortam Değişkenleri

Kök `.env.example` Compose, `backend/.env.example` Docker dışı backend
çalıştırması içindir. Gerçek `.env` dosyaları Git'e alınmaz.

| Grup | Temel değişkenler | Davranış |
|---|---|---|
| Veritabanı | `DATABASE_URL`, `POSTGRES_*` | PostgreSQL bağlantısı; production'da gerçek bağlantı deployment tarafından verilir |
| Çalışma modu | `ENVIRONMENT`, `APP_DEBUG`, `AUTH_BYPASS` | Production debug ve auth bypass fail-closed davranır |
| OIDC | `OIDC_ISSUER_URL`, `OIDC_AUDIENCE`, `OIDC_CLIENT_ID`, redirect/scope ayarları | Production issuer/audience olmadan backend başlamaz |
| HTTP | `CORS_ORIGINS`, `SITE_DOMAIN`, bind/upstream ayarları | Production wildcard CORS reddedilir; Caddy HTTPS edge'dir |
| Zaman | `TIMEZONE`, `SCHEDULER_TZ` | Varsayılan `Europe/Istanbul` |
| Anomali analizi | `LLM_*` | Kapalıysa deterministik demo analizi; anahtar yalnız backend'dedir |
| Aylık rapor | `REPORT_STORAGE_PROVIDER`, `REPORTS_S3_BUCKET`, `CLOUDFRONT_*` | Local development veya private S3; eksik production storage kullanım anında fail-closed |
| E-posta | `SMTP_ENABLED`, `SMTP_*` | İsteğe bağlı aylık rapor teslimi |

Tam liste için `backend/app/core/config.py`, Compose aktarımı için
`docker-compose.yml` source of truth'tur.

## Demo Girişi

Yerel `docker-compose.dev.yml` Keycloak realm'i:

- Kullanıcı: `dev-user`
- Parola: `DevPass123!`

Alternatif demo bypass yalnızca `ENVIRONMENT=development` ortamında backend
`AUTH_BYPASS=true` ve frontend `VITE_AUTH_BYPASS=true` birlikte ayarlanarak
kullanılır. Production bu yapılandırmayı reddeder.

## Sınırlamalar

- Gerçek SAP ve Ocean/ML veri sağlayıcıları bağlı değildir; development/test
  verisi sentetiktir.
- Gerçek Keycloak, SMTP, S3/CloudFront, DNS/TLS ve production PostgreSQL
  provizyonu repository dışında deployment/UAT sırasında doğrulanmalıdır.
- Fine-grained backend RBAC ve endpoint permission enforcement uygulanmıştır
  (üç rol, sabit permission paketi, ALL/FACTORY/PLANT veri kapsamı) — bkz.
  [Güvenlik ve Uyum](06-security.md). Rapor indirme sahiplik değil yalnızca
  veri kapsamı ile korunur; kapsam içindeki bir raporu, onu oluşturmamış
  başka bir kapsam-eşleşen kullanıcı da indirebilir — bilinçli bir
  basitleştirmedir.
- Frontend lint/typecheck/build/audit adımlarına ek olarak Vitest birim/
  bileşen test suite'i (`npm run test`) ve ayrı, CI'a bağlı olmayan bir
  Playwright kritik-yol smoke suite'i (`frontend/scripts/smoke/`) vardır.
- Scheduler tek instance çalıştırılmalıdır; dağıtık scheduler lock'u yoktur.
- `.github/workflows/` altında backend/frontend lint+test CI'ı ve statik
  güvenlik taraması (gitleaks, pip-audit, CodeQL) vardır; PR merge'ini
  yalnızca GitHub branch protection'da required check seçilirse bloklar.
  Gerçek otomatik **deploy** yoktur (`deploy.yml` bilerek iskelet). Merkezi
  metrics/tracing/alerting (OpenTelemetry/Prometheus) uygulanmamıştır;
  mevcut olan yapılandırılmış JSON stdout log + request-id korelasyonudur.
- Sentetik Tespitler üreticisi bugün OEE dışındaki beş üretim KPI'sı için
  senaryo üretir; OEE resmî performans KPI setine ve skorlamaya dahildir.
