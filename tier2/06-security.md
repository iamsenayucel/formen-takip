# 6. Güvenlik ve Uyum Uygulama Notu

## Kimlik Doğrulama (Authentication) — "Kullanıcı kim?"

CORVUS kimlik otoritesi Red Hat SSO/Keycloak uyumlu OIDC sağlayıcısıdır.

Frontend:

- Authorization Code + PKCE kullanır; implicit flow yoktur.
- `oidc-client-ts` ve `react-oidc-context` token yaşam döngüsünü yönetir.
- Session state `sessionStorage` içindedir; automatic silent renew aktiftir.
- Issuer/client ID eksikse uygulama fail-closed config ekranı gösterir.
- Runtime OIDC ayarları production image'ına gömülmez, container başlangıcında
  `/config.js` içine render edilir.

Backend:

- Kendi kullanıcı/parola sistemi veya JWT üretimi yoktur; OIDC resource
  server olarak bearer access token doğrular.
- Discovery/JWKS üzerinden anahtar alınır ve `kid` rotasyonunda cache
  yenilenir.
- JWT signature, issuer, audience, expiration (`exp`) ve issued-at (`iat`)
  doğrulanır.
- Eksik/geçersiz/süresi dolmuş token standart `UNAUTHORIZED` envelope'u ile
  `401` döndürür.
- Yerel `users` tablosu yoktur. Audit ve mutasyon kayıtları yalnız stabil OIDC
  subject claim'ini (`sub` varsayılanı) saklar.

Development bypass iki tarafta ayrıca açılır. Backend `AUTH_BYPASS=true`
değerini yalnız tam olarak `ENVIRONMENT=development` için kabul eder;
production veya diğer ortamlar başlangıçta reddedilir.

Production config fail-closed kuralları:

- `OIDC_ISSUER_URL` ve `OIDC_AUDIENCE` zorunludur.
- `DEBUG=true` reddedilir.
- `CORS_ORIGINS` içinde `*` reddedilir.
- `AUTH_BYPASS=true` reddedilir.

## Yetkilendirme (Authorization) — "Bu kullanıcı bu aksiyonu yapabilir mi?"

Authentication ile authorization ayrı katmanlardır: `get_current_identity`
yalnızca kimlik doğrular, `app/api/authz_deps.py::get_auth_context` ve
`require_permission(...)` ayrı bir yetkilendirme katmanı uygular. Backend
fine-grained RBAC **uygulanmıştır** (deferred değildir):

```text
User (OIDC subject)
  → Role        FOREMAN / SUPERVISOR / OPERATIONS_MANAGER (app/models/enums.py::Role)
  → Permission  atomik izin, ör. "reports.download" (app/core/permissions.py::Permission)
  → Scope       ALL / FACTORY / PLANT (app/models/enums.py::ScopeType)
```

Rol ve scope, JWT claim'i değil **subject-keyed DB tabloları**dır:
`user_role_assignments` (subject → rol) ve `user_scope_assignments`
(subject → bir/daha fazla scope satırı) — migration `3dd3d7f35759`. Bu
tablolar PII içermez, yalnızca OIDC `subject` string'ini taşır. Rol/scope her
request'te DB'den okunur; bir rol geri alındığında eski bir JWT'nin hâlâ eski
yetkiyi taşıması riski yoktur.

`ROLE_PERMISSIONS` (`app/core/permissions.py`) her rolü açık bir permission
kümesi olarak tanımlar (inheritance zinciri yok):

| Permission | Formen | Şef | Operasyon Yöneticisi |
|---|:-:|:-:|:-:|
| `overview.view` | ✅ | ✅ | ✅ |
| `performance.view` | ✅ | ✅ | ✅ |
| `operational_intelligence.view` | ❌ | ✅ | ✅ |
| `operational_impact.contribute` | ❌ | ✅ | ✅ |
| `outputs.view` | ❌ | ❌ | ✅ |
| `reports.create` | ❌ | ❌ | ✅ |
| `reports.download` | ❌ | ❌ | ✅ |

