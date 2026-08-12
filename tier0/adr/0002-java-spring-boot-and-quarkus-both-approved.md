# ADR-0002: Java 21 backend'inde hem Spring Boot hem Quarkus onaylı — final seçim proje bazında

**Durum:** Kabul edildi
**Tarih:** 2026-07-14
**Karar verenler:** CoE (katalog sahibi)
**Yerini aldığı karar:** ADR-0001 (Spring Boot'u tek onaylı Java seçeneği yapan karar)

> Bu bir katalog-seviyesi ADR'dir — bkz. `tier0/adr/0001-...`'deki aynı not.

## Bağlam

ADR-0001, kataloğa tek bir Java seçeneği (Spring Boot) eklemişti ve Quarkus/Micronaut'u
"ileride ayrı bir ADR ile değerlendirilebilir" diye ertelemişti. Katalog sahibinden gelen
geri bildirim, bu ertelemeyi geçersiz kılan somut bilgi getirdi:

- Kurumun backend yükleri genel olarak **Kubernetes'te hızlı açılış** için optimize
  ediliyor — Quarkus'un temel avantajı (düşük ayak izi, hızlı başlangıç, GraalVM native
  image) bu önceliğe doğrudan hizmet ediyor.
- **Red Hat SSO'nun yeni sürümleri Java 21 + Quarkus'a geçti** — kurum bunu zaten
  operasyonel olarak biliyor/deneyimliyor; ayrıca Quarkus'un `quarkus-oidc` uzantısı
  Red Hat SSO/Keycloak ile native entegrasyon sunuyor.
- Kurumda **Spring ile yazılmış, üretimde kanıtlanmış bir e-ticaret uygulaması** var —
  yani Spring Boot da gerçek, mevcut bir üretim izine sahip, sadece Quarkus'tan daha uzun
  süredir.

Bu durumda tek bir "kazanan" seçmek, kataloğun kendisini gereksiz yere daraltır: iki
seçeneğin farklı proje profillerinde farklı avantajları var.

## Değerlendirilen Seçenekler

1. **Yalnızca Spring Boot onaylı kalsın** (ADR-0001'in orijinal kararı) — reddedildi,
   yukarıdaki bağlam bunu artık savunulamaz kılıyor.
2. **Quarkus'u Spring Boot'un yerine geçir** — reddedildi, Spring'in kendi kanıtlanmış
   izi (e-ticaret uygulaması) kaybedilmiş olur.
3. **İkisi de `Onaylı` statüsünde kalsın, final seçim proje bazında yapılsın** — kabul
   edildi.

## Karar

Seçenek 3. `tier1/catalog/backend.md`'ye Quarkus, Spring Boot ile aynı statüde (`Onaylı`)
eklenir. Aralarındaki seçim **kataloğ seviyesinde önceden yapılmaz** — her projenin kendi
`design-flow-agent` Faz 2 oturumunda, o projenin somut ihtiyaçlarına (deployment hedefi
Kubernetes mi, hızlı-açılış/yoğun-konteyner önceliği var mı, ekibin Spring mi Quarkus mu
tecrübesi daha güçlü, Red Hat SSO kullanılacak mı) bakılarak, canlı olarak verilir —
`tier1/catalog/backend.md` "Aynı kategoride birden fazla onaylı seçenek varsa" bölümü ve
`skills/design-flow-agent/SPEC.md` §4 Faz 2 zaten bu mekanizmayı destekliyor.

## Sonuçlar

**Artılar:**
- Katalog, kurumun gerçek, birbirinden farklı iki üretim profilini (Spring/e-ticaret,
  Quarkus/Red Hat SSO+Kubernetes) tek bir zorunlu seçime sıkıştırmıyor.
- `design-flow-agent`'ın zaten sahip olduğu "bağlama göre öner" mekanizması yeniden
  kullanılıyor, yeni bir karar mantığı icat edilmiyor.

**Eksiler / kabul edilen riskler:**
- Kataloğun tek-seçenek basitliği azaldı — Faz 2'de bu kategori için bağlam toplama
  (deployment hedefi, ekip tecrübesi) artık zorunlu bir adım, atlanabilir değil.
- Quarkus için henüz doldurulmuş bir `tier1/playbooks/playbook-backend-*.md` yok (Spring Boot'un
  aksine) — `Statü: Onaylı` bunu zaten öngörüyor ("playbook henüz tam doldurulmamış
  olabilir"), ama ilk Quarkus projesi bunu dolduracak/doldurtacak.

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** ADR-0001'in yerini alır. Auth modeli
satırındaki Quarkus seçeneği, kurumun Red Hat SSO kararıyla (varsa ayrı bir ADR) tutarlı
olmalı.
