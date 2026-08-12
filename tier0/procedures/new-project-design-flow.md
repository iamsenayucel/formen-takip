# Prosedür: Yeni Proje Tasarım Akışı (Greenfield)

> **Kapsam:** Bu prosedür yalnızca **sıfırdan başlayan bir proje**, bu şablonu kopyaladıktan
> sonra, **ilk kod satırı yazılmadan önceki** tasarım fazını kapsar. Devralınan bir
> codebase üzerinde refactor/change/bugfix akışı **ayrı bir prosedürdür** (henüz yazılmadı,
> kapsam dışı — bu dosyayı o amaçla kullanmayın).
>
> Proje küçük veya büyük olsun **aynı sırayı izler.** Değişen şey oturum sayısı/derinliği,
> süreç değil — bkz. Bölüm 6.

## 0. Neden bu sıra, neden `tier1/` en son değil en sonra da değil

`tier1/` playbook'ları bilerek çok sayıda `[köşeli parantez]` içerir — bu bir eksiklik
değil, bir şablonun genel olabilmesinin bedelidir. Sorun, bu parantezleri **soğuk** (hiçbir
karar verilmemişken) doldurmaya çalışmaktır — o zaman agent de siz de tahmin etmeye
başlarsınız (`tier0/RULES.md` §6 tam olarak bunu yasaklıyor).

Bu prosedürün çözümü: `tier1/`'e gelene kadar, `tier1`'deki çoğu parantezin cevabını
**zaten belirlemiş olursunuz** — ADR'lerde ve `tier2` domain iskeletinde. `tier1`'i
doldurmak böylece "yeni karar vermek" değil, **zaten verilmiş kararı Ne/Neden/Kural/Referans
şekline aktarmak** haline gelir. Sıra budur:

```
tier0 (hafif) → ADR seti → tier2 domain iskeleti → tier1 (artık kolay) → tier2 (tamamla) → çıkış kapısı
```

---

## 1. Roller

