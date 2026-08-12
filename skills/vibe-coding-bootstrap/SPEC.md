# Vibe Coding Bootstrap — Operasyonel Spesifikasyon

> Bu dosya **agent'ın** okuyup birebir uyguladığı, tool-agnostik operasyonel
> spesifikasyondur. `skills/vibe-coding-bootstrap/claude-code/SKILL.md` altındaki ince
> kopya buna işaret eder — içerik burada bir kez yazılır (bkz. `skills/README.md`).

> **Bu skill'in `skills/`'teki diğer skill'lerden (örn. `design-flow-agent`) farkı:**
> `design-flow-agent` her yeni projeye **kopyalanır** ve proje kökünden çalışır.
> `vibe-coding-bootstrap` ise proje **henüz yokken** çalışır — kaynak repoyu clone'layıp
> yeni projenin iskeletini kurar. Bu yüzden proje-içi bir kopyası **olmaz**; bu araç,
> kullanıcının kendi AI coding ortamında (CLI skill, global konumda) kurulu kalır ve her
> yeni proje başlatıldığında oradan tetiklenir. Yine de içerik burada, `skills/` altında
> yaşar — kurumun "tüm interaktif skill'lerin tek adresi" ilkesi (`skills/README.md`) bu
> skill için de geçerli, sadece **konuşlanma** modeli farklı.

---

## Ne yapar, ne yapmaz

**Yapar:** `YH-vibe-coding-framework` reposunun mekanik kopyalama/kurulum adımlarını
(kök `README.md`'deki "Hızlı Başlangıç" 1-4) otomatikleştirir — repoyu getirir, seçilen
AI coding tool'a göre doğru adaptör dosyalarını ve `design-flow-agent` skill kopyasını
yeni projenin köküne yerleştirir.

**Yapmaz:** `tier0/RULES.md` içindeki placeholder'ları doldurmaz, ADR yazmaz, stack
seçmez, `tier1/` playbook'larını budamaz. Bunların hepsi kurulum bittikten sonra
tetiklenen **`design-flow-agent`** skill'inin işidir (bkz. Adım 8). Bu skill sadece doğru
dosyaların doğru yerde olmasını sağlar — içerik kararı vermez.

## Kritik kurallar

- **Hiçbir adaptör/kopyalama talimatını ezbere yazma.** Bu dosyada hangi dosyanın nereye
  kopyalanacağına dair sabit bir tablo **bilerek yok** — kaynak repo (`adapters/*/README.md`,
  `skills/README.md`) zamanla değişebilir (yeni araç, yeni skill kopyası eklenebilir). Her
  çalıştırmada o an klonlanmış/güncellenmiş repodaki gerçek README içeriğini oku ve onu
  uygula. Bu, `tier0/RULES.md` Bölüm 6'daki halüsinasyon-önleme kuralının bu skill'e
  yansımasıdır.
- **Hedef proje dizininde var olan hiçbir dosyanın üzerine sormadan yazma.** Özellikle
  `CLAUDE.md`, `.cursor/`, `.github/` gibi yollarda kullanıcının kendi içeriği olabilir.
- `example-projects/` klasörünü **asla** hedef projeye kopyalama — kök `README.md`'nin
  kendi tablosunda "şablonun parçası değil, kopyalanmaz" diye açıkça işaretli, CoE reposunda
  yaşayan referans örneklerdir.
- `tier2/` klasörünü de kopyalama — `tier2/README.md`'nin kendisi "bu repodan kopyalanmaz,
  sadece kontrol listesi" der. Hedef projede sadece boş bir `docs/` klasörü açılır; kontrol
  listesi tasarım fazında kaynaktan (veya cache'lenmiş kopyadan) okunarak kullanılır.
- `tier1/`'i **budamadan, olduğu gibi** kopyala (`catalog/` + `templates/` + `playbooks/`
  hepsi). Hangi stack playbook'unun kalıp hangisinin silineceği bir stack kararı gerektirir
  — bu karar henüz verilmemiştir, `design-flow-agent` Faz 2'nin işidir.
- Seçilmeyen araçların adaptör/skill dosyalarını hedef projeye **taşıma** (gereksiz kalabalık
  yaratır) — yalnız kullanıcının seçtiği araç(lar) için olanları getir.

## Süreç

### 1. Hedef proje dizinini belirle

Kullanıcıya sor: bu iskelet nereye kurulacak — yeni/boş bir klasör mü, yoksa zaten
oluşturulmuş ama henüz doldurulmamış bir proje kökü mü? Tam yol iste (serbest metin, bu
açık uçlu bir girdi — yapılandırılmış bir soru gerekmez).

Yol kontrolü:
- Klasör yoksa `mkdir -p` ile oluştur.
- Klasör varsa ve içinde zaten `tier0/` veya `tier1/` varsa: bu proje **daha önce bootstrap
  edilmiş** demektir — kullanıcıya söyle, üzerine yazmadan önce ne yapmak istediğini sor
  (güncelle/atla/iptal).
- Klasör varsa ve içinde ilgisiz dosyalar varsa (ör. zaten bir `README.md`), kopyalama
  sırasında çakışan her dosya için tek tek onay iste, sessizce ezme.

### 2. AI coding tool seçimini sor

Yapılandırılmış, kapalı-uçlu, çoklu-seçim bir soru olarak (Cursor `AskQuestion` / Claude
Code `AskUserQuestion` — birden fazla araç aynı anda kurulabilir, repo bunu destekliyor,
bkz. `adapters/README.md`):

- **Claude Code** — `CLAUDE.md` + `.claude/skills/design-flow-agent/`
- **Cursor** — `.cursor/rules/*.mdc` + `.cursor/skills/design-flow-agent/`
- **GitHub Copilot** — `.github/copilot-instructions.md` + `.github/instructions/*.md`
- **Antigravity** — kaynak repoda henüz kesinleşmemiş, prensip-düzeyinde (kurulumda
  kullanıcıya bu belirsizlik açıkça söylenecek)

Kullanıcı listede olmayan bir araç derse ("Diğer" serbest metin), `adapters/other-tools/`
akışına düş.

### 3. Kaynak repoyu edin

Yerel bir cache kullan, her çalıştırmada tazele:

```bash
CACHE_DIR="$HOME/.claude/skills/vibe-coding-bootstrap/.source-cache/YH-vibe-coding-framework"
if [ -d "$CACHE_DIR/.git" ]; then
  git -C "$CACHE_DIR" pull --ff-only
else
  mkdir -p "$(dirname "$CACHE_DIR")"
  git clone https://github.com/fatihcenesiz-alfa/YH-vibe-coding-framework.git "$CACHE_DIR"
fi
```

- HTTPS clone/pull başarısız olursa (repo private, kimlik doğrulama gerekebilir) SSH'ı dene
  (`git@github.com:fatihcenesiz-alfa/YH-vibe-coding-framework.git`).
- İkisi de başarısız olursa kullanıcıya söyle ve zaten var olan yerel bir clone'un yolunu
  iste — repo URL'sini veya varlığını **icat etme**.
- Cache güncellendikten sonra `git -C "$CACHE_DIR" log -1 --oneline` ile hangi commit'ten
  çalıştığını not al; kapanış özetinde bu bilgiyi kullanıcıya ver (şeffaflık — hangi repo
  durumundan kurulduğu izlenebilir olsun).

### 4. Kök README ve tier1/README'i oku

`$CACHE_DIR/README.md` (özellikle "Hızlı Başlangıç" ve "Repo Haritası" bölümleri) ve
`$CACHE_DIR/tier1/README.md`'i (yoğunluk/pruning kuralı — bu skill prune etmez ama neden
etmediğini bilerek hareket etmek için) oku. Bu adımı atlama; kullanıcının isteği net biçimde
"repodan README'leri okusun" diyor — bu, sabit bir kopyalama tablosunu ezbere uygulamak
yerine her seferinde güncel yönergeye bakmak demektir.

