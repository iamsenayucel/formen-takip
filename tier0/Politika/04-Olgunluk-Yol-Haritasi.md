# Olgunluk Yol Haritası

**Bağlı olduğu master madde:** 00-Master-Politika.md → Madde 0, Madde 2
**Sorumlu:** AI-Assisted Development Accelerator (→ tanım ve hesap verebilirlik alanı için bkz. Master Politika Madde 2), EA / CoE
**Güncelleme kadansı:** Altı ayda bir veya seviye geçişinde

## Amaç

Master politika statik bir kural setidir; ilerlemenin nasıl ölçüleceğini tanımlamaz. Bu doküman, organizasyonun AI destekli geliştirme olgunluğunu **ölçülebilir bir model** üzerinden takip eder ve bu takibi yürütecek operasyonel rolü tanımlar.

## Olgunluk Seviyeleri

| Seviye | Tanım |
|---|---|
| 1 — Başlangıç | Bireysel geliştiriciler kendi inisiyatifiyle AI araçlarını kullanıyor; standart yok, çıktı kalitesi kişiye bağlı. |
| 2 — Tanımlı | Onaylı araç listesi var, temel kurallar belirlenmiş; uygulama takım bazında farklılık gösteriyor. |
| 3 — Standart | Skill kütüphanesi oluşturulmuş, SDLC fazları AI-assisted sürece göre tanımlanmış, tüm projeler aynı çerçeve üzerinden ilerliyor. |
| 4 — Ölçülen | Metrikler takip ediliyor (cycle time, bug oranı, skill etkinliği); süreç veriye dayalı iyileştiriliyor. |
| 5 — Optimize | Süreç kendi kendini besliyor; lessons-learned otomatik olarak yeni standartlara dönüşüyor. |

**Güncel değerlendirme:** Organizasyon Seviye 1-2 arasında. Bu master politika ve alt dokümanları, Seviye 3'e geçişin altyapısıdır.

## Takip Edilecek Metrikler (Seviye 4 hedefi)

- **Cycle time:** AI-assisted projeler gerçekten daha mı hızlı; darboğaz nerede?
- **Bug oranı:** AI üretimi kod ile insan üretimi kod arasında prod-bug yoğunluğu farkı.
- **Skill/Gate etkinliği:** Hangi skill/gate en sık istisna/atlama talebi görüyor — bu, standardın gerçekçi olup olmadığının göstergesi.
- **Tier dağılımı:** Bug-fix'lerin Tier A/B/C dağılımı; C'nin oranı artıyorsa mimari borç sinyalidir.

## AI-Assisted Development Accelerator Rolü

> **Rol tanımı ve PO ile ilişkisi → Master Politika Madde 2.** Bu bölüm rolün operasyonel sorumluluklarını detaylandırır.

Agile dönüşümde Scrum Master'ın üstlendiği role benzer şekilde, bu dönüşümün de bir **operasyonel sahibi** olmalı — EA/CoE'nin stratejik/onay rolünden ayrı, günlük işletimi yürüten taktik bir rol.

**Sorumlulukları:**
- Mimarlarla birlikte standart ve metodları güncelleme.
- Skill kütüphanesinin üretimi, versiyonlanması, bakımı.
- Araç ekosistemi takibi (yeni araç pilotlama, MCP/local LLM değerlendirmesi vb.).
- Eğitim materyali ve onboarding programının işletilmesi (→ Eğitim Yönergesi).
- Lessons-learned döngüsünü yürütme ve bunu yeni standartlara dönüştürme.
- Bu dokümandaki metriklerin toplanması ve altı ayda bir EA/CoE'ye raporlanması.

> **Gerekçe:** EA/CoE stratejik onay merciidir ama günlük taktik iş (skill üretimi, eğitim, pilot) için ayrı bir zaman/dikkat bütçesi gerekir. Bu rol olmadan olgunluk seviyesi 2'de donar — kurallar vardır ama kimse onları yaşatmaz.

## Seviye Geçiş Kriterleri (özet)

- **2 → 3:** Skill kütüphanesi var, tüm projeler aynı SDLC çerçevesini kullanıyor, Gate Operasyon Standardı fiilen uygulanıyor (uygunluk denetiminde %90+ uyum).
- **3 → 4:** Üç ardışık çeyrekte metrik toplama düzenli, en az bir standart bu verilerle revize edilmiş.
- **4 → 5:** Lessons-learned süreci, bir insan müdahalesi olmadan yeni skill/standart taslağı önerebiliyor.