Rol/scope ataması **olmayan** bir subject tüm korumalı endpoint'lerden `403`
alır (fail-closed) — `GET /auth/me` istisnadır, yetkisiz kullanıcı için de
`role: null, permissions: []` döner ki frontend tek bir kaynaktan "erişimin
yok" durumunu render edebilsin; bu endpoint veri erişimi vermez.

Veri kapsamı (scope) permission'dan ayrı bir eksendir: `FACTORY` scope'u
request başına üye tesislere genişletilir. Liste/filtre uçlarında
(`Depends(scoped_filters)`) istenen id'ler scope ile sessizce kesiştirilir
(kesişim boşsa sonuç boş döner); tekil kaynağa ID ile erişimde
(`assert_plant_in_scope` vb.) kapsam dışıysa **403** döner.

Rol/scope ataması yalnızca CLI üzerinden yapılır (REST admin endpoint'i
yoktur): `app.cli assign-role <subject> <ROL> --scope-type ...` /
`revoke-role`. Tüm state-değiştiren endpoint'ler (`POST`/`PATCH`/`DELETE` —
`anomalies.analyze`/`reanalyze`/`status`, `contribution-works` CRUD,
`reports.generate`) bir `require_permission(...)` dependency'si taşır.

**Bilinen basitleştirme:** rapor indirme sahiplik (creator-only) değil,
yalnızca veri kapsamı ile korunur — kapsamı raporun filtreleriyle örtüşen
herhangi bir kullanıcı, raporu kendisi oluşturmamış olsa bile indirebilir
(`report_service.py::download_report`). Rapor *listesi* kapsamı kısıtlı
kullanıcılar için kendi oluşturduklarıyla sınırlıdır, ama bu ayrı bir
davranıştır ve indirmeye uygulanmaz. İş gereksinimi gerçek creator-only
indirme ise bu ayrı bir değişikliktir.

Katkı domain'indeki `LEAD`/`CONTRIBUTOR` değerleri kullanıcı RBAC rolü değil,
çalışmadaki formen sorumluluğudur — RBAC `Role` enum'uyla karıştırılmaz.

Mutasyonların OIDC subject ve request ID ile `audit_logs` tablosuna yazılması
ek izlenebilirlik sağlar; `permission.denied` (yalnızca POST/PATCH/DELETE
red'lerinde), `role.assigned`/`role.revoked`, `scope.assigned`/`scope.revoked`
olayları da aynı tabloya yazılır.

**Test kapsamı notu:** no-role kullanıcı, üç rol için erişim matrisi, scope
daraltma/IDOR-403, Operational Impact contribute ve rapor create/download
permission ayrımı entegrasyon testleriyle kapsanır
(`backend/tests/integration/test_authorization.py`,
`test_scope_enforcement.py`). Tespitler'in `POST /anomalies/{id}/analyze`,
`/reanalyze` ve `PATCH /status` uçları için **yetkisiz rolde 403 döndüğünü
doğrulayan ayrı bir entegrasyon testi yoktur** — aynı permission dependency'si
yalnızca ilgili `GET` uçları ve birim testleri üzerinden dolaylı doğrulanır;
bu bir test-kapsam boşluğudur, implementasyon boşluğu değil.

## API ve Entegrasyon Güvenliği

- CORS yalnız açıkça tanımlı origin'lere izin verir; CORS authentication
  mekanizması değildir.
- Her response bir request ID taşır; hata body'leri iç exception detayını
  production istemcisine sızdırmayan ortak envelope kullanır.
- Rapor/PDF ve analiz gibi pahalı endpointlerde process-local rate limit
  uygulanır.
- LLM anahtarı yalnız backend secret/environment'ından okunur. Tool calling
  salt-okunur allowlist, parametre/tarih/adım sınırlarıyla çalışır; model SQL
  veya keyfi fonksiyon çalıştıramaz.
- Aylık PDF için S3 provider `AES256` server-side encryption ister.
  Production rapor storage kullanımı S3/bucket eksikliğinde fail-closed'dur.
- CloudFront tam yapılandırılırsa kısa ömürlü signed URL, aksi durumda bearer
  token gerektiren backend proxy kullanılır.
- SMTP isteğe bağlı STARTTLS ve credential destekler. Claim/reconciliation
  modeli belirsiz gönderim sonucunda otomatik çift gönderimi sınırlar.

Caddy production edge'de HTTPS'i sonlandırır ve şu başlıkları ekler:

```text
Strict-Transport-Security: max-age=31536000
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
```

Frontend, backend ve aynı-host PostgreSQL varsayılan olarak `127.0.0.1` veya
private Compose ağı arkasında kalır; public giriş noktası Caddy'dir.

## Veri Gizliliği

- `.env`, token, dump ve secret dosyaları Git'e alınmaz; yalnız `.env.example`
  şablonları versiyonlanır.
- SSO profilinin yerel kullanıcı kopyası tutulmaz. Formen/şef iletişim alanları
  operasyonel domain master data'sıdır ve SSO profili değildir.
- LLM bağlamında personel mümkün olduğunda sicil/teknik referansla temsil edilir.
- Mevcut development/test veri seti sentetiktir; gerçek üretim verisi için
  saklama süresi, erişim, maskeleme ve KVKK sınıflandırması deployment
  tasarımında ayrıca onaylanmalıdır.
- Gerçek DNS/TLS, firewall/VPN, Keycloak, S3/CloudFront, SMTP ve secret manager
  uygulaması repository dışı production UAT kapsamındadır.

## Bağımlılık Güvenliği İstisnası (SCA)

`security-scan.yml`'deki `pip-audit` job'ı **blocking**'dir (`tier0/RULES.md`
§15.2 — Critical/High SCA bulguları düzeltilmeden canlıya alınamaz). Tek
kalıcı istisna:

