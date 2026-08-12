# 10. Domain Süreç Tasarım Şablonu

## Üretim Verisi Ingestion Süreci
1. Dış veri sağlayıcıdan (MVP'de Sentetik Veri, İleride SAP) ham üretim verileri (Gerçekleşen Miktar, GSF, İnkıta) çekilir.
2. `PerformanceDataProvider.fetch()` yöntemiyle veriler standart bir yapıya oturtulur.
3. `ingestion.py` aracılığı ile bu kayıtlar hedef değerler ile kıyaslanarak `kpi_engine`'a gönderilir.
4. Performans skorları hesaplanıp veritabanına `performance_scores` olarak idempotent bir şekilde yazılır.
