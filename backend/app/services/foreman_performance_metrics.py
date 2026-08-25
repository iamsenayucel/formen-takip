from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.schemas.common import Filters
from app.services import analytics, contribution_bonus
from app.services.analytics import GroupScore
from app.services.contribution_bonus import ForemanBonus


def compute_general_foreman_scores(
    db: Session, filters: Filters
) -> tuple[list[GroupScore], dict[UUID, ForemanBonus], dict[UUID, float]]:
    scores = analytics.foreman_scores(db, filters)
    bonuses_by_foreman = contribution_bonus.foreman_contribution_bonuses(
        db, filters.date_to, foreman_ids=[s.key for s in scores]
    )
    general_by_key = {
        s.key: contribution_bonus.general_performance_score(
            s.total_score, bonuses_by_foreman[s.key].bonus if s.key in bonuses_by_foreman else 0
        )
        for s in scores
    }
    return scores, bonuses_by_foreman, general_by_key
