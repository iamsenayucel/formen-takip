# Proje Talimatı (Claude Code)

Bu projenin tüm tool-agnostik geliştirme kuralları `/tier0/RULES.md` dosyasındadır. Her
session başında bu dosyayı oku ve boyunca uygula.

Üzerinde çalıştığın dosyanın alanına göre ek olarak ilgili stack playbook'unu oku — dosya
adı `tier0/RULES.md` §1'de kayıtlı stack'e göre değişir (örn. `playbook-backend-nestjs.md`,
`playbook-backend-java-spring-boot.md`); emin değilsen `tier1/` dizinini listele:

- `apps/api/**` veya backend kodu → `tier1/playbooks/playbook-backend-<stack>.md`
- `apps/web/**` veya frontend kodu → `tier1/playbooks/playbook-frontend-<stack>.md`
- `infrastructure/**` veya IaC → `tier1/playbooks/playbook-infra-<stack>.md`
- Test dosyaları → `tier1/playbooks/playbook-testing-<stack>.md`
- Controller/endpoint tanımı (yeni/değişen bir API sözleşmesi) → ayrıca
  `tier1/playbooks/playbook-api-design.md` (Zorunlu)
- Başka bir kurumsal sisteme (ERP/SAP/başka bir dahili uygulama) entegrasyon kodu → ayrıca
  `tier1/playbooks/playbook-service-integration.md` (Zorunlu, varsa)

Tekrar eden bir görevle karşılaştığında (yeni endpoint/ekran/migration/izin, refactor,
bozuk test) önce `tier0/procedures/` altındaki ilgili prosedürü oku — ya da bu prosedürleri
`.claude/skills/` altına Skill olarak paketleyip tetikleyici açıklamalarla çağır (bkz.
`adapters/claude-code/README.md`).

Bu dosyaya yeni içerik **eklemeyin** — bu sadece bir yönlendiricidir. İçerik her zaman
`tier0/RULES.md` veya `tier1/`'e gider.
