from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ChiefNotFoundError
from app.core.pagination import decode_cursor, encode_cursor, filter_signature
from app.models.foreman import Chief
from app.repositories.chief_repository import ChiefRepository
from app.repositories.foreman_repository import ForemanRepository
from app.repositories.plant_repository import PlantRepository
from app.schemas.common import CursorParams, Filters
from app.services import analytics, contribution_bonus
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import foreman_level_payload, get_performance_levels, level_to_dict
from app.services.performance_scope import resolve_chief_scope

_COMPUTED_SORT_FIELDS = {"foreman_count", "score", "level", "reliability"}


def chief_group_code(employee_number: str) -> str:
    suffix = employee_number.rsplit("-", 1)[-1]
    if suffix.isdigit():
        return f"G{int(suffix):02d}"
    return f"G-{suffix}"


class ChiefService:
    def __init__(
        self,
        db: Session,
        repository: ChiefRepository | None = None,
        foreman_repository: ForemanRepository | None = None,
        plant_repository: PlantRepository | None = None,
    ):
        self.db = db
        self.repository = repository or ChiefRepository(db)
        self.foreman_repository = foreman_repository or ForemanRepository(db)
        self.plant_repository = plant_repository or PlantRepository(db)

    def _get_or_404(self, chief_id: UUID):
        chief = self.repository.get(chief_id)
        if chief is None:
            raise ChiefNotFoundError("Şef bulunamadı.")
        return chief

    def get_list(
        self,
        search: str | None,
        plant_id: UUID | None,
        is_active: bool | None,
        sort_by: str,
        sort_dir: str,
        page: CursorParams,
        filters: Filters,
    ) -> dict:
        if plant_id:
            filters.plant_ids = [plant_id]

        levels = get_performance_levels(self.db)

        filter_sig = filter_signature(
            search, plant_id, is_active,
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
            candidate_ids = self.repository.list_ids(filters, search, is_active)
            teams_by_chief = {t.chief_id: t for t in analytics.chief_team_scores(self.db, filters)}
            if sort_by == "foreman_count":
                sort_values = {
                    cid: teams_by_chief[cid].foreman_count if cid in teams_by_chief else 0
                    for cid in candidate_ids
                }
            elif sort_by == "score":
                sort_values = {
                    cid: teams_by_chief[cid].total_score if cid in teams_by_chief else 0.0
                    for cid in candidate_ids
                }
            elif sort_by == "level":
                sort_values = {
                    cid: resolve_performance_level(
                        teams_by_chief[cid].total_score if cid in teams_by_chief else 0.0, levels
                    ).sort_order
                    for cid in candidate_ids
                }
            else:
                sort_values = {
                    cid: teams_by_chief[cid].is_reliable if cid in teams_by_chief else False
                    for cid in candidate_ids
                }

        rows = self.repository.list_page(
            filters, search, is_active,
            sort_by=sort_by, sort_dir=sort_dir, sort_values=sort_values,
            cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit,
        )
        has_more = len(rows) > page.limit
        page_rows = rows[: page.limit]
        page_chiefs = [c for c, _ in page_rows]

        total = self.repository.count(filters, search, is_active)
        items = self._hydrate_chief_items(page_chiefs, filters, levels)

        next_cursor = None
        if has_more and page_rows:
            last_chief, last_sort_value = page_rows[-1]
            next_cursor = encode_cursor(
                sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig,
                sort_value=last_sort_value, id_=str(last_chief.id),
            )
        return {"items": items, "next_cursor": next_cursor, "has_more": has_more, "total": total}

    def _hydrate_chief_items(self, page_chiefs: list[Chief], filters: Filters, levels) -> list[dict]:
        if not page_chiefs:
            return []
        teams_by_chief = {t.chief_id: t for t in analytics.chief_team_scores(self.db, filters)}
        factories_by_id = self.plant_repository.all_factories_by_id()
        plants_by_chief = self.plant_repository.plants_grouped_by_chief_id()

        items = []
        for c in page_chiefs:
            team = teams_by_chief.get(c.id)
            score = team.total_score if team else 0.0
            chief_plants = sorted(plants_by_chief.get(c.id, []), key=lambda p: p.sequence_number)
            factory = factories_by_id.get(chief_plants[0].factory_id) if chief_plants else None
            level = resolve_performance_level(score, levels)
            items.append(
                {
                    "id": str(c.id),
                    "employee_number": c.employee_number,
                    "code": chief_group_code(c.employee_number),
                    "full_name": f"{c.first_name} {c.last_name}",
                    "is_active": c.is_active,
                    "plants": [{"id": str(p.id), "name": p.name} for p in chief_plants],
                    "factory": {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None,
                    "foreman_count": team.foreman_count if team else 0,
                    "total_score": round(score, 2),
                    "is_reliable": team.is_reliable if team else False,
                    "level": level_to_dict(level),
                }
            )
        return items

    def get_detail(self, chief_id: UUID, filters: Filters) -> dict:
        chief = self._get_or_404(chief_id)
        levels = get_performance_levels(self.db)
        chief_plants = sorted(self.plant_repository.plants_by_chief_id(chief.id), key=lambda p: p.sequence_number)
        factory = self.plant_repository.get_factory(chief_plants[0].factory_id) if chief_plants else None

        scope = resolve_chief_scope(filters)
        all_teams = analytics.chief_team_scores(self.db, scope.ranking)
        my_team = next((t for t in all_teams if t.chief_id == chief_id), None)
        score = my_team.total_score if my_team else 0.0

        ranked = sorted(all_teams, key=lambda t: t.total_score, reverse=True)
        company_rank = next((i + 1 for i, t in enumerate(ranked) if t.chief_id == chief_id), None)

        factory_chief_ids = (
            self.plant_repository.chief_ids_by_factory_id(factory.id) if factory else set()
        )
        factory_ranked = [t for t in ranked if t.chief_id in factory_chief_ids]
        factory_rank = next((i + 1 for i, t in enumerate(factory_ranked) if t.chief_id == chief_id), None)

        return {
            "id": str(chief.id),
            "employee_number": chief.employee_number,
            "code": chief_group_code(chief.employee_number),
            "full_name": f"{chief.first_name} {chief.last_name}",
            "hire_date": chief.hire_date.isoformat(),
            "is_active": chief.is_active,
            "phone_number": chief.phone_number,
            "email": chief.email,
            "plants": [{"id": str(p.id), "name": p.name} for p in chief_plants],
            "factory": {"id": str(factory.id), "code": factory.code, "name": factory.name} if factory else None,
            "foreman_count": my_team.foreman_count if my_team else 0,
            "total_score": round(score, 2),
            "is_reliable": my_team.is_reliable if my_team else False,
            "level": level_to_dict(resolve_performance_level(score, levels)),
            "company_rank": company_rank,
            "company_total": len(ranked),
            "factory_rank": factory_rank,
            "factory_total": len(factory_ranked),
        }

    def get_foremen(self, chief_id: UUID, filters: Filters) -> dict:
        self._get_or_404(chief_id)
        filters.chief_ids = [chief_id]
        levels = get_performance_levels(self.db)

        team = next((t for t in analytics.chief_team_scores(self.db, filters) if t.chief_id == chief_id), None)
        scores = team.foreman_scores if team else []
        foremen_by_id = self.foreman_repository.foremen_by_ids([s.key for s in scores])
        bonuses_by_foreman = contribution_bonus.foreman_contribution_bonuses(
            self.db, filters.date_to, foreman_ids=[s.key for s in scores]
        )
        general_by_key = {
            s.key: contribution_bonus.general_performance_score(
                s.total_score, bonuses_by_foreman[s.key].bonus if s.key in bonuses_by_foreman else 0
            )
            for s in scores
        }

        items = []
        for s in sorted(scores, key=lambda x: general_by_key[x.key], reverse=True):
            f = foremen_by_id.get(s.key)
            items.append(
                {
                    "id": str(s.key),
                    "employee_number": f.employee_number if f else None,
                    "full_name": f"{f.first_name} {f.last_name}" if f else None,
                    "operational_score": round(s.total_score, 2),
                    "contribution_bonus": bonuses_by_foreman[s.key].bonus if s.key in bonuses_by_foreman else 0,
                    "general_performance_score": round(general_by_key[s.key], 2),
                    "is_reliable": s.is_reliable,
                    "level": foreman_level_payload(general_by_key[s.key], levels),
                }
            )
        return {"items": items}

    def get_kpis(self, chief_id: UUID, filters: Filters) -> dict:
        self._get_or_404(chief_id)
        filters.chief_ids = [chief_id]

        rows = analytics.kpi_breakdown(self.db, filters)
        kpis_by_id = self.foreman_repository.all_kpis_by_id()

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
            }
            if kpi.code == "AGIR_GITME" and avg_actual is not None:
                direction = "OVERWEIGHT" if avg_actual > 0 else ("UNDERWEIGHT" if avg_actual < 0 else "ON_TARGET")
                item["agir_gitme"] = {
                    "signed_value": round(avg_actual, kpi.decimal_places),
                    "absolute_value": round(abs(avg_actual), kpi.decimal_places),
                    "direction": direction,
                    "ratio_to_target": round(abs(avg_actual) / avg_target, 4) if avg_target else None,
                }
            elif kpi.code == "INKITA":
                item["inkita"] = {
                    "included_total": item["avg_actual"],
                    "included_components": ["TECHNICAL", "MANUFACTURING"],
                    "excluded_components": ["OTHER"],
                    "note": "Diğer duruş süresi puana dahil edilmez.",
                }
            elif kpi.code == "PLANA_UYUM" and avg_actual is not None:
                planned_qty = row.get("denominator_sum")
                actual_qty = row.get("numerator_sum")
                kg_diff = (actual_qty - planned_qty) if (planned_qty is not None and actual_qty is not None) else None
                signed_pct_deviation = (kg_diff / planned_qty * 100.0) if (kg_diff is not None and planned_qty) else None
                direction = (
                    "ABOVE_PLAN" if (signed_pct_deviation or 0) > 0
                    else ("BELOW_PLAN" if (signed_pct_deviation or 0) < 0 else "ON_PLAN")
                )
                item["plana_uyum"] = {
                    "avg_attainment_pct": round(avg_actual, kpi.decimal_places),
                    "planned_qty": round(planned_qty, 2) if planned_qty is not None else None,
                    "actual_qty": round(actual_qty, 2) if actual_qty is not None else None,
                    "kg_diff": round(kg_diff, 2) if kg_diff is not None else None,
                    "signed_pct_deviation": round(signed_pct_deviation, 2) if signed_pct_deviation is not None else None,
                    "direction": direction,
                }
            items.append(item)
        items.sort(key=lambda i: kpis_by_id[UUID(i["kpi_id"])].display_order)
        return {"items": items}

    def get_foreman_comparison(self, chief_id: UUID, filters: Filters) -> dict:
        self._get_or_404(chief_id)
        filters.chief_ids = [chief_id]
        levels = get_performance_levels(self.db)

        team = next((t for t in analytics.chief_team_scores(self.db, filters) if t.chief_id == chief_id), None)
        scores = team.foreman_scores if team else []
        foreman_ids = [s.key for s in scores]
        foremen_by_id = self.foreman_repository.foremen_by_ids(foreman_ids)
        bonuses_by_foreman = contribution_bonus.foreman_contribution_bonuses(
            self.db, filters.date_to, foreman_ids=foreman_ids
        )
        general_by_key = {
            s.key: contribution_bonus.general_performance_score(
                s.total_score, bonuses_by_foreman[s.key].bonus if s.key in bonuses_by_foreman else 0
            )
            for s in scores
        }

        kpi_rows = analytics.kpi_breakdown(self.db, filters)
        kpis_by_id = self.foreman_repository.all_kpis_by_id()

        kpi_meta = []
        group_kpi_scores: dict[str, float] = {}
        foreman_kpi_matrix: dict[UUID, dict[UUID, dict]] = defaultdict(dict)

        for row in kpi_rows:
            kpi = kpis_by_id.get(row["kpi_id"])
            if kpi is None:
                continue
            kpi_meta.append(kpi)
            group_kpi_scores[str(kpi.id)] = round(float(row["avg_capped_score"]), 2)
            reference_target = row["avg_target"] if row["avg_target"] is not None else float(kpi.default_target_value)
            for fv in analytics.foreman_kpi_values(self.db, filters, kpi, reference_target):
                foreman_kpi_matrix[fv.foreman_id][kpi.id] = {
                    "score": round(fv.capped_score, 2),
                    "actual": round(fv.avg_actual, kpi.decimal_places),
                    "target": round(fv.avg_target, kpi.decimal_places),
                    "record_count": fv.record_count,
                }

        kpi_meta.sort(key=lambda k: k.display_order)

        foremen_out = []
        for s in scores:
            f = foremen_by_id.get(s.key)
            row_scores = foreman_kpi_matrix.get(s.key, {})
            foremen_out.append(
                {
                    "id": str(s.key),
                    "employee_number": f.employee_number if f else None,
                    "full_name": f"{f.first_name} {f.last_name}" if f else None,
                    "total_score": round(general_by_key[s.key], 2),
                    "is_reliable": s.is_reliable,
                    "level": foreman_level_payload(general_by_key[s.key], levels),
                    "kpi_scores": {str(kpi.id): row_scores.get(kpi.id) for kpi in kpi_meta},
                }
            )
        foremen_out.sort(key=lambda it: it["total_score"], reverse=True)

        return {
            "kpis": [
                {
                    "kpi_id": str(kpi.id),
                    "code": kpi.code,
                    "name": kpi.name,
                    "unit": kpi.unit,
                    "decimal_places": kpi.decimal_places,
                    "weight": float(kpi.weight),
                }
                for kpi in kpi_meta
            ],
            "group_average": {
                "total_score": round(team.total_score if team else 0.0, 2),
                "kpi_scores": group_kpi_scores,
            },
            "foremen": foremen_out,
        }

    def get_trend(self, chief_id: UUID, granularity: str, filters: Filters) -> dict:
        self._get_or_404(chief_id)
        filters.chief_ids = [chief_id]
        points = analytics.trend(self.db, filters, granularity)
        return {
            "granularity": granularity,
            "points": [
                {"date": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
                for p in points
            ],
        }
