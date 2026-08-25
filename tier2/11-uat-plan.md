# 11. Kabul Testi (UAT) Planı

## Kullanıcı Personaları

- **Üst Yönetim / Karar Destek Kullanıcısı:** OIDC ile giriş yapar; dashboard,
  tesis, formen, şef/grup, vardiya, anomaly ve rapor sonuçlarını inceler.
- **Rapor Operasyonu:** Genel ve aylık rapor üretim/erişim/teslim akışını
  doğrular.
- **İyileştirme / Anomali Operasyonu:** Operational Impact+ CRUD/PDF ve
  anomaly analiz/durum akışını doğrular.
- **IT/DevOps:** OIDC, PostgreSQL, storage, SMTP, DNS/TLS, scheduler,
  health/readiness ve secret/env yapılandırmasını kabul eder.

Bu personalar current kullanım senaryolarıdır; backend role/permission scope'u
değildir. Fine-grained RBAC deferred olduğundan tüm doğrulanmış kullanıcılar
aynı endpoint yüzeyine erişir. Rol/tesis bazlı izolasyon bu release'in UAT
kabul kriteri değildir.

## Senaryolar

1. **OIDC giriş/oturum:** Authorization Code + PKCE redirect/callback, hedef
   route'a dönüş, logout, silent renew ve süresi dolmuş/geçersiz token'da
   `401` doğrulanır. Eksik OIDC config ve production auth bypass fail-closed
   olmalıdır.
2. **Genel Bakış:** Genel skor, KPI özeti, trend, tesis/formen sıralaması,
   performans dağılımı/liderleri ve vardiya karşılaştırması aynı tarih/filtre
   kapsamında tutarlı olmalıdır.
3. **Altı KPI:** İnkita, OEE, GSF, Ağır Gitme, Plana Uyum ve Iskarta görünmeli;
   ağırlıklar `22/21/20/13/12/12` ve toplam `%100` olmalıdır.
4. **OEE:** Tek formen/vardiya için çalışma dakikası/720, tam tesis günü için
   V1+V2 çalışma dakikaları/1440 ve çok günlük pay/payda aggregation
   doğrulanmalıdır. OEE score `0..105` sınırında olmalıdır.
5. **KPI iş anlamı:** GSF geri kazanılamayan nihai kayıp, Iskarta hamura geri
   katılabilen paketlenmemiş ürün olmalıdır. İnkita yalnız teknik+imalat
   duruşunu içermeli; Plana Uyum plan üstünü olumlu, plan altını daha güçlü
   olumsuz skorlamalıdır.
6. **Tesis performansı:** Tesis listesi/sıralaması, detay, altı KPI, şef,
   formen ve V1/V2 sonuçları filtrelerle uyumlu olmalıdır.
7. **Formen performansı:** Profil, assignment history, çok tesis breakdown'u,
   KPI/trend, seviye/güvenilirlik, contribution bonusu ve aylık rapor
   tutarlı olmalıdır.
8. **Şef/Grup:** Şefin tesis grubu, bağlı formenleri, KPI/trend ve formen
   comparison matrisi doğru kapsamı göstermelidir.
9. **Vardiya analizi:** V1 `07:00–19:00`, geceyi aşan V2 `19:00–07:00`,
   haftalık rotasyon, tamamlanmış ay kart/heatmap/detail ve
   `Europe/Istanbul` tarih sınırları doğrulanmalıdır.
10. **Tespitler:** Liste/özet/detay, severity/status/analysis filtreleri,
    trend/bağlam, Hızlı/Derinlemesine analiz, active-claim `409`, demo fallback
    ve tool source geçmişi doğrulanmalıdır.
11. **Operational Impact+:** Draft/publish validation, çok formen/çok tesis,
    sistem hesaplı 1–5 puan, PDF ve son 90 gün bonusunun genel puana eklenip
    `120`'de tavanlanması doğrulanmalıdır.
12. **Raporlar:** Genel CSV/XLSX/PDF üretim/liste/indirme ve aylık formen
    snapshot/PDF/access akışı doğrulanmalıdır.
13. **Filtre ve tarihler:** Fabrika, tesis, şef, formen, vardiya, KPI,
    başlangıç/bitiş tarihi ve URL state; dashboard ve drill-down kanallarında
    aynı kapsamı üretmelidir.
14. **API contract:** Cursor liste `{data, pagination}`, camelCase JSON,
    ortak error envelope, request ID, 404/409/422/429 sonuçları OpenAPI ile
    uyumlu olmalıdır.
15. **Production startup:** Fresh PostgreSQL → tek Alembic head → uygulama
    startup; `/health`, `/health/live`, `/health/ready` `200`, frontend `/`
    `200` ve korumalı endpoint token olmadan `401` vermelidir.
16. **Production güvenliği:** HTTPS, Caddy security headers, debug kapalı,
    wildcard CORS reddi, auth bypass reddi ve secret'ların image/Git dışında
    sağlanması doğrulanmalıdır.
17. **Scheduler:** Tek instance, Europe/Istanbul cron saatleri, aylık report,
    e-posta ve stale-job logları doğrulanmalıdır.
18. **Kurumsal entegrasyon kabulü:** Gerçek Keycloak client/realm/JWKS,
    production PostgreSQL backup/restore, private S3/CloudFront, SMTP relay,
    DNS/TLS/firewall ve secret yönetimi IT ile ortam üzerinde test edilmelidir.
    Bu provizyonlar repository içinden tamamlanmış varsayılmaz.

UAT'ta kullanılan development dataset sentetiktir. Production master data ve
eski sentetik dump uyumluluğu aynı kabul kriteri değildir; gerçek veri yükleme
ayrı entegrasyon/onay planıyla yürütülmelidir.
