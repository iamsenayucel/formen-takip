# Domain Modeli

## Organizasyon Hiyerarşisi

**Karaman (tek lokasyon) → Fabrika (K1 = 1–27. tesisler, K2 = 28–50. tesisler) → Tesis → Şef → Formen.**

Bu yapı `backend/app/services/synthetic/reference_data.py` içindeki
`FACTORY_SEED` sabitiyle kodlanmış sabit bir iş kuralıdır, yapılandırılabilir
bir parametre değildir. Tesisler `"{n}. Tesis"` biçiminde adlandırılır ve
1–50 arasında benzersiz bir `sequence_number` taşır — **tesisler her zaman
`sequence_number`'a göre sıralanmalı, `name`'e göre değil** ("10. Tesis"
alfabetik olarak "2. Tesis"ten önce gelir).

- Her tesisin tam olarak bir şefi vardır (`Plant.chief_id`), ama bir şef artık
  tek bir tesise değil, **aynı fabrika içindeki tesislerden oluşan sabit bir
  bölgeye** ("zone") sorumludur (`app/services/synthetic/reference_data.py::seed_reference_data`,
  her fabrikanın tesisleri `min_plants_per_foreman`–`max_plants_per_foreman`
  büyüklüğünde bölgelere ayrılır). Bu bölgedeki her formen (her vardiyada bir
  tane, yani bir şefin **en az 2, tipik olarak 3** formeni olur) bölgenin
  **tüm** tesislerinden sorumludur — bu yüzden bir formen hiçbir zaman birden
  fazla şefe bağlı olamaz.
- `Foreman` modeli organizasyon FK'sı taşımaz. Tüm yerleşim `ForemanAssignment`
  tablosunda SCD2 tarzı `start_date`/`end_date` aralıklarıyla tutulur: bir
  formenin şefi ve vardiyası görev süresi boyunca sabittir, yalnızca bölgesi
  ara dönemlerde değişebilir.
- `(plant_id, chief_id) → plants(id, chief_id)` bileşik yabancı anahtarı
  (`foreman_assignments`, `foreman_work_calendar` ve `production_records`
  üzerinde tekrarlanır), tesis/şef uyuşmazlığını veritabanı seviyesinde
  imkânsız kılar.
- Kimlikler benzersiz ve kendini açıklayan biçimde üretilir: ad/soyad çiftleri
  `FIRST_NAMES × LAST_NAMES` (80 × 70 = 5600 kombinasyon) kartezyen çarpımından
  **yerine koymadan** (without replacement) örneklenir, böylece ~1000 kişilik
  havuzda hiçbir şef veya formen aynı tam adı taşımaz. Şef sicil numaraları
  artık tek bir tesisi değil bölgeyi kodlar (`SEF-003`); formen sicil
  numaraları vardiyayı kodlar (`SCL-V1-014`) — ikisi de sözlüksel sıralama
  sayısal sıralamayla eşleşsin diye sıfırla doldurulur.

`docker compose exec backend python -m app.cli regenerate-personnel-identities`
komutu, mevcut şef/formen ad-soyad ve sicil numaralarını performans verisine
dokunmadan (satırlar UUID ile referans verir) yeniden üretir — isim
havuzlarını değiştirdikten sonra tam yeniden seed yerine kullanılır.

## Katkılar

Formenlerin/şeflerin ürettiği iyileştirme çalışmalarını (SMED, Kaizen, sorun
çözme vb.) kaydeden, mali kazanç doğrulaması ve PDF raporu üreten bağımsız
bir modül (`app/models/contribution.py`, `app/api/v1/contributions.py`).
Performans skorlamasıyla hiçbir bağlantısı yoktur — tamamen ayrı bir takip
tablosudur.

- `contribution_works` — başlık, tür (`ContributionWorkType`: SMED, KAIZEN,
  PROBLEM_SOLVING, ...), problem/çözüm/sonuç açıklaması, `status`
  (`ContributionStatus`: DRAFT/PUBLISHED), standardizasyon bayrakları
  (`is_standardized`, `is_applicable_other_plants`, `is_permanent_solution`,
  `work_instruction_updated`) ve mali kazanç alanları
  (`financial_gain_status`, `estimated_amount`/`verified_amount`, `currency`,
  doğrulayan departman, doğrulama tarihi/notu).
