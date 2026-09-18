# 8. Geliştirme ve Operasyon İş Akışı

## Git Akışı (Git Flow)

`.github/workflows/` altında backend/frontend lint+test CI'ı ve statik
güvenlik taraması vardır (bkz. [07-testing.md](07-testing.md)), ancak bunun
PR merge'ini fiilen bloklaması GitHub *Branch protection*'da required status
check seçilmesine bağlıdır — repository kendi başına branch/approval
politikasını enforce etmez. Ekip, kısa ömürlü feature branch ve kontrollü
review yaklaşımını kurumsal Git politikasına göre uygulamalıdır.

Bir değişikliğin minimum doğrulama akışı:

```text
clone
→ .env.example'dan environment config
→ PostgreSQL
→ alembic upgrade head
→ yalnız development/test için boş DB seed
→ backend + frontend
→ backend tests
→ frontend lint/typecheck/build/audit
→ Docker production build/smoke
```

### Doküman Kontrol Listesi (Migration / Domain Değişikliği PR'ları)

- [ ] Migration/model/constraint değiştiyse `03-data-schema.md` güncel mi?
- [ ] KPI/formül/ağırlık/hedef değiştiyse `01`, `03`, `07`, `10`, `11` tutarlı mı?
- [ ] Endpoint veya schema değiştiyse OpenAPI ve `04-api-catalog.md` güncel mi?
- [ ] Frontend route/ekran değiştiyse `05-screen-catalog.md` güncel mi?
- [ ] Authentication/security/deployment değiştiyse `06-security.md` güncel mi?
- [ ] Yeni davranış unit/integration testlerle kapsandı mı?
- [ ] Seed yalnız boş DB kuralını ve DB constraintlerini koruyor mu?

Kod ve migration source of truth'tur; Tier2 current-state dokümanı aynı PR
içinde senkron tutulmalıdır.

## Dağıtım (Deployment)

Compose rolleri:

- `docker-compose.yml`: backend, frontend ve off-by-default scheduler profili.
- `docker-compose.db.yml`: aynı-host PostgreSQL.
- `docker-compose.dev.yml`: yerel Keycloak/development overlay'i.
- `docker-compose.prod.yml`: restart policy ve Caddy HTTPS edge.

Development ve production overlay'leri birlikte kullanılmaz. Backend image
başlangıcında `alembic upgrade head` çalıştırır; production'da sentetik seed
çalıştırılmaz. Frontend backend upstream ve OIDC değerlerini runtime'da render
eder. Caddy public `80/443` girişidir; frontend/backend/DB varsayılan olarak
loopback veya private ağda kalır.

Scheduler `--profile scheduler` ile açılır ve tek instance olmalıdır:

| İş | Europe/Istanbul zamanı |
|---|---|
| `reconcile-stale-jobs` | Her 15 dakika |
| `generate-monthly-reports` | Ayın 1'i 02:00 |
| `send-monthly-report-emails` | Ayın 1'i 03:00 |

### Üretimden performans puanına

`production_records` → KPI pay/payda türetimi → assignment/target/rule çözümü →
`performance_records`/`performance_scores` → dönemsel agregasyon → altı KPI
skoru → ağırlıklı geometrik toplam → tesis/formen/şef/vardiya/dashboard.

Vardiya OEE `working_time/720`, tam tesis günü OEE iki vardiyanın toplam
çalışma süresi/`1440` oranıdır.

### Operational Impact+ ve rapor teslimi

Operational Impact+ draft/publish → backend 1–5 katkı puanı → yayımlanmış son
90 gün bonusu → `min(operasyonel + bonus, 120)` genel puanı.

Aylık rapor: tamamlanmış ay snapshot'ı → PDF → local development/private S3 →
CloudFront signed URL veya authenticated proxy → opsiyonel SMTP. Genel
CSV/XLSX/PDF export'ları `report_exports` içinde ayrı akıştır.

## Olay Müdahalesi (Incident Response)

- `/health/live` process liveness; `/health/ready` PostgreSQL readiness
  kontrolüdür.
- OIDC/config hatası fail-closed startup veya `401` olarak ele alınır.
- LLM yoksa desteklenen demo analiz, CloudFront yoksa authenticated proxy,
  SMTP kapalıysa gönderimsiz çalışma uygulanır.
- `reconcile-stale-jobs`, takılı anomaly claim'lerini ve belirsiz e-posta
  durumlarını operasyonel incelemeye taşır.
- Scheduler ikinci instance ile ölçeklenmemelidir; dağıtık lock yoktur.
- Merkezi metrics/tracing/alerting repository'de uygulanmamıştır; production
  runbook ve alarm sahipliği IT tarafından tamamlanmalıdır.
