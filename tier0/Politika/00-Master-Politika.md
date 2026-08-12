# Yıldız Holding — AI Destekli Kodlama ve Ürün Geliştirme Politikası (Master)

**Versiyon:** 2.0
**Sorumlu:** EA / CoE (Kurumsal ve Yazılım Mimarisi)
**Durum:** v1.4'ü ilke/operasyon ayrımıyla yeniden yapılandıran sürüm

## Bu Sürümde Ne Değişti

Önceki sürüm (v1.0 → v1.4), aynı ay içinde dört kez güncellendi. Bunun nedeni içeriğin yanlış olması değil, dokümanın iki farklı işi aynı anda yapmaya çalışmasıydı: hem **ilke** (nadiren değişmesi gereken) hem **operasyon detayı** (araç adı, eşik, pipeline adımı — sık değişen). Bu sürüm bu ikisini ayırıyor:

- **Bu doküman** artık sadece ilke seviyesinde kalır: kim hesap verir, hangi kontrol noktaları neden var, hangi alanlar kapalı, acil durumda ne olur.
- **Somut detaylar** (skorlama soruları, gate eşikleri, bug-fix sınıflandırması, yetkinlik kriterleri, olgunluk metrikleri, tedarikçi sözleşme maddeleri) altı ayrı standart dokümanına taşındı. Bu dokümanlar bağımsız güncellenir ve master'ın versiyonunu tetiklemez.

Sonuç: master nadiren değişir ve kısa kalır; kapsam hiçbir konuyu atlamaz çünkü her konu bir alt dokümana bağlıdır.

---

## 0. Amaç ve Kapsam

**Amaç:** AI destekli kodlama araçları, fikirden çalışan yazılıma giden süreci önemli ölçüde hızlandırır; bu hız Yıldız Holding için gerçek bir rekabet avantajıdır. Ancak hız ile güvenilirlik aynı şeyi ölçmez — bir AI çıktısının işlevsel görünmesi, doğru ve güvenli olduğu anlamına gelmez; bu farkı ayırt etmek teknik uzmanlık gerektirir.

Bu politika AI kullanımını kısıtlamak için değil, **hız kazancını doğrulama ve hesap verebilirlik mekanizmalarıyla dengelemek** için vardır. Geliştiricinin rolü bu çerçevede ortadan kalkmaz, dönüşür: ağırlık kod üretiminden, üretilen çıktının doğrulanmasına ve nihai sorumluluğun üstlenilmesine kayar.

**Bu doküman neyi düzenler:**
- Kontrol şiddetinin riske göre nasıl ölçeklendiği (ilke seviyesinde)
- Hangi kontrol noktalarının (gate) var olması gerektiği ve neden
- Kim, hangi alanda hesap verir
- Hangi veri/alanlar AI'ya tamamen kapalıdır
- Acil durumda kuralın nasıl işletildiği (istisna ≠ muafiyet)
- Bu politikanın kendisinin ve alt dokümanlarının nasıl yönetildiği

**Bu doküman neyi düzenlemez — ilgili alt dokümana bakınız:**

| Konu | Alt Doküman |
|---|---|
| Risk skorlama soruları, eşik değerleri | `01-Risk-Degerlendirme-Standardi.md` |
| Gate'lerin somut uygulaması (araç, % eşik, pipeline adımı) | `02-Gate-Operasyon-Standardi.md` |
| Bug-fix / CR sınıflandırması, diff bütçesi | `03-CR-BugFix-Runbook.md` |
| Olgunluk seviyeleri, metrikler, dönüşüm yol haritası | `04-Olgunluk-Yol-Haritasi.md` |
| Yetkinlik kriterleri, eğitim/onboarding planı | `05-Egitim-Yonergesi.md` |
| 3. parti tedarikçi sözleşme maddeleri | `06-3Parti-Tedarikci-Eki.md` |

AI kodlama kararının nasıl alındığı ve Demand Management Board ile ilişkisi bu politikanın **Madde 3.5**'inde düzenlenir.

Bir konunun bu listede olması önemsiz olduğu anlamına gelmez — tersine, somut/teknik olduğu ve sık değişeceği, bu yüzden ayrı ve hızlı güncellenebilir bir dokümanda yaşaması gerektiği anlamına gelir.

---

## 1. Temel İlkeler

