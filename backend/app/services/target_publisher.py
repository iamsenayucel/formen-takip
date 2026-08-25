from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import CalculationType, TargetScopeType
from app.models.kpi import KpiCalculationRule, KpiTarget


class TargetPublishConflictError(RuntimeError):
    pass


class RulePublishConflictError(RuntimeError):
    pass


def publish_target(
    db: Session,
    *,
    kpi_id: UUID,
    scope_type: TargetScopeType,
    scope_id: UUID | None,
    target_value: float,
    valid_from: date,
) -> KpiTarget:
    if scope_type == TargetScopeType.COMPANY and scope_id is not None:
        raise ValueError("COMPANY kapsamında scope_id belirtilemez.")
    if scope_type != TargetScopeType.COMPANY and scope_id is None:
        raise ValueError(f"{scope_type.value} kapsamında scope_id zorunludur.")

    scope_filter = KpiTarget.scope_id.is_(None) if scope_id is None else KpiTarget.scope_id == scope_id
    open_ended = db.scalars(
        select(KpiTarget)
        .where(
            KpiTarget.kpi_id == kpi_id,
            KpiTarget.scope_type == scope_type,
            scope_filter,
            KpiTarget.valid_to.is_(None),
        )
        .with_for_update()
    ).all()

    for prev in open_ended:
        if prev.valid_from >= valid_from:
            raise ValueError(
                f"Yeni hedefin başlangıç tarihi ({valid_from}) mevcut açık uçlu hedefin başlangıcından "
                f"({prev.valid_from}) sonra olmalı."
            )
        prev.valid_to = valid_from - timedelta(days=1)

    new_target = KpiTarget(
        kpi_id=kpi_id, scope_type=scope_type, scope_id=scope_id,
        target_value=target_value, valid_from=valid_from, valid_to=None, is_active=True,
    )
    db.add(new_target)
    try:
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TargetPublishConflictError(
            f"Hedef yayınlama başarısız: kpi={kpi_id} scope={scope_type.value}/{scope_id} valid_from={valid_from} "
            "için çakışan bir hedef zaten mevcut (veritabanı bütünlük kısıtı reddetti)."
        ) from exc

    return new_target


def publish_rule(
    db: Session,
    *,
    kpi_id: UUID,
    calculation_type: CalculationType,
    parameters: dict,
    valid_from: date,
) -> KpiCalculationRule:
    open_ended = db.scalars(
        select(KpiCalculationRule)
        .where(KpiCalculationRule.kpi_id == kpi_id, KpiCalculationRule.valid_to.is_(None))
        .with_for_update()
    ).all()

    next_version = (db.scalar(select(func.max(KpiCalculationRule.version)).where(KpiCalculationRule.kpi_id == kpi_id)) or 0) + 1

    for prev in open_ended:
        if prev.valid_from >= valid_from:
            raise ValueError(
                f"Yeni rule'un başlangıç tarihi ({valid_from}) mevcut açık uçlu rule'un başlangıcından "
                f"({prev.valid_from}) sonra olmalı."
            )
        prev.valid_to = valid_from - timedelta(days=1)

    new_rule = KpiCalculationRule(
        kpi_id=kpi_id, version=next_version, calculation_type=calculation_type,
        parameters=parameters, valid_from=valid_from, valid_to=None, is_active=True,
    )
    db.add(new_rule)
    try:
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RulePublishConflictError(
            f"Rule yayınlama başarısız: kpi={kpi_id} valid_from={valid_from} için çakışan bir rule zaten "
            "mevcut (veritabanı bütünlük kısıtı reddetti)."
        ) from exc

    return new_rule
