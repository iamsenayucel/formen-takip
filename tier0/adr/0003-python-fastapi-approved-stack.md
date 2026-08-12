# ADR-0003: Python backend'inde FastAPI onaylı; ML serving ve görev kuyruğunda birden fazla onaylı seçenek, kesin karar verilmedi (bilinçli olarak)

**Durum:** Kabul edildi
**Tarih:** 2026-07-14
**Karar verenler:** CoE (katalog sahibi) + ilgili teknik ekip(ler)

> Bu bir katalog-seviyesi ADR'dir — bkz. `tier0/adr/0001-...`'deki aynı not.

## Bağlam

Kurumda Python; AI/LLM orkestrasyonu, ileri analitik, matematiksel optimizasyon, data/ML
süreçleri ve IoT ekiplerinin MQTT işleri için zaten aktif kullanılıyor. API sunma
ihtiyacında FastAPI kullanılmış ama bunun en güçlü/doğru seçim olup olmadığı netleşmemişti.
Bu ADR, kataloğa ilk Python girdisini eklerken şu iki soruyu netleştiriyor: (1) genel API
katmanı için FastAPI hâlâ doğru mu, (2) FastAPI'nin **gerçek model inference** için mimari
olarak uygun olup olmadığı.

Ayrıca katalog sahibi bilinçli bir kapsam kararı verdi: bu alan (özellikle ML serving ve
görev kuyruğu) **strict olmasın** — teknik ekip, proje bazında seçenekleri değerlendirip
kendi kararını versin. Bu, Spring Boot/Quarkus kararındaki (ADR-0002) aynı ilkenin burada
da uygulanmasıdır.

## Değerlendirilen Seçenekler

**Genel API/orkestrasyon katmanı:**
1. **FastAPI** — async-first, Pydantic v2 native, güçlü OpenAPI desteği, AI/LLM backend
   orkestrasyon işlerine özellikle uygun bulunuyor.
2. **Litestar** — sentetik benchmark'larda (msgspec tabanlı) daha hızlı, ama ekosistem/işe
   alım riski daha yüksek.
3. **Django REST Framework** — CRUD-ağırlıklı, admin-panel gerektiren ürünler için güçlü,
   ama bu kurumun Python kullanım profiline (AI/analitik/ML) daha az uygun.

**ML model serving (gerçek inference, FastAPI'nin mimari olarak zayıf olduğu alan):**
1. **BentoML** — adaptif batching ile event-loop bloklama sorununu çözer; scikit-learn/
   PyTorch/TensorFlow/XGBoost geniş destek; tek makinede de çalışabilir, dağıtık cluster
   şart değil.
2. **Ray Serve** — dağıtık/büyük ölçekli hesaplama ve geniş MLOps ekosistemi (MLflow, ONNX,
   Seldon Alibi) entegrasyonu için daha güçlü, ama operasyonel karmaşıklığı daha yüksek.

**Async görev kuyruğu:**
1. **arq** — FastAPI'nin async event loop'una native uyum, LLM API çağrıları için
   önerilir — **ama yalnızca Redis destekliyor.**
2. **Celery (SQS broker ile)** — kurumun zaten kullandığı **AWS SQS** ile doğrudan uyumlu;
   daha eski/senkron kökenli ama çok-broker desteği olgun.
3. **boto3 + doğrudan SQS tüketici döngüsü** — framework'süz, en basit; küçük ölçekli
   işler için Celery'nin operasyonel yükünü gerektirmeyebilir.

## Karar

- **Genel API katmanı:** Seçenek 1 (FastAPI) — `Referans` statüsünde onaylandı. Gerekçe:
  kurumun mevcut kullanımıyla uyumlu, AI/LLM işlerine özellikle uygun, geniş ekosistem.
- **ML model serving:** **Kesin bir karar verilmedi — hem BentoML hem Ray Serve `Onaylı`
  statüsünde kataloğa eklendi.** Katalog sahibinden gelen bağlam (Jupyter notebook ile
  keşif çalışması + ayrı bir ticari OR/optimizasyon aracı kullanımı — IBM'in bir operasyon
  araştırması ürünü, tam adı netleşmedi) mevcut ihtiyacın dağıtık/büyük-ölçekli mi yoksa
  tek-makine mi olduğunu netleştirmeye yetmedi. Final seçim, projenin somut ölçek/dağıtık
  hesaplama ihtiyacına göre Faz 2'de teknik ekip tarafından yapılır.
- **Async görev kuyruğu:** **arq elenmiştir** (kurumun mevcut SQS altyapısıyla uyumsuz —
  Redis-only). Bunun yerine Celery (SQS broker) ve boto3+doğrudan-SQS-tüketici, ikisi de
  `Onaylı` statüsünde eklendi; final seçim projenin karmaşıklığına göre Faz 2'de yapılır.
- **MQTT/IoT:** aiomqtt, `Onaylı` — 2026'nın async Python MQTT standardı, paho-mqtt'nin
  kanıtlanmış motorunu kullanıyor.
- **Paket yönetimi:** uv, `Onaylı` — pip'ten 10-100x, Poetry'den ~10x hızlı; PyPI
  kütüphane-ağırlıklı kullanım göz önüne alındığında performans farkı somut.

**Kapsam dışı bırakılan (bilinçli):** Matematiksel/OR optimizasyon aracı (IBM ürünü)
kataloğa bir "stack seçimi" olarak eklenmedi — bu, zaten kurulu/kullanılan bir ticari
kütüphane/araç tercihi, CoE governance'ının stack-seviyesi kararlarından farklı bir kategori.

## Sonuçlar

**Artılar:**
- Python ekipleri artık kataloğ-dışına çıkmadan, gerçek kullanım profillerine (API +
  ML serving + IoT) uygun onaylı seçenekler kullanabilir.
- FastAPI'nin model-inference için mimari sınırı açıkça belgelendi — bir proje "FastAPI
  içinde ağır model tahmini çalıştırayım" diye yanlış bir karar vermeden önce bunu görür.
- arq'nin mevcut SQS altyapısıyla uyumsuz olduğu, kataloğa eklenmeden önce yakalandı.

**Eksiler / kabul edilen riskler:**
- ML serving ve görev kuyruğu kategorilerinde kesin bir "kazanan" yok — bu, Faz 2'de her
  seferinde ek bir bağlam-toplama adımını zorunlu kılıyor, atlanabilir değil.
- Hem BentoML hem Ray Serve, hem Celery hem boto3-direct için henüz doldurulmuş bir
  `tier1/*-playbook*.md` yok (`Statü: Onaylı` bunu zaten öngörüyor) — ilk kullanan proje
  dolduracak/doldurtacak.

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** Mevcut Veritabanı (PostgreSQL) ve
Infra/IaC (Terraform + AWS) girdileriyle değişmeden uyumludur.
