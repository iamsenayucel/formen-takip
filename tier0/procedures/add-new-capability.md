# Prosedür: Yeni Yetenek Ekleme

> Tool-agnostik, stack-agnostik şablon. "Yetenek" = yeni bir endpoint, yeni bir ekran, yeni
> bir DB migration, yeni bir izin/rol, yeni bir arka-plan işi vb. — hepsi aynı şekli izler.
> Stack'e özel adımlar (örn. "migration nasıl üretilir") ilgili `tier1/*.md` dosyasına
> aittir, buraya değil.

## 0. Risk Tier'ini belirle — mekanik, tartışmasız

İşe başlamadan önce `tier0/procedures/risk-tiering.md`'deki 5-soru skorlamasını çalıştır.
Bu, agent'ın kendi inisiyatifine bırakılan bir öneri değildir — çıkan Tier (A/B/C,
`tier0/RULES.md` Bölüm 16) aşağıdaki davranışı **doğrudan belirler**, agent bunu
yorumlayarak yumuşatamaz:

- **Tier A:** Agent tek başına ilerler — kod yazar, test ekler, commit eder. İnsan onayı
  yalnızca genel Onay Kapısı disiplinindedir (bkz. `skills/design-flow-agent/SPEC.md` §2.4
  eşdeğeri), ayrı bir diff review zorunlu değildir.
- **Tier B:** Agent implementasyonu yapar ama **commit'lemeden önce** bir insanın diff
  review'ını bekler — kendi kendine merge edemez. Bu bir öneri değil, adım 6'daki
  self-review checklist'in tamamlanma koşuludur.
- **Tier C — agent burada durur (hard stop):** Agent implementasyona **devam etmez**.
  Yapacağı tek şey: sözleşme taslağını (adım 1) ve seçenek/tradeoff araştırmasını sunmak.
  Kod yazmaz, commit etmez. `.design-flow/STATE.md` (veya proje eşdeğeri kayıt) içine
  `Tier: C — insan-led devraldı, <tarih>` olarak yazar ve oturumu bu haliyle kapatır.
  Devam kararı ve implementasyonun kendisi bir insana (yazılımcı) aittir; agent yalnızca
  o kişi açıkça talep ederse öneri sunmaya devam eder — kod üretip commit edemez.
  **Bu kuralın tek istisnası** `tier0/procedures/production-bugfix-cr.md` madde 5'teki
  üretim-kesintisi acil durum protokolüdür (daraltılabilir, asla sessizce atlanamaz, 48
  saat içinde zorunlu retro).

## 1. Sözleşmeyi tanımla

Yeni yetenek ne alır, ne döner, hangi hata durumlarını üretir? Kod yazmadan önce bu
sözleşme (şema/tip/API kontratı) yazılı hale getirilir. Sözleşme netleşmeden implementasyona
geçilmez — belirsiz sözleşme, halüsinasyon üretir (bkz. `tier0/RULES.md` Bölüm 6). Bir HTTP
endpoint'iyse, response zarfı/hata kodu formatı/pagination
`tier1/playbooks/playbook-api-design.md`'deki kurallara uyar — kendi şekli icat edilmez.
Yetenek başka bir kurumsal sisteme (ERP/SAP/başka bir dahili uygulama) erişim gerektiriyorsa
`tier1/playbooks/playbook-service-integration.md` uygulanır — doğrudan bağlantı kurulmaz.

## 2. Güvenlik ve yetki noktalarını belirle

`tier0/RULES.md` Bölüm 4'teki 6 maddeyi bu spesifik yetenek için tek tek işaretle: kim
yetkili, hangi girdi doğrulanacak, hassas veri var mı, audit'e ne yazılacak, rate-limit
gerekir mi, çıktı nerede render ediliyor.

## 3. Katmanlar arası implementasyon sırası

İlgili `tier1/` playbook'unun "Katmanlama" bölümünde tanımlı sırayla ilerle (örn.
sözleşme/şema → servis katmanı → giriş noktası/controller → UI, veya tersi — proje/stack'e
göre). Var olan bir pattern'i taklit et; yeni bir katmanlama icat etme.

