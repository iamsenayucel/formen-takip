from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.foreman_repository import ForemanRepository
from app.schemas.common import Filters
from app.services import analytics
from app.services.foreman_performance_metrics import compute_general_foreman_scores
from app.services.kpi_engine import is_outstanding_performance, resolve_performance_level
from app.services.level_lookup import foreman_level_payload, get_performance_levels, level_to_dict


def _foreman_ranking_items(
    f_scores: list, general_by_key: dict, bonuses_by_foreman: dict, foremen_by_id: dict, levels: list, order: str, limit: int
) -> list[dict]:
    scores = sorted(f_scores, key=lambda s: general_by_key[s.key], reverse=(order == "desc"))[:limit]
    return [
        {
            "foreman_id": str(s.key),
            "employee_number": foremen_by_id[s.key].employee_number if s.key in foremen_by_id else None,
            "full_name": (
                f"{foremen_by_id[s.key].first_name} {foremen_by_id[s.key].last_name}" if s.key in foremen_by_id else None
            ),
            "operational_score": round(s.total_score, 2),
            "contribution_bonus": bonuses_by_foreman[s.key].bonus if s.key in bonuses_by_foreman else 0,
            "general_performance_score": round(general_by_key[s.key], 2),
            "is_reliable": s.is_reliable,
            "level": foreman_level_payload(general_by_key[s.key], levels),
        }
        for s in scores
    ]


def _foreman_trend_items(current_scores: list, previous_scores: list, foremen_by_id: dict, levels: list, direction: str, limit: int) -> list[dict]:
    current_by_key = {s.key: s for s in current_scores}
    previous_by_key = {s.key: s for s in previous_scores}
    deltas = [
        (foreman_id, current, previous_by_key[foreman_id])
        for foreman_id, current in current_by_key.items()
        if foreman_id in previous_by_key
    ]
    deltas.sort(key=lambda item: item[1].total_score - item[2].total_score, reverse=(direction == "improving"))
    deltas = deltas[:limit]
    return [
        {
            "foreman_id": str(foreman_id),
            "employee_number": foremen_by_id[foreman_id].employee_number if foreman_id in foremen_by_id else None,
            "full_name": (
                f"{foremen_by_id[foreman_id].first_name} {foremen_by_id[foreman_id].last_name}"
                if foreman_id in foremen_by_id else None
            ),
            "operational_score": round(current.total_score, 2),
            "previous_operational_score": round(previous.total_score, 2),
            "delta": round(current.total_score - previous.total_score, 2),
            "is_reliable": current.is_reliable and previous.is_reliable,
            "level": foreman_level_payload(current.total_score, levels),
        }
        for foreman_id, current, previous in deltas
    ]


def _distribution_payload(f_scores: list, general_by_key: dict, levels: list) -> dict:
    general_scores = [general_by_key[s.key] for s in f_scores]
    counts = {lv.name: 0 for lv in levels}
    for gs in general_scores:
        level = resolve_performance_level(gs, levels)
        counts[level.name] += 1
    outstanding_count = sum(1 for gs in general_scores if is_outstanding_performance(gs))
    return {
        "items": [
            {**level_to_dict(lv), "count": counts[lv.name]}
            for lv in sorted(levels, key=lambda lv: lv.sort_order)
        ],
        "outstanding_count": outstanding_count,
    }


class DashboardForemanService:
    """Formen ranking, trend ranking ve performance distribution orkestrasyonu.

    foreman_ranking ile performance_distribution ortak general-score pipeline'ını
    `compute_general_foreman_scores` üzerinden paylaşır. foreman_trend_ranking yalnızca
    OPERATIONAL score karşılaştırdığı için bu pipeline'ı bilerek kullanmaz; contribution
    bonus ve general score hesaplamak gereksizdir.
    """

    def __init__(self, db: Session, repository: ForemanRepository | None = None):
        self.db = db
        self.repository = repository or ForemanRepository(db)

    def foreman_ranking(self, filters: Filters, order: str, limit: int) -> dict:
        levels = get_performance_levels(self.db)
        scores, bonuses_by_foreman, general_by_key = compute_general_foreman_scores(self.db, filters)
        foremen_by_id = self.repository.all_foremen_by_id()
        return {
            "items": _foreman_ranking_items(
                scores, general_by_key, bonuses_by_foreman, foremen_by_id, levels, order, limit
            )
        }

    def foreman_trend_ranking(self, filters: Filters, previous_filters: Filters, direction: str, limit: int) -> dict:
        levels = get_performance_levels(self.db)
        current_scores = analytics.foreman_scores(self.db, filters)
        previous_scores = analytics.foreman_scores(self.db, previous_filters)
        foremen_by_id = self.repository.all_foremen_by_id()
        return {
            "items": _foreman_trend_items(current_scores, previous_scores, foremen_by_id, levels, direction, limit)
        }

    def performance_distribution(self, filters: Filters) -> dict:
        levels = get_performance_levels(self.db)
        scores, _bonuses_by_foreman, general_by_key = compute_general_foreman_scores(self.db, filters)
        return _distribution_payload(scores, general_by_key, levels)
