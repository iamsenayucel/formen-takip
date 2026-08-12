# RULES.md — Çekirdek Geliştirme Kuralları (Tier 0)

> Bu dosya **tool-agnostiktir**: Cursor, Claude Code, GitHub Copilot, Antigravity veya
> başka bir AI coding asistanıyla çalışıyor olun fark etmez, bu kurallar aynen geçerlidir.
> Belirli bir aracın bu dosyayı nasıl "yükleyeceği" `adapters/` altındadır — burada araca
> özel hiçbir şey yoktur.
>
> Bu dosya **stack-agnostiktir**: framework/dil seçimlerine göre değişen kalıplar burada
> değil, `tier1/` altındaki playbook'larda yer alır. RULES.md sadece "hangi stack olursa
> olsun geçerli olan" disiplini tanımlar.
>
> **Öz-kontrol (zorunlu, her değişiklikte):** Bu dosyaya yapılan herhangi bir ekleme/değişiklik,
> commit edilmeden önce yukarıdaki iki agnostiklik ilkesine karşı mekanik olarak kontrol edilir
> — RULES.md'nin felsefesi kendi gövdesiyle çelişemez. Soru: **eklenen/değiştirilen satır somut
> bir framework/kütüphane/ürün adı içeriyor mu** (örn. bir veritabanı, SSO sağlayıcısı,
> gözlemlenebilirlik ürünü, cloud servisi)? İçeriyorsa, yalnızca Zorunlu cross-cutting
> mandate'ların (Bölüm 11-14) zaten kurulu deseniyle uyumluysa kabul edilir — yani "bu platform
> proje bazında seçilmez/değiştirilmez, hangi ürün olduğu `tier1/playbooks/...`'dedir" şeklinde
> isim playbook'a yönlendirilir, RULES.md'de tekrar edilmez. Uymuyorsa bu bir felsefe sapmasıdır
> ve commit'ten önce düzeltilir, not edilip ertelenmez (bkz. Bölüm 11-13'ün 2026-07-20 revizyonu
> — Prometheus/Loki/Grafana/Opsgenie, Red Hat SSO/Keycloak, Ocean isimlerinin RULES.md'den
> çıkarılıp playbook'lara taşınması, bu maddenin eklenme nedenidir).
>
> Tüm dosya referansları bu repo kökünden itibarendir (örn. `tier1/playbooks/playbook-backend-nestjs.md`).

---

## 0. Bu şablon nasıl kullanılır

Aşağıdaki liste hızlı bir özettir. **Sıfırdan (greenfield) bir projeye bu şablonu
uyguluyorsanız**, parantezleri hangi sırayla, kimlerin, nasıl bir oturum akışıyla
dolduracağınızı adım adım anlatan `tier0/procedures/new-project-design-flow.md`'yi izleyin
— özellikle `tier1/`'deki çok sayıda parantez, doğru sırayla gidilirse görüldüğünden çok
daha kolay dolar.

1. Bu repoyu yeni projenin köküne kopyala (veya bu repoyu template olarak `gh repo create --template` ile kullan).
2. `tier0/RULES.md`'yi olduğu gibi bırak — sadece `[PROJE_ADI]`, `[ORG_ADI]` gibi köşeli parantez placeholder'ları doldur.
3. `tier1/*.TEMPLATE.md` dosyalarından projenin gerçek stack'ine uyanları kopyalayıp `.TEMPLATE` uzantısını kaldırarak doldur; kullanılmayanları sil.
4. `adapters/` altından hangi AI aracını kullanıyorsan onun klasöründeki kurulum adımlarını izle.
5. `tier0/adr/0000-template.md`'yi kullanarak ilk gerçek mimari kararını (stack seçimi, altyapı, vb.) yaz.
6. `tier2/README.md`'deki doküman setinden projeye uygun olanları oluşturmaya başla.

---

## 1. Proje Kimliği (Proje Künyesi)

> Her yeni proje bu bölümü doldurmadan RULES.md'yi kullanmaya başlamamalı — agent'ın
> stack/kapsam/terminoloji halüsinasyonu yapmasının en büyük nedeni bu bölümün boş kalması.
> Bu bölüm `tier0/procedures/new-project-design-flow.md` Faz 0'ın çıktısıdır — Faz 2 ve
> sonrası, buradaki cevaplara **tekrar sormadan** referans verir.

### Temel Kimlik
- **Proje adı / amaç:** `Karaman üretim tesislerinde formen performansını izleyen karar destek sistemi`
- **Proje türü:** `Devralınan sistem üzerinde çalışma`
- **Geliştirme disiplini:** `Gerçek/üretim projesi`
  - *(yalnızca MVP ise)* **MVP türü:** `Uygulanamaz (Gerçek Proje)`

### Kim Kullanacak
- **Organizasyonel kapsam:** `Tek departman/fonksiyon (Üretim)`
- **Kullanıcı kimliği:** `İç çalışan`
- **Çalışan tipi (iç kullanıcıysa):** `Beyaz yaka (Üst yönetim, salt-okunur)`
- **Erişim izolasyonu:** `Yalnız VPN/kurum içi`

