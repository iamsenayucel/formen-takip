# API Kataloğu

Tüm uçlar `/api/v1` altında, JWT bearer token ile korunur (`/auth/*` hariç).
OpenAPI dokümantasyonu: `http://localhost:8000/docs`.

| Router | Öne çıkan uçlar |
|---|---|
| `auth` | `POST /login`, `POST /refresh`, `POST /logout`, `GET /me` |
| `meta` | `GET /filters` — filtre barının kademeli (cascading) seçenekleri |
| `dashboard` | `GET /summary`, `/trend`, `/kpi-summary`, `/plant-ranking`, `/shift-comparison`, `/foreman-ranking`, `/performance-distribution` |
| `plants` | `GET /plants`, `/{id}`, `/{id}/summary`, `/{id}/kpis`, `/{id}/shifts`, `/{id}/chiefs`, `/{id}/foremen` |
| `chiefs` | `GET /chiefs`, `/{id}`, `/{id}/foremen`, `/{id}/kpis`, `/{id}/trend` |
| `foremen` | `GET /foremen`, `/{id}`, `/{id}/kpis`, `/{id}/kpis/{kpi_id}/calculation-detail`, `/{id}/trend`, `/{id}/assignment-history`, `/{id}/contribution-summary` |
| `kpis` | `GET /kpis`, `/{id}`, `/{id}/analysis` |
| `data_quality` | `GET /issues`, `/summary` |
| `integration` | `GET /runs`, `/runs/{id}`, `POST /resync` |
| `action_plans` | `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}` |
| `contributions` | `GET /contribution-works`, `/summary`, `/{id}`, `/{id}/pdf`, `POST /`, `PATCH /{id}`, `DELETE /{id}` — bkz. [Katkılar](#katkılar) |
| `anomalies` | `GET /anomalies`, `/summary`, `/{id}`, `POST /{id}/analyze`, `/{id}/reanalyze`, `GET /{id}/analysis`, `PATCH /{id}/status` — bkz. [Tespitler Modülü](#tespitler-modülü-anomali-tespiti--yapay-zekâ-analizi) |
| `analyses` | `GET /analyses/{id}`, `GET /analyses/{id}/tool-calls` — Aşama 2 tool calling geçmişi |
| `reports` | `POST /generate`, `GET /`, `GET /{id}/download` |
| `audit_logs` | `GET /` |

Ortak filtreleme: `common_filters` bağımlılığı (`app/schemas/common.py`)
`date_from`, `date_to`, virgülle ayrılmış `plant_ids` / `factory_ids` /
`chief_ids` / `shift_ids` / `kpi_ids` parametrelerini tek bir `Filters`
nesnesine çözer ve `analytics._apply_filters` üzerinden tüm sorgulara
uygulanır. `factory_ids`, `PerformanceRecord`'ın `factory_id` taşımaması
nedeniyle bir `Plant.factory_id` alt sorgusu üzerinden çözülür.

Aksiyon planları performans kaydını hiçbir şekilde değiştirmez — tamamen
bağımsız bir takip tablosudur. Raporlama modülü de mevcut
`analytics.py` sorgularını yeniden kullanır; üretilen dosya içeriği demo
ölçeğinde ayrı bir obje deposu gerektirmediği için `report_exports`
tablosunda (`LargeBinary`) saklanır.

Denetlenebilir eylemler (giriş/çıkış, aksiyon planı CRUD, rapor
oluşturma/indirme, resync tetikleme) `app/services/audit.py::record_audit()`
üzerinden tek noktadan `audit_logs` tablosuna yazılır.