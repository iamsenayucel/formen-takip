# Prosedür: Production Bug-fix / CR

> Tool-agnostik, stack-agnostik şablon. `tier0/procedures/add-new-capability.md` **yeni bir
> yetenek** eklerken izlenir; bu dosya **kabul edilmiş / kullanıcıya sunulmuş mevcut bir
> davranışı** düzeltirken/değiştirirken (bug-fix, Değişiklik Talebi/CR — UX/içerik/ses/metin
> cilası dahil) izlenir — ikisi ayrı prosedürlerdir, karıştırılmaz.
> Dosya adındaki *"production"* yalnızca canlı AWS ortamı demek değildir; **MVP/local/PoC
> dahil**, kabul edilmiş davranış için de geçerlidir. `"Canlıda değiliz → süreç yok"`
> çıkarımı yasaktır.
> `tier0/procedures/fix-failing-test.md`'den de farklıdır: o dosya bir testin **neden**
> kırmızı olduğunu teşhis eder, bu dosya teşhis sonrası **canlı bir düzeltmenin süreç
> ağırlığını** belirler.

## 1. Bug-fix Tier'i belirle

`tier0/procedures/risk-tiering.md`'deki 5-soru skorlaması burada da geçerlidir, ama bug-fix
bağlamında üç ek soruyla hızlı bir ön-sınıflama yapılabilir:

| Soru | Cevap A | Cevap B/C |
|---|---|---|
| Değişikliğin türü ne? | Kozmetik / içerik / config | İş mantığı / davranış |
| Neden bozulduğunu anlıyor muyuz? | Evet — kök neden belli | Hayır — belirsiz / gizemli |
| Kritik bir alana mı dokunuyor? (ödeme, kimlik doğrulama, KVKK) | Hayır | Evet |

| Tier | Profil | Süreç |
|---|---|---|
| **A** | Kozmetik/config, düzgün, kritik alan dışı | Ürün sahibi/Tasarım Sorumlusu + AI tek başına. Branch + commit yeterli; yazılımcı zorunlu değil. |
| **B** | Hassas olmayan iş mantığı bug'ı, neden belirsiz/gizemli | Yazılımcı + AI fix; diff review zorunlu; CR getirilir. |
| **C** | Kritik alana dokunan veya gizemli bug | Baştan yazılımcı-led; AI sadece öneri; ürün sahibi/Tasarım Sorumlusu tek başına dokunamaz. |

**Bu tablo mekanik/tartışmasızdır — agent kendi inisiyatifiyle yumuşatamaz:**

- **Tier A/B:** Agent teşhis (madde 2) ve fix'i uygular; Tier B'de commit'lemeden önce
  insan diff review'ı zorunludur (madde 7 self-review'a bağlı geçiş koşulu).