1. **"Kodu AI yazdı" diyerek sorumluluktan çıkılamaz.** AI bir araçtır, onay merci değil. Üretilen kodun doğruluğundan ve sonuçlarından her zaman onu kullanan insan hesap verir.
2. **Her değişiklik aynı ağırlıkta incelenmez — risk ne kadar büyükse kontrol o kadar sıkıdır.** Tek satır kozmetik bir düzeltme ile kimlik doğrulama akışını değiştiren bir geliştirme aynı süreçten geçmez. Bu bir "MVP mi, production mı" ikiliği de değildir — her değişiklik kendi risk profiline göre değerlendirilir (→ Risk Değerlendirme Standardı).
3. **Her ekip kendi kuralını yazmaz — standartlar ortak tutulur.** Farklı ekiplerin farklı AI kurallarıyla çalışması kaliteyi kişiye ve takıma bağlar, denetimi imkânsız kılar. Standartlar EA/CoE'de tanımlanır ve tüm ekipler aynı çerçeveyi kullanır.
4. **"Neden böyle yaptık?" sorusunun cevabı insanların hafızasında değil, dosyada yaşar.** Bir karar kayıt altına alınmamışsa zamanla ne savunulabilir ne de düzeltilebilir hale gelir. Kişiler değişir, hafızalar solar — kurumsal hafıza dosyada tutulur.
5. **Acil durum, kuralı askıya almaz — hızlandırır.** Üretimde kritik bir kesinti olduğunda bazı adımlar daraltılabilir, ama hiçbiri tamamen atlanamaz. Bunun için tanımlı bir istisna yolu vardır ve sonrasında zorunlu bir değerlendirme yapılır (→ Madde 5).

---

## 2. Roller ve Nihai Hesap Verebilirlik

| Rol | Hesap Verdiği Alan |
|---|---|
| Geliştirici (İç / 3. Parti) | Üretilen kodun doğruluğu, kritik alan review'ı, kurumsal hafızanın güncel tutulması |
| Ürün Ekibi / PO | Kapsamın gerçek ihtiyaca uygunluğu, MVP önceliklendirme, scope disiplini |
| Teknik Lider | Gate'lerin fiilen uygulandığının doğrulanması, uygunluk raporlaması |
| Security | Onaylı araç listesi, AI üretimi koddaki güvenlik açıklarının taranması |
| **AI-Assisted Dev. Accelerator** | AI geliştirme sürecinin günlük operasyon sahibi: skill kütüphanesi, araç ekosistemi takibi, eğitim programı, lessons-learned döngüsü, olgunluk metrikleri (→ Olgunluk Yol Haritası) |
| EA / CoE | Standartların belirlenmesi, nihai onay, bu politikanın ve alt dokümanların yönetişimi |

> **Accelerator — PO ayrımı:** PO, *ne* geliştirileceğini ve kapsamını yönetir. Accelerator, AI destekli geliştirme *sürecinin* kurumsal olgunluğunu işletir. İkisi farklı hesap verebilirlik alanlarına sahip, birbirini denetlemeyen rollerdir. Teknik birikimi olan PO'lar Accelerator rolüne geçiş için değerlendirilebilir (→ Eğitim Yönergesi, PO için Özel Not) — ancak bu rol bir PO pozisyonunun uzantısı değil, ayrı bir atamadır.

Detaylı yetkinlik kriterleri ve "kim hangi risk seviyesinde tek başına çalışabilir" eşiği → Eğitim Yönergesi + Risk Değerlendirme Standardı.

---

## 3. Kalite Kapılarının Varlığı ve Amacı

Beş kontrol noktası vardır. Her birinin **var olma amacı** burada sabittir; **somut uygulaması** (hangi araç, hangi eşik, hangi pipeline adımı) Gate Operasyon Standardı'nda tanımlanır ve orada, master'ı tetiklemeden güncellenir.

1. **Başlangıç** — Proje, kurumsal standartlardan sapmadan başlasın.
2. **Bağlam & Karar** — Mimari kararlar ve AI bağlam dosyaları kayıtlı ve versiyonlu olsun.
3. **CI/CD** — İnsan dikkatine bırakılırsa gözden kaçacak kontroller (bağımlılık, lint, secret) otomatik ve tutarlı uygulansın.
4. **Test & Review** — AI'nın "iddia ettiği" doğruluk somut kanıtla (test) desteklensin; kritik alanda nihai doğrulama insanda kalsın.
5. **Güvenlik** — Canlıya çıkmadan önce, gözle fark edilemeyen güvenlik açıkları otomatik taramayla yakalansın.