| Alan | Değer |
|---|---|
| Advisory | `PYSEC-2026-1325` (alias: `GHSA-wj6h-64fc-37mp`, `CVE-2024-23342`) |
| Paket | `ecdsa` 0.19.2 (transitive — `python-jose[cryptography]`'nin `ecdsa!=0.15` bağımlılığı) |
| Neden düzeltilemiyor | Upstream `python-ecdsa` projesi side-channel/timing saldırılarını proje kapsamı dışı sayıyor ve düzeltme planlamıyor; PyPI'de bu advisory'yi kapatan bir sürüm yok (0.19.2 hâlâ en güncel). |
| Neden sömürülemez | Advisory'nin kendi metni açık: "ECDSA signature verification is unaffected" — saldırı yalnızca `SigningKey.sign_digest()` (imzalama) sırasında nonce timing sızıntısı. Bu uygulama bir OIDC resource server'dır: yalnızca Keycloak'ın imzaladığı JWT'leri **doğrular**, hiçbir zaman kendi başına imzalama yapmaz. `app/core/oidc.py` ayrıca `algorithms=[key.get("alg", "RS256")]` ile kabul edilen algoritmayı JWKS anahtarının `alg`'ıyla sınırlar — pratikte yalnızca RS256 (RSA) kullanılır, `python-jose`'un ECDSA backend'i hiç devreye girmez. |
| Kanıt | `backend/app/core/oidc.py:87`; advisory metni (`pip-audit --desc`); `pip index versions ecdsa` → en güncel sürüm hâlâ 0.19.2. |
| Mekanizma | CI: `pip-audit -r requirements.txt --desc --ignore-vuln PYSEC-2026-1325` (`.github/workflows/security-scan.yml`). |
| Owner | Teknik Sorumlu/Lider (bkz. RULES.md §1 Steward). |
| Gözden geçirme koşulu | Upstream bir fixed sürüm yayınlarsa **veya** `python-jose` ECDSA path'ini kullanan bir değişiklik (ör. ES256 desteği) eklenirse, bu istisna o an yeniden değerlendirilir — süresiz "sessiz" bir muafiyet değildir. |

Bunun dışında requirements.txt'te açık/bilinen bir CVE yoktur (2026-09-18
itibarıyla, `pip-audit -r backend/requirements.txt --ignore-vuln
PYSEC-2026-1325` → 0 bulgu).

Backend RBAC durumu:

```text
IMPLEMENTED — role + permission + ALL/FACTORY/PLANT scope, fail-closed
(no assignment ⇒ 403), CLI-managed. Report download is scope-gated, not
creator-gated (accepted simplification, not a gap).
```
