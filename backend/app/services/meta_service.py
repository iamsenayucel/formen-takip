from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.chief_repository import ChiefRepository
from app.repositories.kpi_repository import KpiRepository
from app.repositories.plant_repository import PlantRepository
from app.repositories.shift_repository import ShiftRepository


class MetaService:
    def __init__(
        self,
        db: Session,
        plant_repository: PlantRepository | None = None,
        chief_repository: ChiefRepository | None = None,
        kpi_repository: KpiRepository | None = None,
        shift_repository: ShiftRepository | None = None,
    ):
        self.db = db
        self.plant_repository = plant_repository or PlantRepository(db)
        self.chief_repository = chief_repository or ChiefRepository(db)
        self.kpi_repository = kpi_repository or KpiRepository(db)
        self.shift_repository = shift_repository or ShiftRepository(db)

    def get_filter_options(
        self, plant_ids: list[UUID] | None, factory_ids: list[UUID] | None
    ) -> dict:
        factories = self.plant_repository.list_active_factories()
        plants = self.plant_repository.list_active_for_factories(factory_ids)
        chiefs = self.chief_repository.list_active_for_filter_options(plant_ids, factory_ids)
        plant_ids_by_chief = {
            chief_id: [str(p.id) for p in plant_list]
            for chief_id, plant_list in self.plant_repository.plants_grouped_by_chief_id().items()
        }
        shifts = self.shift_repository.list_active()
        kpis = self.kpi_repository.list_active()

        return {
            "factories": [{"id": str(f.id), "code": f.code, "name": f.name, "location": f.location} for f in factories],
            "plants": [
                {"id": str(p.id), "code": p.code, "name": p.name, "sequence_number": p.sequence_number, "factory_id": str(p.factory_id)}
                for p in plants
            ],
            "chiefs": [
                {
                    "id": str(c.id), "employee_number": c.employee_number, "name": f"{c.first_name} {c.last_name}",
                    "plant_ids": plant_ids_by_chief.get(c.id, []),
                }
                for c in chiefs
            ],
            "shifts": [{"id": str(s.id), "code": s.code, "name": s.name, "sequence": s.sequence} for s in shifts],
            "kpis": [
                {"id": str(k.id), "code": k.code, "name": k.name, "unit": k.unit, "weight": float(k.weight)}
                for k in kpis
            ],
        }
