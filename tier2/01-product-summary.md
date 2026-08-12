# Ürün Özeti

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

## Yerel Geliştirme

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

## Ortam Değişkenleri

Kök dizindeki `.env.example`, Docker Compose için referans şablondur
(`cp .env.example .env`). `backend/.env.example` ise yerelden (Docker'sız)
çalıştırma için şablondur (`cp backend/.env.example backend/.env`) —
`DATABASE_URL` doğrudan Compose'un host'a map'lediği `5433` portunu hedefler.
Her iki gerçek `.env` dosyası da `.gitignore` ile hariç tutulur; yalnızca
`.example` şablonları repoya dahildir.

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `formen` / `formen` / `formen_takip` | Compose Postgres servisi |
| `DATABASE_URL` | `postgresql+psycopg://formen:formen@localhost:5432/formen_takip` | Backend DB bağlantısı — Compose bunu `postgres:5432` olarak override eder |
| `JWT_SECRET_KEY` | `change-me-in-production` | **Production'da mutlaka değiştirilmeli** |
| `JWT_ALGORITHM` | `HS256` | pydantic-settings alanı, env ile override edilebilir |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | 30 / 7 | JWT ömürleri |
| `MAX_FAILED_LOGIN_ATTEMPTS` / `ACCOUNT_LOCKOUT_MINUTES` | 5 / 15 | Hesap kilitleme eşiği ve süresi |
| `TIMEZONE` | `Europe/Istanbul` | Zaman dilimi |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Compose'da `["http://localhost:5173","http://localhost:8080"]` olarak set edilir |
| `SAP_BASE_URL` / `SAP_CLIENT_ID` / `SAP_CLIENT_SECRET` | boş | `SAPDataProvider` için yer tutucu — bugün kullanılmıyor |
| `LLM_ENABLED` | `false` | `true` olmadıkça Tespitler modülü her zaman demo analiz döndürür |
| `LLM_API_KEY` | boş | LLM sağlayıcısı API anahtarı — yalnızca backend'de okunur, asla frontend'e gönderilmez |
| `LLM_MODEL` | `gpt-4o-mini` | Kullanılacak model adı |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | OpenAI uyumlu `chat/completions` uç noktası |
| `LLM_TIMEOUT_SECONDS` | `30` | LLM isteği zaman aşımı süresi |
| `LLM_ANALYSIS_MODE` | `single_context` | Varsayılan analiz modu — `single_context` \| `tool_calling` |
| `LLM_TOOL_CALLING_ENABLED` | `true` | `false` ise `tool_calling` isteği bile `single_context`'e döner |
| `LLM_DEMO_TOOL_CALLING_ENABLED` | `true` | API anahtarı yokken `tool_calling` modunun demo akışının çalışıp çalışmayacağı |
| `LLM_MAX_TOOL_CALLS` | `10` | Bir analizde izin verilen azami araç çağrısı sayısı |
| `LLM_MAX_ANALYSIS_STEPS` | `12` | Azami LLM tur (round-trip) sayısı |
| `LLM_TOOL_TIMEOUT_SECONDS` | `10` | Tek bir araç çağrısı için azami süre |
| `LLM_ANALYSIS_TIMEOUT_SECONDS` | `60` | Tüm analiz için azami toplam süre |
| `LLM_MAX_DATE_RANGE_DAYS` | `365` | Araçlara verilebilecek azami tarih aralığı |

Ayarların tam listesi ve varsayılanlar için `backend/app/core/config.py`
(pydantic-settings `Settings` sınıfı) doğrudan referans alınmalıdır.

## Demo Girişi

- E-posta: `genel.mudur@formen-demo.com`
- Parola: `Demo!2026`

(Yalnızca `create-admin` komutu çalıştırıldıktan sonra geçerlidir; veritabanında
otomatik oluşturulmaz.)

## Sınırlamalar

- **Gerçek SAP entegrasyonu** yapılmamıştır. `SAPDataProvider`
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
  eğitilmemiştir/kullanılmamıştır), gerçek SAP/Ocean bağlantısı yoktur, RAG
  veya vektör veri tabanı kullanılmaz. Aşama 2'nin tool calling'i, LLM'nin
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
  **henüz yoktur** — hiçbir kod yolu bu durumu şu an için ayarlamaz.