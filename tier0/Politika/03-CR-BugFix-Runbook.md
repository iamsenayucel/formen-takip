# CR / Bug-fix Runbook

**Bağlı olduğu master madde:** 00-Master-Politika.md → Madde 1 (İlke 2), Madde 5
**Sorumlu:** Teknik Lider
**Güncelleme kadansı:** İhtiyaç halinde, master'ı tetiklemeden

## Amaç

Master politika "kontrol şiddeti riskle orantılıdır" der ama bunu canlı sistemlerdeki hata düzeltmeleri (bug-fix) ve Değişiklik Talepleri (CR) için somutlaştırmaz. "Tüm CR/bug-fix'ler tüm gate'lere tabidir" kuralı, tek satırlık kozmetik bir düzeltme için bile ağır bir süreç anlamına gelebilir — bu hem yavaşlatır hem de pratikte sessizce ihlal edilme riski taşır. Bu doküman, bug-fix'leri **Tier'e** ve **diff büyüklüğüne** göre orantılı bir sürece bağlar.

## Bug-fix Tier'leri

Risk Değerlendirme Standardı'ndaki skorlama, bug-fix'e şu üç soruyla uyarlanır:

| Soru | Cevap A | Cevap B/C |
|---|---|---|
| Değişikliğin türü ne? | Kozmetik / içerik / config | İş mantığı / davranış |
| Neden bozulduğunu anlıyor muyuz? | Evet — kök neden belli | Hayır — belirsiz / gizemli |
| Kritik bir alana mı dokunuyor? (ödeme, auth, KVKK, kuruma özel çekirdek paketler) | Hayır | Evet |

| Tier | Profil | Süreç |
|---|---|---|
| **A** | Kozmetik/config, düzgün, kritik alan dışı | Ürün sahibi + AI tek başına. Branch + commit yeterli; yazılımcı zorunlu değil. |
| **B** | Hassas olmayan iş mantığı bug'ı, neden belirsiz/gizemli | Yazılımcı + AI fix; diff review zorunlu; CR getirilir. |
| **C** | Kritik alana dokunan veya gizemli bug | Baştan yazılımcı-led; AI sadece öneri; ürün sahibi tek başına dokunamaz. |

## Diff Bütçesi (Semantik Tetikleyiciler — 2026-07-20 revizyonu)

Önceki sürüm bu bölümü ham satır/dosya sayısına (`>1 dosya` veya `>20 satır`) dayandırıyordu.
AI-üretimi kod bağlamında bu zayıf bir sinyal olduğu teyit edildi: AI için 20 satır üretmek
maliyetsiz — 5 benzer dosyada mekanik bir alan ekleyen 25 satırlık bir diff düşük risklidir,
ama tek satırlık bir yetki kontrolü değişikliği çok yüksek risklidir; ayrıca AI'nın dokunduğu
dosyayı yeniden formatlaması (import sıralama vb.) ham satır sayısını gürültüyle şişirebilir.
Satır sayısı "ne kadar" sorusuna cevap verir, "ne değişti" sorusuna vermez — asıl risk
ikincisindedir.

Tier ne olursa olsun, aşağıdaki **4 semantik tetikleyiciden herhangi biri** doğruysa fix
otomatik olarak bir Tier yukarı çıkar (satır/dosya sayısından bağımsız, OR mantığı):

1. **Yasaklı alana dokunuyor** (ödeme, KVKK kapsamlı iş mantığı — master Madde 6).
2. **Bir Zorunlu cross-cutting mandate'ın kendi implementasyonuna dokunuyor**
   (authentication/observability/api-design/service-integration/CI-CD-güvenlik playbook'unun
   referans aldığı kanonik dosyalar — framework `tier0/RULES.md` §11-15).
3. **Bir sözleşmeyi değiştiriyor** (API response zarfı/hata kodu, DB şeması/migration, event
   şeması) — sözleşme değişimi implementasyon detayından her zaman daha pahalı/geri-dönüşü
   zordur.
4. **Birden fazla katmanı aynı commit'te değiştiriyor** (örn. DB + servis + API) — tek
   katmanda kalmayan bir "fix" fiilen bir refactor'dür.

Bu eşiklerden biri aşıldığında: fix, "bug fix" değil **gizli bir refactor** olarak
değerlendirilir. Otomatik olarak yazılımcı review'ına düşer ve regresyon testi eklenmesi
zorunlu hale gelir.

**Dosya/satır sayısı tamamen atılmadı, rolü değişti:** artık hard-trigger değil —
Accelerator'ın Olgunluk Yol Haritası'nda topladığı metriklere (Tier dağılımı) bilgi olarak
akan yumuşak bir sinyaldir; tek başına tier atamasını belirlemez.

> **Gerekçe:** Bir satırlık bug için 8 dosyaya dokunmak istemek hâlâ bir refactor işaretidir
> — ama bunu yakalayan şey "8 sayısı" değil, madde 4'teki "kaç katman değişti" sorusudur.
> Semantik tetikleyiciler, AI'nın diff boyutunu ucuzca büyütüp küçültebildiği bir ortamda
> daha oyuna-dayanıklı ve daha isabetli bir sinyaldir.

Somut uygulama akışı (teşhis sırası, kayıt, framework tarafındaki karşılığı):
`tier0/procedures/production-bugfix-cr.md`.

## Acil Durum Bağlantısı

Production kesintisi anında diff bütçesi ve Tier ataması **askıya alınmaz**; master Madde 5'teki istisna protokolü devreye girer (güvenlik taraması ve insan onayı asla atlanmaz, sadece review derinliği daraltılabilir). Olay sonrası 48 saat içinde bu runbook'a göre retroaktif sınıflandırma yapılır.

## Kayıt

Her Tier B/C bug-fix, CR sistemine (Jira vb.) Tier etiketiyle kaydedilir; bu kayıt, üç ayda bir EA/CoE uygunluk denetiminde örneklenir (master Madde 8).