- `contribution_work_foremen` — bir çalışmaya katkı veren formenleri
  `ContributionRole` (`LEAD` / `CONTRIBUTOR`) ile ilişkilendiren çoka-çok
  tablo; tek formenli çalışmalar migration `f2a4b8e6c9d1` ile otomatik
  `LEAD` olarak işaretlenmiştir.
- `contribution_gains` — süre/verim kazancı dışındaki diğer kazanım türlerini
  (`OtherGainType`) önceki/sonraki değer ve değişim yüzdesiyle kaydeder.

`app/services/contribution_calc.py`, süre tasarrufu gibi tekrar eden
kazançları (`previous_duration`/`new_duration`, `repeat_period`,
`repeat_count`) aylık toplam tasarruf dakikasına (`monthly_total_saving_minutes`)
çevirir. `GET /{id}/pdf`, `reportlab` ile tek bir çalışmanın özet raporunu
üretir. Sentetik örnek veri `app/services/synthetic/contribution_generator.py`
ile üretilir — `seed` komutunun katkı çalışması adımı (yalnızca en az bir
kullanıcı varsa çalışır, bkz. [Kurulum](#kurulum-docker)) veya bağımsız
olarak `docker compose exec backend python -m app.cli seed-contributions`.

## Tespitler Modülü (Anomali Tespiti + Yapay Zekâ Analizi)

**Amaç:** Üretim verilerindeki olağan dışı durumları ("Ağır Gitme", "GSF",
"Iskarta", "İnkita", "Plana Uyum" KPI'larında) yöneticilere göstermek, önem
derecesi ve durumlarını takip etmek ve her tespit için isteğe bağlı bir yapay
zekâ analizi üretmek. Modül iki kademede geliştirilmiştir:

- **Aşama 1 — Sentetik Veriyle Prototip**: tüm bağlam LLM'ye tek pakette
  gönderilir (`single_context` modu, aşağıda anlatılıyor).
- **Aşama 2 — Tool Calling Destekli Analiz Ajanı**: LLM, ihtiyaç duyduğu ek
  veriyi salt-okunur backend araçlarını çağırarak kendisi toplar
  (`tool_calling` modu, [ayrı bölümde](#aşama-2--tool-calling-destekli-analiz-ajanı) anlatılıyor).

İkisinde de gerçek bir ML modeli, SAP/Ocean entegrasyonu, RAG veya vektör veri
tabanı **kullanılmaz** — tüm operasyonel veri sentetiktir.

### Sentetik tespit verisi

`app/services/synthetic/anomaly_generator.py`, gerçek makine öğrenmesi
tespitiymiş gibi davranan **24 sabit senaryodan** (13 farklı tespit türünü en
az bir kez kapsayan: vardiya bazlı sürekli düşük performans, yükselen trend,
formen bazlı sapma, ürün grubu sapması, duruş yoğunlaşması, art arda plan
altı kalma, tesis geçmişinden sapma, tesisler arası fark, eş zamanlı çoklu
KPI bozulması, tek günlük sıçrama, kronik anormallik, kritik üretim kaybı,
veri kalitesi şüphesi), K1/K2 fabrikaları arasında dengeli biçimde,
gerçek (seed edilmiş) tesis/vardiya/KPI referans verisine bağlı, birbiriyle
tutarlı sayısal veriler (gözlenen/beklenen değer, sapma oranı, vardiya
karşılaştırması, ilişkili KPI sinyalleri, ML güven skoru) üretir. Aynı
`--seed` ile her çalıştırma aynı sonucu verir (tekrar üretilebilirlik);
zaten var olan tespit kodları (`ANM-YYYY-NNNN`) atlanır, bu yüzden komutu
tekrar çalıştırmak güvenlidir:

```bash
docker compose exec backend python -m app.cli seed-anomalies --seed 42
```

(`seed` komutu bu adımı otomatik olarak son adım — `[5/5]` — olarak da çalıştırır.)

Şema (`app/models/anomaly.py`, `Anomaly` ve `AnomalyAnalysis` tabloları),
gelecekte gerçek bir ML tespit servisinin üreteceği çıktıyla aynı alanları
taşır — sentetik üretici ileride bu şemaya yazan gerçek bir servisle
değiştirilebilir, API ve frontend değişmeden kalır.

### Yapay zekâ analizi nasıl çalışır

1. Kullanıcı arayüzden "Yapay Zeka ile Analiz Et" butonuna basar →
   `POST /api/v1/anomalies/{id}/analyze`.
2. `app/services/anomaly_context.py::build_analysis_package()`, tespitin
   tüm sayısal verisini, KPI tanımını, vardiya/tesis/fabrika
   karşılaştırmalarını, ilişkili KPI sinyallerini ve **sentetik** bağlam
   öğelerini (günlük geçmiş, duruş özeti, bakım sinyalleri, ürün dağılımı,
   vardiya notları, benzer geçmiş olaylar) **tek bir JSON paketinde**
   toplar — RAG veya tool calling yoktur, LLM'nin ihtiyaç duyacağı her şey
   bu tek pakette gönderilir. Formen bilgisi isim değil sicil kodu
   (`employee_number`) ile temsil edilir.
3. `app/services/llm_service.py`, `LLM_ENABLED=true` ve `LLM_API_KEY` tanımlıysa
   OpenAI uyumlu bir `chat/completions` uç noktasına (`LLM_BASE_URL`,
   `LLM_MODEL`, `LLM_TIMEOUT_SECONDS`) sistem promptu + JSON paketiyle istek
   atar; sağlayıcı bağımsız tek bir servis katmanıdır (ileride farklı bir
   sağlayıcıya geçmek yalnızca bu dosyanın içini değiştirmeyi gerektirir).
4. LLM cevabı (veya demo fallback çıktısı) `app/schemas/anomaly_analysis.py`
   içindeki `AnalysisResult` Pydantic şemasına karşı doğrulanır. Geçersiz
   JSON, eksik alan veya zaman aşımı durumunda **en fazla bir kez** otomatik
   yeniden denenir; iki deneme de başarısız olursa analiz `failed` durumuna
   geçer ve kullanıcıya jenerik bir hata mesajı gösterilir (teknik ayrıntılar
   yalnızca backend loglarında tutulur).
5. Sonuç `anomaly_analyses` tablosuna **yeni bir satır** olarak yazılır —
   önceki analizler silinmez, arayüzde varsayılan olarak en güncel analiz
   gösterilir (`GET /{id}/analysis` ve tespit detayındaki `latest_analysis`).

### Demo modu (LLM olmadan)

`LLM_ENABLED=false` veya `LLM_API_KEY` boşsa (varsayılan durum),
`app/services/anomaly_demo_fallback.py` gerçek çıktı şemasıyla birebir aynı
şekilde, tespitin gerçek sayısal verilerine dayanan deterministik bir analiz
üretir. Uygulama asla bozulmaz. Arayüzde bu durum küçük bir
**"Demo Yapay Zekâ Analizi"** etiketiyle; gerçek LLM kullanıldığında ise
**"Yapay Zekâ Analizi"** etiketiyle belirtilir.

### Yapılandırılmış çıktı şeması

LLM'den (veya demo üreticiden) beklenen JSON şekli (`AnalysisResult`):
`executive_summary`, `verified_findings[]` (finding/evidence), `possible_causes[]`
(cause/confidence/supporting_evidence/contradicting_evidence/verification_required),
`recommended_investigations[]`, `immediate_actions[]`, `medium_term_actions[]`,
`missing_information[]`, `risk_level`, `analysis_confidence` (0–1),
`requires_human_review` (her zaman `true`), `disclaimer`. Sistem promptu
(`anomaly_context.py::SYSTEM_PROMPT`), formenleri doğrudan suçlamamayı,
doğrulanmış bulgularla varsayımları ayırmayı, her önerinin bir sorumlu birim/
öncelik taşımasını ve tüm aksiyonların yönetici onayı gerektirdiğini açıkça
şart koşar; tespit açıklaması içine sızabilecek "talimatları yok say" türü
metinlerin komut olarak yorumlanmaması için ayrı bir güvenlik notu içerir.

### Güvenlik

`LLM_API_KEY` yalnızca backend ortam değişkeni olarak okunur, frontend'e asla
gönderilmez ve repository'ye yazılmaz (`.env` `.gitignore` ile hariç tutulur).
Tüm LLM çağrıları backend üzerinden yapılır. LLM'nin veritabanına yazma,
SAP/Ocean'a işlem gönderme veya aksiyon uygulama yetkisi yoktur — yalnızca
salt-okunur bir analiz metni üretir, kullanıcı arayüzde bunu yapılandırılmış
kartlar halinde görür (ham HTML render edilmez).

### Aşama 2 — Tool Calling Destekli Analiz Ajanı

Aşama 1'in `single_context` yöntemi **kaldırılmadı** — `LLM_ANALYSIS_MODE`
ayarı veya her analiz isteğinde gönderilebilen `mode` alanı (`single_context`
| `tool_calling`) ile hangi yöntemin kullanılacağı seçilir. Frontend'de tespit
detay ekranındaki **Hızlı Analiz / Derinlemesine Analiz** seçici bu iki moda
karşılık gelir.

**Mimari akış** (`app/services/anomaly_orchestrator.py::AnomalyAnalysisOrchestrator`):

1. LLM'e başlangıçta yalnızca tespitin özeti (başlık, tesis, vardiya, KPI,
   sapma, ML güven skoru, kullanılabilir araçların açıklamaları) verilir —
   Aşama 1'deki gibi tüm bağlam paketi baştan gönderilmez.
2. Model önce kısa bir **iç araştırma planı** üretir (`investigation_plan`,
   kullanıcıya gösterilmez, `anomaly_analyses.investigation_plan` alanında saklanır).
3. Model, ihtiyaç duydukça `app/services/tools/definitions.py`'deki **11
   salt-okunur araçtan** (allowlist) birini çağırır; her çağrı Pydantic ile
   doğrulanır (geçersiz fabrika/tesis/vardiya/KPI/tarih aralığı → kontrollü
   hata), gerçek sentetik sağlayıcı katmanı çalıştırılır ve sonuç modele
   `tool_call_reference` koduyla geri gönderilir. Her çağrı bir
   `anomaly_tool_calls` satırı olarak kaydedilir (adım no, argümanlar, süre,
   dönen kayıt sayısı, hata kodu).
4. Döngü; `LLM_MAX_TOOL_CALLS`, `LLM_MAX_ANALYSIS_STEPS` veya
   `LLM_ANALYSIS_TIMEOUT_SECONDS` sınırlarından biri aşılınca ya da model
   kendiliğinden yeterli veri topladığına karar verince durur.
5. Modelden, topladığı bulgulara dayanan **nihai yapılandırılmış analiz**
   ayrıca istenir; `verified_findings`/`possible_causes` içindeki
   `source_refs`, gerçekten yapılmış `tool_call_reference` kodlarına karşı
   doğrulanır — LLM'nin uydurduğu bir referans varsa sessizce ayıklanır ve
   `analysis_limitations`'a not düşülür (bkz.
   `anomaly_orchestrator.py::_sanitize_source_refs`).

**Sentetik veri tutarlılığı** (`app/services/synthetic/world.py`): Aşama 2'nin
11 aracının hepsi, aynı birkaç temel fonksiyona (özellikle `_value_for_date`)
dayanır — hiçbir araç bağımsız/rastgele veri üretmez. "Zemin gerçeği", Aşama
1'de üretilip `anomalies` tablosuna yazılmış olan tespitlerdir: bir
(tesis, KPI) çifti için bir tespit varsa, o tespitin `observed_value`/
`expected_value`/`comparison` alanları tüm günlük seri, duruş, bakım ve
vardiya karşılaştırması detaylarının çıkış noktasıdır (`get_kpi_history` ile
`compare_shifts`'in aynı vardiya için ürettiği sayı **bit bit aynıdır**).
Tespit olmayan tesis/KPI kombinasyonları için "sağlıklı" (KPI hedefine yakın,
düşük varyanslı) bir seri üretilir. `find_similar_anomalies` gerçek seed
edilmiş `Anomaly` kayıtlarını sorgular.

**Veri sağlayıcı katmanı** (`app/services/data_providers/`): `base.py`'deki 7
soyut arayüz (`AnomalyDataProvider`, `KPIDataProvider`, `DowntimeDataProvider`,
`MaintenanceDataProvider`, `ProductDataProvider`, `ShiftDataProvider`,
`HistoricalCaseDataProvider`) bugün yalnızca `synthetic.py`'deki
`Synthetic*Provider` sınıflarıyla implemente edilir. Araçlar
(`tools/definitions.py`) bu arayüzlere karşı yazılmıştır ve verinin sentetik
mi Ocean mı olduğunu bilmez — `app/services/providers/base.py`'deki
`PerformanceDataProvider` deseniyle aynı mimari. `app/services/data_providers/__init__.py::get_data_providers()`
tek fabrika noktasıdır; gelecekte `OceanKPIDataProvider`/`MLAnomalyDataProvider`
gibi gerçek implementasyonlar eklendiğinde yalnızca bu fonksiyonun içi
değişir — araç adları, LLM şemaları ve frontend etkilenmez.

**Demo tool calling** (`app/services/anomaly_demo_tool_calling.py`):
`LLM_ENABLED=false` veya API anahtarı yokken (`LLM_DEMO_TOOL_CALLING_ENABLED=true`,
varsayılan), `tool_calling` modu tamamen devre dışı kalmaz — sabit bir araç
sırası (`compare_shifts → get_kpi_history → get_downtime_breakdown →
get_maintenance_signals → get_product_mix → find_similar_anomalies`)
**gerçekten çalıştırılır** (gerçek sentetik sağlayıcılara karşı), yalnızca
LLM'nin hangi aracı çağıracağına karar verme adımı atlanır. Nihai analiz metni
Aşama 1'in demo üreticisiyle üretilir ve gerçek tool-call kodlarıyla
ilişkilendirilir; arayüzde **"Demo Yapay Zekâ Analizi"** etiketiyle gösterilir.
Tool calling desteklemeyen bir model 400 hatası döndürürse
(`LLMToolCallingUnsupportedError`), sistem otomatik olarak `single_context`
moduna düşer ve bunu `analysis_limitations`'da belirtir.

**Genişletilmiş çıktı şeması**: Aşama 1'in `AnalysisResult` şeması korunur,
üstüne `tools_used[]` (tool_name/tool_call_id/purpose),
`data_scope` (start_date/end_date/record_count/data_quality_status) ve
`analysis_limitations[]` eklenir; `verified_findings`/`possible_causes`
öğeleri `source_refs[]` taşır. `single_context` modunda bu alanlar boş/`null`
bırakılabilir.

**Genişletilmiş analiz durum modeli** (`AnomalyAnalysisStatus`): Aşama 1'in
`not_analyzed`/`analyzing`/`completed`/`failed` değerlerine ek olarak
`queued`, `planning`, `collecting_data`, `generating_analysis`,
`completed_with_warnings` (sınırlara ulaşıldığında veya `tool_calling`→
`single_context` düşüşünde), `timed_out`, `cancelled` eklenmiştir. Orkestratör
bu durumları analiz sırasında ilerledikçe commit eder — aynı tespidi başka bir
sekmeden görüntüleyen bir kullanıcı kaba taneli ilerlemeyi görebilir.

**Araç çağrı sınırları ve önbellek**: `LLM_MAX_TOOL_CALLS` (varsayılan 10),
`LLM_MAX_ANALYSIS_STEPS` (12), `LLM_TOOL_TIMEOUT_SECONDS` (10),
`LLM_ANALYSIS_TIMEOUT_SECONDS` (60), `LLM_MAX_DATE_RANGE_DAYS` (365) — bir
araç bu tarih aralığını aşan bir istek alırsa `TOOL_VALIDATION_ERROR`
döndürür. Aynı analiz içinde aynı araç aynı parametrelerle tekrar çağrılırsa
bellek-içi önbellekten döner (yeni bir `anomaly_tool_calls` satırı oluşmaz,
tool-call sayacı artmaz). Hata kodları
(`TOOL_VALIDATION_ERROR`, `TOOL_NOT_FOUND`, `TOOL_TIMEOUT`,
`TOOL_DATA_NOT_FOUND`, `LLM_TOOL_LOOP_LIMIT`, `LLM_INVALID_STRUCTURED_OUTPUT`,
`LLM_TIMEOUT`, `LLM_PROVIDER_ERROR`) hem `anomaly_tool_calls.error_code`
hem de `anomaly_analyses.error_code` alanında saklanır; teknik ayrıntılar
kullanıcıya gösterilmez, yalnızca backend loglarında tutulur.

**Frontend**: Tespit detay ekranında "Derinlemesine Analiz" sonuçları için
ek bölümler gösterilir — **Analizde Kullanılan Veriler** (kaç araç
kullanıldığı, incelenen tarih aralığı/kayıt sayısı, veri kalitesi) ve
**Analiz Adımları** (her tool-call için sıra no, araç adı, durum, süre, dönen
kayıt sayısı; `GET /analyses/{id}/tool-calls`'tan gelir). Doğrulanmış
bulgu/neden kartlarında "Kaynak: <araç adı>" etiketiyle hangi araçtan
geldiği görülebilir. Analiz sürerken gerçek iç düşünce zinciri değil, sabit
bir aşama listesi gösterilir.

### Testler

```bash
cd backend
.venv/Scripts/python.exe -m pytest tests/unit/test_anomaly_demo_fallback.py tests/unit/test_anomaly_analysis_schema.py tests/unit/test_anomaly_orchestrator_helpers.py -q
.venv/Scripts/python.exe -m pytest tests/integration/test_anomalies.py tests/integration/test_anomaly_analysis_service.py tests/integration/test_anomaly_generator.py tests/integration/test_world.py tests/integration/test_tools.py tests/integration/test_anomaly_orchestrator.py -q
```

Aşama 1 kapsanan senaryolar: sentetik tespitlerin şemaya uygunluğu (≥20 tespit, 13
tür de temsil ediliyor, benzersiz kod, tutarlı sapma hesabı), liste/detay/
filtreleme/sayfalama uçları, başarılı LLM analizi, geçersiz JSON / eksik alan
/ zaman aşımı durumlarında yeniden deneme ve `failed` düşüşü, API anahtarı
olmadan demo fallback, çift tıklama koruması (`409`), analiz geçmişinin
korunması ve tespit durumu güncelleme.

Aşama 2 kapsanan senaryolar: sentetik veri sağlayıcılarının tutarlılığı
(`get_kpi_history`/`compare_shifts` aynı sayıyı üretir, anchor'sız
kombinasyonlar "sağlıklı" seri üretir, determinizm), her aracın başarılı
çağrı/eksik parametre/geçersiz parametre/tarih sınırı doğrulaması, orkestrasyon
(tek/çoklu tool çağrısı, maksimum araç sınırı, önbellekten dönme, bilinmeyen
araç adı, hatalı argüman, zaman aşımı, bir araç başarısız olsa bile analizin
tamamlanması, uydurma kaynak referanslarının ayıklanması, tool calling
desteklenmeyen modelde `single_context`'e düşüş), demo tool calling akışının
gerçek araçları çalıştırması ve `single_context` modunun bozulmadan çalışmaya
devam etmesi. Frontend tarafında
`frontend/scripts/smoke_test_anomalies.mjs` ve
`frontend/scripts/smoke_test_tool_calling.mjs` (Playwright) liste sayfası,
filtreleme, detay sayfası ve analiz akışını uçtan uca doğrular.