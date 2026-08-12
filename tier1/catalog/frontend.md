# Katalog — Frontend

> Genel kural/statü tanımları `tier1/APPROVED-STACKS.md`'de.

| Kategori | Seçenek | Statü | Playbook / Referans | Not |
|---|---|---|---|---|
| Frontend framework | Next.js 16.x (App Router) | Referans | `tier1/playbooks/playbook-frontend-nextjs.md` | Backend'den bağımsız — NestJS'in yanı sıra Spring Boot/Quarkus (Java) backend'leriyle de REST üzerinden kullanılır; ayrı bir Java-özel frontend girdisine gerek görülmedi; minor/patch projenin kendi lockfile'ında (bkz. `tier1/APPROVED-STACKS.md` "Versiyon Stratejisi") |

## Değerlendirilip şimdilik eklenmeyen seçenekler

- **Angular** — Java arka planlı, büyük/regüle kurumsal ekiplerde araştırmalarda özellikle
  öne çıkan bir frontend seçeneği (TypeScript'in yapılandırılmış doğası, Angular Material
  CDK'nin olgun responsive desteği). Mevcut Next.js/React girdisi Java backend'lerle de
  kullanılabildiği için şimdilik ayrı bir satır açılmadı — ileride büyük/regüle bir Java
  projesi somutlaşırsa `tier1/APPROVED-STACKS.md` "Yeni stack ekleme süreci" ile
  değerlendirilebilir.
- **Vaadin** — Java-native UI framework'ü (frontend tamamen Java'da yazılır, ayrı JS/HTML/CSS
  gerekmez). Bu bir "frontend framework seçimi" değil, "ayrı frontend ekibi gerekmesin"
  tarzı daha büyük bir strateji kararı — kataloğa eklenmedi, ayrı bir konuşma/karar gerekir.
