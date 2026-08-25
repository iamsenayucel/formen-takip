# API Sözleşme Kataloğu

Bu belge `/api/v1` yüzeyinin Tier1 sözleşmesini özetler. Çalışan sistemdeki kesin
şema ve örnekler `/docs` OpenAPI arayüzündedir.

## Ortak kurallar

- JSON alan adları `camelCase`, Python iç modeli `snake_case` kullanır.
- Başarılı tekil ve liste yanıtı: `{"data": ...}`.
- Cursor ile sayfalanan yanıt:
  `{"data": [...], "pagination": {"nextCursor": "...", "hasMore": true, "total": null}}`.
- Hata yanıtı:
  `{"error": {"code": "...", "message": "...", "requestId": "...", "timestamp": "...", "details": ...}}`.
- Her yanıtta `X-Request-Id` bulunur. İstemcinin gönderdiği değer korunur; yoksa
  backend UUID üretir.
- Query parametreleri mevcut `snake_case` adlarını korur (`date_from`,
  `plant_ids`, `sort_by`). CamelCase kuralı JSON gövdeleri içindir.
- Tüm `/api/v1` uçları OIDC Bearer token ister. Sağlık uçları muaftır.

## Sayfalama

Sayfalanan koleksiyonlar `limit` (varsayılan 25, en fazla 200) ve opsiyonel
`cursor` alır. Cursor opaktır; istemci içeriğini çözümlememeli veya değiştirmemelidir.
Cursor sıralama ve filtre imzasını taşır. Başka filtre/sıralamayla kullanılırsa
`400 INVALID_CURSOR` döner.

| Uç | Varsayılan sıralama |
|---|---|
| `GET /api/v1/plants` | `sequence asc` |
| `GET /api/v1/plants/{plantId}/foremen` | performans sırası |
| `GET /api/v1/foremen` | performans sırası |
| `GET /api/v1/chiefs` | performans sırası |
| `GET /api/v1/anomalies` | tespit tarihi/kimlik |
| `GET /api/v1/contribution-works` | oluşturma tarihi/kimlik |
| `GET /api/v1/reports` | oluşturma tarihi/kimlik |

## Uç grupları

| Grup | Başlıca uçlar |
|---|---|
| Kimlik | `GET /auth/me` |
| Meta | `GET /meta/filters` |
| Dashboard | özet, trend, KPI, sıralamalar, dağılım, liderler ve snapshot |
| Tesis | liste, detay, özet, KPI, vardiya, şef, formen ve vardiya matrisi |
| Şef | liste, detay, ekip, KPI, karşılaştırma ve trend |
| Formen | liste, detay, KPI/hesap detayı, trend, atama, katkı ve aylık rapor |
| KPI | liste, detay ve analiz |
| Tespit | liste, özet, detay, inceleme, analiz, durum ve tool-call geçmişi |
| Katkı | liste, özet, CRUD ve PDF |
| Rapor | üretim, geçmiş ve indirme |
| Vardiya analizi | kartlar, heatmap ve detay |

## Hata kodları

| HTTP | Varsayılan kod | Kullanım |
|---|---|---|
| 400 | `BAD_REQUEST` / `INVALID_CURSOR` | Geçersiz istek veya cursor |
| 401 | `UNAUTHORIZED` | Eksik/geçersiz kimlik |
| 403 | `FORBIDDEN` | Yetki yetersizliği |
| 404 | `RESOURCE_NOT_FOUND` veya alan kodu | Kaynak bulunamadı |
| 409 | `CONFLICT` | Eşzamanlı işlem/alan çatışması |
| 422 | `VALIDATION_ERROR` | Query/path/body doğrulaması |
| 429 | `RATE_LIMIT_EXCEEDED` | Kimlik bazlı hız sınırı; `Retry-After` içerir |
| 500 | `INTERNAL_ERROR` | Beklenmeyen, güvenli mesajlı hata |
| 502/503 | servis kodu | Upstream veya zorunlu bağımlılık erişilemiyor |

Validation hatalarında `error.details.fields` listesi `field`, `reason` ve `code`
alanlarını içerir; `field` camelCase yazılır.

## Hız sınırı

Varsayılan API, YZ analizi, rapor ve PDF için ayrı limitler vardır. Anahtar
doğrulanmış `Identity.subject` değeridir. Test ortamında limiter kapalıdır. Mevcut
uygulama proses içi sliding-window kullanır: tek replica için deterministiktir,
fakat çok replica dağıtımında global limit sağlamaz. Çok replica üretimde Redis
gibi ortak bir sayaç zorunludur.

## Sağlık uçları

- `/health` ve `/health/live`: proses canlılığı, standart success zarfı.
- `/health/ready`: veritabanını kontrol eder. Başarı success zarfı, erişim yoksa
  `503 SERVICE_UNAVAILABLE` standart error zarfı döner.

## Sözleşme doğrulaması

`tests/integration/test_api_contract.py` ham JSON envelope, camelCase, request ID,
cursor ve OpenAPI belgelerini; `tests/unit/test_rate_limit.py` kimlik izolasyonu ile
429 davranışını doğrular. Eski sayısal karakterizasyon testleri yalnızca iş kuralı
kıyasları için `tests.helpers.legacy_json` görünümünü kullanır; wire contract bu
adaptör üzerinden test edilmez.
