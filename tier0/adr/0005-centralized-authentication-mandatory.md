# ADR-0005: Kimlik doğrulama (Authentication) Red Hat SSO'ya zorunlu entegre; yetkilendirme (Authorization) proje içinde kalır

**Durum:** Kabul edildi
**Tarih:** 2026-07-14
**Karar verenler:** CoE (katalog sahibi)

> Bu bir katalog-seviyesi ADR'dir — bkz. `tier0/adr/0001-...`'deki aynı not. ADR-0001/0002/
> 0003'teki "Auth modeli" satırlarını **kısmen geçersiz kılar** — bkz. Sonuçlar.

## Bağlam

Kataloğun mevcut "Auth modeli" satırları (NestJS/Spring Boot/Quarkus/FastAPI) her stack'in
**kendi JWT'sini kendisinin ürettiğini** (access+refresh rotation) tanımlıyordu — "kurumsal
OIDC/SSO'ya açık" notuyla, yani SSO'ya bağlanmak bir opsiyondu, zorunluluk değildi.

Katalog sahibi netleştirdi: kurumda merkezi bir SSO sistemi (**Red Hat SSO**, Keycloak
tabanlı) var ve projelerin **kendi kimlik doğrulama implementasyonunu yazması
istenmiyor** — authentication SSO'ya entegre olmalı. **Authorization (RBAC/yetkilendirme)**
ise merkezi değil, her projenin/stack'in kendi içinde geliştirdiği bir şey olarak kalıyor.

Bu, kataloğun önceki "Auth modeli" satırlarının **authentication ile authorization'ı
karıştırdığını** ortaya çıkardı — düzeltilmesi gerekiyor.

## Karar

**Authentication ve authorization iki ayrı kategoriye ayrıldı:**

1. **Authentication — yeni bir Zorunlu cross-cutting konu.** Gözlemlenebilirlik ile aynı
   model: `tier0/RULES.md`'ye yeni bir §12 eklendi (aynı bağlayıcılık seviyesi);
   `tier1/playbooks/playbook-authentication.md` (Zorunlu) Red Hat SSO/OIDC entegrasyon prensiplerini
   ve dil-özel token-doğrulama SDK notlarını taşıyor. Projeler kendi kullanıcı adı/şifre
   deposu, kendi JWT issuance/refresh-rotation mantığı **kurmaz** — kimlik doğrulama
   olayının kendisi Red Hat SSO'ya devredilir (OIDC Authorization Code + PKCE, servisler
   arası çağrılarda Client Credentials).
2. **Authorization — proje/stack içinde kalır, değişmedi.** `tier1/catalog/backend.md`'deki
   satırlar `Auth modeli`'den **`Yetkilendirme (Authorization)`**'a yeniden adlandırıldı ve
   içerikleri, SSO tarafından doğrulanmış kimlik üzerine **yetki/izin kontrolü** (RBAC/ABAC,
   permission resolver, method security) tanımlayacak şekilde düzeltildi — token
   üretimi/rotasyonu artık bu satırlarda yok.
3. Her backend playbook'unun (NestJS, Spring Boot, Python FastAPI) "Kimlik Doğrulama &
   Oturum" bölümü, kendi JWT issuance açıklamasından, `tier1/playbooks/playbook-authentication.md`'ye
   işaret eden + yalnız o stack'e özel token-doğrulama detayını taşıyan bir bölüme
   düzeltildi.

## Sonuçlar

**Artılar:**
- Kurum genelinde tek bir kimlik doğrulama kaynağı — kullanıcı tek bir yerden giriş yapar,
  şifre/MFA politikası merkezi yönetilir, sızıntı riski dağınık implementasyonlara
  yayılmaz.
- Authorization'ın proje-içi kalması, her projenin kendi domain'ine özel izin modelini
  (örn. çok-kiracılı bir SaaS'ın kiracı-bazlı izinleri) esnek şekilde tanımlamasına izin
  veriyor — merkezi bir yetkilendirme motoru bu esnekliği kısıtlardı.

**Eksiler / kabul edilen riskler:**
- Bu, **geriye dönük bir düzeltme** — ADR-0001/0002/0003'teki "her stack kendi JWT'sini
  üretir" çerçevesi artık yanlış; bu üç ADR'nin kendisi güncellenmedi (tarihsel kayıt
  olarak kalıyor), ama onlara dayanan katalog satırları ve playbook'lar bu ADR ile
  düzeltildi.
- Red Hat SSO'nun gerçek entegrasyon detayları (realm/client config, token doğrulama
  endpoint'i) henüz playbook'a girilmedi — placeholder olarak bırakıldı, platform ekibi
  sağladığında doldurulmalı (gözlemlenebilirlik platformunda olduğu gibi aynı durum).

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** ADR-0001, ADR-0002, ADR-0003'teki auth
satırlarını kısmen günceller (bkz. yukarıda); ADR-0004'teki Zorunlu statü modelini
authentication'a da uygular.
