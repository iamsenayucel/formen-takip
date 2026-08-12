# Katalog — Backend

> Genel kural/statü tanımları `tier1/APPROVED-STACKS.md`'de. Bu dosya yalnızca backend
> katmanının (framework, ORM, migration, **yetkilendirme/authorization**, build/paket
> aracı, async görev kuyruğu, MQTT/IoT) onaylı satırlarını taşır.
>
> **Kimlik doğrulama (authentication) burada değil** — `tier0/RULES.md` §12 gereği Zorunlu
> ve merkezi (Red Hat SSO), bkz. `tier1/catalog/cross-cutting.md` +
> `tier1/playbooks/playbook-authentication.md`. Bu dosyadaki "Yetkilendirme (Authorization)" satırları
> yalnızca SSO tarafından doğrulanmış bir kimlik üzerine **izin kontrolünü** tanımlar.

| Kategori | Seçenek | Statü | Playbook / Referans | Not |
|---|---|---|---|---|
| Backend framework | NestJS 11.x (+ Fastify), Node.js 24.x LTS | Referans | `tier1/playbooks/playbook-backend-nestjs.md` | Prod'da doğrulanmış audit/güvenlik pattern'leri mevcut; minor/patch projenin kendi lockfile'ında (bkz. `tier1/APPROVED-STACKS.md` "Versiyon Stratejisi") |
| Backend framework | Spring Boot 3.x (Java 21) | Onaylı | `tier1/playbooks/playbook-backend-java-spring-boot.md` | Kanıtlanmış üretim izi (kurum içi e-ticaret uygulaması); bkz. `tier0/adr/0002-...` |
| Backend framework | Quarkus (Java 21) | Onaylı | `tier1/playbooks/playbook-backend-java-quarkus.md` (TBD, henüz doldurulmadı) | Düşük ayak izi/hızlı açılış — Kubernetes'te optimize edilen yükler için; Red Hat SSO'nun kendisi de Java 21+Quarkus'a geçti; bkz. `tier0/adr/0002-...` |
| Backend framework | FastAPI (Python 3.14.x) | Referans | `tier1/playbooks/playbook-backend-python-fastapi.md` | AI/LLM orkestrasyon işlerine özellikle uygun; bkz. `tier0/adr/0003-...` |
| ORM / veri erişimi | Prisma 7.x | Referans | `tier1/playbooks/playbook-backend-nestjs.md` | NestJS ile birlikte; migration de aynı araçla |
| ORM / veri erişimi | Spring Data JPA + Hibernate | Onaylı | `tier1/playbooks/playbook-backend-java-spring-boot.md` | Spring Boot ile birlikte |
| ORM / veri erişimi | Hibernate ORM with Panache | Onaylı | `tier1/playbooks/playbook-backend-java-quarkus.md` (TBD) | Quarkus ile birlikte — Quarkus'un deyimsel (idiomatic) ORM kalıbı |
| ORM / veri erişimi | SQLAlchemy 2.0 (async) | Onaylı | `tier1/playbooks/playbook-backend-python-fastapi.md` | FastAPI ile birlikte — yalnız DB erişimi gereken servislerde |
| Migration aracı | Flyway | Onaylı | — | Hem Spring Boot hem Quarkus ile birlikte kullanılır (her ikisinin de Flyway uzantısı var) |
| Migration aracı | Alembic | Onaylı | `tier1/playbooks/playbook-backend-python-fastapi.md` | SQLAlchemy ile birlikte |
| Yetkilendirme (Authorization) | NestJS izin decorator'ı/guard'ı + RBAC/ABAC resolver | Referans | `tier1/playbooks/playbook-backend-nestjs.md` | Kimlik doğrulama burada değil — bkz. `tier1/catalog/cross-cutting.md` "Kimlik doğrulama" |
| Yetkilendirme (Authorization) | Spring Security method security (`@PreAuthorize`) + custom `PermissionEvaluator` | Onaylı | `tier1/playbooks/playbook-backend-java-spring-boot.md` | Spring Boot ile birlikte |
| Yetkilendirme (Authorization) | Quarkus Security izin/rol kontrolü | Onaylı | `tier1/playbooks/playbook-backend-java-quarkus.md` (TBD) | Quarkus ile birlikte |
| Yetkilendirme (Authorization) | FastAPI `Depends()` tabanlı izin kontrolü | Onaylı | `tier1/playbooks/playbook-backend-python-fastapi.md` | FastAPI ile birlikte |
| Build aracı (Java) | Gradle *veya* Maven | Onaylı | — | Hem Spring Boot hem Quarkus için — proje bazında ekip tecrübesine göre Faz 2'de karara bağlanır |
| Paket yönetimi (Python) | uv | Onaylı | — | pip'ten 10-100x, Poetry'den ~10x hızlı; Python sürüm yönetimini de üstlenir |
| Async görev kuyruğu | Celery (SQS broker) | Onaylı | — | Kurumun mevcut AWS SQS altyapısıyla (bkz. `tier1/catalog/cross-cutting.md`) uyumlu; bkz. `tier0/adr/0003-...` |
| Async görev kuyruğu | boto3 + doğrudan SQS tüketici | Onaylı | — | Framework'süz, küçük ölçekli işler için Celery'nin operasyonel yükü gerekmeyebilir |
| MQTT / IoT | aiomqtt | Onaylı | `tier1/playbooks/playbook-backend-python-fastapi.md` | paho-mqtt motoru + modern async arayüz, 2026 standardı |

