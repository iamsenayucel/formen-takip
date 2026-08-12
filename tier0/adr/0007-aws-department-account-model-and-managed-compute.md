# ADR-0007: AWS departman-bazlı hesap modeli + yönetilen compute seçenekleri (ECS Fargate / EKS / istisnai on-premise-edge); Azure ve on-prem kullanılmaz, PaaS değerlendirmede

**Durum:** Kabul edildi
**Tarih:** 2026-07-15
**Karar verenler:** CoE (katalog sahibi)

> Bu bir katalog-seviyesi ADR'dir — bkz. `tier0/adr/0001-...`'deki aynı not. Bu ADR
> `tier1/catalog/infra.md`'nin tek satırlık ("Terraform + AWS, 3-hesap izolasyon") halini
> genişletir ve önceden flag'lenmiş bir tutarsızlığı kapatır (bkz. Bağlam).

## Bağlam

`tier1/catalog/backend.md`'deki Quarkus satırı ve `tier1/catalog/infra.md`'nin kendisi,
Kubernetes'in (EKS) henüz kataloğa eklenmediğini, bunun "ayrı bir stack-analizi + ADR
konusu" olduğunu, bilinçli olarak açık bıraktığını not ediyordu. Katalog sahibi bu turda
kurumun gerçek altyapı standardını netleştirdi:

1. Kurum, departman bazında ayrı AWS hesapları işletiyor — tek bir global 3-hesap modeli
   değil, **her departmanın kendi hesap grubu var**, bu hesap grubu içinde ortam
   (dev/staging/prod) ayrımı sürüyor.
2. Her hesapta standart olarak S3 (private), SQS, API Gateway, Secrets Manager hazır;
   istenirse ECS Fargate de kullanılabilir.
3. Kubernetes (EKS) her hesapta zorunlu değil ama **kataloğa resmen eklenmesi gerekiyor** —
   Quarkus gibi K8s-optimize seçeneklerin pratik bir karşılığı olması için.
4. Bu üç compute seçeneği de (Fargate/ECS/EKS) AWS-yönetimli olduğundan, `tier1/
   APPROVED-STACKS.md`'deki "Versiyon Stratejisi" (major sürüm pinleme) burada **uygulanmaz**
   — AWS bunları güncel, desteklenen varsayılan sürümle ayağa kaldırır.
5. Azure ortamları kurumda var ama **vibe coding projeleri için orada servis altyapısı
   açılmayacak** — kataloğa Azure hiç eklenmiyor.
6. On-premise datacenter/fabrika-içi edge server gerçekten zorunlu olduğunda desteklenir
   ama datacenter'da Kubernetes yok — bu **her zaman istisna/son çare**, varsayılan asla
   AWS'nin yerini almaz.
7. Redis/ElastiCache: yönetilen cache hizmeti her hesapta ihtiyaca göre alınabilir, ama
   **hiçbir proje kendi Redis'ini self-host etmez** — bu genel kural netleşiyor, önceki
   "Onaylı" statü ilkesel olarak doğruydu, burada yalnız "self-host yasak" netleşiyor.
8. MVP/POC ölçekli projeler için kurumsal AWS ortamlarından tamamen bağımsız PaaS
   platformları (Railway, Vercel gibi) değerlendiriliyor — **henüz karar verilmedi**, bu
   yüzden `Değerlendirmede` statüsünde kataloğa girer (seçenek olarak sunulmaz).

## Karar

**1. Hesap modeli — departman × ortam (iki boyutlu).** Her departman kendi AWS
hesap grubuna sahiptir; departman içinde dev/staging/prod ortam ayrımı (önceki 3-hesap
modeliyle aynı mantık, artık departman bazında tekrarlanır) sürer. Departmanlar arası
kaynak paylaşımı/erişimi varsayılan olarak yoktur — bir departmanın hesabı başka bir
departmanın kaynağına erişmez (bu, `tier0/RULES.md` §13'teki Ocean zorunluluğuyla
tutarlı: departmanlar-arası ihtiyaç da doğrudan değil, merkezi bir kanaldan geçmeli).

**2. Her hesapta standart hazır (Zorunlu-hazır, kullanım proje kararı):** S3 (yalnız
private bucket — public bucket yasak), SQS, API Gateway, Secrets Manager. Bir uygulama
secret'larını **yalnızca** Secrets Manager'da tutar (`.env`/kod içi sır yasak, zaten
`tier0/RULES.md` §4 madde 3 ile aynı ilke); S3 kullanan bir proje bucket'ı **private**
açar (public erişim gerekiyorsa CloudFront + signed URL gibi bir katman üzerinden, asla
doğrudan public bucket); asenkron/kuyruk ihtiyacı olan bir proje **kendi kuyruk
altyapısını kurmaz**, SQS'ten yararlanır.

