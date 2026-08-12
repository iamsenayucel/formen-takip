# 8. Geliştirme ve Operasyon İş Akışı

## Git Akışı (Git Flow)
- Geliştirme süreci, kısa ömürlü özellik (feature) dalları üzerinden yürütülür.
- Koda yapılacak tüm müdahaleler Pull Request (PR) üzerinden en az 1 teknik yetkilinin (Teknik Sorumlu) onayı ve CI pipeline'ından geçmelidir.

## Dağıtım (Deployment)
- Uygulama Docker konteynerleri (Backend, Frontend, Postgres) olarak çalışır.
- Tüm stack `docker-compose` kullanılarak orkestre edilir. Yeni bir versiyon canlıya alınırken imajlar yeniden derlenir (`docker compose up --build -d`).

## Olay Müdahalesi (Incident Response)
- Beklenmedik bir hata (Örn: LLM servisi bağlantı sorunu) anında, ilgili hata log'ları backend tarafından yakalanarak kaydedilir. İlgili modül gracefully degrade edilerek uygulamanın diğer kısımlarının bozulması engellenir.