> ⚠️ **Kritik:** Kullanıcı kimliği "dış müşteri/bayi" ise, Bölüm 12'deki merkezi kimlik
> sağlayıcı zorunluluğu iç-kullanıcı varsayımıyla yazılmıştır — dış kullanıcılar için ayrı
> bir CIAM (Customer Identity) ihtiyacı değerlendirilmeli (henüz kataloğa eklenmedi, bkz.
> `tier1/catalog/cross-cutting.md`). Bu durumda Faz 2'de agent bunu "katalog dışı ihtiyaç"
> olarak işaretlemeli, sessizce merkezi kimlik sağlayıcıyı (bkz. `tier1/playbooks/
> playbook-authentication.md`) uygulamamalı.

### Ölçek
- **Kullanıcı sayısı:** `1-100 (Sadece üst yönetim)`
- **Büyüme beklentisi:** `Durağan`

### Uygulama Tipi
- **Uygulama tipi:** `Fullstack web`
- **Temel alan (çoklu seçilebilir):** `İş uygulaması, AI & ML (Anomali Tespiti)`

### Kritiklik ve Uyum
- **İş kritiklik seviyesi:** `Seviye 2 — Önemli`
- **Regülasyon/veri hassasiyeti sinyali:** `Yok`

### Görsel Kimlik
- **Frontend var mı:** `Evet`
- **Design system:** `Yok (Tailwind kullanılıyor)`

