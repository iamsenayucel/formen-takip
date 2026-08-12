# ADR-0001: Java 21 backend projeleri için Spring Boot 3.x onaylı stack olarak kataloğa eklendi

**Durum:** Yerini aldı: ADR-0002
**Tarih:** 2026-07-14
**Karar verenler:** CoE (katalog sahibi)

> Bu, bir proje-seviyesi ADR değil — `tier1/APPROVED-STACKS.md`'ye yeni bir stack eklerken
> CoE'nin kendi kararını kaydettiği bir **katalog-seviyesi ADR**'dir. Bu yüzden projelerin
> kendi `docs/adr/`'ı yerine, bu repoda `tier0/adr/` altında birikir (bkz. o dizindeki
> "Yeni stack ekleme süreci" notu).

## Bağlam

Kurumda Java tecrübesi olan ekipler için, `tier1/APPROVED-STACKS.md` kataloğunda bir Java
backend seçeneği yoktu — bu, Java ekiplerinin ya kataloğ dışı bir stack seçip
`mimari-gate`'te tıkanma riskiyle karşılaşmasına ya da CoE sürecini tamamen atlamasına yol
açardı. Java 21 (LTS) ile gelen virtual thread'ler, modern bir Java backend'i (reaktif
karmaşıklığa girmeden) yüksek eşzamanlılık açısından NestJS/Node stack'ine kıyasla rekabetçi
kılıyor — bu nedenle Java'yı "eski/kaçınılması gereken" değil, birinci sınıf bir seçenek
olarak değerlendirdik.

## Değerlendirilen Seçenekler

1. **Spring Boot 3.x (Java 21)** — En olgun ekosistem, en geniş işe alım havuzu; Spring
   Security/Spring Data ile CoE'nin güvenlik baseline'ını (yetkilendirme, audit, rate-limit)
   karşılayacak yerleşik/olgun kütüphaneler mevcut.
2. **Quarkus (Java 21)** — Daha hızlı başlangıç süresi, düşük bellek ayak izi, GraalVM
   native image desteği; cloud-native/serverless ağırlıklı yükler için güçlü ama ekosistem
   ve dokümantasyon hacmi Spring'e göre daha dar.
3. **Micronaut (Java 21)** — Quarkus'a benzer profil (compile-time DI, düşük bellek);
   topluluk/işe alım havuzu ikisinden de daha dar.

## Karar

Seçenek 1 (Spring Boot 3.x) seçildi. Gerekçe: CoE'nin önceliği "en yeni/en performanslı"
değil, **en geniş ekipçe sürdürülebilir ve CoE güvenlik baseline'ını en az sürtünmeyle
karşılayan** stack — Spring Security'nin method-security + OIDC/SSO desteği,
`tier0/RULES.md` §4'teki yetkilendirme ve auth gereksinimlerini NestJS referans stack'iyle
kavramsal olarak birebir eşleştiriyor. Quarkus/Micronaut, cloud-native/serverless ağırlıklı
bir ihtiyaç somutlaştığında ayrı bir ADR ile yeniden değerlendirilebilir.

## Sonuçlar

**Artılar:**
- Java ekipleri artık kataloğ-dışına çıkmadan, governance'a uygun bir seçenek kullanabilir.
- Spring ekosistemi CoE'nin güvenlik baseline'ını (yetkilendirme/audit/rate-limit/PII)
  karşılayacak olgun, yaygın bilinen kütüphaneler sunuyor — sıfırdan icat gerekmez.
- Testcontainers (entegrasyon testi) bu ekosistemde native destekleniyor.

**Eksiler / kabul edilen riskler:**
- Gradle mi Maven mi kullanılacağı bu ADR'de netleştirilmedi — proje bazında Faz 2'de
  ekibin tecrübesine göre karara bağlanmalı, kataloğa "her ikisi de kabul" olarak eklendi.
- Spring Boot, Quarkus/Micronaut'a göre daha yüksek bellek/başlangıç süresi taşır — eğer
  ileride serverless/yüksek-yoğunluklu-konteyner bir ihtiyaç çıkarsa ayrıca değerlendirilir.

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** Mevcut Veritabanı (PostgreSQL) ve
Infra/IaC (Terraform + AWS, ECS Fargate) girdileriyle değişmeden uyumludur — bu ADR
yalnızca backend framework/ORM/migration/auth katmanlarını ekliyor.
