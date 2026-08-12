# ADR-0004: Merkezi gözlemlenebilirlik platformu zorunlu; caching/messaging/veritabanı katalog genişletmesi

**Durum:** Kabul edildi
**Tarih:** 2026-07-14
**Karar verenler:** CoE (katalog sahibi)

> Bu bir katalog-seviyesi ADR'dir — bkz. `tier0/adr/0001-...`'deki aynı not. Tek bir
> oturumda birlikte istenen dört kararı (gözlemlenebilirlik, caching, messaging, veritabanı)
> tek ADR'de topluyor.

## Bağlam

Şu ana kadarki playbook'lar stack-eksenliydi (backend-nestjs, backend-java-*, backend-
python-*). Ama gözlemlenebilirlik, caching ve messaging **stack'ten bağımsız, katman-
eksenli** kavramlar — aynı prensipler NestJS'te de Spring Boot'ta da FastAPI'de de geçerli,
değişen yalnızca dil-özel SDK/kütüphane. Bunları her stack playbook'una tekrar yazmak,
`tier1/README.md`'nin yasakladığı içerik tekrarını üretirdi.

Ayrıca katalog sahibi, kurumun **merkezi, paylaşılan bir gözlemlenebilirlik platformu**
(Prometheus+Loki+Grafana+Opsgenie) inşa ettiğini ve bunun kullanımının **zorunlu** olacağını
belirtti — bu, `tier0/RULES.md` §4 (Güvenlik Baseline) ile aynı bağlayıcılık seviyesinde.

## Karar

**Yeni bir "Cross-Cutting Playbook" kategorisi** `tier1/` altına eklendi — stack playbook'
larından ayrı, tüm stack'lere uygulanan, konuya göre (stack'e göre değil) organize
dosyalar:

1. **Gözlemlenebilirlik — zorunlu.** `tier0/RULES.md`'ye yeni bir §11 eklendi (Bölüm 4 ile
   aynı bağlayıcılık seviyesinde); detay `tier1/playbooks/playbook-observability.md`'de. Platform:
   Prometheus (metrik) + Loki (log) + Grafana (görselleştirme) + Opsgenie (alarm,
   gerekirse), enstrümantasyon OpenTelemetry ile. Projeler kendi gözlemlenebilirlik
   altyapısını kurmaz, merkezi platformu kullanır.
2. **Caching — ihtiyaca göre.** `tier1/playbooks/playbook-caching.md`, Redis onaylı teknoloji olarak
   (zaten rate-limit örneklerinde varsayılan olarak kullanılıyordu, burada resmileşti).
3. **Messaging/kuyruklama — ihtiyaca göre.** `tier1/playbooks/playbook-messaging.md`, AWS SQS onaylı
   broker olarak (ADR-0003'te Python bağlamında kısmen ele alınmıştı, burada stack-bağımsız
   prensiplere — idempotency, DLQ, retry, mesaj şeması — genişletildi).
4. **Veritabanı — kataloğ genişletmesi.** PostgreSQL'e ek olarak **MongoDB** `Onaylı`
   statüsünde eklendi (doküman/esnek şema ihtiyacı olan use case'ler için). Veritabanı
   **hosting modeli** (AWS RDS/Aurora — mevcut, devam; self-deployed — duruma göre) yazılım
   katmanını ilgilendirmediği için `tier1/templates/TEMPLATE-infra.md`'ye ayrı bir bölüm
   olarak eklendi, backend playbook'larına değil.

Kataloğa yeni statü değeri eklendi: **`Zorunlu`** — `Referans`/`Onaylı`'dan farklı olarak,
"en iyi seçenek" değil "tek geçerli seçenek, alternatifi yok" anlamına gelir. Şu an yalnız
gözlemlenebilirlik platformu bu statüde.

## Sonuçlar

**Artılar:**
- Gözlemlenebilirlik/caching/messaging prensipleri bir kez yazıldı, her stack playbook'una
  kopyalanmadı — `tier1/README.md`'nin "içerik bir kez yazılır" ilkesi korundu.
- Zorunlu vs ihtiyaca-göre ayrımı statü seviyesinde açık — bir proje caching/messaging
  dosyalarını silebilir ama gözlemlenebilirliği silemez (RULES.md §11 zorunlu kılıyor).
- Veritabanı hosting kararının (RDS vs self-deployed) yazılım katmanından ayrılması, mevcut
  `tier1/templates/TEMPLATE-infra.md`'nin zaten öngördüğü ayrımla tutarlı.

**Eksiler / kabul edilen riskler:**
- Backend playbook'ları (NestJS, Java, Python) henüz cross-cutting playbook'lara açıkça
  referans vermiyor — bu ADR'nin uygulanışı olarak her birine kısa birer pointer eklenmesi
  gerekiyor (ayrı bir takip işi).
- Gözlemlenebilirlik platformunun gerçek collector endpoint'i/config değerleri henüz
  playbook'a girilmedi — `[CoE'nin merkezi platform dokümantasyonu]` placeholder'ı olarak
  bırakıldı, platform ekibi bu detayı sağladığında doldurulmalı.

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** ADR-0003'teki messaging bulguları
(arq'nin SQS ile uyumsuzluğu) bu ADR'nin messaging playbook'una taşındı, tekrar
değerlendirilmedi.
