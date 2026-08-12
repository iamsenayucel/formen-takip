# CI/CD ve Tedarik Zinciri Güvenliği Playbook — Cross-Cutting, Zorunlu

> `tier1/README.md`'deki yoğunluk kuralına uyar: Ne/Neden/Kural/Referans, kod bloğu istisna.
> `tier0/RULES.md` §15'in detay dosyası. Diğer bölümler stack-bağımsızdır — dil-özel araç
> yalnızca "Kural" alanında kısa bir not olarak geçer, tam kurulum ilgili
> `playbook-backend-*.md`/`playbook-frontend-*.md`'nin kendi CI adımına kalır.
>
> **Somut ürün seçimi bilerek eksik bırakıldı (2026-07-20):** Bu playbook'un önceki bir
> taslağı `check-coe-versions.js` ve yalnız-Nexus bağımlılık kaynağı gibi somut isimler
> kullanıyordu — bunların gerçek/planlı kurumsal altyapı olmadığı teyit edildi. Aynı hatayı
> tekrarlamamak için SAST/SCA/lisans-tarama **ürünü** burada icat edilmez; onaylanana kadar
> `TBD` kalır (bkz. Rol Eşleme, `tier0/Politika/README.md` — Security rolü/EA-CoE onayı
> bekliyor). Yalnız dil-ekosisteminin **açık, yaygın standart** araçları (ESLint, ruff/mypy
> vb.) isimlendirilir — bunlar bir kurumsal satın alma kararı değil, o dilin varsayılan
> pratiğidir.

**Kapsam:** Kod commit'lenmeden/canlıya çıkmadan önce pipeline'da otomatik çalışan üç
kontrol sınıfı — statik analiz/tip güvenliği, bağımlılık+lisans taraması (SCA), statik
güvenlik taraması (SAST). Runtime/kod-seviyesi güvenlik kontrolleri (yetkilendirme, girdi
doğrulama vb.) bu playbook'un kapsamı dışı — `tier0/RULES.md` Bölüm 4'te.

---

### Statik Analiz / Tip Güvenliği

**Ne:** Derleme/lint adımında tip-güvenliğini zayıflatan kalıpların (dinamik/gevşek tip
kullanımı) ve koda gömülü şifre/anahtarın (hardcoded credential) otomatik olarak
engellenmesi.
**Neden:** Bu ihlaller code review'a bırakılırsa insan dikkatine bağlı kalır — bir
reviewer'ın her satırda "bu değer sabit mi kodlanmış" diye kontrol etmesi beklenemez;
otomatik ve CI'ı kırmızı yapan bir kapı olmadan bu kural fiilen uygulanmıyor demektir. Bu,
`tier0/RULES.md` §4 madde 7'nin (Sır yönetimi) mekanik uygulanma noktasıdır — madde 7 bir
niyet beyanı değildir, bu CI adımı onu garanti eder.
**Kural:** Lint adımı CI'da **zorunlu, atlanamaz** bir job'dır — kırmızıysa merge engellenir.
Dil-ekosistemine göre: JS/TS'de ESLint (`no-explicit-any` veya eşdeğeri kural, strict
`tsconfig`) + secret-pattern taraması; Python'da ruff/mypy (strict mode) + secret-pattern
taraması; JVM'de Checkstyle/SpotBugs + eşdeğeri. Somut kural seti ilgili
`playbook-backend-*.md`/`playbook-frontend-*.md`'nin CI bölümünde tutulur, burada tekrar
edilmez.
**Referans:** `TBD`

### Bağımlılık ve Lisans Taraması (SCA)

**Ne:** Açık kaynak bağımlılıklardaki bilinen güvenlik açıklarının (CVE) ve lisans
uyumsuzluklarının canlıya almadan önce otomatik taranması.
**Neden:** Bir bağımlılık zincirindeki zafiyet elle takip edilemeyecek kadar hızlı değişir
(günlük yeni CVE) — otomatik tarama olmadan bu risk sistematik olarak gözden kaçar; lisans
uyumsuzluğu ise fark edilmeden hukuki/itibar riskine dönüşebilir (bkz. Master Politika
Madde 7).
**Kural:** **Critical** ve **High** seviyeli SCA bulguları düzeltilmeden ürün canlıya
alınamaz — bu, Bölüm 11-14'teki "Zorunlu" mandate'lerle aynı ağırlıktadır, proje bazında
gevşetilmez (MVP dahil, bkz. `tier0/RULES.md` §1 "MVP Disiplini Ölçeklenmesi"). Somut SCA
ürünü/lisans-politikası aracı `TBD` — onaylandığında bu satır güncellenir, icat edilmez.
**Referans:** `TBD`

### Statik Güvenlik Taraması (SAST)

**Ne:** Üretilen kodun canlı öncesi otomatik statik güvenlik taramasından geçmesi
(injection, hardcoded secret, güvensiz deserialization gibi bilinen zafiyet sınıfları).
**Neden:** AI-üretimi kod, "çalışıyor gibi görünen" ama güvenlik açısından öngörülemeyen
kalıplar üretebilir (`tier0/RULES.md` §6 halüsinasyon önleme ile aynı kaygı, burada güvenlik
eksenine uygulanmış hali) — otomatik tarama, code review'ın gözden kaçırabileceği bir
güvenlik ağıdır, onun yerine geçmez.
**Kural:** SAST, Gate 3/5 ayrımında **asla atlanamaz** işaretlidir (Master Politika Madde 5)
— üretim kesintisi istisna protokolünde bile bu adım daraltılamaz, yalnızca review derinliği
daraltılabilir (bkz. `tier0/procedures/production-bugfix-cr.md` madde 5). Somut SAST ürünü
`TBD`.
**Referans:** `TBD`

---

### Cross-Cutting ve Kapsam Dışı

Runtime güvenlik kontrolleri (yetkilendirme, girdi doğrulama, hassas veri koruma, audit,
rate-limit, çıktı kaçışı) `tier0/RULES.md` Bölüm 4'tedir, burada tekrarlanmaz. Gizli/secret
değerlerin **saklanması** (secret manager, env injection) ilgili `playbook-infra-*.md`'nin
kapsamındadır — bu playbook yalnızca kodun içine **gömülü** secret'ı yakalayan CI kontrolünü
tanımlar, secret yönetimi altyapısını değil. Somut araç seçimi netleştiğinde bu dosyanın
`Referans` alanları backfill edilir (`tier0/RULES.md` §14 ile aynı "greenfield'da TBD"
deseni, bkz. `skills/design-flow-agent/SPEC.md` §4 Faz 4 madde 3).
