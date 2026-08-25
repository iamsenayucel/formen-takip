# Formen Performans Takip Sistemi — Mevcut Veritabanı Şeması

| | |
|---|---|
| **Doküman türü** | Mevcut durum tespiti (as-is şema dokümantasyonu) |
| **Kaynak** | Çalışan PostgreSQL 16 örneğinin canlı introspection'ı (`information_schema`/`pg_catalog`, `\d+`) — kod dosyalarından değil, veritabanının kendisinden çıkarılmıştır |
| **Alembic revizyonu** | `c7a1f9d0b2e3` (head) |
| **Şema** | `public`, 23 domain tablosu + `alembic_version` (Alembic'in kendi versiyon takip tablosu, uygulama verisi değil) |
| **Kapsam notu** | Bu doküman yeni bir tasarım önermez; yalnızca şu an veritabanında gerçekten var olan tabloları, kolonları, kısıtları, indeksleri ve ilişkileri olduğu gibi raporlar. |

Tüm kolonlarda **DB seviyesinde `DEFAULT` tanımlı değildir** — varsayılan değerler (UUID üretimi, zaman damgaları, sayaç başlangıçları vb.) uygulama katmanında (SQLAlchemy ORM) uygulanıyor, veritabanı bunu bilmiyor. Bu, introspection'da her tabloda gözlemlenen tutarlı bir durumdur.

> **⚠️ Bu doküman güncel değil (tarihsel snapshot).** Yukarıdaki `c7a1f9d0b2e3`
> revizyonu, mevcut alembic HEAD'inden (`backend/alembic/versions/` içinde
> `down_revision` zincirinin ucu — bu yazı itibarıyla `c7a1f9d0b2e3`'ten 10'dan
> fazla migration ileride) çok gerideldir. O tarihten bu yana şema önemli
> ölçüde değişti; en azından şunlar bu dokümana yansımamıştır:
> - `chiefs.plant_id` kaldırıldı, yön tersine döndü (`plants.chief_id`) — bir
>   şef artık tek bir tesise değil bir **bölgeye (zone)** sorumludur.
> - `users` tablosu tamamen kaldırıldı — kimlik doğrulama artık Red Hat SSO /
>   Keycloak (OIDC) üzerinden yapılır, `bcrypt`/`password_hash` yoktur;
>   kalıcı kayıtlar OIDC token'ının stabil kimlik claim'ini (`subject`) düz
>   metin olarak tutar (bkz. kök `README.md` → "Authentication Architecture").
> - `action_plans` tablosu tamamen kaldırıldı (migration `c9e2a4f6b8d0`).
> - `contribution_works`, `contribution_work_foremen`, `contribution_work_plants`,
>   `contribution_gains`, `anomalies`, `anomaly_analyses`, `anomaly_tool_calls`,
>   `foreman_monthly_reports` gibi tablolar bu dokümanın yazıldığı tarihte
>   henüz yoktu.
>
> Güncel şema için `tier2/03-data-schema.md` (tablo grupları + eksiksiz
> migration geçmişi) veya kök `README.md`'nin "Veritabanı Şeması" bölümüne
> bakın; ya da `app/models/*.py` + `backend/alembic/versions/`'ı doğrudan
> inceleyin. Bu doküman yeniden yazılmamıştır (kapsam dışı); yalnızca §3.1
> KPI listesi, somut ve sık başvurulan bir yanlışı önlemek için aşağıda
> güncellenmiştir.

---

## 1. Organizasyon

### 1.1 `factories`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| code | varchar(20) | NOT NULL | UNIQUE (`ix_factories_code`) |
| name | varchar(200) | NOT NULL | |
| location | varchar(100) | NOT NULL | |
| is_active | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `plants.factory_id`

### 1.2 `plants`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| code | varchar(20) | NOT NULL | UNIQUE (`ix_plants_code`) |
| name | varchar(200) | NOT NULL | |
| sequence_number | integer | NOT NULL | UNIQUE (`uq_plants_sequence_number`) |
| factory_id | uuid | NOT NULL | FK → `factories.id` |
| description | varchar(1000) | NULL | |
| is_active | boolean | NOT NULL | |
| sap_plant_code | varchar(20) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `action_plans.plant_id`, `chiefs.plant_id`, `foreman_assignments.plant_id`, `foreman_work_calendar.plant_id`, `performance_records.plant_id`, `production_lines.plant_id`, `production_records.plant_id`

