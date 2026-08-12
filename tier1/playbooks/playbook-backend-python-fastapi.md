# Backend Stack Playbook — FastAPI (Python)

> `tier1/README.md`'deki yoğunluk kuralına uyar: Ne/Neden/Kural/Referans, kod bloğu istisna.
> Onay: `tier0/adr/0003-python-fastapi-approved-stack.md`. `Referans` alanları `TBD` —
> bkz. `tier1/playbooks/playbook-backend-nestjs.md` başındaki aynı not.
>
> **Kapsam sınırı:** Bu playbook FastAPI'nin **genel API/orkestrasyon** katmanını kapsar.
> Gerçek ML model inference'ı, MQTT tüketimi ve async görev kuyruğu ayrı bileşenler olarak
> aşağıda işaretli — bunlar FastAPI process'inin *içinde* çalıştırılmaz.

**Stack:** FastAPI + Python 3.14.x + Pydantic v2 + (gerekirse) SQLAlchemy 2.0 async +
Alembic + uv (minor/patch projenin lockfile'ında — bkz. `tier1/APPROVED-STACKS.md`
"Versiyon Stratejisi")

---

### Katmanlama

**Ne:** Router → Service → Repository; Pydantic modelleri (request/response) DB modellerinden
(SQLAlchemy) ayrı.
**Neden:** DB modelini doğrudan response'a serileştirmek, lazy-loading ve istemeden hassas
alan sızıntısı riski taşır.
**Kural:** Her endpoint ayrı bir Pydantic response modeli döner; router katmanı DB session'ına
doğrudan erişmez.
**Referans:** `TBD`

### Kimlik Doğrulama (Authentication) — Bu Dosyada Değil

**Ne:** Kimlik doğrulama Red Hat SSO'ya (OIDC) devredilir — `tier0/RULES.md` §12,
`tier1/playbooks/playbook-authentication.md`.
**Neden:** Zorunlu, merkezi bir cross-cutting konu; FastAPI'nin kendi JWT issuance/
refresh-rotation implementasyonu kurması artık **istenmiyor** (bkz. `tier0/adr/0005-...`).
**Kural:** FastAPI tarafı `python-keycloak` (veya genel bir OIDC kütüphanesi) ile gelen SSO
token'ını `Depends()` tabanlı bir dependency'de doğrular; kendi login/token issuance akışı
**inşa edilmez.**
**Referans:** `tier1/playbooks/playbook-authentication.md`

### Yetkilendirme / İzin Modeli

**Ne:** FastAPI `Depends()` tabanlı izin kontrolü — her endpoint bir permission-check
dependency'si taşır.
**Neden:** İzin kontrolü endpoint imzasında açık olmalı, servis fonksiyonunun içine gömülü
olmamalı — okunabilirlik ve tutarlılık için.
**Kural:** Her state-değiştiren endpoint bir `Depends(require_permission(...))` taşımadan
merge edilmez.
**Referans:** `TBD`

### Girdi Doğrulama

**Ne:** Pydantic v2 modelleri — request body/query/path parametrelerinin tamamı.
**Neden:** FastAPI'nin type-hint'e dayalı doğrulaması zaten bu prensip üzerine kurulu; bunu
bilerek atlayıp ham `dict`/`Request` kullanmak, RULES.md §4 madde 2'yi ihlal eder.
**Kural:** Hiçbir endpoint ham `Request.json()` okumaz; her girdi tipli bir Pydantic modeli
üzerinden gelir.
**Referans:** `TBD`

### Veritabanı Erişimi (gerekirse)

