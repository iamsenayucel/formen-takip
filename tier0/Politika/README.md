# Kurumsal AI Kodlama Politikası — v3

Bu klasör, Yıldız Holding EA/CoE tarafından yayınlanan **"AI Destekli Kodlama ve Ürün
Geliştirme Politikası"**nın (master + 6 alt standart) v3 kopyasıdır. Kaynak: Yıldız Holding
SharePoint (`BTKurumsalMimari` sitesi, `++Wipe Coding/AI-Kodlama-Politikasi-v3` klasörü).

## Bu klasör neden burada, ne için değil

**Bu dosyalar bir referanstır — bu şablonun bir parçası değildir.** `example-projects/` ve
`tier2/` gibi, `vibe-coding-bootstrap` veya `design-flow-agent` skill'leri tarafından
**hiçbir projeye otomatik kopyalanmaz**. Şimdilik burada yalnızca **kurum kuralının tek,
güncel, herkesin erişebildiği bir kopyası** olarak duruyor — bu repo zaten CoE'nin tool-
agnostik/stack-agnostik disiplinini taşıyor, kurumsal politika ile aynı adreste bulunması
bir "vibe coding" projesine başlayan herkesin ikisine de aynı yerden ulaşmasını sağlıyor.

**Neden okunması önemli:** Bu politika, `tier0/RULES.md`'nin *üstünde* durur — RULES.md
"hangi stack olursa olsun geçerli olan disiplin"i tanımlar, bu politika ise "AI ile kod
üretirken kurumun hesap verebilirlik ve kontrol çerçevesi"ni tanımlar. Biri teknik, diğeri
kurumsal/yönetişimsel — ama ikisi de bağlayıcı. Bir "vibe coding" ekibi yalnızca RULES.md'yi
okuyup bu politikayı atlarsa, teknik olarak doğru ama kurumsal olarak uyumsuz bir süreç
kurma riski taşır (örn. risk skorlaması yapılmadan, gate'ler resmî olarak uygulanmadan
ilerlemek).

