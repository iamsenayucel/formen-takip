# 3. LLM Destekli Tespitler ve Anomali Modülü

Tarih: 2026-08-09
Durum: Kabul Edildi

## Bağlam (Context)
Üretim verilerindeki sapmaları yorumlamak ve olası kök nedenleri yöneticilere sunmak için bir analiz mekanizmasına ihtiyaç vardır.

## Karar (Decision)
Yapay zeka (LLM) kullanılarak üretim verilerinin analiz edilmesi ve tespit kartları (Anomaly Analysis) oluşturulması kararlaştırıldı. LLM çağrıları backend üzerinden (OpenAI veya alternatif sağlayıcılar) yapılacak ve Tool Calling mekanizması (Aşama 2) ile LLM'in ihtiyaç duydukça veriyi kendi okuması sağlanacaktır.

## Sonuçlar (Consequences)
- **Artılar:** Yöneticilere salt veri yerine yorumlanmış, eyleme dönüştürülebilir öngörüler sunulması.
- **Eksiler:** LLM sağlayıcılarına olan bağımlılık ve olası maliyetler/zaman aşımı riskleri. LLM'e giden prompt'ların yönetimi.
