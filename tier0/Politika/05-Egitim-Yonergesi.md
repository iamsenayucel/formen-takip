# Eğitim Yönergesi

**Bağlı olduğu master madde:** 00-Master-Politika.md → Madde 2
**Sorumlu:** AI-Assisted Development Accelerator (→ Olgunluk Yol Haritası), Teknik Lider
**Güncelleme kadansı:** İhtiyaç halinde

## Amaç

Master politika rolleri unvan bazlı tanımlar (Geliştirici, Ürün Ekibi, Teknik Lider) ama "kim AI-assisted geliştirme yapabilir" sorusuna bir yetkinlik kriteri koymaz. Doğru soru "tool'u biliyor mu" değildir — AI kullanmayı bilmek ile AI-assisted yazılım geliştirmeyi kurumsal standartlarda yapmayı bilmek farklı şeylerdir. Bu doküman, ölçülebilir bir yetkinlik eşiği tanımlar; amaç kapı bekçiliği değil, kimin neye hazır olduğunu görüp gerekli eğitimi vermektir.

## Yetkinlik Matrisi

### A. Temel Yazılım Mühendisliği

- **SDLC bilgisi:** Bir uygulamanın analizden production'a kadar hangi aşamalardan geçtiğini bilmek.
- **Katman kavrayışı:** Database, backend, API, frontend, middleware arasındaki ilişkiyi anlamak. AI bir katmanda kod üretirken diğer katmanla bağımlılığı göremeyebilir; bunu fark edecek olan geliştiricidir.
- **Security temelleri:** Authentication, authorization, veri şifreleme, KVKK/GDPR gereksinimleri konusunda en azından neyin riskli olduğunu anlamak.

### B. AI-Assisted Geliştirmeye Özgü Yetkinlikler

- **Skill kullanımı:** Standartlaştırılmış skill'lerin ne işe yaradığını, nasıl tetiklendiğini, çıktısının nasıl değerlendirileceğini bilmek.
- **Repository yönetimi:** Branch stratejisi, commit standartları, PR süreçleri. Agent yanlış branch'te işlem yapabilir veya commit mesajını anlamsız bırakabilir — geliştirici bunu yönetmeli.
- **Context window yönetimi:** Agent'ın hafıza sınırlarını bilmek, session'ları buna göre planlamak, hangi dokümanın ne zaman referans verileceğini bilmek.
- **Prompt mühendisliği:** "Güzel soru sorma" değil — bir session'ın amacını, kapsamını, kısıtlarını ve beklenen çıktıyı agent'a doğru aktarabilme.
- **Debugging ve çıktı değerlendirme:** AI üretimi kodu körü körüne kabul etmemek; çalışsa bile mimari uygunluğunu, performans etkisini, yan etkilerini sorgulayabilmek.

## Yetkinlik Eşiği ve Risk Tier İlişkisi

Yetkinlik matrisi, Risk Değerlendirme Standardı'ndaki Tier'lerle birlikte okunur:

| Yetkinlik Seviyesi | Tek Başına Çalışabileceği Tier |
|---|---|
| Yalnızca B (AI-assisted) yetkinlikleri var, A eksik | Hiçbiri — peer zorunlu |
| A + B temel seviyede | Tier A |
| A + B ileri seviyede, security temelleri doğrulanmış | Tier A, B |
| A + B + kritik alan deneyimi (ödeme/auth/KVKK) | Tier A, B, C (peer ile) |

Tier C'de tek başına nihai onay yetkisi hiçbir yetkinlik seviyesinde otomatik verilmez — master Madde 6 gereği bu alanlarda kapsamlı insan incelemesi her zaman zorunludur.

## Onboarding Akışı

1. Yeni geliştirici, yetkinlik matrisine göre kendi kendini değerlendirir; Teknik Lider doğrular.
2. Eksik alanlar için Accelerator tarafından sağlanan eğitim materyaline yönlendirilir (sadece "tool nasıl kullanılır" değil, "kurumsal standartlarda nasıl yürütülür" odaklı).
3. İlk üç ayda yalnızca Tier A/B işlerde, bir peer ile çalışır.
4. Teknik Lider onayıyla Tier C işlerde (peer eşliğinde) çalışmaya başlar.

## Ürün Sahibi (PO) için Özel Not

PO'lar, AI-assisted geliştirme için doğal adaylardan biridir (uygulama ihtiyaçlarını zaten bilir) ama bu, security/performans/katman ilişkilerini bilmekle aynı şey değildir. %100 hakimiyet gerekmez — ama öğrenmeye istekli olmak ve ne yaptığını bilmeden geliştirme yapmamak şarttır. PO'nun asıl sorumluluğu **scope disiplinidir**: AI'nın hız avantajı "her şeyi üretelim" anlamına gelmez; PO bu filtreyi uygulamalıdır.