**3. Compute — üç seçenek, biri varsayılan:**
- **ECS Fargate** — Referans/varsayılan. Kubernetes gerçekten gerekmiyorsa bu kullanılır.
- **EKS** — Onaylı. Yalnız gerçek bir Kubernetes ihtiyacı olduğunda (bkz. 3.1 aşağıda) —
  her hesapta zorunlu değil, ihtiyaca göre.
- **On-Premise / Edge Server** — Onaylı ama **istisna/son çare**. Yalnız fabrika-içi edge
  veya on-premise datacenter'da çalışması **zorunlu** olan bir uygulama için (örn. yerel
  ağ kesintisinde bile çalışması gereken bir saha sistemi). Datacenter'da Kubernetes
  yoktur — bu seçenek varsayılan olarak asla önerilmez, yalnız gerçek bir zorunluluk
  gerekçesiyle ve ayrı bir stack-analizi ile seçilir.

### 3.1 Fargate'in varsayılan olma gerekçesi — iş yükü bazlı analiz

Bu bir kıyaslanmış performans/maliyet ölçümüne değil, **operasyonel yük simetrisine**
dayanan bir karardır — aşağıda hem bunun neyi kanıtladığı hem kanıtlamadığı açıkça
ayrılıyor.

**Operasyonel yük karşılaştırması (ölçülmüş değil, ikisinin de gerektirdiği gerçek işler):**
Fargate'te cluster yok, node AMI yaması yok, CNI/ingress-controller kurulumu yok — ALB
entegrasyonu, Secrets Manager/SSM injection'ı ve task-bazlı IAM rolü servis tanımının
kendi içinde, ek bir bileşen kurulmadan gelir. EKS'te AWS yalnızca kontrol düzlemini
(API server) yönetir/yamalar — **add-on yığını (AWS Load Balancer Controller, cluster
autoscaler, metrics-server, gerekiyorsa cert-manager) operatörün sorumluluğudur** ve bu,
"AWS sürümü yönetiyor" ifadesinin kapsamadığı, sürekli bir Helm-chart bakım yüküdür. EKS
Fargate-profile ile (node'suz) çalıştırılsa bile bu K8s API yüzeyi/RBAC/ingress yükü
kalır — yalnızca node yönetimi ortadan kalkar.

**Bu kurumdaki tipik iş yükü profilleriyle eşleşme:**
- **Yalnız backend API (çoğu AI/Python orkestrasyon senaryosu gibi)** — durum-bilgisiz
  (stateless) istek-yanıt trafiği, genelde LLM/harici API'lere çağrı yapan bir orkestrasyon
  katmanı. StatefulSet, DaemonSet veya cluster-içi GPU zamanlama gerektirmez (gerçek GPU
  model sunumu ayrı, özel bir servis/karardır — bkz. `tier1/catalog/ml-serving.md` — o
  bile otomatik olarak EKS gerektirmez, ECS de GPU task'ı destekler). Bu, ECS Fargate +
  ALB + task auto-scaling'in tam olarak tasarlandığı şekil.
- **Fullstack, 7/24 canlı uygulamalar** — ECS service (desired-count ≥2) + ALB
  target-tracking autoscaling + native rolling deployment (deployment circuit breaker) ile
  aynı sürekli-çalışan, kendi kendini iyileştiren davranış sağlanır. "7/24" kendi başına
  Kubernetes gerektirmez — bir Fargate servisi de aynı derecede sürekli ve kendini
  onaran'dır.

Bu kurumda tanımlı iki tipik iş yükü profili de (yukarıdaki ikisi) Kubernetes'in var olma
nedeni olan primitiflere (StatefulSet, DaemonSet, CRD/operator, service mesh, çok-takımlı
paylaşılan cluster'da namespace-bazlı RBAC) gerçekten ihtiyaç duymuyor.

**EKS'in karmaşıklığının gerçekten karşılığını bulduğu eşik (somut karar kriterleri):**
- Düzinelerce+ bağımsız servis — Fargate task-bazlı faturalandığından pod-seviyesi
  bin-packing yoğunluğu sağlamaz; K8s node'ları çok sayıda küçük pod'u sıkı paketleyerek
  bu ölçekte maliyet avantajı sağlayabilir.
- Gerçek bir Kubernetes ekosistem bağımlılığı — yalnızca Helm chart olarak dağıtılan
  3. parti yazılım, GitOps'un (ArgoCD/Flux) standart deploy paradigması olması, karmaşık
  east-west trafik için service mesh ihtiyacı, CRD/operator gerektiren bir bileşen.
- Ekibin zaten güçlü, güncel K8s operasyonel deneyimi olması — bu durumda "ek" maliyet
  marjinal değil, zaten karşılanmış bir maliyettir.
- Quarkus gibi K8s-optimize bir backend seçildiğinde, seçimin gerekçesi (hızlı açılış,
  düşük ayak izi) gerçekten Kubernetes ortamında anlamlıdır — Fargate'te Quarkus'un bu
  avantajı büyük ölçüde karşılıksız kalır.

**Kanıtlamadığı şey (dürüst "non-proof"):** Bu kurum için "N servisten sonra EKS'e geç"
diye ölçülmüş/doğrulanmış bir eşik **yok** — bu bir mimari/operasyonel-karmaşıklık
muhakemesi, kontrollü bir benchmark değil. Kanıtlanabilen şey **asimetridir**: yukarıdaki
iki tipik iş yükü profili için Fargate'in ek yükü sıfıra yakınken, EKS'in ek yükü ölçekten
bağımsız olarak sabit ve gerçektir — bu yüzden ispat yükü EKS'i seçmede olmalı, Fargate'i
seçmede değil. Gerçek bir proje yukarıdaki eşik kriterlerinden birine açıkça uymadan EKS
seçerse, `design-flow-agent` bunu sorgulamalı (`skills/design-flow-agent/SPEC.md` §2.5).

Üçü de AWS-yönetimli (Fargate/EKS) veya istisnai (on-prem) olduğundan, **major sürüm
pinleme (`tier1/APPROVED-STACKS.md` "Versiyon Stratejisi") bu üç seçenek için
uygulanmaz** — Fargate/EKS AWS'nin güncel desteklenen varsayılan sürümüyle ayağa kalkar,
proje bunu pinlemez.

**4. Cloud vendor — yalnız AWS.** Azure kataloğa **hiç eklenmez** — kurumda Azure ortamları
var ama vibe coding projeleri için oraya servis altyapısı açılmıyor. Bir proje Azure
önerirse/isterse, bu katalog-dışı bir istek olarak işaretlenir (`tier0/RULES.md` §6 madde 4
ruhu), sessizce uygulanmaz.

**5. Caching — Redis/ElastiCache, yalnız yönetilen, self-host yasak.** `tier1/catalog/
cross-cutting.md`'deki Redis satırı netleşti: yönetilen ElastiCache her hesapta ihtiyaca
göre alınabilir, ama hiçbir proje kendi Redis'ini (örn. bir container'da) self-host etmez.
Hangi projede gerçekten ihtiyaç olduğu proje-özel bir mimari kararı olarak kalır — kural,
"gerekiyorsa self-host değil ElastiCache" ilkesidir, "her projede olmalı" değil.

**6. PaaS (Railway/Vercel benzeri) — `Değerlendirmede`.** MVP/POC ölçekli projeler için
kurumsal AWS ortamlarından bağımsız PaaS değerlendiriliyor, henüz onaylanmadı.
`design-flow-agent` bunu bir seçenek olarak sunmaz, yalnız "değerlendirme aşamasında"
diye bilgi verebilir (bkz. `tier1/APPROVED-STACKS.md` Statü tanımları).

## Sonuçlar

**Artılar:**
- Quarkus'un Kubernetes-optimize avantajı artık gerçek bir infra karşılığı buluyor —
  `tier1/catalog/backend.md`'deki flag'lenmiş tutarsızlık kapandı.
- Departman-bazlı hesap modeli, departmanlar arası blast-radius'u AWS hesap sınırıyla
  yapısal olarak izole ediyor — mevcut ortam-bazlı (dev/staging/prod) izolasyonun üzerine
  ek bir boyut.
- Version-pinning istisnası, AWS-yönetimli servisler için gereksiz/yanıltıcı bir "sürüm
  seç" adımını ortadan kaldırıyor.

**Eksiler / kabul edilen riskler:**
- On-premise/edge seçeneğinin somut IaC detayı (hangi orkestrasyon, hangi araç) henüz
  yok — bu, gerçek bir ihtiyaç ortaya çıktığında ayrı bir stack-analizi gerektirir, burada
  icat edilmedi.
- EKS'in playbook'u (`tier1/playbooks/playbook-infra-terraform-aws-eks.md`) bu ADR ile
  birlikte yazıldı ama gerçek bir projede henüz doğrulanmadı (Referans değil Onaylı statüde
  kalıyor bu yüzden).

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** `tier0/adr/0002-...` (Quarkus'un
Kubernetes gerekçesi, artık karşılığı var); `tier0/adr/0003-...` (SQS'in mevcut kurumsal
kullanımı, bu ADR'de hesap-bazlı hazır servis olarak genelleştirildi); `tier0/RULES.md`
§13 (Ocean — departmanlar-arası erişimin de bu kanaldan geçmesi gerektiği ima edilir,
ayrı bir karar değil, aynı ilkenin uzantısı).
