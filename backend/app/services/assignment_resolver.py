
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.foreman import Foreman, ForemanAssignment
from app.models.organization import Shift
from app.services.shift_rotation import actual_shift_for_date


class AssignmentCandidate(Protocol):
    foreman_id: UUID
    plant_id: UUID
    shift_id: UUID
    start_date: date
    end_date: date | None
    is_active: bool


@dataclass
class ResolvedAssignment:
    expected_shift_id: UUID


class NoActiveAssignmentError(LookupError):
    pass


def resolve_assignment(
    candidates: list[AssignmentCandidate],
    as_of: date,
    foreman_id: UUID,
    plant_id: UUID,
    shifts: list[Shift],
) -> ResolvedAssignment:
    for candidate in candidates:
        if (
            candidate.is_active
            and candidate.foreman_id == foreman_id
            and candidate.plant_id == plant_id
            and candidate.start_date <= as_of
            and (candidate.end_date is None or candidate.end_date >= as_of)
        ):
            anchor_shift = next(s for s in shifts if s.id == candidate.shift_id)
            expected_shift = actual_shift_for_date(as_of, anchor_shift, shifts)
            return ResolvedAssignment(expected_shift_id=expected_shift.id)

    raise NoActiveAssignmentError(
        f"Formen {foreman_id} tesise {plant_id} {as_of} tarihinde atanmış değil."
    )


def assignments_as_of(
    as_of_date: date,
    *,
    plant_id: UUID | None = None,
    chief_id: UUID | None = None,
    shift_id: UUID | None = None,
    foreman_id: UUID | None = None,
    active_foreman_only: bool = False,
) -> Select:
    query = select(ForemanAssignment).where(
        ForemanAssignment.is_active.is_(True),
        ForemanAssignment.start_date <= as_of_date,
        (ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= as_of_date),
    )
    if plant_id is not None:
        query = query.where(ForemanAssignment.plant_id == plant_id)
    if chief_id is not None:
        query = query.where(ForemanAssignment.chief_id == chief_id)
    if shift_id is not None:
        query = query.where(ForemanAssignment.shift_id == shift_id)
    if foreman_id is not None:
        query = query.where(ForemanAssignment.foreman_id == foreman_id)
    if active_foreman_only:
        query = query.join(Foreman, Foreman.id == ForemanAssignment.foreman_id).where(Foreman.is_active.is_(True))
    return query


def active_foreman_count(
    db: Session,
    as_of_date: date,
    *,
    plant_id: UUID | None = None,
    chief_id: UUID | None = None,
    shift_id: UUID | None = None,
) -> int:
    query = assignments_as_of(
        as_of_date, plant_id=plant_id, chief_id=chief_id, shift_id=shift_id, active_foreman_only=True
    ).with_only_columns(func.count(func.distinct(ForemanAssignment.foreman_id)), maintain_column_froms=True)
    return db.scalar(query) or 0


def active_foreman_counts_by_plant(db: Session, as_of_date: date) -> dict[UUID, int]:
    query = assignments_as_of(as_of_date, active_foreman_only=True).with_only_columns(
        ForemanAssignment.plant_id, func.count(func.distinct(ForemanAssignment.foreman_id)),
        maintain_column_froms=True,
    ).group_by(ForemanAssignment.plant_id)
    return dict(db.execute(query).all())


def active_foremen_by_chief(db: Session, as_of_date: date) -> dict[UUID, list[tuple[UUID, str]]]:
    query = assignments_as_of(as_of_date, active_foreman_only=True).with_only_columns(
        ForemanAssignment.chief_id, Foreman.id, Foreman.first_name, Foreman.last_name,
        maintain_column_froms=True,
    ).distinct()
    result: dict[UUID, list[tuple[UUID, str]]] = {}
    for chief_id, foreman_id, first_name, last_name in db.execute(query).all():
        result.setdefault(chief_id, []).append((foreman_id, f"{first_name} {last_name}"))
    return result
