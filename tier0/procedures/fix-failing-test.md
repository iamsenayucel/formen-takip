# Prosedür: Bozuk Testi Teşhis Etme

> Bir test kırmızı olduğunda ilk refleks "testi geçecek şekilde düzelt" olmamalı — önce
> **neden** kırmızı olduğu teşhis edilir. Yanlış teşhis, gerçek bir bug'ı maskeler.

Kırmızı bir test, aşağıdaki 4 kategoriden birine girer — teşhis sırası önemlidir:

## 1. Gerçek bug (en olası, önce bunu ele)

Kod, testin beklediği doğru davranışı üretmiyor. **Çözüm: kodu düzelt, testi değil.**
Bu durumda testi "geçsin diye" gevşetmek, hatayı üretime taşımaktır.

## 2. Eski/artık geçersiz test

Davranış bilinçli olarak değişti (bir kararla, örn. bir ADR ile) ve test hâlâ eski
davranışı bekliyor. **Çözüm: testi yeni davranışa güncelle** — ama bu güncellemenin
gerekçesi (hangi karar/ADR) commit mesajında veya test yorumunda belirtilir.

## 3. Flaky (kararsız) test

Test bazen geçiyor bazen geçmiyor, kod değişmese bile. Genelde zamanlama/sıralama/paylaşılan
state varsayımı sorunudur. **Çözüm: kök nedeni bul (race condition, sabit olmayan sıralama,
temizlenmeyen state) — `test.retry()` gibi bir mekanizmayla üstünü örtme.**

## 4. Ortam sorunu

Test, geliştirici makinesinde/CI'da eksik bir bağımlılık, yanlış env değişkeni veya farklı
bir sürüm yüzünden kırılıyor — kodla ilgisi yok. **Çözüm: ortamı düzelt/dokümante et**, kodu
veya testi değiştirme.

## Teşhis akışı

1. Testi izole çalıştır (tek başına) — flaky mi anlaşılır (kategori 3 ihtimali).
2. Son değişen commit'leri kontrol et — kod mu değişti, test mi, ikisi de mi.
3. Hata mesajını satır satır oku — "assertion failed" mi, "cannot find module" mı
   (kategori 4 sinyali), "timeout" mu (kategori 1 veya 3).
4. Kategori belirlenmeden düzeltme yapılmaz.
