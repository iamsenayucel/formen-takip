# Tier 2 — CORVUS Proje Dokümantasyonu

Bu klasör CORVUS'un Git'e teslim anındaki current-state ürün ve teknik
dokümantasyon paketidir. Kod, migration, route ve deployment config source of
truth'tur; Tier2 belgeleri bunların okunabilir proje envanteridir.

Önerilen okuma sırası `01` → `12` şeklindedir.

## CoE Proje Dokümantasyon Seti

| # | Belge | İçerik |
|---|---|---|
| 1 | [Ürün Özeti](01-product-summary.md) | CORVUS amacı, kapsamı, kurulum ve sınırlar |
| 2 | [Domain Modeli](02-domain-model.md) | Organizasyon, assignment, KPI, katkı, anomaly ve rapor ilişkileri |
| 3 | [Veri Şeması](03-data-schema.md) | Güncel Alembic head, tablolar, constraintler, veri akışı ve altı KPI |
| 4 | [API Kataloğu](04-api-catalog.md) | Aktif endpointler, filtre/pagination, auth ve error contract |
| 5 | [Ekran Kataloğu](05-screen-catalog.md) | React route'ları, ekranlar ve frontend runtime davranışı |
| 6 | [Güvenlik ve Uyum](06-security.md) | OIDC/PKCE/JWT, production fail-closed baseline ve rol/scope tabanlı RBAC |
| 7 | [Test Stratejisi](07-testing.md) | Backend/frontend test yapısı ve doğrulama gate'leri |
| 8 | [Geliştirme ve Operasyon İş Akışı](08-workflow.md) | Geliştirme, deployment, scheduler ve incident yaklaşımı |
| 9 | [Uygulama Yol Haritası](09-roadmap.md) | Tamamlanan yetenekler ve doğrulanmış gelecek işler |
| 10 | [Domain Süreçleri](10-domain-process.md) | Ingestion, skor, Operational Impact+ ve aylık rapor akışları |
| 11 | [Kabul Testi Planı](11-uat-plan.md) | Business/IT UAT personaları ve senaryoları |
| 12 | [Mimari Karar İndeksi](12-adr-index.md) | Repository'de bulunan gerçek ADR'lerin indeksi |

Tier0 kuralları için [tier0/RULES.md](../tier0/RULES.md), proje playbook'ları
için [Tier1 klasörü](../tier1/) kullanılır. Tier1 kural/kısıtı, Tier2 ise bu
kuralların CORVUS repository'sindeki güncel uygulama envanterini açıklar.

## Bu klasörü nasıl kullanacaksınız

- Product/KPI değişikliği: `01`, `03`, `07`, `10`, `11`.
- Model/migration/constraint değişikliği: `02`, `03`.
- Endpoint/schema değişikliği: `04`.
- Frontend route/ekran değişikliği: `05`.
- OIDC/security/deployment değişikliği: `06`, `08`, `11`.
- Test altyapısı veya sonuç baseline'ı değişikliği: `07`.
- Planlanan iş tamamlandığında veya ertelendiğinde: `09`.
- Gerçek ADR eklendiğinde: `12`.

Belgelerde repository-relative Markdown link kullanılır. Developer bilgisayarına
özel absolute path, geçici yerel çıktı yolu, local IDE URI veya tarihsel audit
başarısızlığı current-state bilgi olarak tutulmaz.
