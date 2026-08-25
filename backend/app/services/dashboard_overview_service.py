from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus
from app.models.integration import IntegrationRun
from app.models.organization import Plant
from app.models.performance import PerformanceRecord
from app.repositories.foreman_repository import ForemanRepository
from app.schemas.common import Filters
from app.services import analytics
from app.services.dashboard_comparison_service import _kpi_summary_items, _shift_comparison_items
from app.services.foreman_performance_metrics import compute_general_foreman_scores
from app.services.dashboard_foreman_service import _distribution_payload, _foreman_ranking_items, _foreman_trend_items
from app.services.kpi_engine import is_outstanding_performance, resolve_performance_level
from app.services.level_lookup import get_performance_levels


@dataclass
class _DashboardBase:
    levels: list
    f_scores: list
    bonuses_by_foreman: dict
    general_by_key: dict
    p_scores: list
    sh_scores: list
    kpi_sum: list
    foremen_by_id: dict
    plants_by_id: dict
    shifts_by_id: dict
    kpis_by_id: dict


class DashboardOverviewService:
    """`GET /dashboard/summary` ve `GET /dashboard/snapshot` orkestrasyonu.

    Diğer dashboard service'lerini çağırıp aynı aggregation'ı tekrarlamaz. Yalnızca
    side-effect içermeyen mapping fonksiyonları ile ortak `compute_general_foreman_scores`
    primitive'ini kullanır; service'ler arasında orkestrasyon bağı kurmaz.
    """

    def __init__(self, db: Session, repository: ForemanRepository | None = None):
        self.db = db
        self.repository = repository or ForemanRepository(db)

    def _compute_base(self, filters: Filters) -> _DashboardBase:
        levels = get_performance_levels(self.db)
        f_scores, bonuses_by_foreman, general_by_key = compute_general_foreman_scores(self.db, filters)
        return _DashboardBase(
            levels=levels,
            f_scores=f_scores,
            bonuses_by_foreman=bonuses_by_foreman,
            general_by_key=general_by_key,
            p_scores=analytics.plant_scores(self.db, filters),
            sh_scores=analytics.shift_scores(self.db, filters),
            kpi_sum=analytics.kpi_summary(self.db, filters),
            foremen_by_id=self.repository.all_foremen_by_id(),
            plants_by_id=self.repository.all_plants_by_id(),
            shifts_by_id=self.repository.all_shifts_by_id(),
            kpis_by_id=self.repository.all_kpis_by_id(),
        )

    def _summary_payload(self, filters: Filters, base: _DashboardBase) -> dict:
        total_plants = self.db.scalar(select(func.count()).select_from(Plant))
        active_plants = self.db.scalar(select(func.count()).select_from(Plant).where(Plant.is_active.is_(True)))

        total_active_foremen = len(base.f_scores)
        company_avg = sum(base.general_by_key.values()) / len(base.f_scores) if base.f_scores else 0.0

        above_target = sum(1 for v in base.general_by_key.values() if v >= 100)
        below_target = sum(1 for v in base.general_by_key.values() if v < 100)
        critical = sum(1 for v in base.general_by_key.values() if resolve_performance_level(v, base.levels).name == "Kritik")
        successful = sum(
            1 for v in base.general_by_key.values() if resolve_performance_level(v, base.levels).name == "Başarılı"
        )
        outstanding = sum(1 for v in base.general_by_key.values() if is_outstanding_performance(v))

        best_plant = max(base.p_scores, key=lambda s: s.total_score, default=None)
        worst_plant = min(base.p_scores, key=lambda s: s.total_score, default=None)

        best_shift = max(base.sh_scores, key=lambda s: s.total_score, default=None)
        worst_shift = min(base.sh_scores, key=lambda s: s.total_score, default=None)

        best_foreman_key = max(base.general_by_key, key=lambda k: base.general_by_key[k], default=None)

        weakest_kpi = min(base.kpi_sum, key=lambda s: s.avg_capped_score, default=None)

        missing_plants = self.db.scalar(
            select(func.count(func.distinct(PerformanceRecord.plant_id))).where(
                PerformanceRecord.performance_date >= filters.date_from,
                PerformanceRecord.performance_date <= filters.date_to,
                PerformanceRecord.data_quality_status.in_(
                    [DataQualityStatus.MISSING, DataQualityStatus.NEEDS_SOURCE_CORRECTION]
                ),
            )
        )

        last_run = self.db.scalar(select(IntegrationRun).order_by(IntegrationRun.finished_at.desc()).limit(1))

        def plant_ref(gs):
            if gs is None:
                return None
            p = base.plants_by_id.get(gs.key)
            return {
                "id": str(gs.key), "name": p.name if p else None, "code": p.code if p else None,
                "score": round(gs.total_score, 2),
            }

        def shift_ref(gs):
            if gs is None:
                return None
            s = base.shifts_by_id.get(gs.key)
            return {"id": str(gs.key), "name": s.name if s else None, "score": round(gs.total_score, 2)}

        def foreman_ref(foreman_id):
            if foreman_id is None:
                return None
            f = base.foremen_by_id.get(foreman_id)
            return {
                "id": str(foreman_id),
                "name": f"{f.first_name} {f.last_name}" if f else None,
                "employee_number": f.employee_number if f else None,
                "score": round(base.general_by_key[foreman_id], 2),
            }

        return {
            "total_plants": total_plants,
            "active_plants": active_plants,
            "total_active_foremen": total_active_foremen,
            "avg_company_score": round(company_avg, 2),
            "foremen_above_target": above_target,
            "foremen_below_target": below_target,
            "foremen_critical": critical,
            "foremen_successful": successful,
            "foremen_outstanding": outstanding,
            "best_plant": plant_ref(best_plant),
            "worst_plant": plant_ref(worst_plant),
            "best_shift": shift_ref(best_shift),
            "worst_shift": shift_ref(worst_shift),
            "best_foreman": foreman_ref(best_foreman_key),
            "weakest_kpi": (
                {
                    "id": str(weakest_kpi.kpi_id), "name": base.kpis_by_id[weakest_kpi.kpi_id].name,
                    "avg_score": round(weakest_kpi.avg_capped_score, 2),
                }
                if weakest_kpi else None
            ),
            "plants_with_missing_data": missing_plants or 0,
            "last_sync_at": last_run.finished_at.isoformat() if last_run and last_run.finished_at else None,
            "data_source": "SYNTHETIC",
        }

    def summary(self, filters: Filters) -> dict:
        base = self._compute_base(filters)
        return self._summary_payload(filters, base)

    def snapshot(
        self, filters: Filters, previous_filters: Filters, foreman_ranking_limit: int, foreman_trend_limit: int
    ) -> dict:
        base = self._compute_base(filters)
        f_scores_previous = analytics.foreman_scores(self.db, previous_filters)

        return {
            "summary": self._summary_payload(filters, base),
            "kpi_summary": {"items": _kpi_summary_items(base.kpi_sum, base.kpis_by_id)},
            "shift_comparison": {"items": _shift_comparison_items(base.sh_scores, base.shifts_by_id, base.levels)},
            "foreman_ranking": {
                "top": {"items": _foreman_ranking_items(
                    base.f_scores, base.general_by_key, base.bonuses_by_foreman, base.foremen_by_id, base.levels,
                    "desc", foreman_ranking_limit,
                )},
                "bottom": {"items": _foreman_ranking_items(
                    base.f_scores, base.general_by_key, base.bonuses_by_foreman, base.foremen_by_id, base.levels,
                    "asc", foreman_ranking_limit,
                )},
            },
            "foreman_trend_ranking": {
                "improving": {"items": _foreman_trend_items(
                    base.f_scores, f_scores_previous, base.foremen_by_id, base.levels, "improving", foreman_trend_limit
                )},
                "declining": {"items": _foreman_trend_items(
                    base.f_scores, f_scores_previous, base.foremen_by_id, base.levels, "declining", foreman_trend_limit
                )},
            },
            "performance_distribution": _distribution_payload(base.f_scores, base.general_by_key, base.levels),
        }
