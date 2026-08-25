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

**Deployment'a bağlı tamamlanacak işler**

- **PLANNED / DEFERRED:** Fine-grained backend RBAC ve endpoint permission
  enforcement. Değerlendirilecek roller: `reader`, `report-operator`,
  `contribution-editor`, `anomaly-analyst`, `admin`.
- **PLANNED:** Sentetik provider yerine gerçek SAP ve Ocean/ML entegrasyonları.
- **PLANNED:** Kurumsal Keycloak client/realm, production PostgreSQL,
  S3/CloudFront, SMTP, DNS/TLS ve secret management provizyonu/UAT'ı.
- **PLANNED:** Merkezi logging/metrics/tracing/alerting ve operasyon runbook'u.
- **PLANNED:** Frontend component/E2E otomasyonu ve repository içi CI/CD gate'i.
- **PLANNED:** Birden fazla scheduler instance gerekiyorsa dağıtık lock/claim
  mekanizması.

Roadmap, tamamlanmış OEE/Tier1/security/Docker çalışmalarını gelecek iş gibi
göstermez. Deployment'a bağlı entegrasyonlar kodda adapter/config düzeyinde
bulunsa bile gerçek kurumsal servis doğrulaması tamamlanmış sayılmaz.