Bu sıradaki kurulum bir bağımlılık manifestosuna (`package.json`/`pyproject.toml`/`pom.xml`
vb.) yazım gerektiriyorsa ve onaylı stack'in major sürümü sürtünme çıkarıyorsa (belgelenen
kalıp gerçek sürümle çelişiyor), yazmadan önce `skills/design-flow-agent/SPEC.md` §2.7
gate'i çalışır — sessizce farklı bir sürüme geçilmez.

## 4. Test gereksinimi — coverage kapısı

Yeteneğin en az: (a) mutlu yol, (b) yetkisiz erişim reddi, (c) geçersiz girdi reddi
senaryolarını kapsayan testleri olmadan tamamlanmış sayılmaz.

**Coverage kapısı (mekanik):** Yeteneğin dokunduğu modülün kritiklik seviyesini
(`tier1/playbooks/playbook-testing-<stack>.md`'deki "Coverage Hedefi" tablosu — yüksek/orta/
proje-geneli) belirle ve ölçülen coverage'ı o eşiğe karşı kontrol et. **Bu, Değişiklik Risk
Tier'inden (adım 0) ayrı bir eksendir** — biri "kim onaylar"ı, diğeri "hangi coverage sayısı
gerekir"i belirler, birbirinin yerine geçmez (bkz. `tier0/RULES.md` Bölüm 16). Eşiğin altında
kalan bir modül "done" olarak işaretlenemez; tek istisna
`tier0/procedures/production-bugfix-cr.md` madde 5'teki acil durum protokolüdür.

## 5. Dokümantasyonu güncelle

Sözleşme/şema bir yerde (`tier2/` altındaki API kataloğu, ekran kataloğu vb. — proje-özel
doküman setine bakın) merkezi olarak tutuluyorsa, o doküman bu adımda güncellenir. Kod ile
doküman aynı commit'te değişir; "sonra güncellerim" diye bırakılmaz (doc-drift, bkz.
`tier0/RULES.md` Bölüm 6).

Proje bir issue tracker (Jira vb.) kullanıyorsa, bu adım `tier0/procedures/
issue-tracker-doc-workflow.md`'nin madde 3-4'ünü de kapsar (uygulanma derinliği proje türüne
göre değişir, bkz. o dosyanın §0'ı): ilgili ticket bu dokümana/bölüme referans veriyor mu,
ticket'ın task-özel materyalinden (screenshot, mockup vb.) çıkan kalıcı sonuç buraya distile
edildi mi.

## 6. Self-review checklist (commit'lemeden önce)

- [ ] Adım 0'daki Tier belirlendi ve **o Tier'in gerektirdiği davranış uygulandı mı**
      (Tier B: insan diff review'ı alındı mı; Tier C: agent zaten durmuş olmalı, bu
      checklist'e gelinmemesi gerekir)?
- [ ] Adım 4'teki coverage kapısı geçildi mi (ölçülen coverage, modül-kritiklik eşiğinin
      üstünde mi)?
- [ ] `tier0/RULES.md` Bölüm 4 güvenlik checklist'i tek tek işaretlendi mi?
- [ ] **Bu yetenek bir yasaklı alana dokunuyor mu?** (ödeme veya KVKK kapsamlı iş mantığı —
      Master Politika Madde 6) Dokunuyorsa: AI yalnızca öneri sunar, kapsamlı insan
      incelemesi olmadan bu kod kullanılamaz — Tier A/B'de bile bu madde gevşemez.
- [ ] Var olmayan bir API/alan/izin icat edilmedi, gerçek tanıma bakıldı mı?
- [ ] Test (3 senaryo) yazıldı ve geçiyor mu?
- [ ] Sözleşme değiştiyse ilgili doküman güncellendi mi?
- [ ] Gereksiz soyutlama/kapsam dışı değişiklik eklenmedi mi? (`tier0/RULES.md` Bölüm 2, madde 1)

## 7. Oturum Kapsamı — Context Disiplini

Bu prosedürün oturum sınırı: **bir yetenek = bir oturum.** Bu iş kapanınca (adım 6
checklist'i tamamlanınca) ilgisiz bir ikinci yeteneğe aynı oturumda geçilmez, yeni bir
oturum açılır — gerekçesi ve mekanizması `tier0/RULES.md` Bölüm 2 madde 6'dadır, burada
tekrar edilmez.
