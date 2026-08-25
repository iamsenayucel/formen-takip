# Cross-Cutting Playbook — Gözlemlenebilirlik (Zorunlu)

> `tier1/README.md`'deki yoğunluk kuralına uyar. Bu bir **stack playbook'u değil,
> cross-cutting playbook'tur** — NestJS/Java/Python fark etmeksizin her backend'e uygulanır.
> Zorunluluğun kendisi `tier0/RULES.md` §11'de; burada yalnız **nasıl** uygulanacağı var.
> Onay: `tier0/adr/0004-centralized-observability-mandatory.md`.

**Platform:** Prometheus (metrik) + Loki (log) + Grafana (görselleştirme) + Opsgenie
(alarm, gerekirse) — CoE'nin merkezi, paylaşılan hizmeti. Enstrümantasyon: OpenTelemetry.

---

### Metrik

**Ne:** OpenTelemetry Metrics SDK → Prometheus formatında `/metrics` endpoint'i (veya OTel
Collector üzerinden push).
**Neden:** Her proje kendi metrik toplama altyapısını kurarsa merkezi Grafana panoları
tutarsız/eksik veri gösterir.
**Kural:** Her servis en az şu metrikleri üretir: istek sayısı, hata oranı, p50/p95/p99
gecikme (RED metrikleri). Metrik isimleri OTel semantic conventions'a uyar, uydurulmaz.
**Referans:** `http://localhost:9090 (Lokal Prometheus/Grafana Stack)`

### Log

**Ne:** Yapılandırılmış (JSON) log, OpenTelemetry Logs SDK üzerinden Loki'ye.
**Neden:** Ham metin log Loki'de aranabilir/filtrelenebilir değildir; yapılandırılmamış log
merkezi platformun değerini sıfırlar.
**Kural:** Her log kaydı en az `timestamp`, `level`, `service.name`, `trace_id` (varsa)
alanlarını taşır; `console.log`/`print` ile üretim log'u tutulmaz.
**Referans:** `Lokal stdout (Docker logs üzerinden)`

### Trace

**Ne:** OpenTelemetry Traces SDK — servisler arası çağrılarda trace context propagate edilir
(örn. `traceparent` header'ı).
**Neden:** Bir istek NestJS API'den Python ML servisine geçtiğinde, trace context
propagate edilmezse iki servisin log/metrikleri birbirine bağlanamaz — uçtan uca izleme
kaybolur.
**Kural:** Servisler arası her HTTP/gRPC/queue çağrısı trace context'i taşır; yeni bir
"kök" trace başlatmak yerine gelen context'e span eklenir.
**Referans:** `TBD`

> ⚠️ **Kritik:** Trace/log'a asla PII veya hassas veri gömülmez — `tier0/RULES.md` §4
> madde 3'ün gözlemlenebilirlik karşılığı. Bir kullanıcı ID'si loglanabilir, ad-soyad/
> e-posta/kimlik numarası loglanamaz.

### Zorunlu Resource Attribute'ları

**Ne:** Her servis, OTel resource olarak en az `service.name`, `service.version`,
`deployment.environment` (`dev`/`staging`/`prod`) taşır.
**Neden:** Bu alanlar olmadan Grafana'da "hangi servisin hangi ortamdaki hangi sürümü"
sorusu cevaplanamaz.
**Kural:** `service.name`, projenin `tier0/RULES.md` §1'deki proje adıyla tutarlı olur.
**Referans:** `TBD`

### Dil-Özel Enstrümantasyon (kısa referans, detay değil)

| Stack | OTel SDK / yaklaşım |
|---|---|
| NestJS (Node.js) | `@opentelemetry/sdk-node` + otomatik enstrümantasyon paketleri |
| Spring Boot / Quarkus (Java) | OpenTelemetry Java agent (çoğunlukla otomatik enstrümantasyon, kod değişikliği gerektirmez) |
| FastAPI (Python) | `opentelemetry-sdk` + `opentelemetry-instrumentation-fastapi` |

Her stack'in kendi playbook'una bu tabloyu **kopyalamayın** — buraya işaret edin
(`tier1/README.md`'nin "içerik bir kez yazılır" kuralı burada da geçerli).

### Alarm (Opsgenie, gerekirse)

**Ne:** Kritik metrik/log eşiklerinde Opsgenie'ye alarm.
**Neden:** Gözlemlenebilirlik, kimse bakmıyorsa değersizdir — kritik durumlarda aktif
bildirim gerekir.
**Kural:** Alarm eşikleri gürültü üretmeyecek şekilde kalibre edilir (her hata değil,
anlamlı eşik aşımı); her alarm bir runbook'a veya en azından bir sorumlu ekibe bağlıdır.
**Referans:** `Lokal ortamda devre dışı (N/A)`
