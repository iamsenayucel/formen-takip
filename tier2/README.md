# Tier 2 — Proje Dokümantasyonu

Bu klasör, taşınabilir bir şablon **değildir** — burada yalnızca "bu kategori dokümanlar
önerilir" kontrol listesi var. Gerçek içerik her projede sıfırdan, o projenin domainine göre
yazılır ve bu repodan kopyalanmaz.

## CoE Proje Dokümantasyon Seti (Şablon Liste)

Aşağıdaki doküman tipleri **her projede önerilir** ama içerikleri kesinlikle proje-özeldir.
İsimlendirme/numaralandırma bu setin kendi önerisidir; bir kaynak projeden birebir
alınmamıştır — kurum kendi konvansiyonuna göre uyarlayabilir.

| # | Doküman | İçeriği | Ne zaman yazılır |
|---|---|---|---|
| 1 | **Ürün ve Kapsam Özeti** | Hedef kullanıcı, MVP kapsamı ve kapsam-dışılar, başarı kriterleri | Proje başlangıcında, `tier0/RULES.md` §1 ile birlikte |
| 2 | **Domain Modeli** | Varlıklar, ilişkiler, iş kuralları, durum makineleri | İlk mimari tasarım aşamasında |
| 3 | **Veri Şeması** | Tablo/koleksiyon tanımları, indeksler, PII/şifreleme sınıflandırması | Şema ilk kez yazılırken, her migration'da güncellenir |
| 4 | **API / Sözleşme Kataloğu** | Gerçek endpoint listesi + gerçek error code'lar (şekil/kural değil — o `tier1/playbooks/playbook-api-design.md`'dedir) | İlk API tasarımında; `tier0/procedures/add-new-capability.md` her yeni endpoint'te bunu günceller |
| 5 | **Arayüz / Ekran Kataloğu** | Ekran envanteri, veri kaynağı, durumlar, etkileşimler | Frontend tasarımı başladığında |
| 6 | **Güvenlik & Uyum Uygulama Notu** | Auth akışı detayı, yetki modeli detayı, mevzuat (KVKK/GDPR vb.) uyum notları | Güvenlik mimarisi netleştiğinde; `tier0/RULES.md` §4'ün proje-özel somutlaşması |
| 7 | **Test Stratejisi Detayı** | Coverage matrisi, kritik e2e senaryo listesi | Test altyapısı kurulurken; `tier1/playbooks/playbook-testing-<stack>.md`'nin proje-özel dolgusu |
| 8 | **Geliştirme & Operasyon İş Akışı** | Git akışı, PR süreci, CI/CD, olay müdahale (incident response) | Ekip süreçleri netleştiğinde |
| 9 | **Uygulama Yol Haritası** | Fazlar/milestone'lar, bağımlılık grafiği, risk kaydı — derinliği MVP/Seviye'ye göre ölçeklenir (bkz. `tier0/RULES.md` §1 "MVP Disiplini Ölçeklenmesi") | Planlama aşamasında, düzenli güncellenir |
| 10 | **Domain Süreç Tasarım Şablonu** *(iş akışı/süreç ağırlıklı ürünlerde)* | Yeni bir iş sürecini/özelliğini koda geçmeden tam tanımlamak için doldurulacak taslak | Her yeni süreç tipi eklenmeden önce |
| 11 | **Kabul Testi (UAT) Planı** | Kullanıcı persona'ları ve senaryo bazlı kabul checklist'i | Go-live öncesi |
| 12 | **Mimari Karar İndeksi** | `tier0/adr/`'de biriken kararların (projenin kendi `docs/adr/`'ına taşınmış hallerinin) özet/kronolojik listesi | ADR biriktikçe, salt liste — içerik her zaman ADR'nin kendisinde |

> Not: 4, 6 ve 7 numaralı dokümanlar, ilgili Tier 1 playbook'larıyla (`api-design`,
> `authentication`, `backend`, `frontend`/`testing`) kavramsal olarak örtüşür. Kaynak
> incelemede bu örtüşme (aynı bilgi iki formatta, iki yerde) somut bir bakım riski olarak
> tespit edildi — bu setin önerisi: playbook = **kural/kısıt**, bu Tier 2 dokümanları =
> **o kuralın bu projedeki güncel gerçek hali (envanter)**. Aynı cümleyi iki yerde
> tekrar etmeyin — örn. madde 4'teki hata kodu listesi gerçek kodlardır, hata kodu
> *formatı* (`DOMAIN_ENTITY_CONDITION`) `playbook-api-design.md`'dedir.

## Bu klasörü nasıl kullanacaksınız

Yeni bir proje bu şablonu benimsediğinde, bu README'deki 12 maddeyi kendi `docs/` (veya
tercih ettiğiniz) dizininde, projenin gerçek adlarıyla oluşturur. Bu `tier2/` klasörü şablon
repoda **sadece bu kontrol listesini** taşır — doldurulmuş örnek içerik barındırmaz.
