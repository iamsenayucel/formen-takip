# Test Stratejisi

Backend doğrulamasının ana gate'i:

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q
```

Güncel doğrulanmış sonuç:

```text
1063 passed
31 skipped
0 failed
```

Test paketi `backend/tests/unit` ve `backend/tests/integration` altında
toplanır. Unit kapsamı ağırlıklı olarak DB'sizdir; integration kapsamı
Testcontainers ile geçici PostgreSQL başlatır, migration zincirini uygular ve
deterministik sentetik fixture üretir. Integration suite uygulamanın
`DATABASE_URL` değerine veya kalıcı geliştirici DB'sine fallback yapmaz.

Ana kapsamlar:

| Kategori | Doğrulama |
|---|---|
| Unit | KPI formülleri, target/rule, contribution, schema validation, OIDC config, rate limit, storage/e-posta, clock/shift |
| Integration | API endpointleri, repository/service akışı, gerçek PostgreSQL constraintleri ve migration |
| API contract | `{data, pagination}`, camelCase JSON, ortak error envelope, cursor ve request ID |
| DB integrity | FK, unique, exclusion, date range, assignment slot/overlap ve domain checkleri |
| OEE | 720 dakika shift, 1440 dakika plant-day, period pay/payda ve 0–105 scoring |
| Authentication | PKCE config, JWKS/JWT signature, issuer/audience/exp/iat, bypass fail-closed |
| Timezone/shift | V1/V2, overnight shift, haftalık rotasyon ve Europe/Istanbul sınırları |
| Parity | DB → repository → service → API ve provider/world eşitliği |
| Seed guard | Seed'in dolu DB'yi mutasyonsuz reddetmesi |
| Regression | N+1 query snapshot, dashboard, anomaly, reports ve concurrency |

## Operational Impact+ (Katkılar)

Unit testleri süre/kazanç hesaplarını, publish validation'ı, 1–5 sistem
puanını ve son 90 gün bonusunu doğrular. Integration testleri CRUD, çok
formen/çok tesis ilişkisi, DB check constraintleri, PDF, audit atomicity ve
dashboard/formen/rapor kanalları arasındaki genel puan tutarlılığını kapsar.

```text
genel puan = min(operasyonel puan + katkı bonusu, 120)
```

## Frontend

Frontend için repository'de bulunan otomatik komutlar:

```bash
cd frontend
npm run lint
npx tsc -b
npm run build
npm audit
```

Lint, TypeScript validation, Vite production build ve dependency audit
mevcuttur. `package.json` içinde bağımsız `npm test`, Vitest/Jest component
suite'i veya CI'a bağlı Playwright runner'ı yoktur.

`frontend/scripts/smoke_test_*.mjs` dosyaları ad-hoc manuel betiklerdir.
Developer-specific absolute path içeren untracked olanlar portable hale
getirilmeden resmî test tooling'i veya production staging girdisi sayılmaz.

## Veritabanı Şeması

Integration bootstrap:

1. İzole PostgreSQL container'ı başlatır.
2. Test DB güvenlik guard'ını doğrular.
3. Tek Alembic head'e migration uygular.
4. Sabit dönem ve seed ile sentetik dünyayı üretir.
5. Testlerden sonra geçici kaynakları kaldırır.

Bu nedenle full integration suite için çalışan Docker daemon gerekir.
Constraint testleri SQLite benzetimi yerine gerçek PostgreSQL üzerinde
unique, FK, GiST exclusion, trigger ve check ihlallerini dener.

## Kurulum (Docker)

Production-benzeri manuel gate:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml build --no-cache backend frontend scheduler
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.prod.yml --profile scheduler up -d
```

Kontrol listesi:

```text
GET /health       → 200
GET /health/live  → 200
GET /health/ready → 200 ve database reachable
GET /             → 200
korumalı API      → token yoksa 401
```

Production ve development overlay'leri aynı Compose çağrısında birleştirilmez.
Gerçek domain yoksa Caddy config doğrulaması için `SITE_DOMAIN=localhost`
kullanılabilir.

## Yerel Geliştirme (Docker'sız)

### Backend

```bash
cd backend
python -m venv .venv
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.cli seed --seed 42
uvicorn app.main:app --reload
```

Unit-only koşu Docker gerektirmez:

```bash
.venv/Scripts/python.exe -m pytest tests/unit -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite development sunucusu `/api` isteklerini `127.0.0.1:8000` backend'ine
proxy'ler.

## Testler

Önerilen teslim sırası:

```text
alembic heads
→ fresh DB migration
→ synthetic seed
→ DB integrity
→ full pytest
→ frontend lint
→ TypeScript
→ production build
→ npm audit
→ Docker build/startup
→ health/readiness/proxy smoke
```

Repository içinde otomatik GitHub Actions, GitLab CI veya eşdeğer pipeline
tanımı yoktur. Bu gate'lerin manuel mi yoksa kurumsal harici CI ile mi
enforce edileceği IT teslim sürecinde belirlenmelidir.
