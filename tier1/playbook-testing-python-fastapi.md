# Testing Stack Playbook — FastAPI (pytest + pytest-asyncio + Testcontainers + httpx)

> `tier1/README.md`'deki yoğunluk kuralına uyar: Ne/Neden/Kural/Referans, kod bloğu istisna.
> `Referans` alanları `TBD` — bkz. `tier1/playbooks/playbook-backend-nestjs.md` başındaki aynı
> not. Araç seçimi FastAPI'nin resmi test dokümantasyonuyla uyumlu (httpx `AsyncClient` +
> `ASGITransport`, `pytest-asyncio`) — `playbook-testing-nestjs.md`'deki "testcontainers +
> framework'ün kendi HTTP client'ı" deseninin Python karşılığı.

**Stack:** pytest + pytest-asyncio + httpx (`AsyncClient` + `ASGITransport`) +
testcontainers-python (`postgres`, `redis`, gerekirse `localstack`) + factory_boy + pytest-cov

---

### Birim Testleri

**Ne:** `tests/` altında kaynak yapısını yansıtan ayrı dizin (`app/services/foo_service.py`
→ `tests/services/test_foo_service.py` — pytest'in idiomatik keşif deseni, co-located değil),
async fonksiyonlar `pytest-asyncio` (`asyncio_mode = "auto"`) ile çalışır.
**Neden:** Python ekosisteminde ayrı `tests/` dizini pytest'in varsayılanı; kaynağa gömülü
test dosyaları build/paketleme sırasında yanlışlıkla dağıtılabilir.
**Kural:** Yalnızca sınır bağımlılıklar mock'lanır (SQLAlchemy session, harici HTTP —
`respx`, async görev kuyruğu çağrısı — `.delay()`/`.apply_async()` mock'lanır, gerçek
broker'a gitmez); servisler birbirini gerçek instance ile çağırır. Her public fonksiyon
happy path + her exception path + 1 edge case ile kapsanır; trivial assertion
(`assert result is not None`) yasak.
**Referans:** `TBD`

### Entegrasyon Testleri

**Ne:** `tests/integration/` altında ayrı pytest marker (`@pytest.mark.integration`),
`PostgresContainer` + (kullanılıyorsa) `RedisContainer`/`LocalStackContainer` ile gerçek
container'lar, `httpx.AsyncClient(transport=ASGITransport(app=app))` ile tam HTTP
request → router → service → DB zinciri.
**Neden:** Mock'lanmış SQLAlchemy session'la yazılan bir unit test gerçek Alembic
migration/şema sapmasını yakalamaz; bir async görev kuyruğu kullanılıyorsa (bkz.
`playbook-messaging.md`) mesaj sözleşmesine uyup uymadığı da yalnız gerçek bir kuyruğa
karşı görünür.
**Kural:** Full flow (kritik bir sürecin başlangıç→bitiş zinciri), transaction/rollback
davranışı, ve (varsa) async görev kuyruğunun idempotency sözleşmesi mutlaka gerçek
container'lara karşı test edilir; pure Pydantic validation veya izole business logic unit
katmanında kalır. Her test başında `TRUNCATE ... CASCADE` ile DB state sıfırlanır. Unit ve
integration suite'leri ayrı marker/komutla çalışır.
**Referans:** `TBD`

### Uçtan-Uca (E2E) Testler

**Ne:** Fullstack bir projede kritik kullanıcı yolculukları `tier1/playbooks/playbook-
testing-nextjs.md`'deki Playwright akışıyla frontend üzerinden tetiklenir (backend gerçek,
mock değil). Yalnızca backend-only/API-only bir projede (frontend yoksa) e2e, httpx ile
gerçek çalışan bir instance'a karşı API-seviyesinde yazılır.
**Neden:** Aynı kritik-yol testini hem backend hem frontend playbook'unda ayrı ayrı
tanımlamak `tier1/README.md`'nin "içerik bir kez" ilkesini ihlal eder; frontend varsa e2e'nin
doğal giriş noktası kullanıcı arayüzüdür.
**Kural:** Backend-only projede API-seviyeli e2e, gerçek staging benzeri ortama karşı
(mock'lanmış dış bağımlılık yok) çalışır ve yalnızca "sistem gerçekten çalışıyor mu" sorusunu
kanıtlayan az sayıda kritik akışla sınırlı kalır — her endpoint için ayrı e2e yazılmaz (bu
zaten integration katmanının işi).
**Kritik Yollar:** `[proje bazlı doldurulacak liste — yalnızca frontend'i olmayan projeler
için, örn. "talep oluşturma→işlem→tamamlanma", "yetkisiz erişim reddi"]`
**Referans:** `TBD`

### Coverage Hedefi

**Ne:** Risk-bazlı, modül kritiklik seviyesine göre üç kademeli eşik — tek bir proje-geneli
sayı değil.
**Neden:** `tier0/RULES.md` §5 kalite kapısı somutlaştırması; auth/encryption/audit gibi
modüllerde düşük coverage yetersiz güvence verirken, aynı eşiği basit CRUD modüllerine
dayatmak gereksiz test-yazma maliyeti (feature hızını yavaşlatır) doğurur.
**Kural:** Kimlik doğrulama/yetkilendirme, şifreleme, audit/state-machine gibi iş-kritik
modüllerde line/branch/function coverage en az %90/%85/%100; orta-risk CRUD/entegrasyon
modüllerinde en az %80/%70/%85; proje-geneli minimum en az %75/%65/%80 — bu eşiklerin
altına düşen bir PR CI'da kırmızı olur. Coverage bir **taban**dır, kalitenin kanıtı değildir:
code review, edge case'lerin gerçekten kapsanıp kapsanmadığına ayrıca bakar.
**Referans:** `TBD` (pytest-cov CI job)

### Test Verisi Stratejisi

**Ne:** `tests/factories/` altında entity-bazlı `factory_boy` sınıfları, Faker
entegrasyonuyla override edilebilir default değerler; entegrasyon testlerinde
`SQLAlchemyModelFactory` doğrudan DB'ye yazar, unit testlerde yalnızca in-memory/Pydantic
model döner.
**Neden:** Elle yazılmış sabit fixture'lar şema her değiştiğinde tek tek güncellenmesi
gereken çok dosyaya dönüşür; factory pattern bunu tek merkezi noktaya indirger.
**Kural:** Yeni bir zorunlu şema alanı eklendiğinde önce factory güncellenir, sonra onu
kullanan testler değil — testler factory'nin default'una güvenir, kendi içinde raw obje
literal'ı inşa etmez. Her test kendi factory çağrısıyla kendi verisini üretir, testler
arası paylaşılan mutable state yoktur.
**Referans:** `TBD`

---

### Cross-Cutting ve Kapsam Dışı

Frontend/e2e stratejisi `tier1/playbooks/playbook-testing-nextjs.md`'dedir, burada
tekrarlanmaz. Coverage raporlama/CI entegrasyonu (hangi job, hangi eşik CI'ı kırar) proje
bazlı `docs/07-test-stratejisi-detayi.md`'ye (bkz. `tier2/README.md` madde 7) taşınır — bu
playbook yalnızca araç ve genel eşik kararını taşır, CI job tanımını değil.
