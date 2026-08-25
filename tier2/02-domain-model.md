# Domain Modeli

## Organizasyon Hiyerarşisi

CORVUS organizasyonu aşağıdaki ilişkilerle modellenir:

```text
Fabrika → Tesis → Şef/Grup
                  ↓
          Formen Ataması ↔ Vardiya
```

- `Factory`, K1/K2 fabrika üst kapsamıdır.
- `Plant`, tek fabrikaya ve tek sorumlu şefe bağlıdır. Bir şef aynı fabrika
  içindeki birden fazla tesisten oluşan grubu yönetebilir.
- `Chief`, grup/ekip yöneticisidir; kullanıcı yetkilendirme rolü değildir.
- `Foreman`, sabit organizasyon FK'sı taşımaz. Tesis, şef, vardiya anchor'ı ve
  tarih aralığı `ForemanAssignment` üzerinde tutulur.
- `Shift`, V1 (`07:00–19:00`) ve geceyi aşan V2 (`19:00–07:00`) vardiyalarını
  tanımlar. Anchor vardiya haftalık rotasyonla fiilî vardiyaya çevrilir.

Bir aktif `plant_id + shift_id` slotunda yalnızca bir aktif assignment olabilir.
Aynı slotun tarih aralıkları çakışamaz; inactive assignment'ın `end_date`
değeri bulunmalıdır ve bir formen farklı şeflere bağlanamaz. Tesis/şef bileşik
FK'sı assignment'ın tesisin gerçek şefiyle eşleşmesini sağlar.

Development/test dünyası sentetiktir. Seed sırasında geçerli herhangi bir formen
uygun slota atanabilir; sentetik formen–tesis eşleşmesinin production master
data anlamı yoktur. Seed, boş veritabanında bu constraint'lere uygun kayıt üretir.

Performans domain'i:

- `Kpi`, altı resmî metriğin tanımı ve ağırlığını taşır.
- `KpiCalculationRule`, tarihsel/geçerlilik aralıklı skor kuralıdır.
- `KpiTarget`, `FOREMAN > CHIEF > PLANT > COMPANY` önceliğinde çözülen hedeftir.
- `ProductionRecord`, vardiya seviyesindeki ham üretim ve duruş verisidir.
- `PerformanceRecord`, ham kayıttan türetilmiş KPI actual/pay/payda değeridir.
- `PerformanceScore`, tek performance kaydının uygulanan kural ve skor sonucudur.

## Operational Impact+ (Katkılar)

Operational Impact+, formenlerin iyileştirme çalışmalarını kaydeder.
`ContributionWork`; taslak/yayımlanmış durum, çalışma türü, problem–çözüm–sonuç,
standardizasyon/kalıcılık, mali kazanım ve backend tarafından hesaplanan 1–5
katkı puanını taşır.

Çoka-çok ilişkiler:

- `contribution_work_foremen`: formen ve `LEAD`/`CONTRIBUTOR` çalışma rolü.
- `contribution_work_plants`: çalışmanın etkilediği tesisler.
- `contribution_gains`: ölçülebilir ek kazanımlar.

İstemci katkı puanını belirleyemez. Yalnızca yayımlanmış, puanlı ve değerlendirme
tarihinden geriye son 90 güne düşen çalışmalar formen bonusuna katılır:

```text
genel puan = min(operasyonel puan + katkı bonusu, 120)
```

Bu hesap dashboard, formen detayı ve aylık raporda ortak servis üzerinden
kullanılır.

### Aylık formen raporları

`ForemanMonthlyReport`, tamamlanmış ay için organizasyon, atama dönemleri,
operasyonel puan, katkı bonusu, genel puan, KPI ve haftalık trend snapshot'ını
saklar. `(foreman_id, year, month)` benzersizdir.

PDF development'ta local storage'a, production akışında private S3'e yazılır;
DB yalnız metadata ve snapshot tutar. Erişim yapılandırmaya göre kısa ömürlü
CloudFront signed URL veya authenticated backend proxy ile sağlanır. Opsiyonel
SMTP işi formeni TO, dönemin son şefini CC yapar. Claim/retry/reconciliation
alanları eşzamanlı ve belirsiz gönderim durumlarını yönetir.

