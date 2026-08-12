---
name: vibe-coding-bootstrap
description: "Yeni bir 'vibe coding' projesine, YTech AI-Assisted Coding CoE'nin YH-vibe-coding-framework reposundan mekanik başlangıç iskeletini kurar: AI coding tool'unu sorar, kaynak repoyu clone/pull eder, kök README.md ve seçilen aracın adapters/<tool>/README.md dosyasını okuyup yönergelerini harfiyen uygular. Kullan: \"yeni proje başlat\", \"vibe coding projesi kur\", \"bootstrap yap\", \"proje iskeletini kur\", \"CoE şablonundan başlat\" gibi isteklerde. Kapsamı yalnızca mekanik kurulumdur — tasarım fazının kendisi kurulum bitince tetiklenen ayrı bir skill olan design-flow-agent'a aittir."
---

# Vibe Coding Bootstrap

> **Kaynak:** `skills/vibe-coding-bootstrap/` (bkz. `skills/README.md`). Bu skill'in şu an
> yalnızca bu (Claude Code) kopyası var — Cursor/diğer araçlar için henüz yazılmadı, bkz.
> `SPEC.md` "Bilinen Sınır".

Bu skill içerik **kopyalamaz** — tamamı `skills/vibe-coding-bootstrap/SPEC.md`'de
yazılıdır (kritik kurallar, 9 adımlık süreç, bilinen sınırlar).

## Bu skill çağrıldığında yap

0. **Önce kaynağı edin** (SPEC.md'nin kendisi de bu repoda yaşıyor, okumadan önce
   getirilmesi gerekir):
   ```bash
   CACHE_DIR="$HOME/.claude/skills/vibe-coding-bootstrap/.source-cache/YH-vibe-coding-framework"
   if [ -d "$CACHE_DIR/.git" ]; then
     git -C "$CACHE_DIR" pull --ff-only
   else
     mkdir -p "$(dirname "$CACHE_DIR")"
     git clone https://github.com/fatihcenesiz-alfa/YH-vibe-coding-framework.git "$CACHE_DIR"
   fi
   ```
1. **Oku:** `$CACHE_DIR/skills/vibe-coding-bootstrap/SPEC.md` (tamamı).
2. Spec'teki **Süreç**'i (9 adım) sırayla yürüt — Adım 3 (kaynağı edin) yukarıdaki 0.
   adımla zaten yapıldı, tekrar çalıştırmak zararsız (idempotent `pull`); Adım 4'ü (kök
   README + tier1/README'i oku) hiç varsaymadan uygula.
3. Spec'teki **Kritik kurallar**'ı birebir uygula — özellikle "hiçbir adaptör/kopyalama
   talimatını ezbere yazma" kuralı: her çalıştırmada o an klonlanmış repodaki gerçek
   README içeriğini oku, bu dosyada veya SPEC.md'de sabit bir tablo arama.

## Claude Code'a özel not

Adım 2'deki (AI coding tool seçimi) yapılandırılmış çoklu-seçim soruda `AskUserQuestion`
tool'unu kullan (`multiSelect: true`). Adım 1, 8'deki `git init` onayı gibi açık uçlu/onay
gerektiren noktalarda serbest metin yeterli, `AskUserQuestion` gerekmez.

## Kritik

- `tier0/RULES.md` §6 (halüsinasyon önleme) bu skill'de de geçerlidir.
- Bu dosyanın proje köküne kopyalanan bir hali **yoktur** — `design-flow-agent`'ın aksine,
  bu skill proje henüz yokken çalışır ve kullanıcının kendi global Claude Code skill
  dizininde (`~/.claude/skills/vibe-coding-bootstrap/`) kurulu kalır. Kaynak kopyası
  `skills/vibe-coding-bootstrap/claude-code/SKILL.md`'dedir — içerik değişince ikisini
  senkron tut.
