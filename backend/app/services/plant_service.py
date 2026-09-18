from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import PlantNotFoundError
from app.core.pagination import decode_cursor, encode_cursor, filter_signature
from app.core.turkish import turkish_sort_key
from app.models.organization import Plant
from app.repositories.foreman_repository import ForemanRepository
from app.repositories.plant_repository import PlantRepository
from app.schemas.common import CursorParams, Filters
from app.services import analytics, assignment_resolver
from app.services.chief_service import chief_group_code
from app.services.foreman_performance_metrics import compute_general_foreman_scores
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import foreman_level_payload, get_performance_levels, level_to_dict

_COMPUTED_SORT_FIELDS = {"active_foreman_count", "score", "level"}


class PlantService:
    def __init__(
        self, db: Session, repository: PlantRepository | None = None, foreman_repository: ForemanRepository | None = None
    ):
        self.db = db
        self.repository = repository or PlantRepository(db)
        self.foreman_repository = foreman_repository or ForemanRepository(db)

    def get_detail(self, plant_id: UUID) -> dict:
        plant = self.repository.get(plant_id)
        if plant is None:
            raise PlantNotFoundError("Tesis bulunamadı.")
        factory = self.repository.get_factory(plant.factory_id)
        factory_ref = {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None
        return {
            "id": str(plant.id), "code": plant.code, "name": plant.name, "sequence_number": plant.sequence_number,
            "factory": factory_ref,
            "description": plant.description, "is_active": plant.is_active, "sap_plant_code": plant.sap_plant_code,
        }

    def get_kpis(self, plant_id: UUID, filters: Filters) -> dict:
        filters.plant_ids = [plant_id]
        items = analytics.kpi_summary(self.db, filters)
        kpis_by_id = self.foreman_repository.all_kpis_by_id()
        return {
            "items": [
                {
                    "kpi_id": str(i.kpi_id), "code": kpis_by_id[i.kpi_id].code, "name": kpis_by_id[i.kpi_id].name,
                    "unit": kpis_by_id[i.kpi_id].unit, "avg_score": round(i.avg_capped_score, 2),
                    "avg_target": round(i.avg_target, 2) if i.avg_target is not None else None,
                    "avg_actual": round(i.avg_actual, 2) if i.avg_actual is not None else None,
                }
                for i in items if i.kpi_id in kpis_by_id
            ]
        }

    def get_shifts(self, plant_id: UUID, filters: Filters) -> dict:
        filters.plant_ids = [plant_id]
        levels = get_performance_levels(self.db)
        scores = analytics.shift_scores(self.db, filters)
        shifts_by_id = self.foreman_repository.all_shifts_by_id()
        scores.sort(key=lambda s: shifts_by_id[s.key].sequence if s.key in shifts_by_id else 0)
        return {
            "items": [
                {
                    "shift_id": str(s.key), "code": shifts_by_id[s.key].code, "name": shifts_by_id[s.key].name,
                    "total_score": round(s.total_score, 2),
                    "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
                }
                for s in scores if s.key in shifts_by_id
            ]
        }

    def get_chiefs(self, plant_id: UUID, filters: Filters) -> dict:
        filters.plant_ids = [plant_id]
        levels = get_performance_levels(self.db)
        scores_by_chief = {s.key: s for s in analytics.chief_scores(self.db, filters)}
        plant = self.repository.get(plant_id)
        chief_ids = [plant.chief_id] if plant else []
        chiefs = self.repository.chiefs_by_ids(chief_ids)

        items = []
        for c in chiefs:
            foreman_count = assignment_resolver.active_foreman_count(
                self.db, filters.date_to, plant_id=plant_id, chief_id=c.id
            )
            gs = scores_by_chief.get(c.id)
            score = gs.total_score if gs else 0.0
            items.append(
                {
                    "id": str(c.id), "employee_number": c.employee_number,
                    "full_name": f"{c.first_name} {c.last_name}",
                    "foreman_count": foreman_count,
                    "total_score": round(score, 2),
                    "level": level_to_dict(resolve_performance_level(score, levels)),
                }
            )
        return {"items": items}

    def get_list(
        self,
        search: str | None,
        factory_id: UUID | None,
        is_active: bool | None,
        sort_by: str,
        sort_dir: str,
        page: CursorParams,
        filters: Filters,
    ) -> dict:
        levels = get_performance_levels(self.db)

        filter_sig = filter_signature(
            search, factory_id, is_active,
            filters.date_from, filters.date_to, filters.plant_ids, filters.factory_ids,
            filters.chief_ids, filters.shift_ids, filters.kpi_ids, filters.foreman_ids,
        )
        cursor_value = cursor_id = None
        if page.cursor is not None:
            state = decode_cursor(page.cursor, sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig)
            cursor_value = state.sort_value
            cursor_id = UUID(state.id)

        sort_values = None
        if sort_by in _COMPUTED_SORT_FIELDS:
            candidate_ids = self.repository.list_ids(search, factory_id, is_active, filters)
            if sort_by == "active_foreman_count":
                counts = assignment_resolver.active_foreman_counts_by_plant(
                    self.db, filters.date_to, plant_ids=candidate_ids
                )
                sort_values = {pid: counts.get(pid, 0) for pid in candidate_ids}
            else:
                scores_by_id = {s.key: s.total_score for s in analytics.plant_scores(self.db, filters)}
                if sort_by == "score":
                    sort_values = {pid: scores_by_id.get(pid, 0.0) for pid in candidate_ids}
                else:
                    sort_values = {
                        pid: resolve_performance_level(scores_by_id.get(pid, 0.0), levels).sort_order
                        for pid in candidate_ids
                    }

        rows = self.repository.list_page(
            search, factory_id, is_active, filters,
            sort_by=sort_by, sort_dir=sort_dir, sort_values=sort_values,
            cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit,
        )
        has_more = len(rows) > page.limit
        page_rows = rows[: page.limit]
        page_plants = [p for p, _ in page_rows]

        total = self.repository.count(search, factory_id, is_active, filters)
        items = self._hydrate_plant_items(page_plants, filters, levels)

        next_cursor = None
        if has_more and page_rows:
            last_plant, last_sort_value = page_rows[-1]
            next_cursor = encode_cursor(
                sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig,
                sort_value=last_sort_value, id_=str(last_plant.id),
            )
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more, "total": total}

    def _hydrate_plant_items(self, page_plants: list[Plant], filters: Filters, levels) -> list[dict]:
        if not page_plants:
            return []
        page_ids = [p.id for p in page_plants]
        page_filters = replace(filters, plant_ids=page_ids)
        scores_by_plant = {s.key: s for s in analytics.plant_scores(self.db, page_filters)}
        factories_by_id = self.repository.all_factories_by_id()
        active_foreman_counts = assignment_resolver.active_foreman_counts_by_plant(
            self.db, filters.date_to, plant_ids=page_ids
        )

        chief_ids = list({p.chief_id for p in page_plants})
        chiefs_by_id = {c.id: c for c in self.repository.chiefs_by_ids(chief_ids)}
        scores_by_chief = {s.key: s for s in analytics.chief_scores(self.db, filters)}
        foremen_by_chief = assignment_resolver.active_foremen_by_chief(
            self.db, filters.date_to, chief_ids=chief_ids
        )

        items = []
        for p in page_plants:
            gs = scores_by_plant.get(p.id)
            score = gs.total_score if gs else 0.0
            active_foremen = active_foreman_counts.get(p.id, 0)
            factory = factories_by_id.get(p.factory_id)
            level = resolve_performance_level(score, levels)
            chief = chiefs_by_id.get(p.chief_id)
            chief_score = scores_by_chief.get(p.chief_id)
            group = (
                {
                    "id": str(chief.id),
                    "code": chief_group_code(chief.employee_number),
                    "score": round(chief_score.total_score, 2) if chief_score else 0.0,
                    "supervisor": {"id": str(chief.id), "name": f"{chief.first_name} {chief.last_name}"},
                    "foremen": sorted(
                        (
                            {"id": str(foreman_id), "name": name}
                            for foreman_id, name in foremen_by_chief.get(chief.id, [])
                        ),
                        key=lambda f: turkish_sort_key(f["name"]),
                    ),
                }
                if chief else None
            )
            items.append(
                {
                    "id": str(p.id), "code": p.code, "name": p.name, "sequence_number": p.sequence_number,
                    "factory": {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None,
                    "is_active": p.is_active, "total_score": round(score, 2),
                    "level": level_to_dict(level),
                    "active_foreman_count": active_foremen,
                    "record_count": gs.record_count if gs else 0,
                    "group": group,
                }
            )
        return items

    def get_summary(self, plant_id: UUID, filters: Filters) -> dict:
        plant = self.repository.get(plant_id)
        if plant is None:
            raise PlantNotFoundError("Tesis bulunamadı.")
        filters.plant_ids = [plant_id]
        levels = get_performance_levels(self.db)

        p_scores = analytics.plant_scores(self.db, filters)
        score = next((s.total_score for s in p_scores if s.key == plant_id), 0.0)

        f_scores = analytics.foreman_scores(self.db, filters)
        foremen_average_score = sum(s.total_score for s in f_scores) / len(f_scores) if f_scores else 0.0
        critical_count = sum(1 for s in f_scores if resolve_performance_level(s.total_score, levels).name == "Kritik")

        kpi_items = analytics.kpi_summary(self.db, filters)
        kpis_by_id = self.foreman_repository.all_kpis_by_id()
        strongest = max(kpi_items, key=lambda i: i.avg_capped_score, default=None)
        weakest = min(kpi_items, key=lambda i: i.avg_capped_score, default=None)

        active_foremen = assignment_resolver.active_foreman_count(self.db, filters.date_to, plant_id=plant_id)

        return {
            "plant_id": str(plant_id),
            "total_score": round(score, 2),
            "level": level_to_dict(resolve_performance_level(score, levels)),
            "foremen_average_score": round(foremen_average_score, 2),
            "active_foreman_count": active_foremen,
            "critical_foreman_count": critical_count,
            "strongest_kpi": (
                {
                    "id": str(strongest.kpi_id), "name": kpis_by_id[strongest.kpi_id].name,
                    "avg_score": round(strongest.avg_capped_score, 2),
                }
                if strongest else None
            ),
            "weakest_kpi": (
                {
                    "id": str(weakest.kpi_id), "name": kpis_by_id[weakest.kpi_id].name,
                    "avg_score": round(weakest.avg_capped_score, 2),
                }
                if weakest else None
            ),
        }

    def get_foremen(self, plant_id: UUID, page: CursorParams, filters: Filters) -> dict:
        filters.plant_ids = [plant_id]
        levels = get_performance_levels(self.db)
        scores, bonuses_by_foreman, general_by_key = compute_general_foreman_scores(self.db, filters)
        scores_by_foreman = {s.key: s for s in scores}

        filter_sig = filter_signature(
            str(plant_id), filters.date_from, filters.date_to, filters.plant_ids, filters.factory_ids,
            filters.chief_ids, filters.shift_ids, filters.kpi_ids, filters.foreman_ids,
        )
        cursor_value = cursor_id = None
        if page.cursor is not None:
            state = decode_cursor(
                page.cursor, sort_by="general_performance_score", sort_dir="desc", filter_sig=filter_sig
            )
            cursor_value = state.sort_value
            cursor_id = UUID(state.id)

        rows = self.foreman_repository.list_by_ids_page(
            list(general_by_key.keys()), general_by_key,
            sort_dir="desc", cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit,
        )
        has_more = len(rows) > page.limit
        page_rows = rows[: page.limit]

        items = [
            {
                "foreman_id": str(f.id),
                "employee_number": f.employee_number,
                "full_name": f"{f.first_name} {f.last_name}",
                "operational_score": round(scores_by_foreman[f.id].total_score, 2) if f.id in scores_by_foreman else 0.0,
                "contribution_bonus": bonuses_by_foreman[f.id].bonus if f.id in bonuses_by_foreman else 0,
                "general_performance_score": round(general_by_key[f.id], 2),
                "level": foreman_level_payload(general_by_key[f.id], levels),
            }
            for f, _ in page_rows
        ]

        total = len(general_by_key)
        next_cursor = None
        if has_more and page_rows:
            last_foreman, last_sort_value = page_rows[-1]
            next_cursor = encode_cursor(
                sort_by="general_performance_score", sort_dir="desc", filter_sig=filter_sig,
                sort_value=last_sort_value, id_=str(last_foreman.id),
            )
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more, "total": total}
