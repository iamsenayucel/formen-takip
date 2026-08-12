# Stack Playbook Yazım Kuralı

Bu dizin **Tier 1**'dir: framework/dile özel kalıplar burada yaşar (`tier0/RULES.md`
Tier 0'dır, stack'ten bağımsızdır). Bir playbook, yeni bir proje aynı stack'i (örn.
NestJS+Prisma, veya Next.js+React) kullandığında kopyalanıp doldurulur.

## Neden bu dosya var

Kaynak olarak incelenen bir projede, backend mimarisini anlatan hem 2000 satırlık bir
"spec" dokümanı hem de aynı bilgiyi tekrar eden ~2000 satırlık ayrı "rule" dosyaları vardı.
İkisi de kod örnekleriyle doluydu — neredeyse gerçek implementasyonun bir kopyasıydı. Sonuç:
gerçek kod değiştiğinde iki dokümandan biri (genelde ikisi de) güncel kalmadı, ve AI asistan
context penceresine her session'da binlerce satır düşük-yoğunluklu metin taşındı.

**Bu şablon setinin kural olarak koyduğu denge:** playbook'lar **karar ve kısıt** anlatır,
**implementasyon** anlatmaz. İmplementasyon zaten kod tabanında var — playbook ona işaret eder.

## Her madde için zorunlu 4 alan

```
### <Pattern adı>
**Ne:** <1 cümlede kalıbın adı/kapsamı>
**Neden:** <1-2 cümle — bu kural olmasa model neden yanlış karar verir?>
**Kural:** <somut, ölçülebilir, "kullan X'i, asla Y'nin altına inme" gibi net bir sınır>
**Referans:** <gerçek koddaki canonical örnek dosyanın yolu — kod bloğu değil, path>
```

`Kural` alanı **belirsiz olmamalı.** "Güvenli şekilde hash'le" değil, "bcrypt, cost factor
en az 12" yazılır. Belirsizlik, ajanın kendi yorumunu icat etmesine (halüsinasyona) davetiye
çıkarır — bkz. `tier0/RULES.md` Bölüm 6.

## Kod bloğu ne zaman eklenir (ve ne zaman eklenmez)

**Varsayılan: eklenmez.** `Referans` alanındaki dosya yolu yeterlidir; agent gerektiğinde
o dosyayı okur ve güncel/gerçek implementasyonu görür (dokümandaki donmuş bir kopyayı değil).

Kod bloğu **sadece** şu iki durumda, ve **en fazla 5-8 satır** olacak şekilde eklenir:

1. **Kalıp gerçekten hataya açık ve "doğrusu / yanlışı" yan yana göstermek gerekiyor**
   (örn. bir SQL parametrelemesinin doğru ve yanlış hali).
