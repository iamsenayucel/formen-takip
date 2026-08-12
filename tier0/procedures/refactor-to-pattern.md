# Prosedür: Mevcut Pattern'e Refactor

> Amaç: kodu, kod tabanında zaten kurulu bir kalıba uydurmak — yeni bir kalıp icat etmek değil.

## 1. Kaynağı belirle

Uyulacak pattern nerede tanımlı? Önce ilgili `tier1/*.md` playbook bölümüne, sonra oradaki
**Referans** dosyasına bak. İkisi de yoksa, kod tabanında en yakın benzer örneği bul —
"muhtemelen böyle yapılır" diye tahmin etme (`tier0/RULES.md` Bölüm 6, madde 4).

## 2. Davranışı sabitleyen bir test var mı, kontrol et

Refactor öncesi mevcut davranışı kilitleyen bir test yoksa, önce onu yaz. Refactor,
davranışı **değiştirmeden** yapı değiştirmektir — bunu doğrulayacak bir mekanizma olmadan
"refactor" fiilen "yeniden yazma" riski taşır.

## 3. Küçük, geri alınabilir adımlarla ilerle

Tek dev commit yerine, her adımda testler yeşil kalacak şekilde küçük adımlar at
(`tier0/RULES.md` Bölüm 2, madde 4). Bir adımda testler kırılırsa, bir önceki adıma dön.

## 4. Kapsamı genişletme

Refactor sırasında "madem buradayım" diyerek ilgisiz iyileştirmeler ekleme — ayrı bir
görev olarak not al, bu değişikliğe karıştırma.

## 5. Self-review

- [ ] Davranış değişmedi mi (testler kanıtlıyor mu)?
- [ ] Yeni kod, referans alınan pattern'le tutarlı mı?
- [ ] Kapsam dışı değişiklik sızmadı mı?