Bir gate kaldırılamaz. Uygulama yöntemi değiştiğinde (örn. yeni bir tarama aracı), bu madde etkilenmez — sadece Gate Operasyon Standardı güncellenir.

---

## 3.5. AI Kodlama Çözümüne Giden Karar Yolu

*"AI ile mi kodlayalım?" sorusu, "ne inşa edeceğiz?" sorusundan ayrı ama onunla bağlantılı bir karardır. Bu madde, Demand Management Board sürecinden AI kodlama kararına uzanan yolu tanımlar.*

1. **AI kodlama, çözüm yöntemi kararıdır — iş kararından sonra gelir.** Demand Board önce talebin karşılanıp karşılanmayacağına karar verir. AI kodlama, bu karar verildikten sonra değerlendirilen bir uygulama yöntemidir. "AI ile yapalım" sorusu, "yapalım mı" sorusunun önüne geçemez.

2. **Board sürecinde her talep için "AI kodlama uygunluğu" değerlendirilir.** Aşağıdaki üç grupta sınıflandırılır:

   | Uygun | Dikkatli / Şartlı | Uygun Değil |
   |---|---|---|
   | Net kapsamlı, bölünebilir iş | Gri alan bağımlılıkları mevcut | Ödeme, kimlik doğrulama, KVKK iş mantığı (Madde 6) |
   | Benzer örnekler skill kütüphanesinde var | Risk skoru henüz belirsiz | Güvenlik-kritik konfigürasyonlar |
   | Test edilebilirlik yüksek | Yeni domain, bağlam dosyaları yetersiz | Kuruma özel paylaşılan çekirdek paketler (varsa, Madde 6) |

3. **Risk skoru Board'da belirlenir ve gate yükünü önceden netleştirir.** Board kararı sırasında veya hemen ardından Risk Değerlendirme Standardı'ndaki sorular çalıştırılır. Çıkan Tier (A/B/C) o projenin tabi olacağı kontrolün ağırlığını belirler. Bu adım atlanamaz — sürpriz gate yükü proje ortasında değil, başında görülmelidir.

4. **"Bu talep AI kodlamayla çözülecek" kararı Board kaydının parçasıdır.** Hangi kriterleri karşıladığı, neden uygun ya da şartlı kabul edildiği belgelenir. Bu, Kurumsal Hafıza ilkesinin (Madde 4) ve Demand Board'un mevcut kayıt pratiğinin doğal uzantısıdır.

5. **AI kodlama yöntemi kararı Board'un kolektif değerlendirmesidir; tek kişi veremez.** Tıpkı talebin çözüme alınması gibi, AI kodlamayla çözülmesi de ekip kararıdır. Geliştirici veya PO tek başına bu yöntemi belirleyemez.

---

## 4. Kurumsal Hafıza Sahipliği

Her ürün/projenin AI bağlam dosyaları (`CLAUDE.md`, `.cursorrules`, `.rules`) için **tek bir sorumlu (Steward)** atanır. Steward, bu dosyaların güncel, çelişkisiz ve gerçek mimari kararlarla uyumlu kalmasından sorumludur. Sorumluluk role bağlıdır, kişiye değil — kişi değiştiğinde rol devam eder.

> **Gerekçe:** "Herkesin sorumluluğu" fiilen hiç kimsenin sorumluluğu olur; bu dosyalar güncellenmezse kurumsal hafıza sessizce bayatlar ve AI, geçersiz bağlamla çalışmaya başlar.

---

## 5. İstisna / Acil Durum Protokolü

Üretim ortamında kritik bir kesinti anında, tam gate sürecini eksiksiz tamamlamak operasyonel olarak mümkün olmayabilir. Bu durumda:

- **Asla atlanamaz:** Güvenlik taraması (Gate 5) ve en az bir insanın "evet, bu canlıya çıkar" onayı.
- **Hızlandırılabilir, kaldırılamaz:** Review derinliği ve test kapsamı genişliği daraltılabilir, ama sıfırlanamaz.
- **Zorunlu:** Olay sonrası 48 saat içinde retroaktif inceleme yapılır; atlanan/daraltılan adımlar belgelenir.
- **Yetki:** İstisna hattı yalnızca Teknik Lider veya EA/CoE onayıyla başlatılır; geliştirici tek başına bu kararı veremez.

