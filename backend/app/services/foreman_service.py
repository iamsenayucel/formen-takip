from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ForemanKpiRecordNotFoundError, ForemanNotFoundError
from app.core.pagination import filter_signature, paginate_in_memory
from app.core.turkish import turkish_sort_key
from app.models.foreman import ForemanAssignment
from app.repositories.foreman_repository import ForemanListQueryParams, ForemanRepository
from app.schemas.common import CursorParams, Filters
from app.services import analytics, contribution_bonus, kpi_presentation
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import foreman_level_payload, get_performance_levels
from app.services.performance_scope import resolve_foreman_scope


class ForemanService:
    """Foreman Directory/Profile orkestrasyonu.

    Skor birleştirme, rank, level, sıralama ve sayfalama kararlarını verir;
    persistence'ı `ForemanRepository`'ye, hesaplamaları mevcut domain
    servislerine (`analytics`, `contribution_bonus`, `kpi_engine`,
    `level_lookup`, `performance_scope`) devreder. Salt okunur — transaction
    sınırı gerekmez.
    """

    def __init__(self, db: Session, repository: ForemanRepository | None = None):
        self.db = db
        self.repository = repository or ForemanRepository(db)

    # ------------------------------------------------------------------
    # Serialization (list_foremen ve get_foreman'ın paylaştığı sunum yardımcısı)
    # ------------------------------------------------------------------

    def _assignments_to_dict(
        self, assignments: list[ForemanAssignment], plants_by_id: dict, chiefs_by_id: dict
    ) -> list[dict]:
        ordered = sorted(assignments, key=lambda a: plants_by_id[a.plant_id].sequence_number)
        items = []
        for a in ordered:
            plant = plants_by_id[a.plant_id]
            chief = chiefs_by_id[a.chief_id]
            items.append(
                {
                    "plant": {"id": str(plant.id), "name": plant.name},
                    "chief": {"id": str(chief.id), "name": f"{chief.first_name} {chief.last_name}"},
                }
            )
        return items

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_foremen(
        self,
        *,
        search: str | None,
        ids: str | None,
        plant_id: UUID | None,
        chief_id: UUID | None,
        shift_id: UUID | None,
        is_active: bool | None,
        level: str | None,
        outstanding: bool | None = None,
        sort_by: str,
        sort_dir: str,
        page: CursorParams,
        filters: Filters,
    ) -> dict:
        levels = get_performance_levels(self.db)

        if plant_id:
            filters.plant_ids = [plant_id]
        if chief_id:
            filters.chief_ids = [chief_id]
        if shift_id:
            filters.shift_ids = [shift_id]

        query_params = ForemanListQueryParams(
            search=search, ids=ids, is_active=is_active,
            factory_ids=filters.factory_ids, plant_ids=filters.plant_ids, chief_ids=filters.chief_ids,
            date_from=filters.date_from, date_to=filters.date_to,
        )
        all_foremen = self.repository.list(query_params)

        scores_by_foreman = {s.key: s for s in analytics.foreman_scores(self.db, filters)}
        bonuses_by_foreman = contribution_bonus.foreman_contribution_bonuses(
            self.db, filters.date_to, foreman_ids=[f.id for f in all_foremen]
        )

        foreman_ids = [f.id for f in all_foremen]
        assignments_by_foreman = self.repository.batch_assignments_for_foremen(foreman_ids)
        plants_by_id = self.repository.all_plants_by_id()
        chiefs_by_id = self.repository.all_chiefs_by_id()

        factory_plant_ids = (
            {p.id for p in plants_by_id.values() if p.factory_id in set(filters.factory_ids)}
            if filters.factory_ids
            else None
        )

        def matches_filters(a: ForemanAssignment) -> bool:
            if factory_plant_ids is not None and a.plant_id not in factory_plant_ids:
                return False
            if filters.plant_ids and a.plant_id not in set(filters.plant_ids):
                return False
            if filters.chief_ids and a.chief_id not in set(filters.chief_ids):
                return False
            return True

        def matching_assignments(fid: UUID) -> list[ForemanAssignment]:
            candidates = [
                a for a in assignments_by_foreman.get(fid, [])
                if a.start_date <= filters.date_to and (a.end_date is None or a.end_date >= filters.date_from)
            ]
            return [a for a in candidates if matches_filters(a)] or candidates

        full_items = []
        for f in all_foremen:
            assignments = matching_assignments(f.id)
            gs = scores_by_foreman.get(f.id)
            operational_score = gs.total_score if gs else 0.0
            bonus = bonuses_by_foreman.get(f.id)
            contribution_bonus_value = bonus.bonus if bonus else 0
            general_score = contribution_bonus.general_performance_score(operational_score, contribution_bonus_value)
            assignment_items = self._assignments_to_dict(assignments, plants_by_id, chiefs_by_id)
            min_plant_seq = min(
                (plants_by_id[a.plant_id].sequence_number for a in assignments), default=-1
            )
            chief_name = assignment_items[0]["chief"]["name"] if assignment_items else ""
            f_level = resolve_performance_level(general_score, levels)
            full_items.append(
                {
                    "id": str(f.id), "employee_number": f.employee_number,
                    "full_name": f"{f.first_name} {f.last_name}", "is_active": f.is_active,
                    "assignments": assignment_items,
                    "operational_score": round(operational_score, 2),
                    "contribution_bonus": contribution_bonus_value,
                    "general_performance_score": round(general_score, 2),
                    "is_reliable": gs.is_reliable if gs else False,
                    "level": foreman_level_payload(general_score, levels),
                    "_sort": {
                        "name": (turkish_sort_key(f.first_name), turkish_sort_key(f.last_name)),
                        "employee_number": f.employee_number,
                        "plant": min_plant_seq,
                        "chief": turkish_sort_key(chief_name) if chief_name else (),
                        "score": general_score,
                        "level": f_level.sort_order,
                        "reliability": gs.is_reliable if gs else False,
                    },
                }
            )

        if level:
            full_items = [it for it in full_items if it["level"]["name"] == level]
        if outstanding:
            full_items = [it for it in full_items if it["level"]["outstanding_performance"]]

        reverse = sort_dir == "desc"
        full_items.sort(key=lambda it: (it["_sort"][sort_by], it["id"]), reverse=reverse)
        for it in full_items:
            del it["_sort"]

        total = len(full_items)
        filter_sig = filter_signature(
            search, ids, plant_id, chief_id, shift_id, is_active, level, outstanding,
            filters.date_from, filters.date_to, filters.plant_ids, filters.factory_ids,
            filters.chief_ids, filters.shift_ids, filters.kpi_ids, filters.foreman_ids,
        )
        items, next_cursor, has_more = paginate_in_memory(
            full_items, id_key="id", cursor=page.cursor, limit=page.limit,
            sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig,
        )
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more, "total": total}

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    def get_foreman(self, foreman_id: UUID, filters: Filters) -> dict:
        foreman = self.repository.get(foreman_id)
        if foreman is None:
            raise ForemanNotFoundError("Formen bulunamadı.")

        levels = get_performance_levels(self.db)
        assignments = self.repository.assignments_as_of(foreman_id, filters.date_to)
        plants_by_id = self.repository.plants_by_ids({a.plant_id for a in assignments})
        chiefs_by_id = self.repository.chiefs_by_ids({a.chief_id for a in assignments})
        assignment_items = self._assignments_to_dict(assignments, plants_by_id, chiefs_by_id)
        primary_plant = min(
            (plants_by_id[a.plant_id] for a in assignments), key=lambda p: p.sequence_number, default=None
        )

        scope = resolve_foreman_scope(filters, primary_plant.id if primary_plant else None)

        all_scores = {s.key: s for s in analytics.foreman_scores(self.db, scope.operational)}
        my_score = all_scores.get(foreman_id)
        operational_score = my_score.total_score if my_score else 0.0

        all_bonuses = contribution_bonus.foreman_contribution_bonuses(self.db, scope.contribution_as_of)
        my_bonus = all_bonuses.get(foreman_id)
        contribution_bonus_value = my_bonus.bonus if my_bonus else 0
        general_score = contribution_bonus.general_performance_score(operational_score, contribution_bonus_value)

        def _general(s) -> float:
            b = all_bonuses.get(s.key)
            return contribution_bonus.general_performance_score(s.total_score, b.bonus if b else 0)

        ranked = sorted(all_scores.values(), key=_general, reverse=True)
        company_rank = next((i + 1 for i, s in enumerate(ranked) if s.key == foreman_id), None)

        plant_scores_by_id = (
            all_scores if scope.plant == scope.operational
            else {s.key: s for s in analytics.foreman_scores(self.db, scope.plant)}
        )
        plant_scores = sorted(plant_scores_by_id.values(), key=_general, reverse=True)
        plant_rank = next((i + 1 for i, s in enumerate(plant_scores) if s.key == foreman_id), None)

        return {
            "id": str(foreman.id), "employee_number": foreman.employee_number,
            "full_name": f"{foreman.first_name} {foreman.last_name}",
            "hire_date": foreman.hire_date.isoformat(), "is_active": foreman.is_active,
            "phone_number": foreman.phone_number, "email": foreman.email,
            "assignments": assignment_items,
            "operational_score": round(operational_score, 2),
            "contribution_bonus": contribution_bonus_value,
            "contribution_bonus_breakdown": [
                {
                    "work_id": str(e.work_id), "title": e.title, "work_type": e.work_type,
                    "score": e.score, "work_date": e.work_date.isoformat(),
                }
                for e in (my_bonus.entries if my_bonus else [])
            ],
            "general_performance_score": round(general_score, 2),
            "is_reliable": my_score.is_reliable if my_score else False,
            "in_scope": my_score is not None,
            "level": foreman_level_payload(general_score, levels),
            "company_rank": company_rank,
            "company_total": len(ranked),
            "plant_rank": plant_rank,
            "plant_total": len(plant_scores),
        }

    # ------------------------------------------------------------------
    # KPI / Performance (Slice 2)
    # ------------------------------------------------------------------

    def get_foreman_kpis(self, foreman_id: UUID, filters: Filters) -> dict:
        if self.repository.get(foreman_id) is None:
            raise ForemanNotFoundError("Formen bulunamadı.")

        rows = analytics.foreman_kpi_breakdown(self.db, filters, foreman_id)
        kpis_by_id = self.repository.all_kpis_by_id()
        plant_names_by_id = self.repository.plant_names_by_id()

        items = []
        for row in rows:
            kpi = kpis_by_id.get(row["kpi_id"])
            if kpi is None:
                continue
            avg_target = float(row["avg_target"]) if row["avg_target"] is not None else None
            avg_actual = float(row["avg_actual"]) if row["avg_actual"] is not None else None
            item = {
                "kpi_id": str(row["kpi_id"]), "code": kpi.code, "name": kpi.name,
                "description": kpi.description, "unit": kpi.unit,
                "avg_target": round(avg_target, kpi.decimal_places) if avg_target is not None else None,
                "avg_actual": round(avg_actual, kpi.decimal_places) if avg_actual is not None else None,
                "avg_raw_score": round(float(row["avg_raw_score"]), 2),
                "avg_capped_score": round(float(row["avg_capped_score"]), 2),
                "weight": float(row["weight"]),
                "weighted_contribution_sum": round(float(row["contrib_sum"]), 2),
                "record_count": row["record_count"],
                "calculation_version": row["calculation_version"],
                "calculation_period": {"date_from": filters.date_from.isoformat(), "date_to": filters.date_to.isoformat()},
                "data_quality_status": "complete" if row["record_count"] > 0 else "missing",
                "source_system": "SYNTHETIC",
                "evaluated_plant_count": row.get("evaluated_plant_count", 0),
                "plants": [
                    {
                        "plant_id": str(p["plant_id"]),
                        "plant_name": plant_names_by_id.get(p["plant_id"]),
                        "actual": p["actual"],
                        "target": p["target"],
                        "score": p["score"],
                        "weight": p["weight"],
                        "record_count": p["record_count"],
                    }
                    for p in row.get("plants", [])
                ],
            }
            if kpi.code == "AGIR_GITME" and avg_actual is not None:
                item["agir_gitme"] = kpi_presentation.agir_gitme_presentation(avg_actual, avg_target, kpi.decimal_places)
            elif kpi.code == "INKITA":
                item["inkita"] = kpi_presentation.inkita_presentation(item["avg_actual"])
            elif kpi.code == "PLANA_UYUM" and avg_actual is not None:
                planned_qty = row.get("denominator_sum")
                actual_qty = row.get("numerator_sum")
                item["plana_uyum"] = kpi_presentation.plana_uyum_period_presentation(
                    avg_actual, planned_qty, actual_qty, kpi.decimal_places
                )
            items.append(item)
        items.sort(key=lambda i: kpis_by_id[UUID(i["kpi_id"])].display_order)
        return {"items": items}

    def get_foreman_kpi_calculation_detail(self, foreman_id: UUID, kpi_id: UUID) -> dict:
        row = analytics.latest_foreman_kpi_record(self.db, foreman_id, kpi_id)
        if row is None:
            raise ForemanKpiRecordNotFoundError("Bu formen/KPI için hesaplanmış kayıt bulunamadı.")
        record, score = row
        kpi = self.repository.get_kpi(kpi_id)
        rule = self.repository.get_calculation_rule(score.calculation_rule_id)
        detail = {
            "performance_date": record.performance_date.isoformat(),
            "target_value": float(record.target_value) if record.target_value is not None else None,
            "actual_value": float(record.actual_value) if record.actual_value is not None else None,
            "unit": record.unit,
            "calculation_type": rule.calculation_type.value if rule else None,
            "calculation_rule_parameters": rule.parameters if rule else None,
            "calculation_version": score.calculation_version,
            "raw_score": float(score.raw_score),
            "capped_score": float(score.capped_score),
            "min_score": float(kpi.min_score) if kpi else None,
            "max_score": float(kpi.max_score) if kpi else None,
            "kpi_weight": float(score.kpi_weight),
            "weighted_contribution": float(score.weighted_contribution),
            "data_source": record.source_system.value,
            "source_record_id": record.source_record_id,
        }
        if kpi is not None and kpi.code == "PLANA_UYUM":
            planned_qty = float(record.denominator_value) if record.denominator_value is not None else None
            actual_qty = float(record.numerator_value) if record.numerator_value is not None else None
            detail["plana_uyum"] = kpi_presentation.plana_uyum_calculation_detail_presentation(
                planned_qty, actual_qty, rule.version if rule else None
            )
        return detail

    def get_foreman_trend(self, foreman_id: UUID, granularity: str, filters: Filters) -> dict:
        points = analytics.trend(self.db, filters, granularity, foreman_id=foreman_id)
        return {
            "granularity": granularity,
            "points": [
                {"date": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
                for p in points
            ],
        }

    # ------------------------------------------------------------------
    # Assignment history (Slice 3)
    # ------------------------------------------------------------------

    def get_assignment_history(self, foreman_id: UUID) -> dict:
        if self.repository.get(foreman_id) is None:
            raise ForemanNotFoundError("Formen bulunamadı.")

        assignments = self.repository.assignment_history(foreman_id)

        plants_by_id: dict = {}
        chiefs_by_id: dict = {}
        shifts_by_id: dict = {}
        if assignments:
            plants_by_id = self.repository.plants_by_ids({a.plant_id for a in assignments})
            chiefs_by_id = self.repository.chiefs_by_ids({a.chief_id for a in assignments})
            shifts_by_id = self.repository.shifts_by_ids({a.shift_id for a in assignments})

        items = []
        for a in assignments:
            plant = plants_by_id.get(a.plant_id)
            chief = chiefs_by_id.get(a.chief_id)
            shift = shifts_by_id.get(a.shift_id)
            items.append(
                {
                    "plant": plant.name if plant else None,
                    "chief": f"{chief.first_name} {chief.last_name}" if chief else None,
                    "shift": shift.name if shift else None,
                    "start_date": a.start_date.isoformat(),
                    "end_date": a.end_date.isoformat() if a.end_date else None,
                    "is_active": a.is_active,
                }
            )
        return {"items": items}
