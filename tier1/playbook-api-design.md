# API Tasarım Prensipleri Playbook — Cross-Cutting, Zorunlu

> `tier1/README.md`'deki yoğunluk kuralına uyar: Ne/Neden/Kural/Referans, kod bloğu istisna.
> `tier0/RULES.md` §14'ün detay dosyası. Diğer bölümler stack-bağımsızdır (NestJS, Spring
> Boot, FastAPI aynı prensiplere uyar — dil-özel implementasyon detayı ilgili backend
> playbook'una kalır, burada tekrarlanmaz).

**Kapsam:** REST API sözleşme şekli — response zarfı, hata taksonomisi formatı, pagination,
versiyonlama, rate-limit katmanlaması. Endpoint-özel içerik (gerçek endpoint listesi, gerçek
error code'lar) burada değil — `docs/04-api-sozlesme-katalogu.md`'da (bkz. `tier2/README.md`
madde 4 "API/Sözleşme Kataloğu" — bu proje `tier2/` klasörünü kopyalamaz, kendi doldurduğu
çıktı `docs/` altında yaşar), projenin kendi dokümanında.

---

### Genel Prensipler

**Ne:** URL path üzerinden versiyonlama (`/api/v1/...`), `kebab-case` URL / `camelCase` JSON
alan adı ayrımı, ISO 8601 UTC tarih formatı, her request'e `X-Request-Id` korelasyon
header'ı, `PUT` kullanılmaz (tam değiştirme yerine `PATCH`).
**Neden:** Versiyonlama stratejisi baştan net değilse, ilk breaking change'de agent
"yeni endpoint mi ekleyeyim yeni path mi açayım" sorusunu her seferinde yeniden icat eder;
`X-Request-Id` olmadan bir hata raporu backend log'una bağlanamaz — destek/debug süresi
katlanır.
**Kural:** Major (breaking) değişiklik yeni `/api/v2/` path'i açar, minor değişiklik
backward-compatible kalır ve aynı path'te kalır. Her response'a (başarı/hata fark etmez)
`X-Request-Id` (client gönderdiyse aynen, göndermediyse sunucu üretir) eklenir; hata
response'unun `requestId` alanı bu değerle aynıdır.
**Referans:** `TBD`

### Response Zarfı

**Ne:** Tüm JSON response'lar `{ "data": ... }` (başarı) veya `{ "error": {...} }` (hata)
zarfından biridir; ikisi asla aynı response'ta bulunmaz. Koleksiyon dönen endpoint'ler
sayfalıysa `data` yanında bir `pagination` objesi taşır.
**Neden:** Zarf tutarsızsa (bazı endpoint çıplak obje, bazısı `{data: ...}` döner), frontend
her endpoint için ayrı bir response-parse mantığı yazmak zorunda kalır — bu hem kod
tekrarını hem de "bu endpoint hangi şekli döndürüyordu" hafıza yükünü büyütür.
**Kural:** 2xx response'larında `error` alanı yoktur, non-2xx response'larında `data` alanı
yoktur — istemci ayrıştırmayı yalnızca bu iki alanın varlığına bakarak yapabilmeli, HTTP
status'e ek bir kaynak olarak. Hata zarfı en az `code` (bkz. Error Taxonomy), `message`
(kullanıcıya güvenli, `tier0/RULES.md` §3 dil sözleşmesine uygun dilde), `requestId`,
`timestamp` alanlarını taşır; `details` opsiyoneldir ve yalnız teknik/hata-ayıklama bağlamı
taşır (örn. hangi alan hangi kurala takıldı).
**Referans:** `TBD`

### Hata Taksonomisi (Error Taxonomy)

**Ne:** Sabit enum error code formatı — `DOMAIN_ENTITY_CONDITION` (UPPER_SNAKE_CASE, örn.
`USER_SICIL_DUPLICATE`); her code'un tek bir HTTP status'e, tek bir kullanıcı mesajı
kalıbına bağlı olması.
**Neden:** Serbest metin hata mesajına/rastgele status koduna dayanan bir sistemde frontend
"bu hatada ne yapmalıyım" sorusunu string-eşleştirme ile çözmeye çalışır — bu kırılgan ve
lokalizasyon değiştiğinde bozulan bir pattern'dir; sabit code enum'u frontend'e programatik,
dile bağımsız bir karar yüzeyi verir.
**Kural:** Yeni bir error code eklemek bir geliştirme kararıdır, response'ta ad-hoc string
üretilmez. HTTP status semantiği sabit bir sözleşmedir: `400` girdi/format hatası,
`401` kimlik doğrulama başarısız, `403` yetki/durumsal yasak, `404` kaynak yok,
`409` state conflict/duplicate, `422` syntax doğru ama iş kuralı ihlali, `429` rate limit
(zorunlu `Retry-After` header'ıyla), `5xx` sunucu/bağımlılık hatası. Her yeni error code,
frontend'in bu code'a nasıl tepki vereceğini (toast mı, inline form hatası mı, redirect mi)
de birlikte tanımlar — code eklenip frontend davranışı tanımsız bırakılmaz. Gerçek proje
error code listesi ve HTTP eşlemesi `docs/04-api-sozlesme-katalogu.md`'da tutulur (bkz.
`tier2/README.md` madde 4), burada değil.
**Referans:** `TBD`

### Pagination

**Ne:** Cursor-based pagination varsayılan — opaque, client tarafından parse edilmeyen bir
`cursor` string'i + `limit` query parametresi; offset-based kullanılmaz.
**Neden:** Offset-based pagination, sık yazılan (append-heavy) büyük tablolarda (audit log,
süreç/işlem listesi gibi) sayfa kayması ve performans düşüşü yaşar — cursor bu sınıf hatayı
yapısal olarak önler.
**Kural:** Response `pagination: { nextCursor, hasMore }` taşır; `total` yalnızca ucuz
hesaplanabilen (küçük/aggregat edilebilir) listelerde döner, büyük/append-heavy tablolarda
atlanır — UI bu durumda "sayfa N/M" yerine "daha fazla yükle" desenine döner. Varsayılan
sıralama her liste endpoint'inde sabittir; alternatif sıralama yalnız whitelist edilmiş
`sort` değerleriyle açılır, arbitrary sort ifadesi kabul edilmez.
**Referans:** `TBD`

### Rate Limiting Katmanlaması

**Ne:** İki ayrı katman — edge/WAF seviyesinde kaba, IP-bazlı bir taban limit; backend
(uygulama) seviyesinde kimlik-bazlı, endpoint-hassasiyetine göre farklılaşan ince limit.
**Neden:** `tier0/RULES.md` §4 madde 5 zaten kimlik-bazlı rate limit'i zorunlu kılıyor (yalnız
IP bazlı olursa aynı NAT/ofis birbirini kilitler); edge katmanı bunun yerine geçmez, ona ek
bir kaba filtre olarak durur — ikisi karıştırılırsa (yalnız edge'e güvenilirse) kimlik-bazlı
kural fiilen uygulanmamış olur.
**Kural:** Login, şifre sıfırlama, impersonation başlatma gibi hassas endpoint'lerin kendi,
daha sıkı, kimlik-bazlı limiti vardır (global limitten ayrı); limit parametreleri kod içine
sabit yazılmaz, runtime'da değiştirilebilir bir ayardan okunur. `429` response'u zorunlu
`Retry-After` header'ı taşır; error body `RATE_LIMIT_*` taksonomisine uyar (bkz. Hata
Taksonomisi).
**Referans:** `TBD`