2. **Tam sözdiziminin ezbere doğru yazılması gereken, kısa ve sabit bir şey** (örn. bir
   güvenlik header'ının tam biçimi, bir CLI komutunun tam bayrakları).

**Asla eklenmez:** tam bir servis/component/controller implementasyonu, çoklu-fonksiyon
örnek bloğu, "işte örnek bir modül" tarzı iskelet kod. Bunlar hem context'i şişirir hem de
agent'ı "bu örneği birebir kopyala" refleksine iter — gerçek, güncel dosyaya bakmak yerine.

## Playbook başına hedef uzunluk

**80–150 satır.** Bunun üzerine çıkıyorsa, muhtemelen implementasyon detayına kaymışsınızdır
— o detay ya kod tabanındaki gerçek dosyaya ya da (gerekiyorsa) bir ADR'ye (`tier0/adr/`)
taşınmalı, playbook'a değil.

## İki tür playbook: Stack vs Cross-Cutting

**Stack playbook'u** (`backend-*`, `frontend-*`, `infra-*`, `testing-*`): bir framework/dile
özeldir, o stack'i kullanan proje kopyalar/doldurur.

**Cross-cutting playbook** (`playbook-authentication.md`, `playbook-observability.md`,
`playbook-caching.md`, `playbook-messaging.md`): **stack'ten bağımsız, konuya özeldir** — NestJS de, Spring Boot
da, FastAPI de aynı prensipleri kullanır, değişen yalnızca dil-özel SDK/kütüphane (bu detay
ilgili stack playbook'unda kısa bir referans olarak kalır, cross-cutting dosyaya kopyalanmaz).
Bir stack playbook'u caching/messaging/observability'ye ihtiyaç duyarsa, kendi içinde
tekrar yazmaz — ilgili cross-cutting dosyaya işaret eder
(`tier1/playbooks/playbook-backend-python-fastapi.md`'deki "⚠️ Bu Playbook'un Kapsamı
Dışı" bölümleri örnektir).

Cross-cutting playbook'lar da **zorunlu/ihtiyaca-göre** ayrımı taşır — bu,
`tier1/APPROVED-STACKS.md`'deki `Statü` sütununda görünür (`Zorunlu` vs `Onaylı`).
Gözlemlenebilirlik `Zorunlu`'dur (`tier0/RULES.md` §11), caching/messaging değildir.

## Bu dizindeki dosyalar

Üç alt klasör, üç farklı rol:

- **`catalog/`** — CoE onaylı stack kataloğu, kategoriye bölünmüş (`backend.md`,
  `frontend.md`, `database.md`, `infra.md`, `ml-serving.md`, `cross-cutting.md`). Ayrıca
  bu dizinin hemen üstünde, `tier1/APPROVED-STACKS.md` — kataloğun **indeksi**: bağlayıcı
  kural, statü tanımları, "yeni stack ekleme süreci" orada; bir playbook doldurmadan önce
  önce `APPROVED-STACKS.md`'yi, sonra ilgili `catalog/*.md`'yi okuyun.
- **`templates/`** — boş, `[FRAMEWORK ADI]` gibi doldurulacak alanlar taşıyan şablonlar
  (`TEMPLATE-backend.md`, `TEMPLATE-frontend.md`, `TEMPLATE-infra.md`,
  `TEMPLATE-testing.md`). Yeni bir stack eklerken buradan kopyalanır.
- **`playbooks/`** — doldurulmuş, kullanıma hazır playbook'lar; hem stack playbook'ları
  hem cross-cutting olanlar aynı klasörde, dosya adı hangisi olduğunu belirtir:
  - `playbook-backend-nestjs.md` — **doldurulmuş** (NestJS+Fastify+Prisma), katalogdaki
    `Referans` statüsünü karşılayan asıl playbook
  - `playbook-backend-java-spring-boot.md` — **doldurulmuş** (Spring Boot 3.x/Java 21)
  - `playbook-backend-python-fastapi.md` — **doldurulmuş** (FastAPI) — ML serving/MQTT/
    görev kuyruğu bilerek kapsam dışı bırakılmış, ayrı bileşenler olarak işaretli
  - `playbook-frontend-nextjs.md` — **doldurulmuş** (Next.js App Router)
  - `playbook-infra-terraform-aws.md` — **doldurulmuş** (Terraform + AWS, departman-bazlı
    hesap modeli, ECS Fargate varsayılan compute), veritabanı hosting modelini de içerir
  - `playbook-infra-terraform-aws-eks.md` — **doldurulmuş** (EKS-özel: cluster/IRSA/Helm/
    ingress/autoscaling) — yalnız gerçek bir Kubernetes ihtiyacı varsa kopyalanır, kardeş
    compute seçeneği (ECS Fargate) gibi ele alınır (bkz. aşağıdaki Budama)
  - `playbook-testing-nestjs.md` — **doldurulmuş** (Vitest unit/integration +
    Testcontainers + Supertest) — backend unit/integration; e2e kapsamı
    `playbook-testing-nextjs.md`'ye devredilir (fullstack projede giriş noktası frontend)
  - `playbook-testing-nextjs.md` — **doldurulmuş** (Vitest + React Testing Library + MSW +
    Playwright) — frontend unit/integration ve proje genelinin e2e stratejisi
  - `playbook-testing-python-fastapi.md` — **doldurulmuş** (pytest + pytest-asyncio +
    Testcontainers + httpx) — backend unit/integration; e2e kapsamı yalnız frontend'i
    olmayan (backend-only/API-only) projelerde bu dosyada kalır, fullstack'te
    `playbook-testing-nextjs.md`'ye devredilir (aynı ayrım `playbook-testing-nestjs.md`
    ile)
  - `playbook-authentication.md` — **cross-cutting, Zorunlu** (Red Hat SSO/OIDC) — yalnız
    authentication; authorization ilgili backend playbook'unda kalır
  - `playbook-observability.md` — **cross-cutting, Zorunlu** (Prometheus+Loki+Grafana+Opsgenie)
  - `playbook-api-design.md` — **cross-cutting, Zorunlu** (response zarfı, hata taksonomisi,
    pagination, rate-limit şekli) — endpoint-özel içerik değil, `tier2/README.md` madde 4'te
  - `playbook-cicd-security.md` — **cross-cutting, Zorunlu** (statik analiz/tip güvenliği,
    SCA+lisans taraması, SAST — pipeline-seviyesi güvenlik; runtime güvenlik Bölüm 4'te) —
    somut ürün seçimi henüz `TBD`, `tier0/RULES.md` §15
  - `playbook-service-integration.md` — **cross-cutting, koşullu-Zorunlu** (yalnız proje
    başka bir kurumsal sisteme entegre olacaksa uygulanır — bkz. `tier0/RULES.md` §13; ama
    uygulandığında Ocean tek seçenektir, caching/messaging gibi seçilebilir alternatif yok)
  - `playbook-caching.md` — **cross-cutting, ihtiyaca göre** (Redis)
  - `playbook-messaging.md` — **cross-cutting, ihtiyaca göre** (AWS SQS)

Kullanmadığınız bir katman/cross-cutting dosya varsa (örn. mobil yoksa `frontend`, caching
ihtiyacı yoksa `playbook-caching.md`) o dosyayı `playbooks/`'tan silin — hepsini doldurmak/
tutmak zorunlu değildir. **İstisna:** `playbook-authentication.md`, `playbook-observability.md`,
`playbook-api-design.md` ve `playbook-cicd-security.md` her projede evrensel olarak
geçerlidir (her proje kimlik doğrular, gözlemlenir, bir API sözleşmesi sunar, bir CI
pipeline'ından geçer), `Zorunlu` statüde, silinmez.
`playbook-service-integration.md` **koşullu** — `playbook-caching.md`/`playbook-messaging.md`
gibi önce bir ihtiyaç sorusuyla ("bu proje başka bir kurumsal sisteme entegre olacak mı?")
belirlenir; ihtiyaç yoksa silinir, "gerekli değil" diye işaretlenir. İhtiyaç varsa ise
caching/messaging'den farklı olarak **seçilebilir alternatifi yoktur** — Ocean tek
seçenektir, doldurulur.

**Budama (pruning) — kolayca atlanan bir adım:** Bu repo (CoE'nin kaynak şablonu) bilerek
geniştir — birden fazla onaylı stack'i aynı anda barındırır. Ama **bir projenin kendi
kopyası bu genelin bir alt kümesi olmalı**, tamamı değil. Faz 2'de bir stack seçildikten
sonra, **o katmandaki kardeş stack playbook'ları** (örn. NestJS seçildiyse
`playbook-backend-java-spring-boot.md` ve `playbook-backend-python-fastapi.md`) silinir —
yalnızca "kullanılmayan katman" değil, "kullanılmayan kardeş stack" de silinir. Aynı kural
infra/compute seçimi için de geçerlidir: ECS Fargate seçildiyse
`playbook-infra-terraform-aws-eks.md` silinir (ve tam tersi) — ikisi aynı kategorinin
kardeş seçenekleridir, ikisini birden tutmak yalnız gerçekten karma bir compute modelinde
(bkz. `tier1/catalog/infra.md`) meşrudur. İstisna: gerçekten poliglot bir sistemse (örn.
NestJS ana API + ayrı bir Python ML-serving servisi, bkz.
`tier1/playbooks/playbook-backend-python-fastapi.md`'deki ML serving notu) birden fazla
stack playbook'u meşru şekilde kalabilir — kural "tek dosya" değil, **"gerçekten kullanılan
stack'lerin kümesi"**dir. `design-flow-agent`, Faz 4 sonunda bu budamayı hatırlatır (bkz.
`skills/design-flow-agent/SPEC.md` §4 Faz 4).

Dosya adlandırma kuralı: doldurulmuş bir **stack** playbook'u, `.TEMPLATE` uzantısını
kaldırıp **stack adını dosya adına ekler** (`playbook-backend-<stack>.md` gibi) — bu, aynı
katmanda (örn. backend) birden fazla onaylı stack olduğunda dosyaların çakışmamasını sağlar.
Cross-cutting playbook'ların stack adı taşımaz (`playbook-caching.md`), çünkü zaten
stack-bağımsızdır.
