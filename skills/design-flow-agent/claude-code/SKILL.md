---
name: design-flow-agent
description: "Sıfırdan (greenfield) bir projede Tasarım Sorumlusu ve Teknik Sorumlu'nun yanında 3. kişi olarak çalışan, kodlamadan önceki tasarım fazını (tier0/RULES.md, ADR'ler, tier1 playbook'ları, tier2 doküman seti) adım adım, oturumlar arası hafızayla ilerleten interaktif tasarım ortağı. Kullan: \"tasarım akışını başlat\", \"design flow\", \"yeni proje tasarımı\", \"tier1'i doldur\", \"kaldığımız yerden devam et\" gibi isteklerde veya proje kökünde `.design-flow/STATE.md` bulunduğunda."
---

# Design Flow Agent

> **Kaynak:** `skills/design-flow-agent/` (bkz. `skills/README.md`). **Cursor eşdeğeri:**
> `skills/design-flow-agent/cursor/SKILL.md`. İçerik değişince **her iki kopyayı** senkron
> tut.

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

## Claude Code'a özel not

Yapılandırılmış tekli-seçim sorularında (§2.2'deki "Kime"/seçenekli sorular) `AskUserQuestion`
tool'unu kullan — bu, spec'in "kapalı-uçlu soru" tercihini native olarak destekler ve
insanların serbest metin yazmasını değil, seçim yapmasını sağlar.

**"Faz 6 Sonrası — Yeni Yetenek Rotası" (spec §4) için:** Bu ortamda "keşif +
mimari-alternatif + implementasyon akışı" karşılığı `feature-dev` plugin'idir
(`/feature-dev:feature-dev` komutu, `code-explorer`/`code-architect`/`code-reviewer`
alt-agent'ları). Bu komutu **çağırmadan önce** spec madde 1-2'yi (governance context yükle,
sözleşme netliği) tamamla. Komutu çağırdıktan sonra onun 7 fazını (Discovery → Codebase
Exploration → Clarifying Questions → Architecture Design → Implementation → Quality Review
→ Summary) **olduğu gibi** izle, yalnızca spec madde 3'teki üç enjeksiyonu uygula:
- Phase 2 (Codebase Exploration) için code-explorer'lara verdiğin görev tanımına, madde
  1'de okuduğun ilgili `tier1` playbook'larını ve ADR'leri "bunlar koddan öncelikli kaynak"
  notuyla ekle.
- Phase 4 (Architecture Design) için code-architect'lere verdiğin görev tanımına, "hiçbir
  alternatif şu ADR'lerle çelişemez: [liste]" kısıtını ekle.
- Phase 6 (Quality Review) için üç code-reviewer'dan birinin odağını "RULES/playbook
  uyumu"na çevir (spec madde 3, üçüncü madde).

Phase 7 (Summary) feature-dev'in kendi özetidir — spec madde 4'teki
`add-new-capability.md` §6 checklist'i **buna ek olarak**, feature-dev bittikten sonra
ayrıca uygulanır; feature-dev'in özeti bu checklist'in yerine geçmez.

## Kritik

- `tier0/RULES.md` §6 (halüsinasyon önleme) bu skill'de de geçerlidir: seçenek sunarken
  gerçek/güncel bilgiye dayan, icat etme.
- **Faz 2'de stack/altyapı önerirken yalnızca `tier1/APPROVED-STACKS.md` kataloğunu kullan.**
  Katalog dışı bir seçenek asla önerilmez — bu, `mimari-gate`'te reddedilecek onaysız bir
  stack'e efor harcanmasını önler. Katalogda uygun seçenek yoksa CoE'ye/katalog sahibine
  yönlendir.
- Onaysız hiçbir `tier0`/`tier1`/`tier2` dosyasına yazma. `.design-flow/STATE.md` istisnadır
  (durum takibi, içerik kararı değildir).
- Bu dosyanın proje içindeki yeri `.claude/skills/design-flow-agent/SKILL.md`'dir (Claude
  Code'un skill'leri aradığı sabit konum) — kaynak kopyası `skills/design-flow-agent/
  claude-code/SKILL.md`'dedir.
