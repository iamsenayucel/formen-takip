# 10. Domain Süreçleri

## Üretim Verisi Ingestion Süreci

1. Development/test ortamında sentetik generator fabrika, tesis, şef, formen,
   V1/V2 assignment, ürün, hat, takvim ve vardiya seviyesinde ham
   `production_records` üretir. Gerçek SAP provider henüz uygulanmamıştır.
2. KPI derivation ham kayıttan altı KPI'nın actual/pay/payda bileşenlerini
   çıkarır:
   - GSF: geri kazanılamayan nihai kayıp.
   - Iskarta: paketlenmeyen fakat hamura geri katılabilen ürün.
   - İnkita: teknik+imalat duruşu; diğer duruş hariç.
   - Ağır Gitme: kabul gramaj aralığı dışındaki işaretli sapma.
   - Plana Uyum: gerçekleşen/güncel plan; plan üstü olumlu, plan altı daha
     güçlü olumsuz.
   - OEE: vardiya çalışma dakikası/720.
3. Ingestion entity kodlarını FK'lara, tarihi geçerli formen assignment'a ve
   haftalık fiilî vardiyaya çözer. Hedef önceliği
   `FOREMAN > CHIEF > PLANT > COMPANY`'dir; calculation rule tarih aralığına
   göre seçilir.
4. `performance_records` ve bire-bir `performance_scores`, kaynak/doğal
   anahtarlarla idempotent yazılır; duplicate ve kalite sorunları izlenir.
5. Analitik servisler dönem için pay/paydayı yeniden toplar. Formen çok
   tesisliyse aynı KPI'nın tesis skorları eşit ağırlanır.
6. Altı KPI skoru güncel `22/21/20/13/12/12` ağırlıklarıyla geometrik
   birleştirilir ve tesis/formen/şef/vardiya/dashboard/rapor kanallarına sunulur.
7. Anomaly üretimi/tespiti ayrı akışta sonuçları analiz eder; mevcut sentetik
   senaryo üreticisi OEE dışındaki beş KPI'yı kapsar.

V1 `07:00–19:00`, V2 `19:00–07:00`'dir. V2 geceyi aşar; iş günü ve rotasyon
`Europe/Istanbul`, kalıcı timestamp'ler UTC mantığıyla işlenir. Tam tesis günü
OEE iki vardiyanın çalışma dakikaları toplamı/1440 olarak agregasyonla oluşur.

## Operational Impact+ Süreci

1. OIDC ile doğrulanmış kullanıcı draft çalışma oluşturur; formen(ler), tesis(ler),
   tür, problem, çözüm, sonuç, etki ve kazanım alanlarını girer.
2. Publish validation zorunlu alanları ve domain kurallarını kontrol eder.
3. Backend etki, kapsam, kalıcılık/standardizasyon ve ölçülebilir sonuçtan 1–5
   `contribution_score` hesaplar; istemci override edemez.
4. Yalnız yayımlanmış, puanlı ve son 90 güne düşen çalışmalar ilgili formenlerin
   bonusuna girer.
5. Dashboard, formen ve rapor kanalları ortak formülü kullanır:

```text
genel puan = min(operasyonel puan + bonus, 120)
```

Create/update/delete/PDF eylemleri OIDC subject'iyle audit edilir.

## Aylık Rapor Üretim ve Teslim Süreci

1. Scheduler tamamlanmış ay için eksik formen raporlarını idempotent üretir.
2. Organizasyon/assignment, operasyonel skor, bonus, genel skor, KPI ve trend
   snapshot'ı `(foreman, year, month)` benzersizliğiyle saklanır.
3. PDF development'ta local, production'da private S3 object storage'a yazılır.
4. CloudFront yapılandırılmışsa kısa ömürlü signed URL; değilse authenticated
   backend proxy sağlanır.
5. SMTP etkinse PDF formene TO, dönemin son şefine CC gönderilir.
6. Claim/retry alanları concurrency'yi; stale-job reconciliation belirsiz
   analiz/e-posta durumlarını yönetir.

Genel CSV/XLSX/PDF export akışı aylık formen raporundan ayrıdır ve
`report_exports` modelini kullanır.