- **Tier C — agent burada durur (hard stop):** Agent kod yazmaz, commit etmez. Yapabileceği
  tek şey teşhis (madde 2) ve seçenek/öneri sunmaktır. Issue tracker/STATE.md'ye `Tier: C —
  yazılımcı-led devraldı, <tarih>` olarak yazar, oturumu bu haliyle kapatır. **Bu kuralın tek
  istisnası madde 5'teki üretim-kesintisi acil durum protokolüdür** (daraltılabilir, asla
  sessizce atlanamaz, 48 saat içinde zorunlu retro) — istisna dışında hard stop kesindir.

## 2. Kök nedeni teşhis et

Fix'e başlamadan önce `tier0/procedures/fix-failing-test.md`'deki 4 kategoriden hangisine
girdiğini belirle (gerçek bug / eski test / flaky / ortam sorunu) — yanlış teşhis gerçek bir
bug'ı maskeler.

## 3. Diff Bütçesi — semantik tetikleyiciler

Tier ne olursa olsun, aşağıdakilerden **herhangi biri** doğruysa fix otomatik olarak bir Tier
yukarı çıkar (satır/dosya sayısı **hard-trigger değildir** — bkz. gerekçe):

1. **Yasaklı alana dokunuyor** (ödeme, KVKK kapsamlı iş mantığı — `tier0/RULES.md` Bölüm 4).
2. **Bir Zorunlu cross-cutting mandate'ın kendi implementasyonuna dokunuyor**
   (authentication/observability/api-design/service-integration/CI-CD-güvenlik
   playbook'unun referans aldığı kanonik dosyalar — `tier0/RULES.md` Bölüm 11-15).
3. **Bir sözleşmeyi değiştiriyor** (API response zarfı/hata kodu, DB şeması/migration, event
   şeması).
4. **Birden fazla katmanı aynı commit'te değiştiriyor** (örn. DB + servis + API).
5. **Bir bağımlılık manifestosunda (`package.json`/`pyproject.toml`/`pom.xml`/`go.mod` vb.)
   onaylı bir stack'in major sürümünü değiştiriyor** — yükselt, indir, veya aynı kategoride
   farklı bir araca geç. Bu, `skills/design-flow-agent/SPEC.md` §2.7 gate'ini de tetikler:
   yazmadan önce sürtünme raporlanır, seçenek sunulur, onay alınır — "sadece bağımlılık
   pin'i" diye sessizce geçilmez.

Bu eşiklerden biri aşıldığında: fix, "bug fix" değil **gizli bir refactor** olarak
değerlendirilir. Otomatik olarak yazılımcı review'ına düşer ve regresyon testi eklenmesi
zorunlu hale gelir.

> **Neden satır sayısı değil:** AI için 20 satır üretmek maliyetsizdir — büyüklük riskle
> orantılı olmaktan çıkar (5 benzer dosyada mekanik bir alan eklemek düşük risklidir, tek
> satırlık bir yetki kontrolü değişikliği yüksek risklidir); ayrıca otomatik reformatlama ham
> satır sayısını gürültüyle şişirebilir. Dosya/satır sayısı tamamen atılmadı — hard-trigger
> olmaktan çıkıp, Accelerator'ın olgunluk metriklerine (Tier dağılımı) akan bilgilendirici bir
> sinyale döndü.

## 4. Regresyon testi — coverage kapısı

Diff Bütçesi'nden herhangi biri tetiklendiyse veya Tier B/C ise: fix'in kapsadığı davranışı
kilitleyen bir regresyon testi olmadan tamamlanmış sayılmaz — bu test, bug'ın bir daha sessizce
geri gelmeyeceğinin kanıtıdır.

**Coverage kapısı (mekanik, `tier0/procedures/add-new-capability.md` madde 4 ile aynı
mantık):** Dokunulan modülün kritiklik seviyesini (`tier1/playbooks/
playbook-testing-<stack>.md`'deki "Coverage Hedefi") belirle, ölçülen coverage'ı o eşiğe
karşı kontrol et — bu Bug-fix Tier'inden (madde 1) ayrı bir eksendir. Eşiğin altında kalan
bir fix "done" sayılmaz; tek istisna madde 5'teki acil durum protokolüdür.

## 5. Acil Durum / Üretim Kesintisi İstisna Protokolü

Üretim ortamında kritik bir kesinti anında, yukarıdaki tam süreci eksiksiz tamamlamak
operasyonel olarak mümkün olmayabilir.

- **Asla atlanamaz:** `tier1/playbooks/playbook-cicd-security.md`'deki güvenlik taraması
  (`tier0/RULES.md` §15) ve en az bir insanın "evet, bu canlıya çıkar" onayı.
- **Hızlandırılabilir, kaldırılamaz:** Review derinliği ve test kapsamı genişliği
  daraltılabilir, ama sıfırlanamaz.
- **Zorunlu:** Olay sonrası 48 saat içinde retroaktif inceleme yapılır — atlanan/daraltılan
  adımlar belgelenir, bu prosedüre göre gerçek Tier/diff-bütçesi sınıflandırması retroaktif
  olarak uygulanır.
- **Yetki:** İstisna hattı yalnızca Teknik Sorumlu/Lider onayıyla başlatılır; geliştirici tek
  başına bu kararı veremez.

> **Gerekçe:** "Asla bypass yok" kuralı, gerçek bir kesinti anında sessizce ihlal edilir ve bu,
> sürecin tamamının itibarını zedeler. Kontrollü bir istisna hattı + zorunlu retroaktif
> inceleme, hem hızı hem hesap verebilirliği aynı anda korur.

## 6. Kayıt

Her Tier B/C bug-fix, issue tracker'a (bkz. `tier0/procedures/issue-tracker-doc-workflow.md`)
Tier etiketiyle kaydedilir — bu, Olgunluk Yol Haritası'nın izlediği Tier dağılımı metriğinin
girdisidir.

## 7. Self-review checklist (commit'lemeden önce)

- [ ] Bug-fix Tier'i (madde 1) ve Diff Bütçesi tetikleyicileri (madde 3) değerlendirildi mi
      ve **o Tier'in gerektirdiği davranış uygulandı mı** (Tier C: agent zaten durmuş olmalı,
      bu checklist'e gelinmemesi gerekir)?
- [ ] Kök neden teşhisi (madde 2) yapıldı, sadece "testi geçsin diye" gevşetilmedi mi?
- [ ] Regresyon testi (madde 4) yazıldı, geçiyor ve coverage kapısı geçildi mi?
- [ ] Kritik alana dokunuyorsa (Tier C), yazılımcı-led süreç ve nihai insan onayı sağlandı mı?
- [ ] `tier0/RULES.md` Bölüm 2 madde 1 — kapsam dışı "madem buradayım" değişikliği sızmadı mı?

## 8. Oturum Kapsamı — Context Disiplini

Bu prosedürün oturum sınırı: **bir bug-fix/CR = bir oturum.** Bu iş kapanınca (madde 7
checklist'i tamamlanınca) ilgisiz bir ikinci fix'e aynı oturumda geçilmez, yeni bir oturum
açılır — gerekçesi ve mekanizması `tier0/RULES.md` Bölüm 2 madde 6'dadır, burada tekrar
edilmez.