### 5. tier0/ ve tier1/'i olduğu gibi kopyala

```bash
cp -r "$CACHE_DIR/tier0" "$TARGET/tier0"
cp -r "$CACHE_DIR/tier1" "$TARGET/tier1"
mkdir -p "$TARGET/docs"
```

`tier2/` kopyalanmaz (bkz. Kritik kurallar). `docs/` boş açılır — tasarım fazında
doldurulur.

### 6. skills/design-flow-agent'ı getir

Yalnızca seçilen araç(lar) için:

```bash
mkdir -p "$TARGET/skills/design-flow-agent"
cp "$CACHE_DIR/skills/README.md" "$TARGET/skills/README.md"
cp "$CACHE_DIR/skills/design-flow-agent/SPEC.md" "$TARGET/skills/design-flow-agent/SPEC.md"
# her seçilen <tool> için:
cp -r "$CACHE_DIR/skills/design-flow-agent/<tool>" "$TARGET/skills/design-flow-agent/<tool>"
```

Eğer seçilen araç için `skills/design-flow-agent/<tool>/` kaynak repoda **yoksa**
(kontrolü elle yap, varsayma), bunu kullanıcıya açıkça söyle: bu araç için henüz hazır bir
`SKILL.md` kopyası yok, `SPEC.md`'yi elle referans etmesi gerekecek, isterse CoE'ye
`skills/README.md`'deki "Yeni bir skill eklerken" prosedürüyle bir kopya eklenmesini talep
edebilir. Var olmayan bir dosyayı icat edip oluşturma. `vibe-coding-bootstrap`'ın kendisi
de bu kurala tabidir — şu an yalnızca `claude-code/` kopyası var.

