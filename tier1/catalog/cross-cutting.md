# Katalog — Cross-Cutting (Auth-N / Caching / Messaging / Gözlemlenebilirlik / API Tasarımı / Servis Entegrasyonu)

> Genel kural/statü tanımları `tier1/APPROVED-STACKS.md`'de. Bu satırlar, stack-bağımsız
> `tier1/*-playbook.md` cross-cutting dosyalarıyla birebir eşleşir (bkz. `tier1/README.md`
> "İki tür playbook" bölümü).

| Kategori | Seçenek | Statü | Playbook / Referans | Not |
|---|---|---|---|---|
| Kimlik doğrulama (Authentication) | Red Hat SSO (Keycloak, OIDC) | **Zorunlu** | `tier1/playbooks/playbook-authentication.md` | Projeler kendi auth implementasyonunu kurmaz; `tier0/RULES.md` §12; bkz. `tier0/adr/0005-...`. **Authorization/RBAC burada değil** — bkz. `tier1/catalog/backend.md` "Yetkilendirme (Authorization)" |
| Caching | Redis (AWS ElastiCache, yönetilen) | Onaylı | `tier1/playbooks/playbook-caching.md` | Cross-cutting, ihtiyaca göre — hangi projede gerekli olduğu proje-özel mimari kararı; **self-host Redis yasak**, yalnız yönetilen ElastiCache (her AWS hesabında ihtiyaca göre alınabilir); bkz. `tier0/adr/0004-...`, `0007-...` |
| Message broker | AWS SQS | Referans | `tier1/playbooks/playbook-messaging.md` | Kurumda zaten aktif kullanılıyor; cross-cutting, ihtiyaca göre; dil-özel tüketici kütüphaneleri (Celery/boto3) için bkz. `tier1/catalog/backend.md`; bkz. `tier0/adr/0004-...` |
| Gözlemlenebilirlik platformu | Prometheus + Loki + Grafana (+ Opsgenie) | **Zorunlu** | `tier1/playbooks/playbook-observability.md` | Merkezi, paylaşılan CoE platformu — proje kendi altyapısını kurmaz; `tier0/RULES.md` §11; bkz. `tier0/adr/0004-...` |
| API tasarım prensipleri | Response zarfı + hata taksonomisi + pagination + rate-limit şekli (REST) | **Zorunlu** | `tier1/playbooks/playbook-api-design.md` | Stack-bağımsız kontrat kuralları; endpoint-özel içerik burada değil, `tier2/README.md` madde 4'te; `tier0/RULES.md` §14 |
| Kurumsal sistem entegrasyonu | Ocean servis middleware'i | **Zorunlu** | `tier1/playbooks/playbook-service-integration.md` | Doğrudan app-to-app iletişim yasak; `tier0/RULES.md` §13; bkz. `tier0/adr/0006-...` |
| CI/CD & tedarik zinciri güvenliği | Statik analiz/tip güvenliği + SCA/lisans taraması + SAST | **Zorunlu** | `tier1/playbooks/playbook-cicd-security.md` | Somut ürün seçimi `TBD` — bilerek icat edilmedi (bkz. playbook'un üst notu); `tier0/RULES.md` §15 |
