# 6. Güvenlik ve Uyum Uygulama Notu

## Kimlik Doğrulama
- Sistem JWT tabanlı (access ve refresh token) kimlik doğrulama kullanır (`python-jose`).
- Şifreler PostgreSQL veritabanında `bcrypt` ile hashlenerek saklanır.
- Kullanıcı verileri dışarı açılmaz, yetkilendirme (role-based) backend'de gerçekleşir.

## API ve Entegrasyon Güvenliği
- **LLM Entegrasyonu**: AI Tespitler modülünde kullanılan OpenAI API anahtarı sadece backend ortam değişkenleri (`.env`) üzerinden okunur. Frontend'e hiçbir şekilde gönderilmez veya repoya commit edilmez.
- **CORS**: Yalnızca frontend uygulamasının (varsayılan 8080/8099) backend'e erişebilmesi için FastAPI tarafında CORS kısıtlamaları aktiftir (`CORS_ORIGINS`).

## Veri Gizliliği
- Sistem tamamen kurum içi (VPN) kullanım için tasarlanmıştır. Dış dünyaya açık (public) endpoint bulunmamaktadır.
- Forman ve Şef gibi kişisel sicil numaraları ve verileri, doğrudan dış LLM servislerine ham haliyle gitmemeli, anonimleştirilmelidir.
