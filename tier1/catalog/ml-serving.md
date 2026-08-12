# Katalog — ML Model Serving

> Genel kural/statü tanımları `tier1/APPROVED-STACKS.md`'de. Her projeye değil, özellikle
> gerçek model inference'ı (tahmin) çalıştıran projelere uygulanır — bkz.
> `tier1/playbooks/playbook-backend-python-fastapi.md`'deki "FastAPI'nin kapsamı dışı" notu (FastAPI
> compute-ağırlıklı model tahmini için mimari olarak uygun değildir).

| Kategori | Seçenek | Statü | Playbook / Referans | Not |
|---|---|---|---|---|
| ML model serving | BentoML | Onaylı | `tier1/playbooks/playbook-backend-python-ml-serving.md` (TBD) | Tek makine/orta ölçek; FastAPI'nin event-loop bloklama sorununu adaptif batching ile çözer; bkz. `tier0/adr/0003-...` |
| ML model serving | Ray Serve | Onaylı | `tier1/playbooks/playbook-backend-python-ml-serving.md` (TBD) | Dağıtık/büyük ölçekli hesaplama + geniş MLOps ekosistemi (MLflow, ONNX); bkz. `tier0/adr/0003-...` |

## Aynı kategoride birden fazla onaylı seçenek varsa

**ML model serving (BentoML vs Ray Serve, bkz. `tier0/adr/0003-...`):** Bu kategoride
katalog sahibi **bilinçli olarak** kesin karar vermedi — soru: proje tek makinede mi
çalışacak yoksa dağıtık/çoklu-GPU bir ölçek mi gerekiyor? Agent Faz 2'de bunu sormadan
öneri yapmaz. Belirsizse (örn. "Jupyter'da prototip yaptık ama üretim ölçeği netleşmedi"),
agent varsayılan olarak BentoML'i önerebilir (daha düşük operasyonel karmaşıklık) ama bunu
açıkça "ölçek netleşince gözden geçirin" notuyla sunar.
