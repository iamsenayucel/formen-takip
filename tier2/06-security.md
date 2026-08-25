# 6. Güvenlik ve Uyum Uygulama Notu

## Kimlik Doğrulama (Authentication) — "Kullanıcı kim?"

CORVUS kimlik otoritesi Red Hat SSO/Keycloak uyumlu OIDC sağlayıcısıdır.

Frontend:

- Authorization Code + PKCE kullanır; implicit flow yoktur.
- `oidc-client-ts` ve `react-oidc-context` token yaşam döngüsünü yönetir.
- Session state `sessionStorage` içindedir; automatic silent renew aktiftir.
- Issuer/client ID eksikse uygulama fail-closed config ekranı gösterir.
- Runtime OIDC ayarları production image'ına gömülmez, container başlangıcında
  `/config.js` içine render edilir.

Backend:

- Kendi kullanıcı/parola sistemi veya JWT üretimi yoktur; OIDC resource
  server olarak bearer access token doğrular.
- Discovery/JWKS üzerinden anahtar alınır ve `kid` rotasyonunda cache
  yenilenir.
- JWT signature, issuer, audience, expiration (`exp`) ve issued-at (`iat`)
  doğrulanır.
- Eksik/geçersiz/süresi dolmuş token standart `UNAUTHORIZED` envelope'u ile
  `401` döndürür.
- Yerel `users` tablosu yoktur. Audit ve mutasyon kayıtları yalnız stabil OIDC
  subject claim'ini (`sub` varsayılanı) saklar.

Development bypass iki tarafta ayrıca açılır. Backend `AUTH_BYPASS=true`
değerini yalnız tam olarak `ENVIRONMENT=development` için kabul eder;
production veya diğer ortamlar başlangıçta reddedilir.

Production config fail-closed kuralları:

- `OIDC_ISSUER_URL` ve `OIDC_AUDIENCE` zorunludur.
- `DEBUG=true` reddedilir.
- `CORS_ORIGINS` içinde `*` reddedilir.
- `AUTH_BYPASS=true` reddedilir.

## Yetkilendirme (Authorization) — "Bu kullanıcı bu aksiyonu yapabilir mi?"

Authentication mevcuttur. Fine-grained backend RBAC ve endpoint permission
enforcement bu release için bilinçli olarak uygulanmamıştır ve blocker değildir.
Doğrulanmış OIDC kullanıcıları aynı `/api/v1` endpoint yüzeyine erişir;
`require_role`/`require_permission` benzeri dependency yoktur.

Gelecek sürüm roadmap'inde değerlendirilecek rol adları:

```text
reader
report-operator
contribution-editor
anomaly-analyst
admin
```

Bu adlar mevcut backend tarafından enforce edilen roller değildir. Katkı
domain'indeki `LEAD`/`CONTRIBUTOR` değerleri kullanıcı RBAC rolü değil,
çalışmadaki formen sorumluluğudur.

Mutasyonların OIDC subject ve request ID ile `audit_logs` tablosuna yazılması
izlenebilirlik sağlar; authorization kontrolünün yerine geçmez.

## API ve Entegrasyon Güvenliği

- CORS yalnız açıkça tanımlı origin'lere izin verir; CORS authentication
  mekanizması değildir.
- Her response bir request ID taşır; hata body'leri iç exception detayını
  production istemcisine sızdırmayan ortak envelope kullanır.
- Rapor/PDF ve analiz gibi pahalı endpointlerde process-local rate limit
  uygulanır.
- LLM anahtarı yalnız backend secret/environment'ından okunur. Tool calling
  salt-okunur allowlist, parametre/tarih/adım sınırlarıyla çalışır; model SQL
  veya keyfi fonksiyon çalıştıramaz.
- Aylık PDF için S3 provider `AES256` server-side encryption ister.
  Production rapor storage kullanımı S3/bucket eksikliğinde fail-closed'dur.
- CloudFront tam yapılandırılırsa kısa ömürlü signed URL, aksi durumda bearer
  token gerektiren backend proxy kullanılır.
- SMTP isteğe bağlı STARTTLS ve credential destekler. Claim/reconciliation
  modeli belirsiz gönderim sonucunda otomatik çift gönderimi sınırlar.

Caddy production edge'de HTTPS'i sonlandırır ve şu başlıkları ekler:

```text
Strict-Transport-Security: max-age=31536000
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Frame-Options: DENY
```

Frontend, backend ve aynı-host PostgreSQL varsayılan olarak `127.0.0.1` veya
private Compose ağı arkasında kalır; public giriş noktası Caddy'dir.

## Veri Gizliliği

- `.env`, token, dump ve secret dosyaları Git'e alınmaz; yalnız `.env.example`
  şablonları versiyonlanır.
- SSO profilinin yerel kullanıcı kopyası tutulmaz. Formen/şef iletişim alanları
  operasyonel domain master data'sıdır ve SSO profili değildir.
- LLM bağlamında personel mümkün olduğunda sicil/teknik referansla temsil edilir.
- Mevcut development/test veri seti sentetiktir; gerçek üretim verisi için
  saklama süresi, erişim, maskeleme ve KVKK sınıflandırması deployment
  tasarımında ayrıca onaylanmalıdır.
- Gerçek DNS/TLS, firewall/VPN, Keycloak, S3/CloudFront, SMTP ve secret manager
  uygulaması repository dışı production UAT kapsamındadır.

Backend RBAC durumu:

```text
DEFERRED — accepted product decision, planned for future release.
```
