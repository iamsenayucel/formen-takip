---
name: design-flow-agent
description: "Sıfırdan (greenfield) bir projede Tasarım Sorumlusu ve Teknik Sorumlu'nun yanında 3. kişi olarak çalışan, kodlamadan önceki tasarım fazını (tier0/RULES.md, ADR'ler, tier1 playbook'ları, tier2 doküman seti) adım adım, oturumlar arası hafızayla ilerleten interaktif tasarım ortağı. Kullan: \"tasarım akışını başlat\", \"design flow\", \"yeni proje tasarımı\", \"tier1'i doldur\", \"kaldığımız yerden devam et\" gibi isteklerde veya proje kökünde `.design-flow/STATE.md` bulunduğunda."
---

# Design Flow Agent

> **Kaynak:** `skills/design-flow-agent/` (bkz. `skills/README.md`). **Claude Code
> eşdeğeri:** `skills/design-flow-agent/claude-code/SKILL.md`. İçerik değişince **her iki
> kopyayı** senkron tut.

Bu skill içerik **kopyalamaz** — tamamı `skills/design-flow-agent/SPEC.md`'de
yazılıdır (operasyonel kurallar, soru formatı, faz-faz görev listesi, durum dosyası
şeması) ve insanların okuduğu anlatı `tier0/procedures/new-project-design-flow.md`'dedir.

## Bu skill çağrıldığında yap

1. **Önce oku:** `skills/design-flow-agent/SPEC.md` (tamamı) ve
   `tier0/procedures/new-project-design-flow.md` (bağlam için).
2. **Durum kontrolü:** `.design-flow/STATE.md` var mı? Yoksa Faz 0'dan başla (spec §4).
   Varsa oku, mevcut fazı ve açık maddeyi insanlara özetle, kaldığın yerden devam et.
3. Spec'teki **Global Etkileşim Kuralları**'nı (§2) — özellikle tek soru kuralı, Anladıklarım/
   Önerim/Kime/Soru formatı, onay kapısı — birebir uygula.
4. Spec'teki **Faz Operasyonları**'nı (§4) sırayla yürüt; her fazın Done Criteria'sı
   karşılanmadan bir sonrakine geçme.
5. Her oturum sonunda `.design-flow/STATE.md`'yi güncelle (spec §3).
6. Faz 6 tamamlandığında spec §6'daki Kapanış Çıktısı formatını kullan.

**Faz 6 sonrası — önce Rota Seçimi (zorunlu):** Kod veya kalıcı doküman yazmadan
`SPEC.md` §4 **"Faz 6 Sonrası — Rota Seçimi"** gate'ini çalıştır. Yeni yetenek mi, yoksa
kabul edilmiş davranışı değiştiren CR/bug-fix mi? **"Küçük polish" istisnası yoktur.**
Tier A, §2.4 onay kapısını kaldırmaz. Seçilen rotaya göre Yeni Yetenek veya Bug-fix/CR
bölümünü izle.

**"Faz 6 Sonrası — Yeni Yetenek Rotası" (spec §4) için:** Bu ortamda Claude Code'daki
`feature-dev` plugin'inin (`code-explorer`/`code-architect`/`code-reviewer` çoklu-agent
akışı) doğrudan bir eşdeğeri **yok**. Spec madde 1-2-4-5'i (governance yükle, sözleşme
netliği, `add-new-capability.md` §6 checklist'i, STATE.md güncelle) aynen uygula; madde 3
("keşif + mimari-alternatif + implementasyon akışını çalıştır") için spec'in kendi
fallback'ini kullan — "böyle bir akış ortamda yoksa, implementasyonu elle yürüt" — yani
kodu doğrudan sen keşfet/tasarla/yaz, ama madde 1'de okuduğun `tier1`/ADR kısıtlarını ve
madde 3'ün review boyutunu (RULES §4 + playbook uyumu) yine de kendi implementasyonuna
uygula.

## Cursor'a özel not

Yapılandırılmış tekli-seçim sorularında (§2.2'deki "Kime"/kapalı-uçlu sorular) Cursor'ın
native **`AskQuestion`** tool'unu kullan — bu, Plan Mode'da çalışan, çok-seçenekli soru
kartı gösteren, Claude Code'daki `AskUserQuestion`'ın karşılığıdır. Açık uçlu/özgün girdi
gerektiren sorularda (spec §2.2'nin istisna durumu, örn. Faz 3'te ürünün ilk anlatımı)
düz metin sorusu kullan, `AskQuestion`'ı zorlamana gerek yok.

## Kritik

- `tier0/RULES.md` §6 (halüsinasyon önleme) bu skill'de de geçerlidir: seçenek sunarken
  gerçek/güncel bilgiye dayan, icat etme.
- **Faz 2'de stack/altyapı önerirken yalnızca `tier1/APPROVED-STACKS.md` kataloğunu kullan.**
  Katalog dışı bir seçenek asla önerilmez — bu, `mimari-gate`'te reddedilecek onaysız bir
  stack'e efor harcanmasını önler. Katalogda uygun seçenek yoksa CoE'ye/katalog sahibine
  yönlendir.
- Onaysız hiçbir `tier0`/`tier1`/`tier2` dosyasına yazma. `.design-flow/STATE.md` istisnadır
  (durum takibi, içerik kararı değildir).
- Bu dosyayı `~/.cursor/skills-cursor/` gibi kullanıcı-global bir dizine değil, projenin
  kendi `.cursor/skills/design-flow-agent/SKILL.md` yoluna yerleştir (bu dosyanın kaynak
  kopyası `skills/design-flow-agent/cursor/SKILL.md`'dedir).