## Tespitler Modülü (Anomali Tespiti + Yapay Zekâ Analizi)

`Anomaly`, tesis/KPI/dönem ve opsiyonel vardiya kapsamındaki tespiti; observed,
expected, deviation, güven, severity ve iş durumuyla birlikte tutar.
`AnomalyAnalysis` analiz denemesini ve yapılandırılmış çıktıyı,
`AnomalyToolCall` ise allowlist araç çağrı geçmişini saklar.

Mevcut sentetik tespit üreticisi Ağır Gitme, GSF, Iskarta, İnkita ve Plana Uyum
senaryoları üretir. OEE resmî altıncı performans KPI'sıdır; sentetik anomaly
senaryo setine henüz eklenmemiştir.

### Sentetik tespit verisi

`backend/app/services/synthetic/anomaly_generator.py`, seed edilmiş gerçek referans
kimliklerine bağlı deterministik anomaliler üretir. Bu kayıtlar gerçek ML
çıktısı değildir; 13 senaryo ailesi, filtreleme, trend, severity ve analiz
akışlarının development/test doğrulaması içindir.

`AnomalyDataProvider` ve ilgili KPI/duruş provider arayüzleri sentetik kaynakla
uygulanır. Gerçek Ocean/ML sağlayıcıları henüz uygulanmamıştır.

### Yapay zekâ analizi nasıl çalışır

Kullanıcı Hızlı veya Derinlemesine analiz başlatabilir:

1. Backend anomaliyi ve doğrulanmış bağlamı yükler.
2. Aynı anomali için aktif claim varsa ikinci istek `409` alır.
3. `single_context` modunda hazırlanmış bağlam tek istekte modele gönderilir.
4. `tool_calling` modunda model yalnızca tanımlı, salt-okunur allowlist araçlarını
   çağırabilir.
5. Çıktı Pydantic şemasıyla doğrulanır; geçersiz kaynak referansları temizlenir.
6. Sonuç ve çağrı izi saklanır; hata durumunda kontrollü status/error code üretilir.

LLM SQL üretemez, DB'ye yazamaz ve serbest bir backend fonksiyonu çağıramaz.

### Demo modu (LLM olmadan)

`LLM_ENABLED=false` veya API anahtarı bulunmayan desteklenen demo
yapılandırmasında backend deterministik, şema uyumlu bir demo analizi üretir.
Bu fallback production entegrasyonu olarak değil development/UAT kolaylığı
olarak değerlendirilir.

### Yapılandırılmış çıktı şeması

Analiz sonucu; doğrulanmış bulgular, olası nedenler, araştırma adımları, acil ve
orta vadeli aksiyonlar, risk/güven seviyeleri, kullanılan araç referansları ve
disclaimer alanlarından oluşur. Public JSON alanları camelCase serialize edilir.

### Güvenlik

- LLM anahtarı yalnız backend environment'ında tutulur.
- Tool calling araçları salt-okunur ve allowlist'tedir.
- Tarih aralığı, entity kimliği ve çağrı/adım sayısı sınırları backend'de
  doğrulanır.
- Analiz ve durum mutasyonları OIDC subject'iyle audit edilir.
- Tool çıktıları sentetik operasyonel veri içindir; gerçek production verisinde
  saklama/minimizasyon politikası deployment öncesi ayrıca değerlendirilmelidir.

### Aşama 2 — Tool Calling Destekli Analiz Ajanı

Aşama 2; KPI geçmişi, vardiya/fabrika karşılaştırması, duruş kırılımı, ilişkili
sinyaller ve benzer tespitler gibi kaynakları backend servislerinden getirir.
Araç çıktıları aynı provider/service hesaplarını kullandığı için ekran, API ve
analiz bağlamı arasında sayı parity'si korunur. `single_context` modu geriye
dönük desteklenmeye devam eder.

### Testler

Unit ve integration testleri; sentetik determinizm, provider parity, analiz
şeması, demo fallback, tool allowlist/validation, concurrency claim'i, timeout,
yeniden analiz, geçmişin korunması, timezone sınırı ve API error contract'ını
kapsar. Güncel test özeti `07-testing.md` içindedir.