### 1.3 `shifts`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| code | varchar(20) | NOT NULL | UNIQUE (`shifts_code_key`) |
| name | varchar(100) | NOT NULL | |
| start_time | time (tz'siz) | NOT NULL | |
| end_time | time (tz'siz) | NOT NULL | |
| sequence | integer | NOT NULL | |
| crosses_midnight | boolean | NOT NULL | |
| is_active | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `action_plans.shift_id`, `foreman_assignments.shift_id`, `foreman_work_calendar.shift_id`, `performance_records.shift_id`, `production_records.shift_id`

---

## 2. Personel

### 2.1 `chiefs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK; ayrıca `(id, plant_id)` bileşik UNIQUE (`uq_chiefs_id_plant_id`) |
| employee_number | varchar(30) | NOT NULL | UNIQUE (`ix_chiefs_employee_number`) |
| first_name / last_name | varchar(100) | NOT NULL | |
| plant_id | uuid | NOT NULL | FK → `plants.id` |
| hire_date | date | NOT NULL | |
| is_active | boolean | NOT NULL | |
| sap_personnel_number | varchar(30) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `action_plans.chief_id`, `foreman_assignments.(chief_id,plant_id)` (bileşik FK, `fk_foreman_assignments_chief_plant`), `foreman_work_calendar.chief_id`, `performance_records.chief_id`, `production_records.chief_id`

### 2.2 `foremen`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| employee_number | varchar(30) | NOT NULL | UNIQUE (`ix_foremen_employee_number`) |
| first_name / last_name | varchar(100) | NOT NULL | |
| hire_date | date | NOT NULL | |
| termination_date | date | NULL | |
| is_active | boolean | NOT NULL | |
| sap_personnel_number | varchar(30) | NULL | |
| photo_url | varchar(500) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

Not: `foremen` tablosunda organizasyon FK'sı yok — yerleşim tamamen `foreman_assignments` üzerinden.

**Referans veren:** `action_plans.foreman_id`, `foreman_assignments.foreman_id`, `foreman_work_calendar.foreman_id`, `performance_records.foreman_id`, `production_records.foreman_id`

### 2.3 `foreman_assignments`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| foreman_id | uuid | NOT NULL | FK → `foremen.id` |
| plant_id | uuid | NOT NULL | FK → `plants.id` |
| chief_id | uuid | NOT NULL | bileşik FK `(chief_id, plant_id)` → `chiefs(id, plant_id)` |
| shift_id | uuid | NOT NULL | FK → `shifts.id` |
| start_date | date | NOT NULL | |
| end_date | date | NULL | |
| is_active | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

SCD2 desenli (start/end_date ile geçmişi koruyan) yerleşim geçmişi tablosu. `(chief_id, plant_id)` bileşik FK, bir şefin kendi tesisi dışında bir formene atanmasını DB seviyesinde imkânsız kılıyor.

---

## 3. KPI Tanımı

### 3.1 `kpis`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| code | varchar(30) | NOT NULL | UNIQUE (`ix_kpis_code`) |
| name | varchar(200) | NOT NULL | |
| description | varchar(1000) | NULL | |
| unit | varchar(30) | NOT NULL | |
| calculation_type | enum `calculation_type` | NOT NULL | |
| success_direction_higher | boolean | NOT NULL | |
| default_target_value | numeric(12,4) | NOT NULL | |
| min_valid_value / max_valid_value | numeric(12,4) | NOT NULL | |
| min_score / max_score | numeric(12,2) | NOT NULL | |
| weight | numeric(5,2) | NOT NULL | |
| valid_from | date | NOT NULL | |
| valid_to | date | NULL | |
| is_active | boolean | NOT NULL | |
| source_data_field | varchar(100) | NULL | |
| aggregation_method | enum `aggregation_method` | NOT NULL | |
| decimal_places | integer | NOT NULL | |
| is_critical | boolean | NOT NULL | |
| display_order | integer | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `action_plans.kpi_id`, `kpi_calculation_rules.kpi_id`, `kpi_targets.kpi_id`, `performance_records.kpi_id`

**Current (canlı DB'de doğrulandı, `SELECT code, weight FROM kpis`):** 5 KPI,
her biri ağırlık 20 (toplam 100) — `AGIR_GITME`, `GSF`, `ISKARTA`, `INKITA`,
`PLANA_UYUM`. Kaynak: `backend/app/services/synthetic/reference_data.py::DEFAULT_KPI_SEED`.
Hepsi `calculation_type=CUSTOM_FORMULA`; ayrıntılı formüller için kök
`README.md` → "KPI Hesaplama Motoru" bölümüne bakın.

**Legacy/history:** Bu dokümanın önceki sürümü, `PLANLI_INKITA`(w=5) /
`PLANSIZ_INKITA`(w=15) ikilisinin ayrı KPI olduğu ve `ISKARTA`(w=25) /
`GSF`(w=15) ağırlıklarının farklı olduğu daha eski bir seed setini
listeliyordu. O set kodda artık mevcut değil — `INKITA` tek bir KPI'a
birleşti (yalnızca Teknik + İmalat duruşu, Diğer duruşlar hariç), ağırlıklar
eşitlendi (5×20).

### 3.2 `kpi_calculation_rules`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| kpi_id | uuid | NOT NULL | FK → `kpis.id` |
| version | integer | NOT NULL | |
| calculation_type | enum `calc_rule_type` | NOT NULL | |
| parameters | json | NOT NULL | |
| valid_from | date | NOT NULL | |
| valid_to | date | NULL | |
| is_active | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `performance_scores.calculation_rule_id`

### 3.3 `kpi_targets`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| kpi_id | uuid | NOT NULL | FK → `kpis.id` |
| scope_type | enum `target_scope_type` (COMPANY/PLANT/CHIEF/FOREMAN) | NOT NULL | |
| scope_id | uuid | NULL | (COMPANY için NULL) |
| target_value | numeric(12,4) | NOT NULL | |
| valid_from | date | NOT NULL | |
| valid_to | date | NULL | |
| is_active | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

72 kayıt: 66 PLANT kapsamlı (11 tesis × 6 KPI) + 6 COMPANY kapsamlı (fallback). CHIEF/FOREMAN kapsamlı hedef şu an veri setinde yok (kod destekliyor).

### 3.4 `performance_level_rules`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| name | varchar(50) | NOT NULL | UNIQUE |
| min_score / max_score | numeric(6,2) | NOT NULL | |
| description | varchar(500) | NOT NULL | |
| color | varchar(20) | NOT NULL | |
| icon | varchar(50) | NOT NULL | |
| sort_order | integer | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

---

## 4. Üretim Verisi (ham katman)

### 4.1 `products`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| code | varchar(30) | NOT NULL | UNIQUE (`products_code_key`) |
| name | varchar(200) | NOT NULL | |
| unit | varchar(20) | NOT NULL | |
| standard_gram | numeric(10,3) | NULL | |
| lower_gram_limit / upper_gram_limit | numeric(10,3) | NULL | |
| is_active | boolean | NOT NULL | |
| sap_material_code | varchar(30) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `production_records.product_id`

### 4.2 `production_lines`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| code | varchar(30) | NOT NULL | UNIQUE |
| name | varchar(200) | NOT NULL | |
| plant_id | uuid | NOT NULL | FK → `plants.id` |
| is_active | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `foreman_work_calendar.line_id`, `production_records.line_id`

### 4.3 `company_calendar`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| calendar_date | date | NOT NULL | UNIQUE |
| is_holiday | boolean | NOT NULL | |
| note | varchar(200) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

Yalnızca tatil günleri için satır tutuluyor (7 kayıt) — hafta sonu tarihin kendisinden hesaplanıyor, ayrıca satır gerektirmiyor.

### 4.4 `foreman_work_calendar`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| foreman_id | uuid | NOT NULL | FK → `foremen.id`; `(foreman_id, work_date)` UNIQUE (`uq_foreman_work_calendar_foreman_date`) |
| work_date | date | NOT NULL | |
| plant_id | uuid | NOT NULL | FK → `plants.id` |
| chief_id | uuid | NOT NULL | FK → `chiefs.id` |
| shift_id | uuid | NOT NULL | FK → `shifts.id` |
| line_id | uuid | NOT NULL | FK → `production_lines.id` |
| is_working | boolean | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

### 4.5 `production_records`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| source_system | enum `production_source_system` (SYNTHETIC/SAP) | NOT NULL | |
| source_record_id | varchar(100) | NOT NULL | `(source_system, source_record_id)` UNIQUE (`uq_production_record_source`) |
| production_order_number | varchar(50) | NOT NULL | |
| batch_number | varchar(50) | NOT NULL | |
| plant_id / line_id / product_id / foreman_id / chief_id / shift_id | uuid | NOT NULL | FK'ler ilgili tablolara |
| production_date | date | NOT NULL | `(foreman_id, production_date, shift_id)` UNIQUE (`uq_production_record_natural_key`) |
| unit | varchar(20) | NOT NULL | |
| planned_qty / actual_qty | numeric(14,4) | NULL | |
| planned_start_at / planned_end_at / actual_start_at / actual_end_at | timestamptz | NULL | |
| standard_speed / actual_speed | numeric(14,4) | NULL | |
| measured_avg_gram | numeric(10,3) | NULL | |
| gram_sample_count | integer | NULL | |
| gsf_qty / iskarta_qty | numeric(14,4) | NULL | |
| planned_downtime_minutes / unplanned_downtime_minutes | numeric(10,2) | NULL | |
| plan_revision_no | integer | NOT NULL | |
| plan_revision_at | timestamptz | NULL | |
| source_updated_at | timestamptz | NULL | |
| imported_at | timestamptz | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `performance_records.production_record_id` (`ON DELETE SET NULL`)

---

## 5. Performans (türetilmiş, salt okunur)

### 5.1 `performance_records`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| source_system | enum `source_system` (SYNTHETIC/SAP) | NOT NULL | |
| source_record_id | varchar(100) | NOT NULL | `(source_system, source_record_id)` UNIQUE (`uq_perf_record_source`) |
| integration_run_id | uuid | NOT NULL | FK → `integration_runs.id` |
| performance_date | date | NOT NULL | `(foreman_id, kpi_id, chief_id, shift_id, performance_date)` UNIQUE (`uq_perf_record_natural_key`) |
| plant_id / chief_id / shift_id / foreman_id / kpi_id | uuid | NOT NULL | FK'ler ilgili tablolara |
| target_value / actual_value / numerator_value / denominator_value | numeric(14,4) | NULL | |
| unit | varchar(30) | NOT NULL | |
| data_quality_status | enum `data_quality_status` | NOT NULL | |
| source_updated_at | timestamptz | NULL | |
| imported_at | timestamptz | NOT NULL | |
| production_record_id | uuid | NULL | FK → `production_records.id` ON DELETE SET NULL — hangi ham üretim kaydından türetildiğinin izi |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `data_quality_issues.performance_record_id`, `performance_scores.performance_record_id`

### 5.2 `performance_scores`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| performance_record_id | uuid | NOT NULL | UNIQUE (`ix_performance_scores_performance_record_id`) — 1:1 ilişki; FK → `performance_records.id` |
| calculation_rule_id | uuid | NOT NULL | FK → `kpi_calculation_rules.id` |
| raw_score / capped_score / weighted_contribution | numeric(14,3) | NOT NULL | |
| kpi_weight | numeric(5,2) | NOT NULL | |
| calculation_version | integer | NOT NULL | |
| calculated_at | timestamptz | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

---

## 6. Entegrasyon ve Veri Kalitesi

### 6.1 `integration_runs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| source_system | enum `run_source_system` | NOT NULL | |
| started_at | timestamptz | NOT NULL | |
| finished_at | timestamptz | NULL | |
| status | enum `integration_status` (RUNNING/SUCCESS/PARTIAL_SUCCESS/FAILED) | NOT NULL | |
| processed_count / success_count / error_count / skipped_count | integer | NOT NULL | |
| notes | varchar(2000) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `performance_records.integration_run_id`

### 6.2 `data_quality_issues`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| performance_record_id | uuid | NULL | FK → `performance_records.id` (DUPLICATE tipi sorunlarda NULL olabilir) |
| issue_type | enum `issue_type` | NOT NULL | |
| description | varchar(1000) | NOT NULL | |
| detected_at | timestamptz | NOT NULL | |
| status | varchar(30) | NOT NULL | (enum değil, düz metin) |
| created_at / updated_at | timestamptz | NOT NULL | |

---

## 7. Aksiyon Planı, Rapor, Kimlik

### 7.1 `action_plans`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| title | varchar(300) | NOT NULL | |
| description | varchar(4000) | NULL | |
| plant_id / shift_id / foreman_id / kpi_id / chief_id | uuid | NULL | FK'ler (hepsi opsiyonel — performans verisinden bağımsız) |
| owner | varchar(200) | NOT NULL | |
| created_by_user_id | uuid | NOT NULL | FK → `users.id` |
| priority | enum `action_plan_priority` | NOT NULL | |
| status | enum `action_plan_status` | NOT NULL | |
| start_date / target_end_date | date | NOT NULL | |
| actual_end_date | date | NULL | |
| completion_percentage | integer | NOT NULL | |
| outcome_notes | varchar(4000) | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

### 7.2 `report_exports`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| report_type | enum `report_type` | NOT NULL | |
| format | enum `report_format` (CSV/XLSX/PDF) | NOT NULL | |
| filters_json | json | NOT NULL | |
| requested_by_user_id | uuid | NOT NULL | FK → `users.id` |
| file_name | varchar(300) | NOT NULL | |
| file_content | bytea | NOT NULL | (dosya ikili içeriği DB'de saklanıyor) |
| row_count | integer | NOT NULL | |
| status | enum `report_status` (COMPLETED/FAILED) | NOT NULL | |
| completed_at | timestamptz | NOT NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

### 7.3 `users`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| email | varchar(255) | NOT NULL | UNIQUE (`ix_users_email`) |
| password_hash | varchar(200) | NOT NULL | |
| full_name | varchar(200) | NOT NULL | |
| title | varchar(200) | NULL | |
| is_active | boolean | NOT NULL | |
| failed_login_attempts | integer | NOT NULL | |
| locked_until | timestamptz | NULL | |
| last_login_at | timestamptz | NULL | |
| created_at / updated_at | timestamptz | NOT NULL | |

**Referans veren:** `action_plans.created_by_user_id`, `audit_logs.user_id`, `report_exports.requested_by_user_id`

### 7.4 `audit_logs`

| Kolon | Tip | Null | Not |
|---|---|---|---|
| id | uuid | NOT NULL | PK |
| user_id | uuid | NULL | FK → `users.id` |
| action | varchar(100) | NOT NULL | |
| entity | varchar(100) | NULL | |
| old_value / new_value | varchar(2000) | NULL | |
| ip_address | varchar(64) | NULL | |
| session_info | varchar(200) | NULL | |
| success | boolean | NOT NULL | |
| error_message | varchar(1000) | NULL | |
| created_at | timestamptz | NOT NULL | |

---

## 8. Enum Tipleri (mevcut değerleriyle)

| Enum adı | Değerler | Kullanan kolon(lar) |
|---|---|---|
| `calculation_type` | HIGHER_IS_BETTER, LOWER_IS_BETTER, RANGE_TARGET, DIRECT_SCORE, PROPORTIONAL_PENALTY, CUSTOM_FORMULA | `kpis.calculation_type` |
| `calc_rule_type` | (aynı 6 değer) | `kpi_calculation_rules.calculation_type` |
| `aggregation_method` | SUM, AVERAGE, WEIGHTED_AVERAGE, MIN, MAX, LAST_VALUE, RATIO_RECOMPUTE | `kpis.aggregation_method` |
| `target_scope_type` | COMPANY, PLANT, CHIEF, FOREMAN | `kpi_targets.scope_type` |
| `data_quality_status` | COMPLETE, MISSING, INVALID, SUSPICIOUS, DUPLICATE, NEEDS_SOURCE_CORRECTION, PENDING_RESYNC, REPROCESSED | `performance_records.data_quality_status` |
| `issue_type` | (aynı 8 değer) | `data_quality_issues.issue_type` |
| `source_system` | SYNTHETIC, SAP | `performance_records.source_system` |
| `run_source_system` | SYNTHETIC, SAP | `integration_runs.source_system` |
| `production_source_system` | SYNTHETIC, SAP | `production_records.source_system` |
| `integration_status` | RUNNING, SUCCESS, PARTIAL_SUCCESS, FAILED | `integration_runs.status` |
| `action_plan_priority` | LOW, NORMAL, HIGH, CRITICAL | `action_plans.priority` |
| `action_plan_status` | OPEN, IN_PROGRESS, ON_HOLD, COMPLETED, CANCELLED, DELAYED | `action_plans.status` |
| `report_type` | COMPANY_SUMMARY, PLANT_COMPARISON, SHIFT_COMPARISON, FOREMAN_PERFORMANCE, KPI_ANALYSIS, CRITICAL_PERFORMANCE, MISSING_DATA | `report_exports.report_type` |
| `report_format` | CSV, XLSX, PDF | `report_exports.format` |
| `report_status` | COMPLETED, FAILED | `report_exports.status` |

**Gözlem (yorum değil, olgu):** `calculation_type`/`calc_rule_type`, `data_quality_status`/`issue_type`, `source_system`/`run_source_system`/`production_source_system` üçlüsü — her biri aynı değer kümesine sahip ama Postgres'te **ayrı ayrı isimlendirilmiş enum tipleri** olarak tanımlı (her tablo kendi enum'unu SQLAlchemy `Enum(..., name=...)` ile bağımsız oluşturmuş). Fonksiyonel bir sorun yaratmıyor, yalnızca `\dT` çıktısında 15 farklı enum tipi olarak görünmesinin nedeni budur.

---

## 9. İlişki Özeti (FK grafiği, metinsel)

```
factories 1─N plants 1─N chiefs 1─N foreman_assignments N─1 foremen
                    │                        │
                    ├─N production_lines      └─N foreman_work_calendar N─1 shifts
                    │
                    └─N (chief_id,plant_id) bileşik FK ile şef-tesis tutarlılığı garanti altında

kpis 1─N kpi_calculation_rules
kpis 1─N kpi_targets (scope_type'a göre plant/chief/foreman'a serbest FK değil, scope_id UUID + uygulama seviyesi çözümleme)

products ─┐
production_lines ─┤
plants/chiefs/foremen/shifts ─┴─N production_records 1─N (production_record_id ile) performance_records 1─1 performance_scores
                                                              │                              │
                                                              └─N data_quality_issues         └─1 kpi_calculation_rules
                                                              │
                                                        N─1 integration_runs

users 1─N action_plans (opsiyonel plant/shift/foreman/kpi/chief FK'leri)
users 1─N report_exports
users 1─N audit_logs
```

---

## 10. Mevcut Veri Hacmi (introspection anındaki yaklaşık satır sayıları)

| Tablo | ~Satır | Tablo | ~Satır |
|---|---|---|---|
| performance_records | 75.298 | performance_scores | 74.929 |
| data_quality_issues | 837 | foreman_work_calendar | 14.143 |
| production_records | 13.479 | audit_logs | 1.138 |
| production_lines | 15 | kpi_targets | 72 |
| foreman_assignments | 49 | foremen | 44 |
| products | 8 | plants / chiefs | 11 / 11 |
| integration_runs | 4 | kpis / kpi_calculation_rules | 6 / 6 |
| report_exports | 18 | factories | 2 |
| shifts | 3 | users | 3 |
| company_calendar | 7 | performance_level_rules | 5 |
| action_plans | 2 | | |

---

*Bu doküman `docker compose exec postgres psql` ile çalışan veritabanına doğrudan bağlanılarak, `information_schema`/`pg_catalog` üzerinden üretilmiştir. Kod dosyalarındaki (`app/models/*.py`) tanımlarla karşılaştırma yapılmamıştır — bu, yalnızca veritabanının şu anki gerçek halinin dökümüdür.*