### Onay Yapısı
- **İş kararları onayı:** `Tasarım Sorumlusu yürütür`
- **Teknik kararlar (ADR) onayı — tek bir bayrak değil, bir kural (aşağıdaki 3 satır
  bağımsızdır, her ADR'ye ayrı ayrı uygulanır — bkz. Bölüm 8, `Mimari İncelemede` statüsü):**
  - Varsayılan: `Teknik Sorumlu onayı yeterli`
  - KVKK/PII'ye dokunan kararlar (veri modeli/erişim/saklama): `Ayrıca Bilgi Güvenliği onayı gerekir`
  - Çok-tesis/çok-tenant/ölçek varsayımı içeren kararlar: `Ayrıca Mimari Ekip incelemesi gerekir`

### AI Bağlam Dosyası Sorumlusu (Steward)
- **Steward:** `Teknik Sorumlu/Lider` — sorumluluk role bağlıdır, kişiye değil;
  kişi değiştiğinde rol devam eder. "Herkesin sorumluluğu" fiilen hiç kimsenin sorumluluğu
  olur ve bu dosyalar sessizce bayatlar.

### Kapsam
- **Stack:** `FastAPI, React+Vite, PostgreSQL, Docker`
- **Domain terimleri:** `KPI: Key Performance Indicator, GSF: Gerçekleşen Standart Fire`
- **Kapsam dışı (non-goals):** `Veri girişi sağlamaz, tamamen salt okunurdur`

### MVP Disiplini Ölçeklenmesi

> Daha önce ertelenmiş bir konuydu — "Geliştirme disiplini" alanının (yukarıda) `MVP` mi
> `Gerçek/üretim projesi` mi olduğuna göre **ne kadar** dokümantasyon/derinlik gerektiği
> hiçbir yerde açık değildi, agent'ın inisiyatifine kalıyordu. Bu bölüm o boşluğu kapatır.

**Ölçeklenen şey: derinlik/hacim, zorunluluk değil.** Aşağıdaki üç eksen MVP/Seviye'ye göre
yalınlaşır veya derinleşir — ama Bölüm 4 (Güvenlik Baseline), Bölüm 11-13'teki Zorunlu
cross-cutting mandatlar (gözlemlenebilirlik, authentication, kurumsal sistem entegrasyonu)
**hiçbir zaman** MVP gerekçesiyle atlanmaz veya gevşetilmez — "MVP'de auth'u basitleştirelim"
gibi bir karar bu dosyanın kapsamında değildir, geçersizdir.

1. **`tier2/` doküman derinliği** (`tier2/README.md`'deki 12 madde) — `MVP — Atılacak`
   projelerde yalnız kritik olanlar yazılır (Ürün Özeti, Domain Modeli, Veri Şeması, Güvenlik
   Notu — bkz. Bölüm 4/11-13); `Uygulama Yol Haritası` (madde 9) faz listesi + bağımlılık
   kadar yalın kalabilir, bağımlılık grafiği/risk kaydı/agent-kickoff-prompt-şablonu gibi
   eklentiler zorunlu değildir. `MVP — Evrilecek` ve `Gerçek/üretim` projelerde 12 maddenin
   tamamı beklenir; Seviye 1 (kritik) projelerde madde 9 ayrıca risk kaydı + teknik borç
   kaydı + faz-bazlı human-gate tanımı taşır — bu derinlik Seviye 1 için doğru referans
   noktasıdır, MVP dry-run için değil.
2. **Test coverage eşiği** (Bölüm 5, `playbook-testing-<stack>.md`'deki risk-bazlı tablo) —
   MVP'de proje-geneli minimum eşik gevşetilebilir, ama iş-kritik modüller (auth, ödeme,
   veri-bütünlüğü) için yüksek eşik MVP'de de geçerliliğini korur; "MVP olduğu için hiç test
   yok" bir seçenek değildir.
3. **ADR titizliği** (Bölüm 8) — MVP'de küçük/geri-alınabilir kararlar için ADR yazımı
   esnetilebilir (Tasarım Sorumlusu'nun sözlü onayı yeterli olabilir), ama KVKK/PII'ye
   dokunan veya çok-tesis/ölçek varsayımı içeren kararlar (Proje Künyesi'ndeki Onay Yapısı
   satırları) MVP'de de aynı iki-gate modelini izler — bu gate MVP'ye özel gevşemez.

**Kural:** Bir agent bir dokümanın/testin/gate'in "MVP olduğu için" atlanabileceğine karar
verdiğinde, önce bu üç eksenden hangisine girdiğini (derinlik mi, zorunluluk mu) ayırt eder;
zorunluluk eksenindeyse (Bölüm 4/11-13, KVKK/ölçek gate'leri, iş-kritik modül coverage'ı)
MVP gerekçesi geçersizdir ve bu açıkça (sessizce değil) kullanıcıya/Tasarım Sorumlusu'na
bildirilir.

---

## 2. Kodlama Felsefesi

Bu paket, AI asistanla "vibe coding" yaparken ekibin çoğunlukla kaçırdığı şeyi hedefler:
**hız ile disiplin arasındaki dengeyi bir defa yazıp her session'da otomatik uygulamak.**

1. **Kapsam saygısı.** Bir görev ne istendiyse onu yapar. İstenmeyen refactor, istenmeyen
   soyutlama, "ileride lazım olur" diye eklenen katman — yasak. Üç benzer satır, erken
   soyutlamadan iyidir.
2. **Test-first / test-alongside.** Yeni davranış, onu doğrulayan bir testle birlikte gelir.
   Test yazmadan "çalışıyor gibi görünüyor" demek yeterli değildir.
3. **Zorunlu self-review.** Kod üretildikten sonra, commit'lenmeden önce, üretilen diff
   yeniden okunur: gereksiz karmaşıklık var mı, güvenlik checklist'i (Bölüm 4) uygulandı mı,
   var olan bir pattern yeniden icat edildi mi (bkz. Bölüm 6 — halüsinasyon önleme).
4. **Küçük, geri alınabilir adımlar.** Büyük tek commit yerine, her biri kendi başına
   anlamlı ve test edilebilir küçük adımlar. Bir adım yanlış giderse geri almak ucuz olmalı.
5. **Yorum değil, isim.** Kodun NE yaptığını isimler anlatır. Yorum sadece NEDEN'i, yani
   kod okuyarak çıkarılamayacak bir kısıtı/geçmişi anlatır.
6. **Context/oturum disiplini.** Bir oturum (session/context) tek bir işe bağlı kalır — bir
   yetenek ekleme (`tier0/procedures/add-new-capability.md`) veya bir bug-fix/CR
   (`tier0/procedures/production-bugfix-cr.md`); iş bitince ilgisiz bir ikinci işe aynı
   oturumda geçilmez, yeni bir oturum açılır. Kalıcı olması gereken hiçbir bilgi (bir karar,
   bir kısıt, bir kural) yalnızca konuşma geçmişinde tutulmaz — ADR/RULES.md/STATE.md gibi
   dosyalara yazılır, agent buna "hatırlayarak" değil dosyayı okuyarak erişir. Bu ikisi
   context büyümesine karşı **birincil** savunmadır; kullanılan AI aracının kendi otomatik
   context-özetleme/sıkıştırma mekanizması (`adapters/<araç>/README.md` "Context Disiplini")
   bir yedektir, birincil savunma değil — özetleme lossy'dir, erken talimatların/kısıtların
   sessizce kaybolma riski taşır. Bir oturumda üretilen kod satırı sayısı tek başına bir
   eşik/tetikleyici **değildir** — aynı gerekçeyle (`tier0/procedures/production-bugfix-cr.md`
   madde 3'teki "Neden satır sayısı değil" notu) satır sayısı ne context tüketimiyle ne
   riskle doğrudan orantılıdır; `tier0/procedures/risk-tiering.md`'de yalnızca
   bilgilendirici bir soft-metrik olarak izlenir.

---

## 3. Dil ve İsimlendirme Sözleşmesi

> İçerik projeye göre değişir ama **sözleşmenin açıkça yazılı olması evrenseldir** — yoksa
> her session'da agent farklı bir dil/isimlendirme kararı üretir ve kod tabanı tutarsızlaşır.

- **Kullanıcıya görünen metin:** `Türkçe`
- **Kod içi tanımlayıcılar (değişken/fonksiyon/sınıf adı):** `İngilizce`
- **Commit mesajları:** `İngilizce, Conventional Commits`
- **Hata mesajları / log'lar:** `Geliştiriciye İngilizce, Kullanıcıya Türkçe`
- **Karma durumlarda karar kuralı:** `Kullanıcı görürse Türkçe, kod/log İngilizce`

---

## 4. Güvenlik Baseline — Her Değişiklikte Zorunlu Kontroller

Bu checklist **her endpoint, her form, her DB sorgusu için mekanik olarak** uygulanır —
"bu sefer gerek yok" diye atlanmaz.

1. **Yetkilendirme** — Her endpoint/aksiyon, çağıran kimliğin buna yetkisi olduğunu
   doğrular. "Login olmuş" yeterli değildir; "bu spesifik aksiyona izinli mi" sorusu
   ayrıca sorulur.
2. **Girdi doğrulama** — Dışarıdan gelen her veri (body/query/param/dosya) şema ile
   doğrulanır. "TypeScript tipi var" doğrulama değildir — runtime şema (Zod/Joi/Pydantic vb.)
   zorunludur.
3. **Hassas veri koruma** — PII/secret alanlar at-rest şifrelenir, log'a asla düz metin
   yazılmaz, ve **harici bir servise (üçüncü parti API, LLM sağlayıcı vb.) hiçbir hassas
   veri, o karar bir ADR'de açıkça yazılmadan gönderilmez.** Kullanıcı kimlik verisi için
   (ad/e-posta gibi görünen alanlar) bu kuralın identity-özel somutlaşması:
   `tier1/playbooks/playbook-authentication.md` "Kimlik Verisinin Kalıcılaştırılması" bölümü
   — genel kural, uygulama DB'sinin yalnızca stabil bir tanımlayıcı (sicil no/`sub`) tutması,
   ad/e-posta gibi alanların SSO'dan runtime'da okunup **hiç kalıcılaştırılmamasıdır.**
4. **Denetim kaydı (audit)** — Her durum-değiştiren aksiyon audit log'a yazılır ve
   **gerçek aktöre atfedilir** — bir kullanıcı başka bir kimlik altında işlem yapıyorsa
   (impersonation, service-account, vb.) audit kaydı gerçek aktörü göstermelidir.
   **Audit kaydına yazılan hiçbir alan, o alanın DB'de şifreli tutulma amacını bypass
   etmemelidir** — yani "audit için okunabilir olsun" diye şifreli bir alanı çözüp log'a
   düz metin yazmak yasaktır.
5. **Hız sınırlama** — Hassas/pahalı endpoint'ler rate-limit'lenir, **ve bu limit kimlik
   bazlıdır, yalnızca IP bazlı değildir** — aksi halde aynı NAT/proxy arkasındaki tüm
   kullanıcılar birbirinin kotasını tüketir.
6. **Çıktı kaçışı** — Kullanıcı girdisi veya AI-üretimi içerik render edilirken XSS/injection
   riskine karşı kaçışlanır (`dangerouslySetInnerHTML` benzeri kaçışları atlayan API'ler,
   açık bir gerekçe olmadan kullanılmaz).
7. **Sır yönetimi** — Kod, konfigürasyon dosyaları (`.env` dahil) veya versiyon kontrolüne
   **hiçbir zaman** düz metin secret (API anahtarı, DB şifresi, imzalama anahtarı, üçüncü
   parti token) girmez. Sır'lar yalnızca onaylı, merkezi bir sır yönetimi servisinden
   runtime'da inject edilir — bu servis proje bazında seçilmez/değiştirilmez, hangi ürün
   olduğu `tier1/catalog/infra.md`'dedir; başka bir sır deposu (kod içi sabit, ayrı bir 3.
   parti vault, DB'de düz metin) kullanılmaz. `.env` dosyaları yalnızca yerel geliştirme
   içindir, asla commit edilmez ve asla production secret'ı taşımaz. Somut enjeksiyon
   mekanizması (`tier1/playbooks/playbook-infra-terraform-aws.md` "Sır (Secret) Yönetimi")
   ve uygulama-kodu tarafındaki okuma deseni (ilgili `tier1/playbooks/playbook-backend-*.md`
   "Konfigürasyon & Sır Yönetimi") ayrı dosyalarda, burada tekrar edilmez.

### 4.1 Bu maddeler neden bu kadar spesifik

Bu 7 madde soyut "güvenli kod yaz" tavsiyesi değil — özellikle 3, 4, 5 ve 7. maddeler somut,
tekrar eden hata sınıflarını doğrudan hedefler: şifreli tutulması gereken bir kimlik
alanının audit log'a düz metin yazılması; harici bir servise (örn. bir LLM sağlayıcısına)
ayrı bir onay olmadan PII gönderilmesi; kimlik-bazlı olması gereken bir hız sınırlamasının
IP-bazlı yapılıp aynı ofis/NAT arkasındaki kullanıcıları birbirine kilitlemesi; bir
secret'ın `.env`'e veya koda gömülüp repoya sızması. Bunlar "muhtemelen olur" değil, bu
sınıf sistemlerde **sık görülen, öngörülebilir** hata kalıplarıdır — kural seti bu
öngörülebilirlik varsayımıyla yazılmıştır. Madde 7'nin mekanik uygulanabilirliği
`tier1/playbooks/playbook-cicd-security.md`'deki secret-pattern taramasıyla desteklenir —
kod review'a bırakılmaz, CI'da otomatik yakalanır.

---

## 5. Kalite Kapıları

> Sayısal eşikler proje bazlı doldurulur; **var olması** evrenseldir.

| Kapı | Eşik | Nasıl ölçülür |
|---|---|---|
| Test coverage (kritik yol) | `%80` | `Coverage Report` |
| Bundle / paket boyutu bütçesi | `Yok` | `Yok` |
| Performans SLO (p95 latency vb.) | `Yok` | `Yok` |
| PR merge kriteri | `Yeşil CI + 1 Review` | — |

Bu tablo doldurulmadan bir proje "production-ready" sayılmaz — kalite, insan yorumuna değil
ölçülebilir bir eşiğe bağlanır.

Bu kapılar, nedeni ne olursa olsun (uzun bir oturumda context-drift dahil) kalite düşüşünü
yakalayan objektif backstop'tur — Bölüm 2 madde 6'daki context/oturum disiplini bunu
**önler**, bu tablo önlenemeyeni **yakalar**; ikisi birbirinin yerine geçmez.

---

## 6. Halüsinasyon Önleme / Kesinlik Kuralları

AI asistanların en pahalı hataları "yaratıcı" oldukları anlarda, yani var olmayan bir şeyi
var gibi davrandıklarında olur. Aşağıdakiler **hiçbir stack'te istisnasız** geçerlidir:

1. **Var olmayan API/kütüphane/fonksiyon icat etme.** Bir import yazmadan önce o paketin
   gerçekten bağımlılıklarda olduğunu (package.json/pyproject.toml/go.mod vb.) doğrula.
   "Muhtemelen böyle bir metod vardır" diye kod yazma.
2. **Var olmayan enum/permission/şema alanı icat etme.** Bir izin adı, bir durum değeri,
   bir DB kolonu kullanmadan önce gerçek tanımını (type/enum/schema dosyası) oku.
3. **"Zaten böyle bir pattern var" iddiasını dosya referansıyla destekle.** "Bu zaten X'te
   yapılıyor" demek, `dosya.ts:42` gibi somut bir referans gerektirir — varsayım değil.
4. **Playbook'ta olmayan bir durumla karşılaşınca sessizce icat etme.** Ya kod tabanındaki
   en yakın benzer örneği canonical referans olarak göster, ya da "bu konuda belirlenmiş bir
   pattern yok, ekiple teyit gerekir" diye açıkça belirt.
5. **Kod tabanı hakkındaki sayıları (dosya sayısı, satır sayısı, "N tane X var" gibi
   ifadeleri) elle/ezberden yazma — gerçek bir listeleme komutuyla doğrula.** (Bu kuralın
   kendisi, bir projede kurulum dokümanının "40 dosya" dediği ama gerçekte 47 dosya olduğu
   bir doc-drift vakasından geliyor — küçük görünür ama agent'ın güvenini boşa çıkarır.)
6. **Belirsizlik durumunda dur ve sor / bayrakla — üretme.** Kapsamı netleştirecek bir soru
   sormak, yanlış varsayımla ilerlemekten her zaman ucuzdur.
7. **Onaylı bir kararın (stack sürümü, araç, mandate) tam şekli sürtünme çıkarınca sessizce
   farklı bir şekle/sürüme kayma.** Bir ADR/katalog `Referans`/`Onaylı`/`Zorunlu` satırı
   belirli bir major sürümü veya aracı işaret ediyorsa ve gerçek implementasyon o tam şekle
   uymuyorsa (kırılan bir kalıp, geçmeyen bir kurulum adımı), bu **"bağımlılık pin'i" veya
   "implementasyon detayı" değil, kararın kendisinden bir sapmadır** — icat etmeme kuralıyla
   aynı sınıf. Sürtünme raporlanır, seçenekler sunulur, onay alınır, sonra uygulanır —
   sessizce "çalışan" bir alternatife geçilmez. Operasyonel karşılığı (tetikleyici + gerekli
   çıktı): `skills/design-flow-agent/SPEC.md` §2.7.

---

## 7. Test Stratejisi (İlke)

- **Piramit:** çok sayıda hızlı birim testi, orta sayıda entegrasyon testi, az sayıda ama
  kritik-yolu kapsayan uçtan-uca (e2e) testi. Araç seçimi (Vitest/Jest/pytest/Playwright vb.)
  `tier1/playbooks/playbook-testing-<stack>.md`'dedir.
- **Kritik yol tanımlı olmalı.** Hangi kullanıcı akışlarının e2e ile korunduğu açıkça
  listelenir — "her şeyi test et" bir strateji değildir, kritik yolu kaybetmemek stratejidir.
- Bozuk bir testle karşılaşıldığında izlenecek teşhis akışı: `tier0/procedures/fix-failing-test.md`.

---

## 8. Mimari Kararlar (ADR)

Stack/altyapı/güvenlik modeli gibi geri dönüşü pahalı kararlar bir ADR (Architecture
Decision Record, MADR 3.0 formatı) ile yazılır. Şablon: `tier0/adr/0000-template.md`.
Bir ADR: **bağlam → seçenekler → karar → sonuçlar (artı/eksi)** yapısını izler ve
numaralandırılmış sırayla `tier2/` altında (veya projenin kendi `docs/adr/`'ında) birikir.
ADR'ler proje-özeldir, bu RULES.md dosyasına asla taşınmaz — ama "ADR yazma süreci"
evrenseldir.

---

## 9. Prosedür Şablonları

- `tier0/procedures/new-project-design-flow.md` — **sıfırdan bir proje bu şablonu
  benimsediğinde, ilk kod satırından önceki tasarım fazı** için: roller, tool-agnostik Plan
  Mode tanımı, `tier0`→ADR→`tier2` domain iskeleti→`tier1`→`tier2` tamamlama sırası, ve
  kodlamaya geçiş kapı kriterleri. Bu, aşağıdaki tekrar-eden-görev prosedürlerinden farklıdır
  — bir kez, proje başında çalışır.
- `skills/design-flow-agent/SPEC.md` — yukarıdaki akışı **interaktif olarak
  yürüten agent'ın** operasyonel spesifikasyonu (soru formatı, durum dosyası protokolü,
  faz-faz görev listesi). Cursor/Claude Code'da `design-flow-agent` skill'i olarak kurulur
  (bkz. `adapters/cursor/README.md`, `adapters/claude-code/README.md`).

Sık tekrarlanan geliştirme görevleri (yeni endpoint, yeni ekran, yeni migration, yeni izin
gibi) için ayrı ayrı 300 satırlık dosyalar yerine **tek bir genel şablon** kullanılır —
stack'e özel adımlar `tier1/` içinde doldurulur:

- `tier0/procedures/add-new-capability.md` — yeni bir uç-uca yetenek eklerken (endpoint,
  ekran, migration, izin, vb. hepsi aynı şekli izler: sözleşme → güvenlik → implementasyon
  sırası → test → dokümantasyon).
- `tier0/procedures/refactor-to-pattern.md` — mevcut kodu belirlenmiş bir pattern'e
  uydururken güvenli refactor akışı.
- `tier0/procedures/fix-failing-test.md` — bozuk bir testin gerçek bug mı, eski test mi,
  flaky mi, ortam sorunu mu olduğunu teşhis etme.
- `tier0/procedures/issue-tracker-doc-workflow.md` — proje bir issue tracker (Jira vb.)
  kullanıyorsa: kalıcı karar/sözleşme ile task-özel çalışma materyalinin (screenshot, mockup
  vb.) nerede yaşayacağı, ticket↔doküman referans kuralı, kapanışta distilasyon.
- `tier0/procedures/scrum-workflow.md` — Scrum board kullanan projeler için yukarıdakinin
  üzerine kurulu cadence detayı (sprint↔roadmap ilişkisi, epic/story/task↔doküman eşlemesi,
  sprint kapanışı). Kanban için ayrı bir dosya henüz yok, ihtiyaç çıktığında eklenir.
- `tier0/procedures/risk-tiering.md` — her yeni yetenek/bug-fix'in Değişiklik Risk Tier'ini
  (Bölüm 16) belirleyen 5-soru skorlama.
- `tier0/procedures/production-bugfix-cr.md` — canlıdaki bir hatayı düzeltirken/CR işlerken
  Tier'e göre orantılı süreç, semantik diff-bütçesi tetikleyicileri, ve üretim kesintisi
  istisna protokolü.

---

## 10. Stack Playbook'ları — Ne Zaman ve Nasıl

Bu dosyada **hiçbir framework/kütüphane adı geçmez** — bilerek. Framework'e özel kalıplar
`tier1/` altındadır ve o dosyaların nasıl yazılması gerektiğine dair kurallar (özellikle
**kod örneği yoğunluğu**) `tier1/README.md`'de açıklanmıştır — bu, bu şablon setinin en
kritik meta-kuralıdır, mutlaka okuyun.

---

## 11. Gözlemlenebilirlik Baseline — Zorunlu

Güvenlik baseline'ı (Bölüm 4) gibi, bu da **seçim değil zorunluluktur**: her proje,
stack'i ne olursa olsun, kurumun **merkezi, paylaşılan gözlemlenebilirlik platformuna**
telemetri gönderir. Bu, her projenin kendi log/metrik/trace altyapısını ayrı ayrı kurmasını
önler — CoE'nin sunduğu bir hizmettir, yeniden inşa edilmez.

1. **Enstrümantasyon:** OpenTelemetry SDK (dil-bağımsız standart) ile yapılandırılmış log +
   metrik + trace üretimi zorunludur — ham `console.log`/`print` ile üretim log'u tutmak
   kabul edilmez.
2. **Platform:** Metrikler, log'lar ve trace'ler kurumun merkezi, paylaşılan
   gözlemlenebilirlik platformuna akar; gerekirse merkezi alarm yönetimine bağlanır. Bu
   platformun bileşenleri proje bazında seçilmez/değiştirilmez — hangi ürünler kullanıldığı
   `tier1/playbooks/playbook-observability.md`'dedir.
3. **Detay:** Dil-özel SDK kurulumu, zorunlu resource attribute'ları, span/log korelasyon
   kuralı `tier1/playbooks/playbook-observability.md`'dedir — bu bölüm yalnızca zorunluluğu belirtir,
   uygulama detayına girmez (Bölüm 10'daki aynı ayrım).

**Neden zorunlu:** Merkezi bir platform olmadan, bir olay/hata birden fazla stack'i (örn.
NestJS API + Python ML servisi) kapsadığında, uçtan uca izleme (trace) imkansızlaşır —
her ekip kendi log'una bakar, kimse tam resmi göremez.

---

## 12. Kimlik Doğrulama (Authentication) Baseline — Zorunlu

Gözlemlenebilirlik (Bölüm 11) gibi, bu da seçim değil zorunluluktur — ama **yalnızca
authentication için.** Authorization (RBAC/yetkilendirme) bu bölümün kapsamı dışıdır ve
her projenin/stack'in kendi içinde geliştirdiği bir şey olarak kalır (bkz. Bölüm 10 ve
ilgili `tier1/playbooks/playbook-backend-*.md`'nin "Yetkilendirme" bölümü).

1. **Merkezi kimlik sağlayıcı:** Her proje, kullanıcı kimlik doğrulamasını kurumun merkezi
   kimlik sağlayıcısına OIDC üzerinden devreder. Sağlayıcının kendisi proje bazında
   seçilmez/değiştirilmez — hangi ürün olduğu `tier1/playbooks/playbook-authentication.md`'dedir.
2. **Kendi implementasyonu yasak:** Projeler kendi kullanıcı adı/şifre deposunu, kendi JWT
   issuance/refresh-rotation mantığını, kendi MFA akışını **kurmaz.** Bu, "yeniden icat
   etme" değil — merkezi kimlik yönetiminin (şifre politikası, MFA, sızıntı sonrası tüm
   kullanıcıların tek yerden devre dışı bırakılması) parçalanmasını önlemek içindir.
3. **Detay:** Merkezi kimlik sağlayıcı/OIDC entegrasyon prensipleri, token doğrulama,
   servisler arası kimlik doğrulama (client credentials) ve dil-özel SDK notları
   `tier1/playbooks/playbook-authentication.md`'dedir — bu bölüm yalnızca zorunluluğu belirtir.

**Neden zorunlu:** Her proje kendi auth'unu yazarsa, kurum içinde N farklı şifre
politikası/MFA implementasyonu/token formatı birikir — hem kullanıcı deneyimi (her
uygulamaya ayrı giriş) hem güvenlik (bir implementasyondaki zafiyet diğerlerine sıçramaz
ama tek tek denetlenmesi gereken N ayrı yüzey) açısından kötüleşir.

---

## 13. Kurumsal Sistem Entegrasyonu Baseline — Zorunlu

Gözlemlenebilirlik (Bölüm 11) ve authentication (Bölüm 12) gibi, bu da seçim değil
zorunluluktur — bir proje başka bir kurumsal sisteme (ERP, SAP, başka bir dahili uygulama
vb.) entegre olması gerektiğinde geçerlidir.

1. **Doğrudan app-to-app iletişim yasak.** Kurumsal ağdaki sistemler birbirine doğrudan
   (nokta-nokta) bağlanmaz.
2. **Merkezi entegrasyon platformu üzerinden entegrasyon zorunlu.** Kurumun sahipliğinde bir
   servis middleware/entegrasyon platformu var; bir uygulama başka bir kurumsal sisteme
   erişmesi gerektiğinde bunu **yalnızca bu merkezi platform üzerinden** yapar — kendi
   doğrudan bağlantısını kurmaz. Platformun kendisi proje bazında seçilmez/değiştirilmez —
   hangi ürün olduğu `tier1/playbooks/playbook-service-integration.md`'dedir.
3. **Bu, "kendi servisini sunma"dan farklı bir eksen.** Bir uygulamanın kendi API'sini dışa
   açması (örn. AWS/Azure'ın kendi API Gateway'i üzerinden) merkezi entegrasyon platformunun
   yerini almaz — "başkasının sistemine erişiyorum" (merkezi platform zorunlu) ile "kendi
   servisimi sunuyorum" (bulut platformunun kendi gateway'i, proje kararı) birbirinden ayrı
   sorular, karıştırılmaz.
4. **İnternet/internal arayüz ayrımı zorunlu.** İnternete açık bir API arayüzü ile yalnızca
   kurum-içi (internal) bir API arayüzü, aynı gateway/listener üzerinden hizmet vermez —
   mimari olarak ayrıdır.
5. **Detay:** Merkezi entegrasyon platformunun adı, entegrasyon prensipleri, protokol/kimlik
   doğrulama detayı, başvuru süreci `tier1/playbooks/playbook-service-integration.md`'dedir
   — bu bölüm yalnızca zorunluluğu belirtir (Bölüm 10'daki aynı ayrım).

**Neden zorunlu:** Dağınık, doğrudan app-to-app entegrasyonların her biri ayrı bir
güvenlik/uyum denetim yüzeyi doğurur — hangi uygulamanın hangi kurumsal sisteme, hangi
kimlik bilgisiyle eriştiğini merkezi olarak görmek imkansızlaşır. Tek bir denetlenebilir
kapı, bu görünürlüğü ve tutarlı bir kimlik doğrulama/yetkilendirme modelini korur.

---

## 14. API Tasarım Prensipleri Baseline — Zorunlu

Gözlemlenebilirlik (Bölüm 11), authentication (Bölüm 12) ve kurumsal sistem entegrasyonu
(Bölüm 13) gibi, bu da seçim değil zorunluluktur — her proje kendi API'sinin **sözleşme
şeklini** aynı prensiplerle kurar; **hangi endpoint'ler var olduğu** proje-özel kalır
(bkz. Bölüm 10 ayrımı, `tier2/README.md` madde 4).

1. **Tek response zarfı, tek hata taksonomisi.** Her proje `{ data }` / `{ error }` zarfını
   ve `DOMAIN_ENTITY_CONDITION` formatındaki sabit error code enum'unu kullanır — serbest
   metin hata mesajına veya ad-hoc response şekline dayanılmaz.
2. **Kendi kuralı icat edilmez.** Pagination stratejisi (cursor-based), versiyonlama
   (URL path), rate-limit katmanlaması (edge + kimlik-bazlı) proje bazında yeniden
   tasarlanmaz — stack'i ne olursa olsun aynı prensipler geçerlidir.
3. **Detay:** Tam kural seti, HTTP status semantiği, rate-limit/gateway ayrımı
   `tier1/playbooks/playbook-api-design.md`'dedir — bu bölüm yalnızca zorunluluğu belirtir,
   uygulama detayına girmez (Bölüm 10'daki aynı ayrım).

**Neden zorunlu:** Her proje kendi response/hata şeklini icat ederse, frontend (ve bu
platformlarla entegre olan diğer sistemler) her API için ayrı bir parse/hata-işleme mantığı
yazmak zorunda kalır — bu, N farklı sözleşme şeklinin toplamda katlanan bir bakım yüküne
dönüşmesidir; Bölüm 11-13'teki aynı "merkezi platform, tekrar icat etme" mantığı burada da
geçerlidir.

---

## 15. CI/CD ve Tedarik Zinciri Güvenliği Baseline — Zorunlu

Güvenlik baseline'ı (Bölüm 4) kod-seviyesi/runtime kontrollerini kapsar; bu bölüm **pipeline
seviyesi** kontrolleri kapsar — ikisi farklı katmandır, biri diğerinin yerini almaz.
Gözlemlenebilirlik (Bölüm 11) gibi bu da seçim değil zorunluluktur.

1. **Statik analiz / tip güvenliği:** Her proje, derleme/lint adımında tip-güvenliğini
   zayıflatan kalıpları (örn. dinamik/gevşek tip kullanımı) ve koda gömülü şifre/anahtar
   (hardcoded credential) otomatik olarak engeller — bu bir "code review notu" değil, CI'ı
   kırmızı yapan bir kapıdır.
2. **Bağımlılık/lisans taraması:** Açık kaynak bağımlılıklardaki bilinen güvenlik açıkları
   (SCA) ve lisans uyumsuzlukları, canlıya almadan önce otomatik taranır; **Critical/High**
   seviyeli bulgular düzeltilmeden ürün canlıya alınamaz.
3. **Statik güvenlik taraması (SAST):** Üretilen kod, canlı öncesi otomatik statik güvenlik
   taramasından geçer.
4. **Detay:** Hangi somut araçla (lint kuralı seti, SCA/SAST ürünü) bu üç maddenin
   karşılandığı proje bazında seçilmez/değiştirilmez — hangi araç olduğu
   `tier1/playbooks/playbook-cicd-security.md`'dedir; bu bölüm yalnızca zorunluluğu belirtir
   (Bölüm 10'daki aynı ayrım).

**Neden zorunlu:** Bu kontroller insan dikkatine bırakılırsa (her PR'da elle "bağımlılık
güncel mi", "gizli anahtar var mı" diye bakmak) gözden kaçar — otomatik ve tutarlı
uygulanmadıkları sürece var olmadıkları kadar değersizdir.

---

## 16. Değişiklik Risk Tier'i — Her Yeni Yetenek ve Bug-fix'te Zorunlu

Bölüm 1'deki MVP/Gerçek-üretim ayrımı **proje-geneli bir derinlik bayrağıdır** — Değişiklik
Risk Tier'i ise **her değişikliğe ayrı ayrı** uygulanan bir inceleme-şiddeti kararıdır; ikisi
aynı ekseni ölçmez, biri diğerinin yerine geçmez (bir MVP projede de Tier C bir değişiklik
olabilir — örn. MVP'nin ödeme akışına dokunan bir değişiklik).

1. **Ne zaman uygulanır:** Yeni bir yetenek eklerken (`tier0/procedures/
   add-new-capability.md`) ve bir production bug-fix/CR'da (`tier0/procedures/
   production-bugfix-cr.md`) — her ikisi de işe başlamadan önce bu skorlamayı çalıştırır.
2. **Skorlama:** 5 soru, 0-2 puan, toplam 0-10 → Tier A (0-2, düşük risk) / B (3-6, orta) /
   C (7-10, yüksek). Tam soru seti ve eşleşme tablosu: `tier0/procedures/risk-tiering.md`.
3. **Tier, inceleme derinliğini belirler — bu mekanik bir gate'tir, agent'ın kendi
   inisiyatifine bırakılan bir öneri değildir:** Tier A tek başına ilerleyebilir
   (branch+commit yeterli), Tier B diff review zorunlu kılar, **Tier C agent'ı durdurur**
   — agent implementasyona devam etmez, kod yazmaz/commit etmez; yalnızca teşhis/sözleşme
   taslağı ve öneri sunar, süreci bir insana (yazılımcı) devreder. Bu davranış
   `tier0/procedures/add-new-capability.md` §0 ve `tier0/procedures/
   production-bugfix-cr.md` madde 1'de somutlaşır.
4. **Kritik alan dokunuşu otomatik yükseltir:** Hassas bir alana (ödeme, kimlik doğrulama,
   KVKK verisi) dokunan bir değişiklik, toplam skor düşük olsa bile en az Tier B'ye çıkar —
   bu, Bölüm 4'teki güvenlik baseline'ının doğal uzantısıdır.
5. **Bu gate'in tek istisnası:** üretim kesintisi anındaki acil durum protokolü
   (`tier0/procedures/production-bugfix-cr.md` madde 5) — daraltılabilir ama asla sessizce
   atlanamaz, Teknik Sorumlu/Lider onayıyla başlar, 48 saat içinde zorunlu retro gerektirir.
   Bunun dışında Tier C hard-stop'u kesindir; "agent zaten başlamıştı, devam etsin" gibi bir
   gerekçeyle yumuşatılmaz.

**Neden zorunlu:** Her değişikliği aynı ağırlıkla incelemek (ya hepsini ağır, ya hepsini
hafif) hem yavaşlatır hem pratikte sessizce ihlal edilme riski taşır — kontrol şiddeti riske
orantılı olmalı, bu da ölçülebilir bir skorlama gerektirir.