### 7. Her seçilen araç için adaptörü kur

Her seçilen `<tool>` için `$CACHE_DIR/adapters/<tool>/README.md`'yi oku ve **yazdığı
adımları harfiyen uygula** — hangi örnek dosyanın hedef projede hangi yola kopyalanacağı
o dosyada yazar (ör. Claude Code için `CLAUDE.md` proje köküne, Cursor için
`.cursor/rules/00-rules-pointer.mdc`, GitHub Copilot için `.github/copilot-instructions.md`
+ `.github/instructions/backend.instructions.md`). Bu adım için sabit bir kopyalama listesi
kullanma; okuduğun README ne diyorsa onu yap.

Aynı README'nin "Tasarım fazı için: Design Flow Agent skill'i" bölümü, o aracın
skill-keşif konumunu da söyler (ör. Claude Code'da `.claude/skills/design-flow-agent/
SKILL.md`, Cursor'da `.cursor/skills/design-flow-agent/SKILL.md`) — Adım 6'da
`skills/design-flow-agent/<tool>/SKILL.md`'ye getirdiğin dosyanın **aynısını** bu ikinci
konuma da kopyala (repo bilerek iki kopya tutuyor: biri kaynak/senkron kopyası, biri aracın
gerçekten okuduğu sabit yol).

Antigravity veya "diğer araç" seçildiyse ilgili README prensip-düzeyinde ve kasıtlı olarak
kesin bir dosya adı vermiyor — kullanıcıya bu belirsizliği olduğu gibi aktar, kesinmiş gibi
bir dosya adı uydurma. README'deki "Kurulumdan önce doğrulanacaklar" listesini kullanıcıya
göster ve aracın güncel resmi dokümantasyonundan doğrulamasını iste.

### 8. Proje künyesi ve git durumunu hazırla

- Hedef proje henüz bir git reposu değilse (`$TARGET/.git` yok), kullanıcıya sorup
  onay alarak `git init` çalıştır (tersine çevrilebilir, düşük riskli ama yine de sorulmadan
  yapılmaz).
- `tier0/RULES.md` içindeki köşeli parantez placeholder sayısını say ve kullanıcıya bildir
  — bunların `design-flow-agent` tarafından Faz 0-1'de dolduracağını hatırlat, burada
  doldurma. **Placeholder formatı sabit "..." değil**, keyfi içerikli köşeli parantezlerdir
  (ör. `` `[PROJE_ADI]` ``, `` `[Evet | Hayır]` ``) — dosyanın kendi §1 açıklamasında
  ("... köşeli parantez placeholder'larını doldur") da böyle tarif edilir. Sayım için
  `grep -oE '\[[^]]+\]' tier0/RULES.md | wc -l` kullan, literal `\[\.\.\.\]` deseni **yanlış
  sonuç verir** (bir test çalıştırmasında 0 döndürdüğü, gerçek sayının 30+ olduğu görüldü).

### 9. Kapanış özeti

Kullanıcıya kısa bir özet ver:
- Hangi commit'ten (`git -C "$CACHE_DIR" log -1 --oneline`) kurulduğu.
- Hedef projeye getirilen klasör/dosya ağacı (`tier0/`, `tier1/`, `skills/design-flow-agent/`,
  seçilen araç(lar)ın adaptör dosyaları, boş `docs/`).
- Adım 6/7'de atlanan/eksik kalan bir şey varsa (ör. bir araç için henüz SKILL.md kopyası
  yok, Antigravity'nin dosya adı doğrulanmadı) açık bir liste olarak.
- Sıradaki adım: tasarım fazını başlatmak için `design-flow-agent`'ı tetikleyecek bir ifade
  kullanması yeterli ("tasarım akışını başlat", "yeni proje tasarımı", vb. — bkz. o skill'in
  kendi tetikleyici açıklaması). Bu skill kendisi tasarım fazını başlatmaz, sadece ona
  devretmeye hazır bir iskelet bırakır.

## Bilinen Sınır: Doğrulanmış vs Doğrulanmamış Alanlar

Bu skill `design-flow-agent`'ın kendisi kadar çok kez test edilmedi. Şu an **canlı
doğrulanmış** olan tek yol: hedef Claude Code, boş bir klasör, HTTPS clone (bkz.
`example-projects/saha-vardiya-devir-teslim/`'in `.design-flow/TEST-FINDINGS.md`'i).
Cursor/GitHub Copilot/Antigravity adaptör kurulum adımları henüz canlı test edilmedi —
Adım 7'nin "README ne diyorsa onu yap" kuralı bu belirsizliği zaten telafi eder, ama bir
kullanıcıya "bu yol test edildi" diye yanlış güven verilmemeli.
