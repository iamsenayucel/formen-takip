# 9. Uygulama Yol Haritası

**Tamamlanan ürün/altyapı kapsamı**

- **DONE:** Altı KPI (İnkita, OEE, GSF, Ağır Gitme, Plana Uyum, Iskarta),
  güncel ağırlıklar ve ağırlıklı geometrik performans skoru.
- **DONE:** Tier1 `{data, pagination}` / error envelope / camelCase JSON API
  contract migration'ı.
- **DONE:** Dashboard, tesis, formen, şef/grup, KPI ve yönetici özeti ekranları.
- **DONE:** V1/V2 overnight vardiya analizi, heatmap, drill-down ve formen
  comparison.
- **DONE:** Sentetik anomaly/Tespitler akışı, demo analiz ve allowlist tool
  calling.
- **DONE:** Operational Impact+, genel puan bonusu, genel export ve aylık
  formen raporu kodu.
- **DONE:** OIDC Authorization Code + PKCE, backend JWT/JWKS validation,
  production debug/CORS/bypass fail-closed baseline.
- **DONE:** Backend/frontend/scheduler Docker imajları, runtime frontend config,
  Caddy HTTPS/security headers ve health/readiness.
- **DONE:** Fine-grained backend RBAC ve endpoint permission enforcement —
  üç rol (`FOREMAN`/`SUPERVISOR`/`OPERATIONS_MANAGER`), sabit permission
  paketleri, ALL/FACTORY/PLANT veri kapsamı, fail-closed (atama yoksa 403),
  frontend `<Can>`/`ProtectedRoute` UI gate'i + backend-contract testi.
- **DONE:** Frontend Vitest birim/bileşen suite'i (25 dosya/259 test) ve
  repository içi CI (`.github/workflows/`: backend lint+full pytest, frontend
  lint+typecheck+test+build, gitleaks, pip-audit, CodeQL).
- **DONE:** Yapılandırılmış JSON log + request-id korelasyonu + gerçek
  client IP (trusted proxy middleware) ve configurable DB connection pool.

**Deployment'a bağlı tamamlanacak işler**

- **PLANNED:** Sentetik provider yerine gerçek SAP ve Ocean/ML entegrasyonları.
- **PLANNED:** Kurumsal Keycloak client/realm, production PostgreSQL,
  S3/CloudFront, SMTP, DNS/TLS ve secret management provizyonu/UAT'ı.
- **PLANNED:** Merkezi metrics/tracing/alerting (OpenTelemetry/Prometheus) ve
  operasyon runbook'u — mevcut olan yalnızca stdout JSON log'dur, merkezi bir
  gözlemlenebilirlik platformuna gönderim yoktur.
- **PLANNED:** Gerçek otomatik deploy (`deploy.yml` bilerek iskelet) ve
  GitHub branch protection'da required status check yapılandırması.
- **PLANNED:** Playwright kritik-yol smoke suite'inin CI'a bağlanması (bugün
  bilerek yerel/manuel çalıştırılıyor — bkz. [07-testing.md](07-testing.md)).
- **PLANNED:** pip-audit'in blocking hale getirilmesi (bugün 5 pakette 40
  bilinen CVE nedeniyle `continue-on-error`, non-blocking).
- **PLANNED:** Birden fazla scheduler instance gerekiyorsa dağıtık lock/claim
  mekanizması.

Roadmap, tamamlanmış OEE/Tier1/security/Docker/RBAC/CI çalışmalarını gelecek iş
gibi göstermez. Deployment'a bağlı entegrasyonlar kodda adapter/config
düzeyinde bulunsa bile gerçek kurumsal servis doğrulaması tamamlanmış sayılmaz.
