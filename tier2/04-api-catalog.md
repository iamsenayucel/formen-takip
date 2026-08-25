# API Kataloğu

Uygulama API'si `/api/v1` prefix'ini kullanır. Bu prefix altındaki tüm
endpointler bearer access token ister; backend OIDC/JWKS ile token imzası,
issuer, audience, `exp` ve `iat` doğrular. `/health`, `/health/live`,
`/health/ready`, `/docs`, `/redoc` ve `/openapi.json` kimlik doğrulaması istemez.

Public JSON body/response alanları Pydantic alias'larıyla camelCase'dir.
Tekil response:

```json
{"data": {}}
```

Cursor kullanan liste response'u:

```json
{
  "data": [],
  "pagination": {
    "nextCursor": null,
    "hasMore": false,
    "total": null
  }
}
```

Cursor kullanan listeler `cursor` ve `limit` alır; offset tabanlı sayfalama
public standart değildir. Query parametre adları router'da tanımlandığı
şekliyle kullanılır; ortak filtreler `date_from`, `date_to` ve virgülle ayrılmış
`factory_ids`, `plant_ids`, `chief_ids`, `shift_ids`, `kpi_ids`,
`foreman_ids` değerleridir. Kesin opsiyonel alan, enum ve sınırlar runtime
OpenAPI'de source of truth'tur.

