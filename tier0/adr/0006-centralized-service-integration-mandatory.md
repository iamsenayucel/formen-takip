# ADR-0006: Kurumsal sistem entegrasyonu Ocean servis middleware'i üzerinden zorunlu; doğrudan app-to-app iletişim yasak

**Durum:** Kabul edildi
**Tarih:** 2026-07-15
**Karar verenler:** CoE (katalog sahibi)

> Bu bir katalog-seviyesi ADR'dir — bkz. `tier0/adr/0001-...`'deki aynı not. ADR-0004
> (gözlemlenebilirlik) ve ADR-0005 (authentication) ile aynı "Zorunlu cross-cutting" modelini
> izler.

## Bağlam

`playbook-api-design.md` taslağı yazılırken "Servis Middleware Pattern'leri" bölümü açık
bırakılmıştı — o başlığın framework-içi middleware'i (NestJS interceptor vb., zaten
`playbook-backend-*.md`'nin kapsamında) mı, yoksa servisler-arası iletişim middleware'ini mi
kastettiği netleşmemişti. Kullanıcı (katalog sahibi) netleştirdi: kurumda bir **kurumsal
kısıt** var, önceden hiçbir katalog dosyasında yazılı değildi:

- Kurumsal ağdaki sistemler arasında **doğrudan app-to-app iletişim izinli değil.**
- Kurumun sahipliğinde **Ocean** adlı bir servis middleware/entegrasyon platformu var;
  uygulamalar kurumsal sistemlere **yalnızca Ocean üzerinden** erişir/entegre olur.
- AWS/Azure tarafında, bir uygulamanın **kendi servisini dışa açması** ayrı bir konu — bu,
  ilgili bulut platformunun kendi API Gateway'i üzerinden yapılabilir (Ocean'ın yerini almaz,
  farklı bir eksen: "başkasının sistemine eriş" vs. "kendi servisini sun").
- İnternet'e açık ve yalnızca kurum-içi (internal) API arayüzleri **mimari olarak ayrı**
  olmalı — aynı gateway/listener ikisine birden hizmet etmemeli.

Bu, hem yazılım tasarımının (hangi entegrasyonun nasıl kurulacağı) hem deployment
mimarisinin (`deployment-design` skill'inin HLA topoloji çıktısı) parçası — ikisinde de
temsil edilmesi gerekiyor.

## Karar

**Kurumsal sistem entegrasyonu — yeni bir Zorunlu cross-cutting konu**, gözlemlenebilirlik
ve authentication ile aynı model:

1. `tier0/RULES.md`'ye yeni bir §13 eklendi (aynı bağlayıcılık seviyesi — "seçim değil
   zorunluluk").
2. `tier1/playbooks/playbook-service-integration.md` (Zorunlu) yazıldı — Ocean üzerinden
   entegrasyon kuralını, kendi-servisini-sunma ile başka-sisteme-erişme ayrımını, ve
   internet/internal arayüz ayrımını taşıyor.
3. `playbook-api-design.md`'nin "API Gateway Yerleşimi" ve "Servis Middleware Pattern'leri"
   bölümleri dolduruldu: fiziksel/topolojik yerleşim kararı `deployment-design` skill'inde
   kalıyor (bu ADR onu değiştirmiyor), ama bu playbook artık internet/internal arayüz
   ayrımı zorunluluğuna ve Ocean'a atıfta bulunuyor — **iki sorumluluk ayrı ama ikisi de
   var**, biri diğerini görmezden gelmiyor.
4. `deployment-design` skill'inin kendisi (bu reponun dışında, `.claude/skills/` altında)
   bu kararı henüz yansıtmıyor — ayrı, takip edilmesi gereken bir güncelleme, bu ADR'nin
   kapsamı dışı bırakıldı (bkz. Sonuçlar).

## Sonuçlar

**Artılar:**
- Kurumsal sistemlere erişimin tek, denetlenebilir bir kapıdan (Ocean) geçmesi — dağınık
  doğrudan entegrasyonların her biri ayrı bir güvenlik/uyum denetim yüzeyi olmaktan çıkar.
- İnternet/internal ayrımının zorunlu kılınması, bir internal-only entegrasyonun yanlışlıkla
  internete açık bir gateway'in arkasına düşme riskini yapısal olarak azaltır.

**Eksiler / kabul edilen riskler:**
- Ocean'ın gerçek teknik detayları (protokol, kimlik doğrulama, entegrasyon başvuru süreci)
  henüz playbook'a girilmedi — placeholder olarak bırakıldı, platform ekibi/Ocean sahibi
  sağladığında doldurulmalı (gözlemlenebilirlik ve authentication playbook'larında olduğu
  gibi aynı durum).
- `deployment-design` skill'i bu ADR ile senkron değil — HLA topoloji çıktısı üretirken bu
  kısıtı henüz otomatik hatırlatmıyor. Ayrı bir görev olarak takip edilmeli, bu ADR'nin
  kapsamına dahil edilmedi (skill dosyaları bu reponun parçası değil).

**Bu kararın bağlı olduğu diğer kararlar/ADR'ler:** ADR-0004'teki Zorunlu statü modelini
(gözlemlenebilirlik) ve ADR-0005'teki aynı modeli (authentication) izler; üçü birlikte
"Zorunlu cross-cutting" kategorisinin üçüncü örneğini oluşturur.
