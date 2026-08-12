# Skill'ler — Tek Adres

Bu klasör, kurumun **tüm interaktif skill'lerinin** tek, merkezi adresidir. "Skill" —
`tier0/procedures/*.md`'deki pasif prosedürlerin aksine — **tetiklenerek çağrılan,
oturumlar arası hafızası olan, insanlarla soru-cevap yürüten** bir agent davranışıdır.

## Klasör kalıbı

Her skill kendi alt klasöründe, şu yapıyla yaşar:

```
skills/<skill-adı>/
  SPEC.md              ← tool-agnostik operasyonel spec — skill'in "beyni"
  cursor/SKILL.md       ← Cursor'a özel ince kopya (proje köküne .cursor/skills/<skill-adı>/'a kopyalanır)
  claude-code/SKILL.md  ← Claude Code'a özel ince kopya (proje köküne .claude/skills/<skill-adı>/'a kopyalanır)
```

**Altın kural, burada da geçerli:** `SPEC.md` içerik taşır (kurallar, soru formatı, durum
makinesi, faz-faz görev listesi). `cursor/SKILL.md` ve `claude-code/SKILL.md` içerik
**kopyalamaz** — yalnızca "önce `SPEC.md`'yi oku, sonra uygula" der + o aracın kendine özgü
küçük notlarını (örn. Cursor'da `AskQuestion` tool'u, Claude Code'da `AskUserQuestion`
tool'u) taşır. Bu, `tier1/README.md`'deki "içerik bir kez yazılır" ilkesinin skill'ler
için karşılığıdır.

## Neden `tier0/procedures/` veya `adapters/` altında değil

- `tier0/procedures/` **pasif** prosedürler içindir — bir insan (veya agent) okur, elle
  uygular; oturumlar arası durum takibi yoktur. Bir skill ise `.design-flow/STATE.md`
  benzeri bir durum dosyasıyla **aktif olarak** ilerler.
- `adapters/` yalnızca **her-zaman-yüklü** kural mekanizmasını kurar (`.cursor/rules/`,
  `CLAUDE.md`) — **tetiklenerek** çağrılan skill'ler kavramsal olarak farklı bir
  mekanizma, kendi klasörünü hak ediyor.

## Mevcut skill'ler

| Skill | Ne yapar | Zorunlu mu |
|---|---|---|
| `design-flow-agent` | Greenfield tasarım fazında (`tier0/procedures/new-project-design-flow.md`) Tasarım Sorumlusu + Teknik Sorumlu'nun yanında çalışan interaktif tasarım ortağı | Kullanımı zorunlu değil ama önerilir — tasarım fazını elle de yürütebilirsiniz |
| `vibe-coding-bootstrap` | Bu repoyu clone'layıp yeni bir projenin mekanik iskeletini (tier0/tier1, seçilen AI aracının adaptörü, `design-flow-agent` kopyası) kurar — kök `README.md`'nin "Hızlı Başlangıç" 1-4'ünü otomatikleştirir | Kullanımı zorunlu değil, elle de kurulabilir. **Diğer skill'lerden farkı:** proje kökünde yaşamaz, kullanıcının global CLI skill dizininde kurulu kalır (bkz. kendi `SPEC.md`'si) |

## Yeni bir skill eklerken

1. `skills/<yeni-skill-adı>/SPEC.md` yazın — tool-agnostik, `design-flow-agent/SPEC.md`'yi
   örnek alın (persona, global etkileşim kuralları, durum dosyası protokolü, faz/görev
   listesi, anti-pattern tablosu).
2. Desteklemek istediğiniz her araç için `skills/<yeni-skill-adı>/<araç>/SKILL.md` yazın —
   birkaç satırlık, yalnızca `SPEC.md`'ye işaret eden bir dosya.
3. İlgili `adapters/<araç>/README.md`'ye "Bu skill'i nasıl kurarsınız" notu ekleyin (bkz.
   `adapters/cursor/README.md`'deki "Tasarım fazı için: Design Flow Agent skill'i" bölümü
   örnek alınabilir).
4. Bu dosyadaki "Mevcut skill'ler" tablosuna satır ekleyin.
