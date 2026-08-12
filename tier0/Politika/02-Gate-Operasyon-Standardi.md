# Gate Operasyon Standardı

**Bağlı olduğu master madde:** 00-Master-Politika.md → Madde 3
**Sorumlu:** EA / CoE, Teknik Lider
**Güncelleme kadansı:** Araç/eşik değiştiğinde, master'ı tetiklemeden

## Amaç

Master Madde 3, beş gate'in **var olma amacını** sabitler. Bu doküman, her gate'in **bugün hangi araçla, hangi eşikle** uygulandığını tanımlar. Bir araç veya eşik değiştiğinde sadece bu doküman güncellenir.

## Gate 1 — Başlangıç

- Mimari Gate onayı alınmadan kodlamaya başlanmaz.
- Tüm projeler YH-vibe-coding-framework üzerinden açılır (`vibe-coding-bootstrap` skill'i
  veya reponun `gh repo create --template` ile kullanılması) — bu, kurumsal standarttan
  sapan bir "elle kurulum" değildir, framework'ün kendi standart başlangıç iskeletidir; bkz.
  `tier0/procedures/new-project-design-flow.md`.
  > *(Not, 2026-07-20: bu madde önceden `npx @yildiz/create-app` adlı ayrı bir CLI'a atıfta
  > bulunuyordu — o araç hayata geçmedi/planlanmıyor, teyit edildi. Proje başlatma mekanizması
  > bu framework'e devredildi, kaldırıldı.)*
- Başlangıç Risk Tier'i (→ Risk Değerlendirme Standardı, framework tarafında karşılığı
  `tier0/procedures/risk-tiering.md`) bu onaya eklenir.

## Gate 2 — Bağlam ve Karar

- AI bağlam dosyaları (`CLAUDE.md`, `.cursorrules`) repo'ya aittir ve versiyonlanır; Steward bu dosyaların sahibidir (master Madde 4).
- Mimari kararlar ADR (Architecture Decision Record) olarak yazılır; her ADR'de **"AI Katkısı / Gerekçesi"** alanı zorunludur.
- İterasyon planlaması, AI'nın context window sınırını gözeterek tek katmana odaklanacak şekilde tasarlanır (örn. bir iterasyonda yalnızca veritabanı şeması, ayrı bir iterasyonda yalnızca API katmanı).

## Gate 3 — CI/CD Pipeline

- Statik kod analizi/tip güvenliği ihlalleri (örn. `any` tipi kullanımı) ve koda gömülü
  şifre/anahtar (hardcoded credential) otomatik olarak engellenir.
- Açık kaynak lisans taraması (master Madde 7) bu adımda çalışır.
- **Somut araç/pipeline adımı artık framework tarafında tanımlıdır:**
  `tier1/playbooks/playbook-cicd-security.md` (`tier0/RULES.md` §15, Zorunlu) — hangi
  lint/SCA/lisans-tarama aracının kullanılacağı proje stack'ine göre orada taşınır, burada
  tekrar edilmez.
  > *(Not, 2026-07-20: bu madde önceden `check-coe-versions.js` adlı bir pipeline script'ine
  > ve yalnız-Nexus bağımlılık kaynağına atıfta bulunuyordu — ikisi de gerçek/planlı bir
  > kurumsal standart değil, önceki bir taslak oturumdan kalan yer tutucu olduğu teyit
  > edildi; kaldırıldı.)*

## Gate 4 — Test ve Code Review

- AI üretimi fonksiyonlar için birim testi şarttır: **Unit ≥ %85, Integration ≥ %70**.
- AI üretimi kodlar, bağlam kontrolü ve kodlama kalitesi açısından AI destekli otomatik kod review aracından geçer.
- İnsan incelemesi zorunlu olduğu alanlar: mimari karar kayıtları, güvenlik-kritik kod (ödeme, login vb.), KVKK kapsamındaki değişiklikler. Bu alanlarda sorumluluk yetkili geliştiriciye aittir.
- Review, codebase'in tamamı üzerinde tek seferde değil, **katman katman** yürütülür (data layer → business logic → API → frontend); her katmanın kendi kuralı üzerinden değerlendirilir.
- AI kendi ürettiği kodu kendi onaylayıp birleştiremez; nihai onay insanda kalır.

## Gate 5 — Güvenlik (SecOps)

- Canlı öncesi otomatik **SAST/SCA** (statik kod ve bağımlılık güvenlik taraması) çalıştırılır.
- **Critical** ve **High** seviyeli bulgular düzeltilmeden ürün canlıya alınamaz.
- Bu gate, master Madde 5'teki istisna protokolünde **asla atlanamaz** olarak işaretlenmiştir.

## Eşiklerin Gözden Geçirilmesi

Unit/Integration test eşikleri ve SAST/SCA önem seviyesi sınırları, EA/CoE tarafından yıllık olarak veya araç değişikliğinde gözden geçirilir. Değişiklik, master politikayı etkilemez, sadece bu doküman güncellenir.
