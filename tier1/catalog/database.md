# Katalog — Veritabanı

> Genel kural/statü tanımları `tier1/APPROVED-STACKS.md`'de. Veritabanı **hosting modeli**
> (RDS/Aurora vs self-deployed) burada değil, `tier1/catalog/infra.md` ve
> `tier1/playbooks/playbook-infra-terraform-aws.md`'dedir — bu bir yazılım-katmanı kararı değildir.

| Kategori | Seçenek | Statü | Playbook / Referans | Not |
|---|---|---|---|---|
| Veritabanı | PostgreSQL 18.x (Aurora/RDS) | Referans | `tier1/playbooks/playbook-infra-terraform-aws.md` | Stack'ten bağımsız, her backend seçeneğiyle kullanılır; minor/patch projenin kendi altyapı IaC'ında (bkz. `tier1/APPROVED-STACKS.md` "Versiyon Stratejisi") |
| Veritabanı | MongoDB | Onaylı | `tier1/playbooks/playbook-infra-terraform-aws.md` | Doküman/esnek şema ihtiyacı olan use case'ler için; bkz. `tier0/adr/0004-...` |