| Rol | Sorumluluk | Sınır |
|---|---|---|
| **Tasarım Sorumlusu** | Ürün/domain kararları: kapsam, kullanıcı/persona, domain modeli, ekranlar, iş kuralları, non-goal'lar | Teknik implementasyon detayına karar vermez |
| **Teknik Sorumlu** | Mimari kararlar: stack, altyapı, güvenlik modeli, test stratejisi, kalite eşikleri | Domain/iş kuralı kararı vermez, tasarım sorumlusuna sorar |
| **AI Agent** (Cursor/Claude Code/Copilot/Antigravity — Plan Mode'da) | Araştırır, seçenek sunar, taslak yazar, çelişki/eksik işaretler, onay sonrası dosyaya yazar | **Belirsiz bir iş/mimari kararı kendi başına vermez** — `tier0/RULES.md` §6, madde 6 |

İki insan rolü **aynı oturumlarda birlikte** çalışır, silo halinde değil — çoğu `tier1`
parantezi hem domain bilgisi (tasarım sorumlusu) hem teknik karar (teknik sorumlu) gerektirir
(örn. "hangi alanlar PII, nasıl şifrelenecek" — biri neyin hassas olduğunu bilir, diğeri nasıl
şifreleneceğine karar verir).

---

## 2. Tool-Agnostik "Plan Mode" Tanımı

Bu akışın tamamı, kullanılan araç ne olursa olsun, aşağıdaki özellikleri taşıyan bir modda
yürütülür:

- Agent dosya okuyabilir, arama yapabilir, soru sorabilir, taslak yazabilir.
- Agent **onay almadan dosyaya kalıcı yazmaz / kod üretmez.**
- Her oturumun çıktısı, bir insanın açıkça onayladığı, gözden geçirilebilir bir taslaktır.

| Araç | Bu modun karşılığı |
|---|---|
| Cursor | Ask / Plan modu (kod yazmadan sohbet/planlama) |
| Claude Code | Plan Mode (onay olmadan dosya değişmez) |
| GitHub Copilot | Copilot Chat (Edits/Agent modunun dışında, salt-sohbet) |
| Antigravity | *(doğrulanmalı — bkz. `adapters/antigravity/README.md`)* |

Hangi araç kullanılırsa kullanılsın, **otonom-yazma modunda tasarım fazı yürütülmez.**

---

## 3. Fazlar

### Faz 0 — Kickoff (Proje Künyesi)

**Katılımcılar:** Tasarım Sorumlusu + Teknik Sorumlu
**Çıktı:** `tier0/RULES.md` §1'deki **Proje Künyesi**'nin tamamı — Faz 2 ve sonrası bu
bilgiye **tekrar sormadan** referans verir. Resmi bir doküman değil, ama yüzeysel de değil:
projenin "kim, ne için, ne ölçekte, ne kadar kritik" sorularının tümüne burada cevap
verilir. Yukarıdan aşağıya, en genel sorudan en spesifiğe doğru ilerler.

Sıra şöyledir (agent bunu kapalı-uçlu soruları ilgili konu başlığı altında gruplayarak
sorar, bkz. `skills/design-flow-agent/SPEC.md` §2.1):

1. **Giriş kontrolü** — üç seçenek: **(a) yepyeni proje (greenfield)** → bu akış
   uygulanır; **(b) yeni feature geliştirme** (proje daha önce bu akıştan geçmiş, tier0/
   tier1/ADR'ler zaten dolu, şimdi üstüne feature ekleniyor) → bu akış değil, ayrı bir
   rotaya gider (bkz. Bölüm 6, "Sonraki Adım" — bu rota henüz yazılmadı); **(c) devralınan/
   organik sistem** (hiç bu akıştan geçmemiş, tier0/tier1 yok) → bu akış uygulanmaz, tamamen
   ayrı ve kapsam dışı bir konu (bkz. Bölüm 6). (b) ile (c) karıştırılmamalı: (b)'de kurumsal
   tasarım dokümanları zaten var, (c)'de hiç yok.
2. **Proje adı/amacı** — tek cümlede ne yapıyor, kim için.
3. **MVP mi, gerçek/üretim projesi mi (gate sorusu)** — bu cevap aşağıdaki 5 ve 7 numaralı
   adımların tam mı sorulacağını yoksa varsayılan değerle mi geçileceğini belirler. MVP ise
   ek olarak: bu MVP gerçek projenin temeli mi olacak, yoksa atılacak bir kanıt mı? (MVP
   disiplininin RULES.md'nin hangi kurallarını nasıl gevşettiği ayrı bir konu — henüz
   tanımlanmadı, ileride ayrı bir playbook veya RULES.md eki olarak eklenecek.)
4. **Kim kullanacak** — organizasyonel kapsam (tek şirket/tüm holding/tek departman),
   kullanıcı kimliği (iç çalışan/dış müşteri-bayi/karma), çalışan tipi (beyaz/mavi
   yaka/karma), erişim izolasyonu (internete açık/yalnız VPN/tesis-izole). MVP'de de
   atlanmaz — auth ve altyapı kararlarını doğrudan etkiler. Kullanıcı kimliği dış
   müşteri/bayi ise, mevcut Red Hat SSO zorunluluğunun (§12) iç-kullanıcı varsayımıyla
   yazıldığı, ayrı bir CIAM ihtiyacının değerlendirilmesi gerektiği bu noktada işaretlenir.
5. **Ölçek** — kullanıcı sayısı (1-100 / 100-1.000 / 1.000-10.000 / 10.000+), büyüme
   beklentisi. **MVP ise atlanır**, varsayılan "küçük ölçek" yazılır.
6. **Uygulama tipi ve temel alan** — uygulama tipi (backend/fullstack/mobile/BFF/
   worker/diğer), temel alan (iş uygulaması/AI & ML/Agentic Workflow/Chatbot/IoT/veri
   platformu/diğer — birden fazla seçilebilir). MVP'de de atlanmaz — stack seçimini
   doğrudan besler.
7. **Kritiklik ve uyum** — iş kritiklik seviyesi (Seviye 1 Kritik / Seviye 2 Önemli /
   Seviye 3 Destekleyici), regülasyon/veri hassasiyeti sinyali. Kritiklik sorusu **MVP ise
   atlanır** (varsayılan Seviye 3); regülasyon/veri hassasiyeti sinyali **MVP'de de
   sorulur** — kişisel veri işleniyorsa MVP olmak güvenlik baseline'ını (§4) muaf tutmaz.
8. **Görsel kimlik** — frontend var mı, varsa design system kaynağı (Figma+tasarımcı
   ekip/ajans/CoE'nin mevcut component kütüphanesi/henüz yok).
9. **Onay yapısı** — iş kararlarını kim onaylıyor; teknik kararlar (ADR) **varsayılan olarak**
   yalnız oturum-içi Teknik Sorumlu mu onaylıyor. Bu, **tek bir proje-geneli bayrak değil**,
   üç bağımsız soruya cevaptır: (a) varsayılan onay, (b) KVKK/PII'ye dokunan kararlar için
   ek onay mercii var mı (örn. Bilgi Güvenliği ekibi), (c) çok-tesis/çok-tenant/ölçek
   varsayımı içeren kararlar için ek onay mercii var mı (örn. Mimari Ekip). Bir ADR bu
   koşullardan birine, ikisine veya hiçbirine dokunabilir — Faz 2'de her ADR **kendi
   içeriğine göre ayrı ayrı** değerlendirilir, statü akışını (`Mimari İncelemede` vs.
   doğrudan `Kabul edildi`) bu belirler, tek bir proje-geneli varsayım değil.

### Faz 1 — Tier 0 Bootstrap

**Girdi:** Faz 0'da doldurulan Proje Künyesi
**Agent görevleri:** `tier0/RULES.md` §1, §3, §5'teki parantezler için sırayla hedefli
sorular sor; cevapları taslak halinde yaz; onay bekle.
**İnsan görevleri:** §1 Proje Kimliği ve §3 Dil Sözleşmesi'ni birlikte doldur. §4 Güvenlik
Baseline zaten CoE varsayılanıyla dolu — sadece domain-özel uyum notu (KVKK/GDPR vb.)
eklenip eklenmeyeceği değerlendirilir, madde yeniden yazılmaz. §5 Kalite Kapıları'ndaki
sayısal eşikler bu aşamada taslak/geçici olabilir — Faz 2 sonrası netleşir.
**Kapı:** §1, §3 dolu; §5 en az taslak değerde.

### Faz 2 — Temel Mimari Kararları (ADR seti)

**Girdi:** Faz 1 çıktısı
**Agent görevleri:** Her büyük karar için (stack, hosting/altyapı, veri deposu, auth modeli)
seçenekleri **yalnızca `tier1/APPROVED-STACKS.md` kataloğundan** sunar — katalog dışı bir
stack'i asla icat etmez veya önermez (bkz. `tier0/RULES.md` §6). Bu, kurumsal governance
için kritik: onaysız bir stack'e efor harcanıp sonradan `mimari-gate`'te reddedilmesi,
tamamen önlenebilir bir kayıptır. Katalogda uygun seçenek yoksa agent bunu açıkça
"katalog dışı ihtiyaç" olarak işaretler ve karar CoE/katalog sahibine yönlendirilir —
sessizce katalog dışına çıkılmaz. Teknik Sorumlu seçince `tier0/adr/0000-template.md`
formatında taslak ADR yazar.
**İnsan görevleri:** Teknik Sorumlu kararı verir; Tasarım Sorumlusu kullanıcı/performans
kısıtı gibi domain girdisi sağlar.
**Çıktı:** `ADR-0001`, `ADR-0002`, ... — en az stack, hosting, veri deposu, auth modeli.
**Kapı:** Bu 4 kararın ADR'si onaylı ve kayıtlı.

> Kurumda ADR'lerin ayrıca bir Mimari Ekip ve/veya Bilgi Güvenliği Ekibi tarafından
> onaylanması gerekiyorsa (Faz 0'da netleşir), Teknik Sorumlu'nun oturum-içi onayı ADR'yi
> `Kabul edildi` yapmaz — `Mimari İncelemede` statüsüyle kaydedilir ve bu liste Faz 6 çıkış
> kapısında boş olmalıdır (bkz. `tier0/adr/0000-template.md`,
> `skills/design-flow-agent/SPEC.md` §4 Faz 2).

### Faz 3 — Tier 2 Domain İskeleti (tier1'den ÖNCE)

**Girdi:** Faz 2 ADR'leri
**Agent görevleri:** `tier2/README.md`'deki 1-2-3-5 numaralı dokümanları (Ürün Özeti,
Domain Modeli, Veri Şeması taslağı, Ekran Kataloğu taslağı) Tasarım Sorumlusu'yla birlikte
doldurur — bu aşamada implementasyon detayı değil, **isimlendirilmiş varlıklar/ekranlar/
kurallar** hedeflenir.
**Kapı:** Domain modelindeki ana varlıklar ve hangi alanların hassas/PII olduğu netleşmiş.

> Bu faz `tier1`'den önce gelir çünkü `tier1`'in "Denetim Kaydı" ve "Girdi Doğrulama"
> gibi bölümleri, hangi varlığın/alanın hassas olduğunu bilmeden anlamlı doldurulamaz.

### Faz 4 — Tier 1 Doldurma (artık kolay kısım)

**Girdi:** Faz 2 (ADR'ler) + Faz 3 (domain iskeleti)
**Sıra:** `tier1/README.md`'yi (yoğunluk kuralı, **Stack vs Cross-Cutting playbook**
ayrımı) tekrar oku → backend → frontend → infra → testing (backend/veri genelde
diğerlerini gater, bu yüzden önce o) → **authentication (zorunlu, `tier0/RULES.md` §12)**
→ **observability (zorunlu, `tier0/RULES.md` §11)** → **api-design (zorunlu,
`tier0/RULES.md` §14)** → caching/messaging (yalnız ihtiyaç varsa) →
**service-integration (yalnız kurumsal sistem entegrasyonu ihtiyacı varsa, `tier0/RULES.md`
§13 — ama varsa Ocean tek seçenek)**.
**Agent görevleri:** Her bölüm için (Katmanlama, Yetkilendirme, ...) ADR'den ve domain
iskeletinden zaten bilinen cevabı **Ne/Neden/Kural/Referans** şekline taslak olarak
döker; Teknik Sorumlu onaylar/düzeltir. Authentication, observability ve api-design için
"kullanalım mı" diye sorulmaz — `Zorunlu` statüsü zaten kesindir, yalnız proje-özel alanlar
(SSO client adı, servis adı, gerçek base URL vb.) doldurulur. **Authentication ile
authorization karıştırılmaz** — authentication (kimlik doğrulama) Red Hat SSO'ya zorunlu
devredilir, authorization (RBAC/izin) backend playbook'unun kendi bölümünde proje-özel
kalır. Caching/messaging/service-integration için önce ihtiyaç sorulur; ihtiyaç yoksa o
dosya hiç oluşturulmaz. Service-integration'da ihtiyaç varsa (caching/messaging'in aksine)
"hangi araç" sorusu sorulmaz — Ocean tek seçenektir.
**Referans alanı hakkında (greenfield'e özgü):** Henüz kod yoksa `Referans` alanına gerçek
bir dosya yolu yazılamaz — bunun yerine ilgili ADR'ye işaret edilir ve alanın yanına
`(TBD — ilk implementasyondan sonra backfill edilecek)` notu düşülür. **Bu proje ilgili
pattern'i ilk kez implemente ettiğinde, o dosya yolu geri gelip Referans alanına yazılır** —
bu adım atlanırsa playbook zamanla gerçek koddan kopar (tam da `tier1/README.md`'nin
uyardığı doc-drift).
**Kapı:** Dört playbook'un tamamındaki `Kural` alanları somut (belirsiz değil); `Referans`
alanları ya gerçek yol ya da açık `TBD` etiketi taşıyor.

**Budama:** Bu şablon deposu (CoE'nin kaynağı) bilerek birden fazla onaylı stack barındırır
— ama projenizin kopyası bunun bir alt kümesi olmalı. Faz 2'de bir stack seçildikten sonra,
**seçilmeyen kardeş stack playbook'ları** (aynı katmanda, örn. backend'de kullanılmayan
diğer dillerin dolu playbook'ları) silinir — gerçekten poliglot bir sistem değilseniz.
Bu adım kolayca atlanır, `design-flow-agent` Faz 4 sonunda hatırlatır.

### Faz 5 — Tier 2 Tamamlama

**Girdi:** Faz 4'te netleşen teknik kurallar
**Agent görevleri:** `tier2/README.md`'deki kalan maddeleri (6 Güvenlik&Uyum, 7 Test
Stratejisi Detayı, 8 Dev/Ops, 9 Roadmap, 10 varsa Domain Süreç Şablonu, 11 UAT taslağı, 12
ADR indeksi) artık `tier1`'de netleşmiş kurallara referansla doldurur — aynı cümleyi iki kez
yazmaz, `tier1`'e işaret eder.
**Kapı:** 12 maddelik listenin tamamı en az taslak seviyesinde var.

> **Faz 3-5 tek geçiş olmak zorunda değil:** henüz kod yazılmadan, kapsamı dilim dilim
> (bugün auth, yarın frontend) tasarlamak isterseniz, ilk dilimden sonraki her yeni dilim
> `skills/design-flow-agent/SPEC.md`'deki "Faz 6 Öncesi — Kapsam Dilimi Rotası"nı izler —
> aynı Faz 3-5 görevleri, artık önceki dilimlerle tutarlılık kontrolü eklenmiş halde. Bu
> prosedür dosyası (insan-okur "neden" versiyonu) bu rotanın operasyonel detayını tekrar
> etmez, yalnızca işaret eder — detay SPEC.md'dedir.

### Faz 6 — Çıkış Kapısı

Kodlamaya geçmeden önce bir tamlık kontrolü yapılır:

- [ ] `tier0/RULES.md` §1, §3, §5 dolu
- [ ] Stack/hosting/veri/auth için ADR'ler onaylı
- [ ] `Mimari İncelemede` statüsünde bekleyen ADR kalmadı (hepsi `Kabul edildi`)
- [ ] `tier2` 1-5 numaralı dokümanlar dolu
- [ ] `tier1` dört stack playbook'u dolu (Referans'lar gerçek veya TBD-etiketli)
- [ ] `tier1/playbooks/playbook-authentication.md` dolu (Zorunlu — eksikse kapı geçilmez)
- [ ] `tier1/playbooks/playbook-observability.md` dolu (Zorunlu — eksikse kapı geçilmez)
- [ ] `tier1/playbooks/playbook-api-design.md` dolu (Zorunlu — eksikse kapı geçilmez)
- [ ] Caching/messaging: ya doldurulmuş ya da "gerekli değil" diye açıkça işaretli
- [ ] `tier1/playbooks/playbook-service-integration.md`: ihtiyaç varsa dolu, yoksa "gerekli
  değil" diye açıkça işaretli (ihtiyaç varsa ve dolu değilse kapı geçilmez)
- [ ] `tier2` 6-12 numaralı dokümanlar en az taslak

Bu kontrol elle yapılabilir; kurumda `mimari-gate` benzeri bir pre-implementation gate
süreci varsa, bu tamlık listesi doğrudan onun girdisi olarak kullanılabilir. Kapı
geçtikten sonra ekip implementasyona geçer ve bundan sonraki her yeni yetenek
`tier0/procedures/add-new-capability.md`'yi izler.

---

## 4. Oturum Mekaniği

Her tasarım oturumu aynı döngüyü izler:

1. Agent, o oturumun kapsamındaki dosyanın **güncel halini** ve ilgili önceki ADR'leri okur.
2. Agent, o oturumun kapsamındaki parantezler için **toplu** (tek tek değil, bölüm bazlı)
   hedefli sorular sorar.
3. İnsanlar cevaplar.
4. Agent taslağı yazar (henüz dosyaya değil, gösterir).
5. İnsanlar onaylar veya düzeltir.
6. **Yalnızca onay sonrası** agent dosyaya yazar; değişiklik küçük, gözden geçirilebilir bir
   commit olarak kaydedilir (`tier0/RULES.md` §2, madde 4).
7. Oturum, bir sonraki oturumun kapsamı belirlenerek kapanır.

Bir oturumda tüm `tier1`'i doldurmaya çalışmayın — bölüm bazlı ilerleyin (örn. "bugün sadece
backend playbook'un Auth + Yetkilendirme bölümleri").

---

## 5. Ölçek Notu

Küçük ve büyük proje **aynı 6 fazı, aynı sırayla** izler. Fark:

- **Küçük proje:** Faz 1+2 tek oturumda birleşebilir; `tier1`'in bazı bölümleri ("Harici
  Servis Entegrasyonları" gibi) proje kapsamında yoksa playbook'tan silinir, boş bırakılmaz.
- **Büyük proje:** Her faz kendi oturumuna/oturumlarına ayrılır; Faz 4 birden fazla teknik
  sorumlu arasında playbook bazında paylaşılabilir (biri backend, biri frontend), ama sıra
  (önce ADR+domain, sonra tier1) değişmez.

---

## 6. Sonraki Adım

Bu prosedür yalnızca greenfield tasarım fazını kapsar. İki farklı "sonraki adım" var,
karıştırılmamalı (bkz. yukarıdaki Giriş kontrolü (b) vs (c)):

- **Yeni feature geliştirme (b):** Bu proje zaten bu akıştan geçmiş — tier0/tier1/ADR'ler
  hazır, şimdi üstüne bir yetenek ekleniyor. Bu, kapsam dışı değil, **bu şablonun bir
  sonraki genişletmesi** — `skills/design-flow-agent/SPEC.md`'deki "Faz 6 Sonrası: Yeni
  Yetenek Rotası" bölümü ve `tier0/procedures/add-new-capability.md` üzerinden yürütülür
  (kod-öncesi, Faz 6'dan önceki eşdeğeri için bkz. Faz 5 sonundaki not — "Faz 6 Öncesi —
  Kapsam Dilimi Rotası").
- **Devralınan/organik sistem (c) — kapsam dışı, ileride yazılacak:** Bu proje hiç bu
  akıştan geçmemiş, tier0/tier1 yok, dışarıdan gelen bir codebase. Bu şablonu böyle bir
  codebase'e uygulama, ve o codebase üzerinde refactor/change/bugfix akışı **ayrı bir
  prosedür** olarak ayrıca tasarlanacak — o akış muhtemelen "önce mevcut kodu tier0/tier1/
  tier2 şablonuna karşı tersine-envanterle, sonra sapmaları ADR ile kayıtla" şeklinde farklı
  bir sırayı izleyecektir, buradaki "önce karar, sonra kod" sırasının tersi.