## Aynı kategoride birden fazla onaylı seçenek varsa

**Backend framework (Spring Boot vs Quarkus, bkz. `tier0/adr/0002-...`):** Kataloğun kendisi
burada bir kazanan seçmiyor; agent Faz 2'de şu bağlamı sorup ona göre öneri yapmalı:
deployment hedefi Kubernetes mi ve hızlı-açılış/düşük-ayak-izi öncelikli mi (→ Quarkus'a
işaret eder), kurumsal Red Hat SSO/Keycloak kullanılacak mı (→ Quarkus'un native
`quarkus-oidc` entegrasyonu avantaj), ekibin hangisinde daha güçlü tecrübesi var (→ mevcut
kurum-içi Spring uygulaması varsa Spring bilinirliği yüksek olabilir). Bu üç sorunun cevabı
çelişirse (örn. ekip Spring biliyor ama proje Kubernetes'te hızlı-açılış gerektiriyor),
agent kendi başına seçmez — çelişkiyi yüzeye çıkarır (`skills/design-flow-agent/SPEC.md`
§2.5).

> ✅ **Çözülmüş tutarlılık notu:** Bu satır önceden Quarkus'un Kubernetes avantajının infra
> tarafında karşılıksız kaldığını flag'liyordu — `tier1/catalog/infra.md`'ye EKS eklendi
> (`tier0/adr/0007-...`), bu tutarsızlık artık kapalı. Quarkus + EKS kombinasyonu şimdi
> gerçek bir infra karşılığına sahip.

**Async görev kuyruğu (Celery+SQS vs boto3-direct, bkz. `tier0/adr/0003-...`):** Kurumun
mevcut AWS SQS altyapısı zaten var — soru sadece "Celery'nin ek soyutlaması gerekli mi,
yoksa iş basitse doğrudan boto3 tüketici döngüsü yeterli mi?" Agent, işin retry/scheduling/
çoklu-worker gibi ihtiyaçları olup olmadığını sorar; varsa Celery, yoksa boto3-direct önerir.

## Değerlendirilip şimdilik eklenmeyen seçenekler

- **arq** (async görev kuyruğu) — FastAPI'nin async event loop'una en doğal uyan, LLM
  çağrıları için özellikle önerilen bir kütüphane, ama **yalnızca Redis backend
  destekliyor.** Kurumun mevcut kuyruk altyapısı AWS SQS olduğu için değerlendirmeden
  elendi — kataloğa hiç eklenmedi (bkz. `tier0/adr/0003-...`). Kurumda ayrıca Redis
  altyapısı kurulursa yeniden değerlendirilebilir.