> ⚠️ **Bilinen durum (güncellendi 2026-07-20 — v4 uzlaştırma geçti):** Bu politika seti ile
> `tier0/RULES.md`/`tier1/` arasındaki bilinen çelişkilerin çoğu bu tarihte çözüldü:
> - **Proje başlatma mekanizması** — `npx @yildiz/create-app` gerçek/planlı değildi (teyit
>   edildi), `02-Gate-Operasyon-Standardi.md` Gate 1 artık framework'ün kendi bootstrap'ına
>   işaret ediyor.
> - **Risk modellemesi** — framework artık kendi `tier0/procedures/risk-tiering.md`'sini
>   (RULES.md §16) taşıyor, proje-geneli MVP bayrağının **yanında**, yerine değil.
> - **Test coverage** — iki farklı eksen (policy: AI-üretimi-kod ekseni; framework: modül-
>   risk ekseni) olarak isimlendirildi, bkz. `tier1/playbooks/playbook-testing-*.md`
>   "Coverage Hedefi"; framework'te ayrı bir integration-coverage sayısı hâlâ yok, açık madde.
> - **ADR şablonu** — `tier0/adr/0000-template.md`'ye `AI Katkısı/Gerekçesi` alanı eklendi.
> - **CI/CD Gate 3/5 somut araçları** (`check-coe-versions.js`, Nexus-only, `@yildiz/*`) —
>   üçü de gerçek/planlı değildi (teyit edildi), kaldırıldı; gerçek gereksinimler (lint/tip
>   güvenliği, SCA/lisans taraması, SAST) `tier0/RULES.md` §15 +
>   `tier1/playbooks/playbook-cicd-security.md`'ye taşındı.
> - **Diff bütçesi** (`03-CR-BugFix-Runbook.md`) — ham satır/dosya sayısı yerine 4 semantik
>   tetikleyiciye çevrildi (AI-üretimi diff'lerde boyutun risikle orantısız olması nedeniyle).
> - **Rol isimlendirmesi** — aşağıdaki "Rol Eşleme" bölümünde netleştirildi.
>
> Hâlâ açık/teyit bekleyen: **Steward** ve **AI-Assisted Dev. Accelerator** rollerinin
> framework'teki karşılığı kısmi (bkz. Rol Eşleme); framework'ün integration-özel bir
> coverage eşiği yok. Bir çelişki fark ederseniz, önce ilgili dosyanın üstündeki
> "(Not: ... kaldırıldı/güncellendi)" işaretlerine bakın — sessizce birini yok saymayın.

## Rol Eşleme (v4, 2026-07-20)

Politika ve framework farklı zamanlarda, farklı amaçlarla (kurumsal hesap verebilirlik vs.
tasarım fazı operasyonu) yazıldığından aynı rolü farklı adlandırıyor. Bir vibe-coding
projesinde bu isimler şöyle eşleşir:

| Politika | Framework karşılığı | Not |
|---|---|---|
| Teknik Lider | Teknik Sorumlu | Aynı kişi/rol — Teknik Sorumlu, tasarım fazındaki (design-flow-agent) adı; proje canlıya çıktıktan sonra aynı kişi Teknik Lider sorumluluğunu (gate uygulaması, uygunluk raporlama) taşımaya devam eder. |
| Ürün Ekibi / PO | Tasarım Sorumlusu | Aynı kişi/rol — kapsam/domain/persona kararlarını Tasarım Sorumlusu tasarım fazında, PO olarak canlı süreçte verir. |
| Steward | `tier0/RULES.md` §1 "AI Bağlam Dosyası Sorumlusu" | Framework'e bu v4 geçişinde eklendi. Varsayılan olarak Teknik Sorumlu/Lider üstlenir; proje büyükse ayrı atanabilir. |
| Security | *(framework'te doğrudan karşılığı yok)* | En yakın karşılık: `tier1/playbooks/playbook-cicd-security.md`'nin sahibi + onaylı-araç listesini işleten kişi. Proje bazında Teknik Lider'e düşer; ayrı bir atama gerekiyorsa Master Politika Madde 2'deki tanım geçerlidir. |
| AI-Assisted Dev. Accelerator | *(framework'te doğrudan karşılığı yok — org-seviyesi rol)* | Bu repo (framework + skill kütüphanesi) bu rolün ürettiği/bakımını yaptığı bir **çıktıdır** — rolün kendisi framework dosyalarında bir "kişi" olarak temsil edilmez, framework'ün varlığı Olgunluk Yol Haritası'nın Seviye 3 kriterini karşılamanın kanıtıdır (bkz. `04-Olgunluk-Yol-Haritasi.md`). |
| EA / CoE | *(framework'te doğrudan karşılığı yok — org-seviyesi rol)* | Kataloğun/framework'ün sahibi; `tier1/APPROVED-STACKS.md` "Yeni stack ekleme süreci" madde 3'teki "katalog sahibi" bu role işaret eder. |

## İçerik

| Dosya | Ne anlatır |
|---|---|
| `00-Master-Politika.md` | İlke seviyesi: roller/hesap verebilirlik, 5 kalite kapısının var olma amacı, AI kodlama kararının Demand Board ile ilişkisi, veri gizliliği/yasaklı alanlar, istisna protokolü |
| `01-Risk-Degerlendirme-Standardi.md` | Her değişikliğin (5 soru, 0-10 puan) Tier A/B/C'ye nasıl sınıflandırıldığı |
| `02-Gate-Operasyon-Standardi.md` | 5 kalite kapısının bugün hangi somut araç/eşikle uygulandığı |
| `03-CR-BugFix-Runbook.md` | Bug-fix/CR'ların Tier'e ve diff büyüklüğüne göre süreci |
| `04-Olgunluk-Yol-Haritasi.md` | Organizasyonun AI-assisted geliştirme olgunluk seviyeleri ve metrikleri |
| `05-Egitim-Yonergesi.md` | Kimin hangi Tier'de tek başına çalışabileceğinin yetkinlik kriterleri |
| `06-3Parti-Tedarikci-Eki.md` | Dış tedarikçiler için minimum gereksinimler |

## Vibe coding ekiplerine

**Bu dokümanları okumak, RULES.md'yi okumak kadar zorunludur.** Teknik disiplin (bu repo)
ve kurumsal hesap verebilirlik (bu klasör) birbirini tamamlar, biri diğerinin yerine
geçmez. Projenize başlamadan önce en azından `00-Master-Politika.md`'yi ve değişikliğinizin
risk Tier'ini belirleyeceğiniz `01-Risk-Degerlendirme-Standardi.md`'yi okuyun —
`design-flow-agent` Faz 0'da bunu size ayrıca hatırlatacak.

## Güncelleme

Bu bir **dondurulmuş kopyadır**, canlı senkronize değil. Kaynak SharePoint'te güncelleme
olduğunda burası elle tazelenmeli — otomatik bir mekanizma yok. Versiyon numarasını (bugün
v3) dosya adlarından takip edin.