| Alan | Method ve path | Amaç / önemli request–response |
|---|---|---|
| Kimlik | `GET /auth/me` | Token subject, display name ve e-posta |
| Meta | `GET /meta/filters` | Cascading fabrika/tesis/şef/vardiya/KPI/formen seçenekleri |
| Dashboard | `GET /dashboard/summary` | Dönem genel özeti |
|  | `GET /dashboard/trend` | Günlük/haftalık trend |
|  | `GET /dashboard/kpi-summary` | Altı KPI özeti |
|  | `GET /dashboard/plant-ranking` | Tesis sıralaması; sort/limit |
|  | `GET /dashboard/shift-comparison` | V1/V2 karşılaştırması |
|  | `GET /dashboard/foreman-ranking` | Formen sıralaması; sort/limit |
|  | `GET /dashboard/foreman-trend-ranking` | İyileşen/gerileyen formenler |
|  | `GET /dashboard/performance-distribution` | Performans seviye dağılımı |
|  | `GET /dashboard/performance-leaders` | Yıllık liderlik özeti |
|  | `GET /dashboard/snapshot` | Dashboard bileşik snapshot'ı |
| Tesis | `GET /plants` | Cursor liste; arama, fabrika/şef/aktiflik, sıralama |
|  | `GET /plants/{plant_id}` | Tesis kimlik/organizasyon detayı |
|  | `GET /plants/{plant_id}/summary` | Dönem performans özeti |
|  | `GET /plants/{plant_id}/kpis` | KPI sonuçları |
|  | `GET /plants/{plant_id}/shifts` | Vardiya sonuçları |
|  | `GET /plants/{plant_id}/chiefs` | İlişkili şef bilgisi |
|  | `GET /plants/{plant_id}/foreman-shift-matrix` | KPI bazlı formen/vardiya matrisi |
|  | `GET /plants/{plant_id}/foremen` | Cursor formen listesi |
| Şef/Grup | `GET /chiefs` | Cursor liste; arama/tesis/aktiflik/sıralama |
|  | `GET /chiefs/{chief_id}` | Şef ve grup detayı |
|  | `GET /chiefs/{chief_id}/foremen` | Gruptaki formenler |
|  | `GET /chiefs/{chief_id}/kpis` | Şef KPI sonuçları |
|  | `GET /chiefs/{chief_id}/foreman-comparison` | Formen KPI karşılaştırması |
|  | `GET /chiefs/{chief_id}/trend` | Şef/grup trendi |
| Formen | `GET /foremen` | Cursor liste; kapsam, seviye, outstanding ve sıralama filtreleri |
|  | `GET /foremen/{foreman_id}` | Profil ve performans detayı |
|  | `GET /foremen/{foreman_id}/kpis` | KPI ve tesis breakdown'u |
|  | `GET /foremen/{foreman_id}/kpis/{kpi_id}/calculation-detail` | Hesap bileşenleri |
|  | `GET /foremen/{foreman_id}/trend` | Dönem trendi |
|  | `GET /foremen/{foreman_id}/assignment-history` | Tarihsel atamalar |
|  | `GET /foremen/{foreman_id}/contribution-summary` | Son 90 gün katkı bonusu |
|  | `GET /foremen/{foreman_id}/monthly-reports` | Aylık rapor listesi |
|  | `GET /foremen/{foreman_id}/monthly-reports/latest` | Son rapor |
|  | `GET /foremen/{foreman_id}/monthly-reports/{year}/{month}` | Snapshot detayı |
|  | `GET /foremen/{foreman_id}/monthly-reports/{year}/{month}/pdf` | Authenticated PDF |
|  | `GET /foremen/{foreman_id}/monthly-reports/{year}/{month}/access` | Signed URL/proxy erişim kararı |
| KPI | `GET /kpis` | Aktif KPI listesi |
|  | `GET /kpis/{kpi_id}` | KPI tanımı |
|  | `GET /kpis/{kpi_id}/analysis` | Tesis/vardiya/formen analiz breakdown'u |
| Vardiya | `GET /shift-analysis/cards` | Tamamlanmış ay tespit kartları |
|  | `GET /shift-analysis/heatmap` | Tesis/vardiya/KPI heatmap |
|  | `GET /shift-analysis/detail` | Tek tesis+vardiya+KPI detayı |
| Operational Impact+ | `GET /contribution-works` | Cursor liste; tarih, kapsam, tür, durum, etki, finansal ve arama filtreleri |
|  | `GET /contribution-works/summary` | Filtrelenmiş özet |
|  | `POST /contribution-works` | `ContributionWorkCreate`; `201` |
|  | `GET /contribution-works/{work_id}` | Çalışma detayı |
|  | `PATCH /contribution-works/{work_id}` | `ContributionWorkUpdate` |
|  | `DELETE /contribution-works/{work_id}` | `204` |
|  | `GET /contribution-works/{work_id}/pdf` | PDF indirme |
| Tespit | `GET /anomalies` | Cursor liste; fabrika/tesis/vardiya/KPI/severity/status/analysis/tarih |
|  | `GET /anomalies/summary` | Aktif tespit özeti |
|  | `GET /anomalies/{anomaly_id}` | Tespit detayı |
|  | `GET /anomalies/{anomaly_id}/investigation` | Doğrulanmış araştırma bağlamı |
|  | `GET /anomalies/{anomaly_id}/analysis` | Son analiz |
|  | `POST /anomalies/{anomaly_id}/analyze` | `{mode, forceRefresh}`; rate limit ve active-claim kontrolü |
|  | `POST /anomalies/{anomaly_id}/reanalyze` | Yeni analiz denemesi |
|  | `PATCH /anomalies/{anomaly_id}/status` | `{status}` |
| Analiz | `GET /analyses/{analysis_id}` | Analiz kaydı |
|  | `GET /analyses/{analysis_id}/tool-calls` | Tool calling geçmişi |
| Rapor | `POST /reports/generate` | `ReportGenerateRequest`; `201`, rate limited |
|  | `GET /reports` | Cursor export geçmişi |
|  | `GET /reports/{report_id}/download` | CSV/XLSX/PDF indirme, rate limited |

Standart error envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Kaynak bulunamadı.",
    "requestId": "...",
    "timestamp": "...",
    "details": null
  }
}
```

Önemli kod aileleri: `UNAUTHORIZED` (401), `BAD_REQUEST`/`INVALID_CURSOR`
(400), entity-specific `*_NOT_FOUND` (404), `ANOMALY_ANALYSIS_IN_PROGRESS`
(409), `VALIDATION_ERROR`/`CONTRIBUTION_WORK_VALIDATION_FAILED` (422),
`RATE_LIMIT_EXCEEDED` (429), `UPSTREAM_SERVICE_ERROR` (502) ve
`SERVICE_UNAVAILABLE` (503).

Fine-grained backend RBAC uygulanmamıştır; doğrulanmış OIDC kimliği için
endpoint permission enforcement gelecek sürüme deferred'dır. Mutasyonlar
OIDC subject ve request ID ile `audit_logs` tablosuna yazılır.