**Ne:** SQLAlchemy 2.0 (async engine) + Alembic migration.
**Neden:** Her Python servisi DB'ye ihtiyaç duymaz (bazıları salt hesaplama/orkestrasyon
yapar) — bu bölüm yalnız DB erişimi gerektiğinde geçerlidir.
**Kural:** Şema-kırıcı migration'lar expand-contract pattern'iyle yapılır (diğer stack
playbook'larıyla aynı kural).
**Referans:** `TBD`

### Konfigürasyon & Sır Yönetimi — Mekanizma Burada, Sır Deposu `playbook-infra-terraform-aws.md`'de

**Ne:** `pydantic-settings` (`BaseSettings`) ile tipli bir `Settings` nesnesi; tüm
konfigürasyon (secret dahil) ortam değişkeni üzerinden okunur.
**Neden:** `tier0/RULES.md` §4 madde 7 — secret'lar koda/`.env`'e gömülmez; production'da
bu değişkenler ECS task tanımının `secrets` alanı üzerinden Secrets Manager'dan inject
edilir — bkz. `tier1/playbooks/playbook-infra-terraform-aws.md` "Sır (Secret) Yönetimi" —
uygulama kodu bunun kaynağını bilmek zorunda değildir; sadece `os.environ`/`Settings`
üzerinden okur.
**Kural:** `Settings` sınıfı repoya commit edilmez bir `.env` dosyasından **yalnızca yerel
geliştirmede** değer okur (`python-dotenv`, gitignore'lu); production'da `.env` dosyası
imajın içine **hiç konmaz**, değerler container ortamına Secrets Manager'dan inject
edilmiş olarak gelir. Hiçbir secret değeri `Settings` sınıfının varsayılan değeri (`default=`)
olarak koda yazılmaz; secret-pattern taraması `tier1/playbooks/playbook-cicd-security.md`'de.
**Referans:** `TBD`

### Hata Yönetimi & Yanıt Zarfı — Mekanizma Burada, Şekil `playbook-api-design.md`'de

**Ne:** FastAPI `exception_handler` ile merkezi hata yakalama, tipli exception sınıfları.
Response zarfının/error taksonomisinin **şekli** `tier1/playbooks/playbook-api-design.md`'dedir
(Zorunlu, tüm backend stack'lerinde aynı), burada tekrarlanmaz.
**Neden:** Aynı kuralı iki yerde tutmak `tier1/README.md` "içerik bir kez" ilkesini ihlal
eder; FastAPI'ye özel olan yalnız **hangi mekanizmanın** bu şekli ürettiğidir.
**Kural:** Her exception bir error code + kullanıcıya-güvenli mesaj taşır (bkz. api-design
playbook'undaki `DOMAIN_ENTITY_CONDITION` formatı); ham traceback response'a asla sızmaz.
**Referans:** `tier1/playbooks/playbook-api-design.md`

### Denetim Kaydı (Audit)

**Ne:** Middleware veya dependency-tabanlı audit loglama; `tier0/RULES.md` §4 madde 4'teki
gerçek-aktöre-atfetme kuralı.
**Neden:** Diğer stack'lerle aynı gerekçe — audit kaydı gerçek aktöre çözülmeli, delegasyon
varsa da.
**Kural:** Her state-değiştiren endpoint audit middleware'inden geçer; audit metadata'sına
yazılan hiçbir alan başka bir yerde şifreli tutulma amacını bypass etmez.
**Referans:** `TBD`

### Hız Sınırlama — Mekanizma Burada, Katmanlama `playbook-api-design.md`'de

**Ne:** Kimlik-bazlı rate limiting (örn. `slowapi` veya Redis-tabanlı özel middleware).
Rate-limit katmanlaması (edge vs kimlik-bazlı app-level)
`tier1/playbooks/playbook-api-design.md`'deki "Rate Limiting Katmanlaması" bölümündedir.
**Neden:** `tier0/RULES.md` §4 madde 5 — IP-bazlı değil, kimlik-bazlı olmalı; bu kural tüm
backend stack'lerinde aynı, burada tekrar yazılmaz.
**Kural:** Rate limit key'i `user_id` (veya servis-kimliği), `client.host` değil.
**Referans:** `tier1/playbooks/playbook-api-design.md`

---

### ⚠️ ML Model Serving — Bu Playbook'un Kapsamı Dışı

**Ne:** Gerçek model tahmini (inference) FastAPI process'i içinde çalıştırılmaz.
**Neden:** FastAPI I/O-ağırlıklı işler için tasarlandı; model tahmini hesaplama-ağırlıklıdır
— endpoint async olsa bile tahmin çağrısı ana event loop'u bloklar. Bu, sentetik bir kural
değil, gerçek bir mimari sınırlamadır.
**Kural:** FastAPI, ML serving katmanına (BentoML veya Ray Serve — bkz.
`tier1/catalog/ml-serving.md`) HTTP/gRPC ile çağrı yapan bir istemci olarak davranır;
modeli kendi process'inde `.predict()` ile doğrudan çağırmaz.
**Referans:** `tier1/playbooks/playbook-backend-python-ml-serving.md` (TBD) + `tier0/adr/0003-...`

### ⚠️ MQTT / IoT — Ayrı Bir Servis

**Ne:** aiomqtt tabanlı bir consumer, FastAPI'den **ayrı bir process/servis** olarak çalışır.
**Neden:** MQTT bağlantısı uzun-ömürlü, sürekli dinleyen bir bağlantıdır — bir HTTP request-
response döngüsüne sığmaz.
**Kural:** MQTT tüketici mantığı FastAPI router'ı içine gömülmez; ayrı bir worker/servis
olarak deploy edilir.
**Referans:** `TBD`

### ⚠️ Async Görev Kuyruğu — Ayrı Bir Servis

**Ne:** Celery (SQS broker) veya boto3+doğrudan SQS tüketici — proje karmaşıklığına göre
(bkz. `tier1/catalog/backend.md` "Aynı kategoride birden fazla onaylı seçenek varsa").
**Neden:** Uzun süren işler (LLM çağrısı, ML tahmini, toplu işlem) bir HTTP request'i içinde
senkron beklenmez — kullanıcıyı bloklar ve timeout riski taşır.
**Kural:** FastAPI endpoint'i işi kuyruğa yazar ve hemen döner; işin kendisi ayrı bir
worker'da çalışır.
**Referans:** `TBD`

---

### Cross-Cutting Playbook'lar (bu dosyada tekrar edilmez)

Gözlemlenebilirlik (**Zorunlu**), API sözleşme şekli (**Zorunlu**), kurumsal sistem
entegrasyonu (**Zorunlu, varsa**), CI/CD güvenliği (**Zorunlu**), caching ve messaging
ihtiyaçları için bu dosyaya değil, sırasıyla `tier1/playbooks/playbook-observability.md`,
`tier1/playbooks/playbook-api-design.md`, `tier1/playbooks/playbook-service-integration.md`,
`tier1/playbooks/playbook-cicd-security.md`, `tier1/playbooks/playbook-caching.md`,
`tier1/playbooks/playbook-messaging.md` dosyalarına bakın — FastAPI için tek fark
enstrümantasyon SDK'sı (OpenTelemetry Python SDK), o da gözlemlenebilirlik playbook'unun
tablosunda.
