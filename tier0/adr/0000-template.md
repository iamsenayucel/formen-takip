# ADR-0000: `<Karar başlığı — kısa, fiil içeren bir cümle>`

**Durum:** `Taslak | Mimari İncelemede | Kabul edildi | Reddedildi | Yerini aldı: ADR-XXXX`
**Tarih:** `YYYY-MM-DD`
**Karar verenler:** `[isim(ler)]`

> `Mimari İncelemede` — kurumda ADR'lerin ayrıca bir Mimari Ekip ve/veya Bilgi Güvenliği
> Ekibi tarafından onaylanması gerekiyorsa (bkz. `skills/design-flow-agent/SPEC.md`
> Faz 2) kullanılır: Teknik Sorumlu oturum içinde onayladı ama harici incelme sonucu
> bekleniyor. Böyle bir onay mercii yoksa bu statü atlanır, doğrudan `Taslak` →
> `Kabul edildi` geçilir.

## Bağlam

`Bu kararı gerektiren durum ne? Hangi kısıt/gereksinim/olay bu kararı tetikledi?
1-2 paragraf — "neden şimdi karar vermemiz gerekiyor" sorusuna cevap.`

## Değerlendirilen Seçenekler

1. **`Seçenek A`** — `kısa açıklama`
2. **`Seçenek B`** — `kısa açıklama`
3. **`Seçenek C (varsa)`** — `kısa açıklama`

## Karar

`Hangi seçenek seçildi ve tek cümlede neden.`

## AI Katkısı / Gerekçesi

`Bu kararın araştırma/taslak/seçenek-üretme aşamasında AI'nın rolü ne oldu — seçenekleri mi
araştırdı, taslağı mı yazdı, yoksa karar tamamen insan tarafından mı verildi ve AI yalnızca
belgeye mi döktü? Kurumsal politika (Master Politika Madde 1: "kodu AI yazdı diyerek
sorumluluktan çıkılamaz") gereği bu alan zorunludur — nihai kararın insan tarafından
verildiğini ve AI'nın rolünün neresinde durduğunu açıkça kaydeder.`

## Sonuçlar

**Artılar:**
- `...`

**Eksiler / kabul edilen riskler:**
- `...`

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** `[varsa referans]`

---

> ⚠️ Hassas veri / harici servis / üçüncü-parti AI entegrasyonu içeren kararlarda
> (`tier0/RULES.md` Bölüm 4, madde 3) **"Sonuçlar"** bölümünde hangi verinin nereye gittiği,
> hangi ortamda (dev/prod) geçerli olduğu açıkça yazılmalı — bu bilgi sadece dokümanda
> kalmamalı, ilgili `tier1/` playbook'una da (Kural alanına) yansıtılmalıdır.
