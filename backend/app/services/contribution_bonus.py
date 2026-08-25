from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contribution import ContributionWork, ContributionWorkForeman
from app.models.enums import ContributionStatus

CONTRIBUTION_BONUS_WINDOW_DAYS = 90
MAX_GENERAL_SCORE = 120.0


@dataclass
class ContributionBonusEntry:
    work_id: UUID
    title: str
    work_type: str | None
    score: int
    work_date: date


@dataclass
class ForemanBonus:
    bonus: int
    entries: list[ContributionBonusEntry]


def foreman_contribution_bonuses(
    db: Session, as_of: date, foreman_ids: Collection[UUID] | None = None
) -> dict[UUID, ForemanBonus]:
    if foreman_ids is not None and not foreman_ids:
        return {}

    window_start = as_of - timedelta(days=CONTRIBUTION_BONUS_WINDOW_DAYS)
    stmt = (
        select(ContributionWork, ContributionWorkForeman.foreman_id)
        .join(ContributionWorkForeman, ContributionWorkForeman.work_id == ContributionWork.id)
        .where(
            ContributionWork.status == ContributionStatus.PUBLISHED,
            ContributionWork.contribution_score.isnot(None),
            ContributionWork.work_date.isnot(None),
            ContributionWork.work_date >= window_start,
            ContributionWork.work_date <= as_of,
        )
    )
    if foreman_ids is not None:
        stmt = stmt.where(ContributionWorkForeman.foreman_id.in_(foreman_ids))

    grouped: dict[UUID, list[ContributionBonusEntry]] = defaultdict(list)
    for work, foreman_id in db.execute(stmt):
        grouped[foreman_id].append(
            ContributionBonusEntry(
                work_id=work.id,
                title=work.title,
                work_type=work.work_type.value if work.work_type else None,
                score=work.contribution_score,
                work_date=work.work_date,
            )
        )

    return {
        fid: ForemanBonus(
            bonus=sum(e.score for e in entries),
            entries=sorted(entries, key=lambda e: e.work_date, reverse=True),
        )
        for fid, entries in grouped.items()
    }


def general_performance_score(operational_score: float, bonus: int) -> float:
    return min(operational_score + bonus, MAX_GENERAL_SCORE)