> **Gerekçe:** "Asla bypass yok" kuralı, gerçek bir kesinti anında sessizce ihlal edilir ve bu, politikanın tamamının itibarını zedeler. Kontrollü bir istisna hattı + zorunlu retroaktif inceleme, hem hızı hem hesap verebilirliği aynı anda korur.

---

## 6. Veri Gizliliği ve Yasaklı Alanlar

- Yalnızca holding onaylı, **zero-data-retention** garantili kurumsal AI lisansları kullanılabilir.
- Açık/genel tüketici LLM'lerine (ücretsiz sürümler dahil) şirket kodu, müşteri verisi veya KVKK kapsamındaki veri girilemez.
- **Yasaklı alanlar:** Ödeme, kimlik doğrulama, KVKK kapsamlı akışların iş mantığı; güvenlik-kritik konfigürasyonlar; kuruma özel paylaşılan çekirdek paketler (varsa — hangi paketlerin bu kapsamda olduğu Teknik Lider/EA-CoE tarafından proje bazında belirlenir). Bu alanlarda AI yalnızca öneri sunabilir; kapsamlı insan incelemesi olmadan kod kullanılamaz.
  > *(Not, 2026-07-20: bu madde önceden somut bir paket adı — `@yildiz/*` — kullanıyordu; böyle
  > adlandırılmış bir paket seti şu an gerçek/planlı değil olduğu teyit edildi, genel ilke
  > korunarak isim kaldırıldı.)*

> **Gerekçe:** Onaysız bir araca girilen kurumsal/kişisel veri o aracın sağlayıcısında kalıcı olarak saklanabilir — bu geri alınamaz bir risktir. Ödeme/kimlik doğrulama gibi alanlarda bir hatanın sonucu da aynı şekilde geri alınamaz olduğundan, bu alanlar otomatik onaydan istisna tutulur.

---

## 7. Telif / Lisans Riski

AI modelleri, eğitim verisindeki lisanslı veya telifli kodu yeniden üretebilir.

- Üretilen kod, bilinen açık kaynak lisans ihlali taraması (Gate 3/5 kapsamında) yapılmadan birleştirilemez.
- Şüpheli veya atıf gerektiren çıktı tespit edildiğinde EA/CoE, hukuk birimiyle istişare eder.

> **Gerekçe:** Bu risk fark edilmediğinde kurum bilmeden bir lisans ihlaline maruz kalabilir — bu da geri alınamaz bir hukuki/itibar riskidir.

---

## 8. Doküman Yönetişimi

- Bu master doküman **çeyreklik döngüde** EA/CoE tarafından gözden geçirilir. İlke değişikliği gerektirmeyen güncellemeler alt dokümanlara yönlendirilir.
- Alt dokümanlar bu politikanın **eki** sayılır; EA/CoE onayıyla bağımsız güncellenir ve master'ın versiyonunu tetiklemez.
- Yeni bir alt doküman ihtiyacı doğduğunda, önce Madde 0'daki tabloya bir referans satırı eklenir.
- **Uygunluk denetimi:** Teknik Lider'ler, üç ayda bir örnekleme yöntemiyle gate'lerin fiilen uygulandığını EA/CoE'ye raporlar.

---

## 9. Sözlük

- **Gate:** Bir aşamadan sonrakine geçişi engelleyen zorunlu kontrol noktası.
- **Risk Skoru:** Bir değişikliğin hassasiyet, geri alınabilirlik, bağlantısallık, kullanıcı maruziyeti ve kalıcılık boyutlarında değerlendirilmesiyle elde edilen, kontrol şiddetini belirleyen ölçüt (→ Risk Değerlendirme Standardı).
- **Tier (A/B/C):** Risk skoruna göre bir değişikliğin tabi olacağı inceleme şiddeti sınıfı (→ CR/Bug-fix Runbook).
- **Accelerator (AI-Assisted Dev. Accelerator):** AI geliştirme sürecinin günlük operasyon sahibi; EA/CoE'nin stratejik rolünden ayrı, taktik yürütümü üstlenen rol (→ Madde 2, Olgunluk Yol Haritası).
- **Steward:** Bir ürünün AI bağlam dosyalarının güncelliğinden sorumlu rol.
- **CoE:** AI Geliştirme Mükemmeliyet Merkezi (Center of Excellence).
- **EA:** Enterprise Architecture (Kurumsal Mimari).

---

*Revizyon önerileri için EA / CoE ekibine iletiniz.*
