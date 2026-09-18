from __future__ import annotations

from dataclasses import replace
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ForemanKpiRecordNotFoundError, ForemanNotFoundError
from app.core.pagination import decode_cursor, encode_cursor, filter_signature
from app.models.foreman import ForemanAssignment
from app.repositories.foreman_repository import ForemanListQueryParams, ForemanRepository
from app.schemas.common import CursorParams, Filters
from app.services import analytics, contribution_bonus, kpi_presentation
from app.services.kpi_engine import is_outstanding_performance, resolve_performance_level
from app.services.level_lookup import foreman_level_payload, get_performance_levels
from app.services.performance_scope import resolve_foreman_scope

_COMPUTED_SORT_FIELDS = {"plant", "chief", "score", "level", "reliability"}


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

        filter_sig = filter_signature(
            search, ids, plant_id, chief_id, shift_id, is_active, level, outstanding,
            filters.date_from, filters.date_to, filters.plant_ids, filters.factory_ids,
            filters.chief_ids, filters.shift_ids, filters.kpi_ids, filters.foreman_ids,
        )
        cursor_value = cursor_id = None
        if page.cursor is not None:
            state = decode_cursor(page.cursor, sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig)
            cursor_value = state.sort_value
            cursor_id = UUID(state.id)

        candidate_ids = self.repository.list_ids(query_params)

        plants_by_id = self.repository.all_plants_by_id()
        chiefs_by_id = self.repository.all_chiefs_by_id()

        factory_plant_ids = (
            {p.id for p in plants_by_id.values() if p.factory_id in set(filters.factory_ids)}
            if filters.factory_ids is not None
            else None
        )

        def matches_filters(a: ForemanAssignment) -> bool:
            if factory_plant_ids is not None and a.plant_id not in factory_plant_ids:
                return False
            if filters.plant_ids is not None and a.plant_id not in set(filters.plant_ids):
                return False
            if filters.chief_ids is not None and a.chief_id not in set(filters.chief_ids):
                return False
            return True

        assignments_by_foreman: dict[UUID, list[ForemanAssignment]] = {}

        def matching_assignments(fid: UUID) -> list[ForemanAssignment]:
            candidates = [
                a for a in assignments_by_foreman.get(fid, [])
                if a.start_date <= filters.date_to and (a.end_date is None or a.end_date >= filters.date_from)
            ]
            return [a for a in candidates if matches_filters(a)] or candidates

        general_scores: dict[UUID, float] = {}
        reliabilities: dict[UUID, bool] = {}
        scores_by_foreman: dict[UUID, object] = {}
        bonuses_by_foreman: dict[UUID, object] = {}
        sort_values = None

        # `level`/`outstanding` filtreleri ve computed-field sıralaması (plant/chief/score/
        # level/reliability) TÜM adayların skorunu gerektirir — DB sayfalaması yapıldıktan
        # sonra skor hesaplamak global sıralama/filtrelemeyi bozar. Bunlar talep edilmemişse
        # (varsayılan sort_by="name") skor/bonus/atama hesaplaması yalnızca sayfa için yapılır —
        # aynı desen plant_service.PlantService._hydrate_plant_items'ta da kullanılıyor.
        needs_full_candidate_scores = bool(level) or bool(outstanding) or sort_by in _COMPUTED_SORT_FIELDS

        if needs_full_candidate_scores:
            scores_by_foreman = {s.key: s for s in analytics.foreman_scores(self.db, filters)}
            bonuses_by_foreman = contribution_bonus.foreman_contribution_bonuses(
                self.db, filters.date_to, foreman_ids=candidate_ids
            )
            assignments_by_foreman = self.repository.batch_assignments_for_foremen(candidate_ids)

            level_objs: dict[UUID, object] = {}
            min_plant_seqs: dict[UUID, int] = {}
            chief_names: dict[UUID, str] = {}

            for fid in candidate_ids:
                assignments = matching_assignments(fid)
                gs = scores_by_foreman.get(fid)
                operational_score = gs.total_score if gs else 0.0
                bonus = bonuses_by_foreman.get(fid)
                contribution_bonus_value = bonus.bonus if bonus else 0
                general_score = contribution_bonus.general_performance_score(operational_score, contribution_bonus_value)
                min_plant_seq = min((plants_by_id[a.plant_id].sequence_number for a in assignments), default=-1)
                ordered = sorted(assignments, key=lambda a: plants_by_id[a.plant_id].sequence_number)
                chief_name = (
                    f"{chiefs_by_id[ordered[0].chief_id].first_name} {chiefs_by_id[ordered[0].chief_id].last_name}"
                    if ordered else ""
                )

                general_scores[fid] = general_score
                level_objs[fid] = resolve_performance_level(general_score, levels)
                min_plant_seqs[fid] = min_plant_seq
                chief_names[fid] = chief_name
                reliabilities[fid] = gs.is_reliable if gs else False

            if level or outstanding:
                filtered_ids = []
                for fid in candidate_ids:
                    if level and level_objs[fid].name != level:
                        continue
                    if outstanding and not is_outstanding_performance(general_scores[fid]):
                        continue
                    filtered_ids.append(fid)
                candidate_ids = filtered_ids
                query_params = replace(query_params, id_allowlist=candidate_ids)

            if sort_by in _COMPUTED_SORT_FIELDS:
                if sort_by == "plant":
                    sort_values = {fid: min_plant_seqs[fid] for fid in candidate_ids}
                elif sort_by == "chief":
                    sort_values = {fid: chief_names[fid] for fid in candidate_ids}
                elif sort_by == "score":
                    sort_values = {fid: general_scores[fid] for fid in candidate_ids}
                elif sort_by == "level":
                    sort_values = {fid: level_objs[fid].sort_order for fid in candidate_ids}
                else:
                    sort_values = {fid: reliabilities[fid] for fid in candidate_ids}

        rows = self.repository.list_page(
            query_params, sort_by=sort_by, sort_dir=sort_dir, sort_values=sort_values,
            cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit,
        )
        has_more = len(rows) > page.limit
        page_rows = rows[: page.limit]
        page_foremen = [f for f, _ in page_rows]

        total = self.repository.count(query_params)

        if not needs_full_candidate_scores:
            # Global skor/filtre gerekmiyor: yalnızca DB'nin döndürdüğü sayfa için hesapla.
            # analytics.foreman_scores'u foreman_ids ile daraltmak GROUP BY foreman_id
            # sonucunu değiştirmez (her grup diğerlerinden bağımsız aggregate edilir) —
            # yalnızca taranan satır sayısını sayfa boyutuna indirger.
            page_ids = [f.id for f in page_foremen]
            assignments_by_foreman = self.repository.batch_assignments_for_foremen(page_ids)
            if page_ids:
                page_filters = replace(filters, foreman_ids=page_ids)
                scores_by_foreman = {s.key: s for s in analytics.foreman_scores(self.db, page_filters)}
                bonuses_by_foreman = contribution_bonus.foreman_contribution_bonuses(
                    self.db, filters.date_to, foreman_ids=page_ids
                )
            for f in page_foremen:
                gs = scores_by_foreman.get(f.id)
                bonus = bonuses_by_foreman.get(f.id)
                operational_score = gs.total_score if gs else 0.0
                contribution_bonus_value = bonus.bonus if bonus else 0
                general_scores[f.id] = contribution_bonus.general_performance_score(operational_score, contribution_bonus_value)

        items = []
        for f in page_foremen:
            assignments = matching_assignments(f.id)
            assignment_items = self._assignments_to_dict(assignments, plants_by_id, chiefs_by_id)
            gs = scores_by_foreman.get(f.id)
            bonus = bonuses_by_foreman.get(f.id)
            items.append(
                {
                    "id": str(f.id), "employee_number": f.employee_number,
                    "full_name": f"{f.first_name} {f.last_name}", "is_active": f.is_active,
                    "assignments": assignment_items,
                    "operational_score": round(gs.total_score if gs else 0.0, 2),
                    "contribution_bonus": bonus.bonus if bonus else 0,
                    "general_performance_score": round(general_scores[f.id], 2),
                    "is_reliable": gs.is_reliable if gs else False,
                    "level": foreman_level_payload(general_scores[f.id], levels),
                }
            )

        next_cursor = None
        if has_more and page_rows:
            last_foreman, last_sort_value = page_rows[-1]
            next_cursor = encode_cursor(
                sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig,
                sort_value=last_sort_value, id_=str(last_foreman.id),
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
    # KPI / Performance
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
    # Assignment history
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
