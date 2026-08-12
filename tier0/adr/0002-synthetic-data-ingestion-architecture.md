# 2. Sentetik Veri Üretimi ve Ingestion Mimarisi

Tarih: 2026-08-09
Durum: Kabul Edildi

## Bağlam (Context)
Geliştirme ve gösterim (MVP/Demo) aşamasında, gerçek SAP veya Ocean verilerinin yokluğunda sistemi besleyecek gerçekçi bir veri setine ihtiyaç vardır.

## Karar (Decision)
Veritabanını beslemek için `SyntheticDataProvider` üzerinden sentetik üretim kayıtları (KPI, GSF, İnkıta vb.) üretilecek ve asıl Ingestion süreci gerçek bir dış veri kaynağı (SAP) varmış gibi bu sentetik kayıtları okuyarak puan hesaplaması yapacaktır.

## Sonuçlar (Consequences)
- **Artılar:** Gerçek veri kaynağı entegrasyonu tamamlanmadan uygulamanın tam işlevsel olarak test edilebilmesi. Veri akışı katmanının (ingestion) bağımsız kalması.
- **Eksiler:** Sentetik verilerin her senaryoyu tam yansıtamama ihtimali.
