# Prosedür: Değişiklik Risk Tier'i

> Tool-agnostik, stack-agnostik şablon. Bu skorlama **projenin geneli** için değil, **tek bir
> değişiklik** (yeni yetenek veya bug-fix/CR) için çalışır — `tier0/RULES.md` Bölüm 1'deki
> MVP/Gerçek-üretim ayrımıyla karıştırılmaz, onun yanında ayrı bir eksendir (bkz. RULES.md
> Bölüm 16). Bir MVP projede de Tier C bir değişiklik olabilir.

## Ne zaman çalıştırılır

- Yeni bir yetenek eklerken, işe başlamadan önce (`tier0/procedures/add-new-capability.md`).
- Bir production bug-fix/CR'a başlarken (`tier0/procedures/production-bugfix-cr.md`).
- Proje başlangıcında bir kez (`tier0/procedures/new-project-design-flow.md` Faz 0/1) —
  projenin **başlangıç** Tier'i olarak kaydedilir, önemli bir mimari değişiklikte yeniden
  skorlanır.

## Skorlama

Beş soru, her biri 0-2 puan. Toplam 0-10.

| # | Soru | Düşük (0) | Orta (1) | Yüksek (2) |
|---|---|---|---|---|
| 1 | Hassas bir alana mı dokunuyor? (ödeme, kimlik doğrulama, KVKK verisi, kuruma özel çekirdek paketler) | Hayır, dokunmuyor | — | Evet, kritik alan |
| 2 | Geri alınabilirlik — bir şey ters giderse? | Anında, veri kaybı olmadan rollback | Zor / kısmen geri alınır | Geri alınamaz veya veri kaybı riski |
| 3 | Bağlantısallık — diğer sistemlerle ilişkisi? | Bağımsız (standalone) araç/modül | Birkaç sisteme bağlı | Çekirdek sistemlere derin entegre |
| 4 | Kullanıcı maruziyeti — kim kullanacak? | Küçük iç ekip | Geniş iç kullanım | Müşteriye / dışa dönük |
| 5 | Kalıcılık — ne kadar yaşayacak? | Atılacak PoC / doğrulama | Belirsiz | Uzun ömürlü, CR biriktirecek sistem |

> **Satır sayısı (diff'te ya da oturumda üretilen) bilerek 6. soru değil.** Aynı gerekçeyle
> (`tier0/procedures/production-bugfix-cr.md` madde 3'teki "Neden satır sayısı değil" notu)
> büyüklük risk veya context-tüketimiyle orantılı değildir. Bir oturumda üretilen kod satırı
> sayısı, diff-budget'ın ham satır/dosya sayısıyla aynı muameleyi görür — Accelerator'ın
> olgunluk metriklerine akan bilgilendirici bir soft-sinyal olabilir, ama Tier skorunu
> **hiçbir zaman** doğrudan etkilemez.

## Eşik ve Tier Eşleşmesi

| Toplam Skor | Tier | Anlamı |
|---|---|---|
| 0–2 | **A** | Düşük risk. Ürün sahibi/Tasarım Sorumlusu + AI tek başına ilerleyebilir. Yazılımcı zorunlu değildir, branch + commit yeterlidir. |
| 3–6 | **B** | Orta risk. Geliştirici + AI birlikte çalışır. Yazılımcı diff review zorunludur, AI tek başına merge edemez. |
| 7–10 | **C** | Yüksek risk. Süreç baştan yazılımcı-led ilerler; AI yalnızca öneri sunar. Ürün sahibi/Tasarım Sorumlusu tek başına dokunamaz. |

> Soru 1'de "Evet, kritik alan" cevabı (2 puan) tek başına, toplam skor düşük olsa bile
> değişikliği **en az Tier B**'ye yükseltir — kritik alan dokunuşu, `tier0/RULES.md` Bölüm
> 4'teki güvenlik baseline'ıyla otomatik olarak ağırlık kazanır.

## Sahiplik

Skorlamayı kim yaptığından bağımsız olarak, Teknik Sorumlu/Lider Tier atamasını onaylar.
Anlaşmazlık durumunda EA/CoE (kurumda varsa) nihai kararı verir.

## Agent Davranışı — mekanik, tartışmasız

Bu skorlamayı çalıştıran bir AI agent için Tier, bir öneri değil bir **durum geçişidir**
(`tier0/RULES.md` Bölüm 16): Tier A/B'de agent adımlarına devam eder (B'de commit'lemeden
önce insan diff review'ını bekleyerek); **Tier C'de agent durur** — kod yazmayı/commit
etmeyi bırakır, yalnızca teşhis/sözleşme taslağı ve öneri sunar, oturumu "insan devraldı"
olarak kapatır. Tek istisna `tier0/procedures/production-bugfix-cr.md` madde 5'teki üretim-
kesintisi acil durum protokolüdür — onun dışında bu hard-stop kesindir, "zaten başlanmıştı"
gerekçesiyle yumuşatılmaz.