---

### API Gateway Yerleşimi — İki Ayrı Sorumluluk

**Ne:** Gateway'in fiziksel/topolojik yerleşimi (hangi VPC katmanı, kaç instance, hangi
bulut kaynağı) `deployment-design` skill'inin HLA çıktısındadır — bu playbook onu tekrar
tasarlamaz. Bu playbook yalnızca gateway'in **kontrat üzerindeki etkisini** tanımlar:
internet'e açık ve yalnız kurum-içi (internal) arayüzlerin ayrı olması zorunluluğu, ve
kurumsal sistemlere erişimin Ocean üzerinden geçmesi zorunluluğu.
**Neden:** Yerleşim kararı ile kontrat kararı aynı yerde karışırsa, bir tasarım
dokümanı hem "nerede duracak" hem "nasıl davranacak" sorularını aynı anda cevaplamaya
çalışır — ikisi farklı roller (mimari/altyapı vs. API sözleşmesi) tarafından, farklı
zamanlarda karara bağlanır.
**Kural:** İnternet'e açık ve internal API arayüzleri aynı gateway/listener'ı paylaşmaz
(`tier0/RULES.md` §13 madde 4); kurumsal bir sisteme erişim gerekiyorsa bu Ocean üzerinden
kurulur, doğrudan değil (`tier0/RULES.md` §13, detay
`tier1/playbooks/playbook-service-integration.md`). Fiziksel yerleşim sorusu
(`deployment-design` skill'i) ile bu kontrat kuralı birbirine referans verir, biri
diğerini görmezden gelmez.
**Referans:** `TBD`

### Servis Middleware Pattern'leri — Ocean, Zorunlu

**Ne:** Kurum içinde bir uygulamanın başka bir kurumsal sisteme (ERP, SAP, başka bir dahili
uygulama vb.) erişmesi gerektiğinde bunun nasıl kurulacağı — bu playbook'un kapsamı dışında,
ayrı bir Zorunlu cross-cutting playbook'ta.
**Neden:** Bu, "kendi API'mi nasıl tasarlarım" sorusundan farklı bir soru ("başka bir
sisteme nasıl erişirim") — `tier1/README.md`'nin cross-cutting ayrımı burada da geçerli,
aynı playbook'a karıştırılmaz.
**Kural:** Kurumsal sistem entegrasyonu ihtiyacı ortaya çıktığında
`tier1/playbooks/playbook-service-integration.md` uygulanır (Ocean üzerinden zorunlu
entegrasyon, `tier0/RULES.md` §13, bkz. `tier0/adr/0006-...`); framework'ün kendi HTTP
middleware/interceptor katmanı (NestJS interceptor, Spring filter chain vb.) ise ilgili
`playbook-backend-*.md`'nin kapsamındadır, burada tekrarlanmaz.
**Referans:** `tier1/playbooks/playbook-service-integration.md`

---

### Cross-Cutting ve Kapsam Dışı

Authentication akışının kendisi (token modeli, OIDC/SSO entegrasyonu, CSRF koruması)
`tier1/playbooks/playbook-authentication.md`'dedir, burada tekrarlanmaz — bu playbook yalnız
authenticated/anonim isteklerin genel response/hata şeklini tanımlar. Audit annotation
disiplini (`tier0/RULES.md` §4 madde 4) ve DB erişim pattern'leri ilgili
`playbook-backend-*.md`'nin kendi bölümlerindedir. Webhook (dışa/dışarıdan olay tabanlı
entegrasyon) bu playbook'un ilk sürümünde kapsam dışıdır — ihtiyaç somutlaştığında ayrı bir
bölüm/ADR ile eklenir, şimdiden icat edilmez.
