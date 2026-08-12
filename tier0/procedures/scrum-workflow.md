# Prosedür: Scrum Board İş Akışı

> `issue-tracker-doc-workflow.md`'nin üzerine kurulur — doküman-konumlandırma temel kuralı
> orada, burada tekrar edilmez. Bu dosya yalnızca **Scrum'a özel cadence** (sprint, epic/
> story/task hiyerarşisi, sprint kapanışı) detayını taşır. Proje Kanban kullanıyorsa bu dosya
> uygulanmaz — gerekirse ayrı bir `kanban-workflow.md` yazılır (henüz yok, ihtiyaç çıktığında
> eklenir).
>
> **Uygulanma derecesi:** `issue-tracker-doc-workflow.md` §0'daki eksenle aynı — Scrum board
> **açmanın kendisi** her proje türünde ekibin tercihidir, hiç zorunlu kılınmaz. Board zaten
> açıldıysa, bu dosyanın maddelerini uygulama derinliği Gerçek/üretim projelerde beklenir,
> MVP/deneme projelerinde ekibin takdirine kalır.

## 1. Roadmap ↔ Sprint ilişkisi

`docs/09-uygulama-yol-haritasi.md`, sprint planının **canonical kaynağı değildir** —
canonical kaynak tracker'ın board/sprint yapısıdır. `docs/09` yalnızca faz/bağımlılık
**özetini** taşır ve tracker ile senkron tutulur (sprint tamamlandıkça ilgili maddenin durumu
güncellenir); sprint'in ikinci bir kopyası olarak büyütülmez.

## 2. Epic/Story/Task ↔ docs/0X ilişkisi

Bir Epic genelde bir veya birkaç `docs/0X` bölümüne karşılık gelir (örn. "silme talebi
backend servisi" epic'i → `docs/03` şema + `docs/04` API + `docs/10` süreç). Alt task'lar
**aynı dokümanın farklı bölümlerini** günceller — bir task için yeni, ayrı bir doküman açmak
yasaktır (bkz. `issue-tracker-doc-workflow.md` madde 1, "içerik bir kez yazılır").

## 3. Definition of Done (task/story bazında)

`tier0/procedures/add-new-capability.md`'nin 7 adımı + `issue-tracker-doc-workflow.md`
madde 3-4 (referans + distilasyon). Bir ticket, bu iki prosedürün toplamı tamamlanmadan
"Done" sayılmaz.

## 4. Sprint kapanışı

Sprint kapanışında **yeni bir doküman üretilmez**. Yalnızca:
- `docs/09`'daki ilgili faz/maddenin durumu güncellenir (Taslak → Tamamlandı/Devam ediyor).
- Sprint içinde ortaya çıkan yeni mimari kararlar (varsa) ADR olarak eklenmiş olmalı —
  kapanışta eksik ADR var mı diye kontrol edilir; sprint retro'suna not düşülüp bırakılmaz,
  ADR'ye dönüştürülür.

## 5. Risk kaydı

`docs/09`'daki risk kaydı (varsa, Seviye 1/2 projelerde — bkz. `tier0/RULES.md` §1 "MVP
Disiplini Ölçeklenmesi") sprint bazında değil, **gerçek durum değiştiğinde** güncellenir —
her sprint kapanışında mekanik olarak "gözden geçirildi" denip aynen bırakılmaz.
