# Cross-Cutting Playbook — Kimlik Doğrulama / Authentication (Zorunlu)

> `tier1/README.md`'deki yoğunluk kuralına uyar. **Stack playbook'u değil, cross-cutting
> playbook'tur.** Zorunluluğun kendisi `tier0/RULES.md` §12'de; burada yalnız **nasıl**
> uygulanacağı var. Onay: `tier0/adr/0005-centralized-authentication-mandatory.md`.
>
> **Kapsam sınırı:** Bu playbook yalnız **authentication**'ı (kullanıcının kim olduğunu
> doğrulama) kapsar. **Authorization** (kullanıcının neye yetkisi olduğu — RBAC/ABAC)
> burada değil, ilgili `tier1/playbooks/playbook-backend-*.md`'nin kendi "Yetkilendirme / İzin
> Modeli" bölümündedir — o, proje/stack içinde geliştirilir, merkezi değildir.

**Kimlik sağlayıcı:** Red Hat SSO (Keycloak tabanlı), OIDC — CoE'nin merkezi, paylaşılan
hizmeti.

---

### Kullanıcı Girişi (Authorization Code + PKCE)

**Ne:** Tarayıcı-tabanlı uygulamalar, OIDC Authorization Code flow + PKCE ile Red Hat
SSO'ya yönlendirilir; kullanıcı kimlik bilgisini uygulama değil, SSO görür.
**Neden:** Uygulama hiçbir zaman kullanıcının şifresini görmemeli/işlememeli — bu,
kendi auth implementasyonu kurmamanın doğal sonucu.
**Kural:** Login akışı her zaman SSO'ya redirect ile başlar; uygulama içinde bir
"kullanıcı adı/şifre" formu **inşa edilmez.**
**Referans:** `Uygulama İçi (Yerel) JWT Kimlik Doğrulama Mekanizması (python-jose, bcrypt)`

### Token Doğrulama

**Ne:** Gelen istekteki OIDC access token'ı (JWT), Red Hat SSO'nun public key'leriyle
imza/issuer/audience/expiry kontrolünden geçirilir.
**Neden:** Doğrulanmamış bir token'ı güvenmek, kimlik doğrulamasını fiilen atlamaktır.
**Kural:** Her korumalı endpoint, isteği işlemeden önce token'ı doğrular; doğrulama
başarısızsa 401 döner — "muhtemelen geçerlidir" varsayımıyla işlenmez.
**Referans:** `TBD`

### Servisler Arası Kimlik Doğrulama

**Ne:** Bir servis başka bir servisi çağırırken (kullanıcı bağlamı olmadan) OIDC Client
Credentials flow kullanılır.
**Neden:** Servisler arası çağrılarda kullanıcı token'ını taşımak (veya hiç doğrulama
yapmamak) yanlış güven sınırı oluşturur.
**Kural:** Servisler arası çağrılar kendi client kimlik bilgileriyle ayrı bir token alır;
kullanıcı token'ı yalnızca kullanıcı bağlamı gerçekten varsa iletilir.
**Referans:** `TBD`

> ⚠️ **Kritik:** Bir kullanıcı token'ı asla log'a/trace'e düz metin yazılmaz
> (`tier1/playbooks/playbook-observability.md`'deki PII kuralıyla aynı mantık) — token'ın kendisi
> hassas bir sırdır, kullanıcı ID'sinden farklı olarak.

### Kimlik Verisinin Kalıcılaştırılması (Persistence) Kuralı

**Ne:** Uygulama veritabanı, kullanıcıyı yalnızca SSO'nun **stabil, değişmeyen
tanımlayıcısıyla** (örn. sicil no/employee ID, OIDC `sub` claim) referanslar. Ad-soyad,
e-posta gibi **görünen** kimlik alanları veritabanına **yazılmaz** — ihtiyaç anında SSO
token'ından (veya token üzerinden erişilen HR verisinden) okunup yalnızca uygulama
arayüzünde gösterilir.
**Neden:** Bu, KVKK'nın veri minimizasyonu ilkesinin operasyonel karşılığı — bir uygulamanın
kendi DB'sinde tuttuğu her kopya, ayrı bir sızıntı/uyumsuzluk yüzeyi ve ayrı bir "bu veri ne
zaman silinecek" sorusu demektir. SSO/HR sistemi zaten bu alanların tek doğruluk kaynağı
(source of truth); isim/e-posta değişikliğinde (soyadı değişikliği, departman transferi vb.)
iki ayrı kayıt senkron kalmak zorunda kalmaz.
**Kural:**
- Herhangi bir tablo/koleksiyon, bir kullanıcıyı yalnızca stabil tanımlayıcıyla (`employee_id`
  / `sub`) ilişkilendirir; ayrı bir "users" tablosuna ad/soyad/e-posta **kopyalanıp
  saklanmaz.**
- Genel kural: **KVKK kapsamındaki kişisel veriler harici/ikincil veri depolarına**
  (analytics DB, log deposu, üçüncü-parti servis, cache vb.) **çoğaltılmaz** — tek yetkili
  kopya SSO/HR sistemindedir, uygulama yalnızca runtime'da okur.
- Bu kural `tier0/RULES.md` §4 madde 3 (Hassas Veri Koruma) ile aynı ilkenin identity-özel
  somutlaşmasıdır — orada tekrar yazılmaz, buraya referans verilir.
**Referans:** `TBD`

### Dil-Özel Enstrümantasyon (kısa referans, detay değil)

| Stack | Yaklaşım |
|---|---|
| NestJS (Node.js) | Genel OIDC/passport tabanlı bir strateji veya Keycloak-uyumlu bir guard/middleware ile token doğrulama |
| Spring Boot / Quarkus (Java) | Spring Security OAuth2 Resource Server (OIDC) / Quarkus `quarkus-oidc` — ikisi de Keycloak ile native uyumlu |
| FastAPI (Python) | `python-keycloak` veya genel bir OIDC doğrulama kütüphanesi, `Depends()` tabanlı bir dependency olarak |

Her stack'in kendi playbook'una bu tabloyu **kopyalamayın** — buraya işaret edin
(`tier1/README.md`'nin "içerik bir kez yazılır" kuralı).

### Bu Playbook'un Kapsamı Dışı

**Authorization/RBAC** — SSO yalnızca "bu kullanıcı kim" sorusunu cevaplar, "bu kullanıcı
neye yetkili" sorusunu değil. Bu ikinci soru her zaman ilgili
`tier1/playbooks/playbook-backend-*.md`'nin "Yetkilendirme / İzin Modeli" bölümünde, proje/stack
içinde geliştirilir — bkz. `tier1/catalog/backend.md` "Yetkilendirme (Authorization)"
kategorisi.
