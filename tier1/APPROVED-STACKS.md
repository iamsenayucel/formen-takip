# CoE Onaylı Stack Kataloğu

> **Kural (bağlayıcı):** Tasarım fazında (`tier0/procedures/new-project-design-flow.md`
> Faz 2, `design-flow-agent` skill'i) bir stack/altyapı önerisi yapılırken **yalnızca bu
> katalogdaki seçenekler** sunulur. Katalog dışı bir stack asla seçenek olarak önerilmez —
> ne agent tarafından icat edilerek, ne de "güncel/popüler" olduğu için.

## Neden bu kural var

Kataloğun dışına çıkan bir öneri, deneyimsiz bir "vibe coder"ın onaylanmamış bir stack'i
seçip haftalarca üzerine geliştirme yapmasına, sonra `mimari-gate` (veya eşdeğeri
pre-implementation gate) incelemesinde bunun reddedilmesine yol açabilir — bu, tamamen
önlenebilir bir efor kaybıdır. Kural basit: **önce onay, sonra öneri** — tersi değil.

## Kategoriler (`tier1/catalog/`)

Bu dosya bir **indekstir** — satır tabloları büyüdükçe (bu dosya kategori bazlı bölünmeden
önce tek başına ~130 satıra ulaşmıştı) kategoriye göre ayrı dosyalara taşındı. Her kategori
dosyası kendi "birden fazla onaylı seçenek varsa" örneklerini ve "değerlendirilip
eklenmeyenler" notlarını da taşır.

| Dosya | Kapsam |
|---|---|
| `tier1/catalog/backend.md` | Backend framework, ORM, migration, auth, build/paket aracı, async görev kuyruğu, MQTT/IoT |
| `tier1/catalog/frontend.md` | Frontend framework |
| `tier1/catalog/database.md` | Veritabanı ürünü (hosting modeli değil — o `infra.md`'de) |
| `tier1/catalog/infra.md` | Infra / IaC |
| `tier1/catalog/ml-serving.md` | ML model serving (yalnız gerçek model inference çalıştıran projelere uygulanır) |
| `tier1/catalog/cross-cutting.md` | Caching, message broker, gözlemlenebilirlik platformu, API tasarım prensipleri, kurumsal sistem entegrasyonu |

**Yeni bir kategori dosyası ne zaman açılır:** bir kategori dosyası ~150 satırı geçmeye
başlarsa, o dosya kendi içinde alt-kategoriye bölünür (örn. `backend.md` çok büyürse
`backend-auth.md` gibi) — aynı "içerik bir kez, gerektiğinde böl" ilkesi kategori
dosyalarının kendisi için de geçerlidir.

## Statü tanımları

- **Zorunlu** — `Referans`/`Onaylı`'dan farklı: "en iyi seçenek" değil, **tek geçerli
  seçenek**, alternatifi yok. `design-flow-agent` bunu bir "seçenek" olarak sunmaz,
  doğrudan zorunlu kılar (Faz 2'de soru sormaz, sadece uygulanacağını bildirir).
- **Referans** — Kanıtlanmış, tam playbook'u var, ilk tercih olarak önerilir.
- **Onaylı** — Kullanılabilir, playbook henüz tam doldurulmamış olabilir; önerilebilir ama
  playbook doldurma işi projeye düşer.
- **Değerlendirmede** — Henüz onaylanmadı. `design-flow-agent` bunu **seçenek olarak
  sunamaz**; yalnızca "bu katalogda değerlendirme aşamasında" diye bilgi verebilir.

## Aynı kategoride birden fazla onaylı seçenek varsa (genel ilke)

Kural katalog dışına çıkmamaktır, tek seçeneğe sıkışmak değildir. Bir kategoride birden
fazla **Referans/Onaylı** seçenek varsa, agent projenin doğasına (ölçek, ekip tecrübesi,
domain) en uygun ve mimari açıdan en güçlü 1-3 alternatifi, yine yalnızca ilgili kategori
dosyasından, önerebilir — bkz. `skills/design-flow-agent/SPEC.md` §4 Faz 2.
Somut, çalışılmış örnekler için ilgili kategori dosyasına bakın (örn. Spring Boot vs
Quarkus → `tier1/catalog/backend.md`; BentoML vs Ray Serve → `tier1/catalog/ml-serving.md`).

## Yeni stack ekleme süreci

1. Kurumda ayrıca kullanılan/kullanılması istenen bir stack varsa bu tablolara **doğrudan
   eklenmez** — önce bir stack analizi yapılır (mevcut kullanım, ekip tecrübesi, bakım
   yükü, güvenlik pattern'lerinin o stack'e taşınabilirliği).
2. Analiz sonucu onaylanırsa: `tier0/adr/0000-template.md` kopyalanıp **bu repoda**
   `tier0/adr/000N-...md` olarak (proje-seviyesi değil, katalog-seviyesi karar olduğu için —
   bkz. `tier0/adr/0001-java-spring-boot-approved-stack.md` örneği) kaydedilir, ilgili
   `tier1/catalog/*.md` dosyasına satır eklenir (`Statü: Onaylı`), ve mümkünse ilgili
   `tier1/*-playbook*.md` o stack için ayrıca doldurulur (`tier1/README.md`'deki yoğunluk
   kuralına uyarak).
3. Katalog sahibi bu süreci yönetir ve ilgili kategori dosyasını günceller.

## Versiyon Stratejisi — Major Sürüm Kataloğu, Minor Projede

**Kural:** Katalog ve playbook'lar yalnızca **major sürüm + destek hattı** (LTS/stable) taşır
(örn. "NestJS 11.x", "Node.js 24.x LTS", "Next.js 16.x App Router") — her `catalog/*.md`
satırının **Seçenek** sütununda ve ilgili playbook'un **Stack:** satırında görünür. Minor/patch
sürüm asla katalogda sabitlenmez; proje kendi `package.json`/lockfile'ında (pnpm-lock.yaml,
poetry.lock vb.) karar verir ve bu dosyayı commit eder. Bu, iki farklı endişeyi ayırır: major
sürüm **uyumluluk/pattern** garantisi verir (playbook'un anlattığı kalıplar o major'da
geçerlidir), minor/patch **güvenlik yaması** meselesidir ve projeden projeye farklılaşması
zararsızdır.

**Neden:** Her proje kendi başına farklı bir major sürüm seçerse (biri NestJS 10, biri 11),
playbook'taki "Kural" alanları hangi projede geçerli olduğu belirsizleşir — bir pattern bir
major'da doğruyken bir sonrakinde deprecate olmuş olabilir. Aynı anda, minor/patch'i de
kataloğa sabitlemek gereksiz sürtünme yaratır (her patch güncellemesi bir katalog PR'ı
gerektirir) ve katalog güncel tutulamayacağı için hızla yalan söylemeye başlar.

**Bozulmayı önleyen mekanizma:** Katalog sahibi, her yeni greenfield projede (veya bulunmadıysa
en az yılda bir) her satırın major sürümünü gerçek kaynağa karşı (resmi release sayfası/
endoflife.date) doğrular. Bir major'ın **desteği sona ermek üzereyse** veya **playbook'un
anlattığı pattern'leri değiştiren bir sonraki major** çıktıysa (örn. bir framework'ün ana
API şeklini değiştiren bir sürüm), bu bir **stack-analizi + değerlendirme** konusudur — yeni
bir kategori eklemekle aynı ağırlıkta değildir ama sessizce "satırı değiştir" ile de
geçilmez; playbook'un içeriği o yeni major'a karşı gerçekten geçerli mi diye kontrol edilir,
gerekiyorsa playbook güncellenir. Yalnızca destekleyici/pattern-değiştirmeyen bir major artışı
(örn. mevcut playbook içeriği hâlâ geçerliyse) doğrudan satır güncellemesiyle yapılabilir.

**Şu an tek bir istisna bilinçli olarak bırakıldı:** Spring Boot kataloğu hâlâ "3.x (Java 21)"
diyor — bu playbook'un (`playbook-backend-java-spring-boot.md`) yazıldığı andaki gerçek
karardı (`tier0/adr/0001-...`, `0002-...`). Spring Boot 4.x zaten çıkmış olsa da, playbook
içeriği 4.x'e karşı doğrulanmadan satır güncellenmedi — bu, yukarıdaki "stack-analizi
gerektiren major artışı" durumunun canlı bir örneği, ileride ele alınmalı.

**Genel istisna — AWS-yönetimli compute:** ECS Fargate ve EKS bu stratejinin dışındadır —
major sürüm dahi pinlenmez (bkz. `tier1/catalog/infra.md` "Versiyon Notu", `tier0/adr/
0007-...`). Bu iki servis AWS tarafından işletilir/yükseltilir, güncel desteklenen
varsayılan sürümle ayağa kalkar; "hangi versiyon" sorusu bu servisler için proje kararı
değildir. Bu, yukarıdaki genel kuralın istisnası değil, kuralın **kapsamı dışıdır** — kural
"projenin kendi bağımlılıkları" için var, AWS'nin kendi işlettiği bir servis için değil.
