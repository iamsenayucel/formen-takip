# Katalog — Infra / IaC

> Genel kural/statü tanımları `tier1/APPROVED-STACKS.md`'de. Onay: `tier0/adr/0007-...`.

## Hesap Modeli

Kurum, **departman bazında ayrı AWS hesapları** işletir — tek bir global hesap grubu değil.
Her departmanın kendi hesap grubu içinde ortam (dev/staging/prod) ayrımı sürer; bu, önceki
"3-hesap izolasyonu" modelinin departman bazında tekrarlanmasıdır (bkz.
`tier1/playbooks/playbook-infra-terraform-aws.md` "Hesap Modeli" bölümü, detay orada).
Departmanlar arası doğrudan kaynak erişimi yoktur.

## Katalog

| Kategori | Seçenek | Statü | Playbook / Referans | Not |
|---|---|---|---|---|
| IaC aracı | Terraform | Referans | `tier1/playbooks/playbook-infra-terraform-aws.md` | Stack'ten bağımsız, tüm compute seçeneklerinde ortak |
| Compute | ECS Fargate | Referans (varsayılan) | `tier1/playbooks/playbook-infra-terraform-aws.md` | Kubernetes gerçekten gerekmiyorsa kullanılır; AWS-yönetimli, versiyon pinlenmez |
| Compute | EKS (Kubernetes) | Onaylı | `tier1/playbooks/playbook-infra-terraform-aws-eks.md` | Yalnız gerçek K8s ihtiyacı varsa (örn. Quarkus'un hızlı-açılış avantajı, çok sayıda bağımsız servis) — her hesapta zorunlu değil; AWS-yönetimli, versiyon pinlenmez |
| Compute | On-Premise / Fabrika-İçi Edge Server | Onaylı — **istisna/son çare** | — (TBD, gerçek ihtiyaç çıkarsa ayrı stack-analizi) | Datacenter'da Kubernetes yok; yalnız gerçekten zorunlu olduğunda (örn. yerel ağ kesintisinde de çalışması gereken saha sistemi), varsayılan asla değil |
| Object storage | S3 (private) | Zorunlu (kullanılıyorsa) | `tier1/playbooks/playbook-infra-terraform-aws.md` | Her hesapta hazır; public bucket yasak — public erişim gerekiyorsa CloudFront+signed URL üzerinden |
| Kuyruk | SQS | Zorunlu (kuyruk ihtiyacı varsa) | `tier1/catalog/cross-cutting.md`, `tier1/playbooks/playbook-messaging.md` | Her hesapta hazır; proje kendi kuyruk altyapısını kurmaz |
| Secret yönetimi | AWS Secrets Manager | Zorunlu | `tier1/playbooks/playbook-infra-terraform-aws.md` | Her hesapta hazır; `.env`/kod-içi sır yasak |
| API katmanı | API Gateway | Onaylı | `tier1/playbooks/playbook-infra-terraform-aws.md` | Her hesapta hazır; internet/internal ayrımı `tier0/RULES.md` §13 madde 4 |
| Bağımsız PaaS (MVP/POC) | Railway, Vercel vb. | **Değerlendirmede** | — | Kurumsal AWS ortamlarından tamamen bağımsız; henüz onaylanmadı, seçenek olarak sunulmaz |

## Cloud Vendor Sınırı

**Yalnız AWS.** Azure kurumda başka amaçlarla kullanılıyor ama vibe coding projeleri için
Azure'da servis altyapısı **açılmaz** — kataloğa hiç eklenmedi, bir proje Azure isterse bu
katalog-dışı bir istek olarak işaretlenir (`tier0/RULES.md` §6 madde 4), sessizce
uygulanmaz.

## Aynı kategoride birden fazla onaylı seçenek varsa (Compute)

**ECS Fargate vs EKS — ispat yükü EKS'te (bkz. `tier0/adr/0007-...` §3.1, tam gerekçe
orada):** Bu bir kıyaslanmış performans/maliyet ölçümü değil, operasyonel yük
asimetrisine dayanan bir varsayılan — Fargate'in ek yükü (cluster yok, node yaması yok,
ingress-controller kurulumu yok) bu kurumdaki iki tipik iş yükü profili için (yalnız
backend API / AI-orkestrasyon tarzı, ve fullstack 7/24 canlı uygulama) sıfıra yakınken,
EKS'in add-on bakım yükü (ingress controller, cluster autoscaler, metrics-server —
"AWS sürüm yönetiyor" ifadesinin kapsamadığı kısım) ölçekten bağımsız sabit bir maliyet.
Agent Faz 2'de EKS'i **yalnızca** şu kriterlerden biri gerçekten karşılanıyorsa önerir:
düzinelerce+ bağımsız servis (pod bin-packing yoğunluğu maliyet avantajı sağlar), gerçek
bir K8s-ekosistem bağımlılığı (yalnız Helm dağıtılan 3. parti yazılım, GitOps/ArgoCD
standart paradigma, CRD/operator gerektiren bileşen, service mesh ihtiyacı), veya ekibin
zaten güçlü/güncel K8s operasyonel deneyimi. Quarkus gibi K8s-optimize bir backend
seçilmesi tek başına yeterli değildir — kriterlerden biri karşılanmıyorsa Quarkus'un
Fargate'te çalıştığı ama K8s-optimize avantajının bir kısmının karşılıksız kaldığı
agent tarafından açıkça belirtilir. Kriterler çelişirse (örn. Quarkus seçildi ama proje
basit ve tek servis) agent kendi başına seçmez, çelişkiyi yüzeye çıkarır
(`skills/design-flow-agent/SPEC.md` §2.5).

> ✅ **Çözülmüş tutarlılık notu:** Bu katalog daha önce yalnızca Terraform + AWS/ECS Fargate
> içeriyordu, Kubernetes (EKS) eksikti — bu, `tier1/catalog/backend.md`'deki Quarkus
> satırının Kubernetes avantajını infra tarafında karşılıksız bırakıyordu. `tier0/adr/
> 0007-...` ile EKS kataloğa eklendi, bu tutarsızlık kapandı.

## Versiyon Notu (istisna)

`tier1/APPROVED-STACKS.md`'deki "Versiyon Stratejisi" (major sürüm pinleme) **ECS
Fargate/EKS için uygulanmaz** — bunlar AWS-yönetimli servisler, AWS güncel/desteklenen
varsayılan sürümle ayağa kaldırır; proje bir Kubernetes/Fargate platform sürümü pinlemez.

## Değerlendirilip şimdilik eklenmeyen / karar bekleyen seçenekler

- **Azure** — kurumda var ama vibe coding kapsamında bilinçli olarak dışlandı (yukarıya
  bakın), "değerlendirilip reddedilen" değil "kullanılmayacağı netleşen" bir seçenek.
- **PaaS (Railway, Vercel)** — `Değerlendirmede` statüsünde, yukarıdaki tabloda.
- **On-Premise / Edge orkestrasyon aracı** — hangi somut araçla (bkz. tablo "TBD") henüz
  belirlenmedi, gerçek bir ihtiyaç çıktığında stack-analizi ile netleşir.
