# Risk Değerlendirme Standardı

**Bağlı olduğu master madde:** 00-Master-Politika.md → Madde 1 (İlke 2), Madde 2
**Sorumlu:** EA / CoE
**Güncelleme kadansı:** İhtiyaç halinde, master'ı tetiklemeden

## Amaç

Master politika, kontrol şiddetinin riske orantılı olması ilkesini koyar ama "MVP mi / Production mı" gibi ikili bir anahtar kullanmaz. Bu doküman, bir değişikliğin (yeni geliştirme, bug-fix, CR) hangi risk seviyesinde olduğunu **ölçülebilir** bir şekilde belirler. Çıktı, hem geliştirmenin başında ("bu iş yazılımcı gerektirir mi?") hem bug-fix anında (→ `03-CR-BugFix-Runbook.md`) kullanılır.

## Skorlama Yöntemi

Beş soru, her biri 0-2 puan. Toplam 0-10.

| # | Soru | Düşük (0) | Orta (1) | Yüksek (2) |
|---|---|---|---|---|
| 1 | Hassas bir alana mı dokunuyor? (ödeme, kimlik doğrulama, KVKK verisi, kuruma özel paylaşılan çekirdek paketler) | Hayır, dokunmuyor | — | Evet, kritik alan |
| 2 | Geri alınabilirlik — bir şey ters giderse? | Anında, veri kaybı olmadan rollback | Zor / kısmen geri alınır | Geri alınamaz veya veri kaybı riski |
| 3 | Bağlantısallık — diğer sistemlerle ilişkisi? | Bağımsız (standalone) araç/modül | Birkaç sisteme bağlı | Çekirdek sistemlere derin entegre |
| 4 | Kullanıcı maruziyeti — kim kullanacak? | Küçük iç ekip | Geniş iç kullanım | Müşteriye / dışa dönük |
| 5 | Kalıcılık — ne kadar yaşayacak? | Atılacak PoC / doğrulama | Belirsiz | Uzun ömürlü, CR biriktirecek sistem |

## Eşik ve Tier Eşleşmesi

| Toplam Skor | Tier | Anlamı |
|---|---|---|
| 0–2 | **A** | Düşük risk. Ürün sahibi + AI tek başına ilerleyebilir. Yazılımcı zorunlu değildir, branch + commit yeterlidir. |
| 3–6 | **B** | Orta risk. Geliştirici + AI birlikte çalışır. Yazılımcı diff review zorunludur, AI tek başına merge edemez. |
| 7–10 | **C** | Yüksek risk. Süreç baştan yazılımcı-led ilerler; AI yalnızca öneri sunar. Ürün sahibi tek başına dokunamaz. |

> Not: Soru 1'de "Evet, kritik alan" cevabı (2 puan) tek başına, toplam skor düşük olsa bile değişikliği **en az Tier B**'ye yükseltir — kritik alan dokunuşu, master Madde 6'daki yasaklı alan kuralıyla otomatik olarak ağırlık kazanır.

## Kullanım Anları

1. **Geliştirme başlangıcında** ("bu iş yazılımcı gerektirir mi?") — Ürün ekibi veya geliştirici, işe başlamadan bu 5 soruyu yanıtlar, Tier belirlenir, Teknik Lider'e bildirilir.
2. **Bug-fix/CR anında** — aynı skorlama, `03-CR-BugFix-Runbook.md`'deki diff bütçesiyle birlikte kullanılır.
3. **Gate 1 (Başlangıç) sırasında** — proje başlangıç Tier'i, ilk Mimari Gate onayına eklenir ve projenin ömrü boyunca referans alınır; önemli bir mimari değişiklik olduğunda yeniden skorlanır.

## Sahiplik

Skorlamayı kim yaptığından bağımsız olarak, **Teknik Lider** Tier atamasını onaylar. Anlaşmazlık durumunda EA/CoE nihai kararı verir (master Madde 2).
