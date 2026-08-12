# 3. Parti Tedarikçi Eki

**Bağlı olduğu master madde:** 00-Master-Politika.md → Madde 1 (İlke 3), Madde 6
**Sorumlu:** EA / CoE, Satınalma/Hukuk ile koordineli
**Güncelleme kadansı:** Organizasyon olgunluk seviyesi değiştiğinde (→ Olgunluk Yol Haritası)

## Yaklaşım

2026 itibarıyla bir tedarikçiye "AI kullanabilirsin / kullanamazsın" demek gerçekçi değildir — code completion, refactoring, test yazımı gibi alanlarda AI kullanımı zaten sektör standardıdır. Bunu yasaklamaya çalışmak hem uygulanamaz hem de denetlenemez.

Asıl risk, sıfırdan bir platformu "vibe-coding" yaklaşımıyla dış tedarikçiye verip denetimi kaybetmektir. Kendi iç sürecimiz bile Madde 0-8'deki standartları titizlikle uygulamayı gerektirirken, bir dış tedarikçinin aynı titizlikte çalıştığını doğrulamak çok daha zordur.

**İlke:** Önce kendi sürecimizi olgunlaştırırız (→ Olgunluk Yol Haritası, Seviye 3+); tedarikçiden süreç uyumu istemek, biz bu seviyeye gelmeden hem anlamsız hem denetlenemez olur. Bugün için istenen, **süreç değil çıktı (deliverable) standardıdır.**

## Bugün İçin Minimum Gereksinimler

1. **Veri güvenliği sözleşme maddesi:** Kurumsal/müşteri verisinin cloud-hosted genel AI servislerine gönderilmemesi sözleşmeye madde olarak girer (master Madde 6 ile uyumlu).
2. **Deliverable kalite standardı:** Tedarikçi kodu nasıl üretmiş olursa olsun (AI ile veya değil), teslim edilen çıktı bizim Gate Operasyon Standardı'ndaki Gate 3-5'ten (CI/CD, Test & Review, Güvenlik) aynen geçer. Süreç denetlenmez, çıktı denetlenir.
3. **Yasaklı alan istisnası yoktur:** Master Madde 6'daki yasaklı alanlar (ödeme, kimlik doğrulama, KVKK, kuruma özel paylaşılan çekirdek paketler varsa) tedarikçi için de aynen geçerlidir; bu alanlarda tedarikçi kodu da kapsamlı insan incelemesinden geçer.

## İleride Genişleyecek Alan

Organizasyon Olgunluk Yol Haritası'nda Seviye 3'e ulaştığında, tedarikçilerden de:
- Kendi AI bağlam dosyalarını (rules) bizim standartlarımıza uygun tutmaları,
- Risk Değerlendirme Standardı'ndaki Tier sınıflandırmasını kendi CR süreçlerinde uygulamaları

istenebilir. Bu, bugün için erken — kendi sürecimiz bu olgunlukta değilken tedarikçiye dayatmak, bize değil tedarikçiye fayda sağlar (denetleyemediğimiz bir standart, kağıt üstünde kalır).

## Sahiplik

Sözleşme maddelerinin güncel tutulması Satınalma/Hukuk ile EA/CoE'nin ortak sorumluluğudur; deliverable kalite denetimi Teknik Lider'in görevidir (master Madde 2).
