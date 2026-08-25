from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.foreman_repository import ForemanRepository
from app.schemas.common import Filters
from app.services import analytics
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels, level_to_dict


def _kpi_summary_items(kpi_sum: list, kpis_by_id: dict) -> list[dict]:
    return [
        {
            "kpi_id": str(i.kpi_id),
            "code": kpis_by_id[i.kpi_id].code if i.kpi_id in kpis_by_id else None,
            "name": kpis_by_id[i.kpi_id].name if i.kpi_id in kpis_by_id else None,
            "unit": kpis_by_id[i.kpi_id].unit if i.kpi_id in kpis_by_id else None,
            "avg_score": round(i.avg_capped_score, 2),
            "avg_target": round(i.avg_target, 2) if i.avg_target is not None else None,
            "avg_actual": round(i.avg_actual, 2) if i.avg_actual is not None else None,
            "record_count": i.record_count,
        }
        for i in kpi_sum
    ]


def _shift_comparison_items(sh_scores: list, shifts_by_id: dict, levels: list) -> list[dict]:
    scores = sorted(sh_scores, key=lambda s: shifts_by_id[s.key].sequence if s.key in shifts_by_id else 0)
    return [
        {
            "shift_id": str(s.key),
            "code": shifts_by_id[s.key].code if s.key in shifts_by_id else None,
            "name": shifts_by_id[s.key].name if s.key in shifts_by_id else None,
            "total_score": round(s.total_score, 2),
            "record_count": s.record_count,
            "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
        }
        for s in scores
    ]


class DashboardComparisonService:
    """`GET /dashboard/kpi-summary`, `.../plant-ranking` ve `.../shift-comparison`
    orkestrasyonu.

    Yalnızca bu üç ranking/comparison read akışını kapsar. Scoring işlemlerini
    `analytics.*`, boyut lookup'larını `ForemanRepository` yönetir; burada iş hesabı
    çoğaltılmaz, yalnızca orkestrasyon ve response mapping yapılır.
    """

    def __init__(self, db: Session, repository: ForemanRepository | None = None):
        self.db = db
        self.repository = repository or ForemanRepository(db)

    def kpi_summary(self, filters: Filters) -> dict:
        items = analytics.kpi_summary(self.db, filters)
        kpis_by_id = self.repository.all_kpis_by_id()
        return {"items": _kpi_summary_items(items, kpis_by_id)}

    def plant_ranking(self, filters: Filters, order: str, limit: int) -> dict:
        levels = get_performance_levels(self.db)
        scores = analytics.plant_scores(self.db, filters)
        plants_by_id = self.repository.all_plants_by_id()
        scores.sort(key=lambda s: s.total_score, reverse=(order == "desc"))
        scores = scores[:limit]
        return {
            "items": [
                {
                    "plant_id": str(s.key),
                    "code": plants_by_id[s.key].code if s.key in plants_by_id else None,
                    "name": plants_by_id[s.key].name if s.key in plants_by_id else None,
                    "total_score": round(s.total_score, 2),
                    "is_reliable": s.is_reliable,
                    "level": level_to_dict(resolve_performance_level(s.total_score, levels)),
                }
                for s in scores
            ]
        }

    def shift_comparison(self, filters: Filters) -> dict:
        levels = get_performance_levels(self.db)
        scores = analytics.shift_scores(self.db, filters)
        shifts_by_id = self.repository.all_shifts_by_id()
        return {"items": _shift_comparison_items(scores, shifts_by_id, levels)}
