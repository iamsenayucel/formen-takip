# Prosedür: İş Takip Aracı ↔ Doküman İlişkisi

> Tool-agnostik, metodoloji-agnostik temel kural. Proje bir issue tracker (Jira, Linear, vb.)
> kullanıyorsa bu prosedür uygulanır. Metodolojiye özel akış detayı (sprint cadence, board
> state vb.) burada değil, ayrı bir `<metodoloji>-workflow.md` dosyasındadır (bkz.
> `scrum-workflow.md`) — bu dosya yalnızca "hangi içerik nerede yaşar" sorusuna cevap verir.
> `tier0/RULES.md`'de bir Zorunlu madde değildir — proje bir issue tracker kullanıyorsa
> uygulanır, kullanmıyorsa devre dışı kalır.

## 0. Kapsam ve Uygulanma Derecesi

Bu prosedürün maddeleri tek bir zorunluluk derecesinde değildir — iki ayrı eksen var:

- **Madde 1-2 (içerik yerleşimi: kalıcı karar→git, task-özel materyal→tracker) her zaman
  geçerlidir**, proje MVP olsa da — bu bir yük değil, yükün *yokluğu*dur (git'e gereksiz
  binary/ephemeral içerik taşınmaması). Issue tracker kullanan hiçbir proje bundan muaf
  değildir; ekstra bir disiplin gerektirmez, tam tersi.
- **Madde 3-4 (referans + distilasyon ritüeli) ve `scrum-workflow.md`'nin tamamı, proje
  türüne göre değişir** (bkz. `tier0/RULES.md` §1 Proje Künyesi → "Geliştirme disiplini:
  MVP | Gerçek/üretim"):
  - **Gerçek/üretim projelerde** bu ritüel beklenir — bir Zorunlu mandate değil (RULES.md'ye
    girmez) ama proje kendi `docs/08` "Geliştirme & Operasyon İş Akışı"nda bu prosedürü
    benimsediğini kaydeder ve uygular.
  - **MVP/deneme projelerinde** ritüelin derinliği ekibin tercihidir — `tier0/RULES.md`
    §1'deki "MVP Disiplini Ölçeklenmesi" ile aynı mantık (derinlik ekseni) burada da
    geçerlidir: madde 3-4'ü hafifletmek meşrudur, tamamen atlamak da olabilir.
- **Bir issue tracker/Scrum board açıp açmama kararının kendisi** her zaman ekibin
  tercihidir, hiçbir proje türünde zorunlu kılınmaz — bu prosedür yalnızca "tracker zaten
  kullanılıyorsa" devreye girer, tracker seçimini dayatmaz.

## 1. Kalıcı karar/sözleşme → git

Bir ADR, bir API/ekran/şema/süreç kararı, bir güvenlik notu — kısacası `tier2/README.md`'nin
12 maddesinden herhangi birine giren her şey **git'te** yaşar (`docs/0X` veya
`tier0/adr/000N-...`). Bu, `tier0/RULES.md`'nin "içerik bir kez yazılır" ilkesinin issue
tracker'a genişletilmiş halidir: aynı kararın bir de tracker'da (ticket açıklamasında,
Confluence'ta) ayrı bir kopyası oluşmaz.

## 2. Task-özel çalışma materyali → tracker'ın kendi mekanizması

Screenshot, mockup, tasarım sistemi keşif notu, iterasyon geçmişi, toplantı notu gibi büyük
ölçüde binary/ephemeral/tek-task-ömürlü materyal git'e **girmez**. Doğal olarak üretildiği
yerde kalır:
- Küçük/az sayıda dosya → ticket'ın kendi attachment mekanizması.
- Uzun/resim-ağırlıklı doküman → Confluence (aynı iş takip ekosistemi içindeyse).
- Tasarım sisteminin kendisi → kaynak araç (Figma vb.), sadece link referans verilir.

**Neden:** Git, binary/ephemeral içerikte diff/merge avantajı sağlamaz — sadece repo'yu
şişirir ve çoğu materyal task kapanınca zaten değersizleşir.

## 3. Ticket → git dokümanı referans kuralı

Her ticket, dokunduğu git dokümanına/bölümüne **açıkça link verir** (ticket açıklaması veya
ilk yorum üzerinden, örn. `docs/04-api-sozlesme-katalogu.md#silme-talebi-endpoint`). Bu, "bu
ticket hangi tasarım kararını uyguluyor" sorusunun tracker'dan git'e tek adımda
cevaplanmasını sağlar — tersi yönde (git'ten tracker'a) referans zorunlu değildir; git
dokümanı, tracker'ın varlığından bağımsız okunabilir kalmalıdır.

## 4. Kapanışta distilasyon kuralı

Ticket kapanmadan önce, task-özel materyalden çıkan **kalıcı sonuç** (onaylanmış final
layout, kesinleşmiş bir parametre, yeni bir mimari karar) ilgili `docs/0X`'e veya yeni bir
ADR'ye eklenir — `tier0/procedures/add-new-capability.md` §5'in aynısı, **aynı commit/PR'da**.
Ham materyalin kendisi (tüm screenshot'lar, tüm iterasyonlar) git'e taşınmaz; yalnızca sonuç
taşınır.

## 5. Hızlı karar tablosu

| İçerik | Nerede yaşar |
|---|---|
| ADR, API/ekran/şema/süreç kararı | git (`tier0/adr/`, `docs/0X`) |
| Ticket'ın kendi sözleşme/kapsam açıklaması | Tracker (git dokümanına link verir) |
| Screenshot, mockup, keşif notu | Tracker attachment / Confluence |
| Tasarım sistemi kaynağı | Figma (veya eşdeğeri), link referans |
| Kapanışta çıkan kalıcı karar | git'e distile edilir (madde 4) |
