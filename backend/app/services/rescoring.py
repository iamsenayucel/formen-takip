
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import bindparam, select, update
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus, SourceSystem
from app.models.kpi import Kpi, KpiCalculationRule
from app.models.performance import PerformanceRecord, PerformanceScore
from app.models.production import Product, ProductionRecord
from app.services.ingestion import run_ingestion
from app.services.kpi_engine import KpiCalculationError, compute_score_for_rule
from app.services.production_kpi_derivation import derive_agir_gitme, derive_raw_performance_records
from app.services.providers.base import PerformanceDataProvider
from app.services.rule_resolver import NoRuleFoundError, resolve_rule

BATCH_SIZE = 2000


def recalculate_agir_gitme_actuals(db: Session, batch_size: int = BATCH_SIZE) -> dict:
    agir_gitme = db.scalar(select(Kpi).where(Kpi.code == "AGIR_GITME"))
    if agir_gitme is None:
        return {"updated": 0, "skipped": 0}

    stmt = (
        select(
            PerformanceRecord.id,
            ProductionRecord.actual_qty,
            ProductionRecord.measured_avg_gram,
            Product.standard_gram,
            Product.lower_gram_limit,
            Product.upper_gram_limit,
        )
        .join(ProductionRecord, ProductionRecord.id == PerformanceRecord.production_record_id)
        .join(Product, Product.id == ProductionRecord.product_id)
        .where(PerformanceRecord.kpi_id == agir_gitme.id)
    )

    updated = skipped = 0
    batch: list[dict] = []

    def flush() -> None:
        nonlocal batch, updated
        if not batch:
            return
        upd = (
            update(PerformanceRecord)
            .where(PerformanceRecord.id == bindparam("pid"))
            .values(
                actual_value=bindparam("actual_value"),
                numerator_value=bindparam("numerator_value"),
                denominator_value=bindparam("denominator_value"),
            )
        )
        db.execute(upd, batch)
        db.commit()
        updated += len(batch)
        batch = []

    for row in db.execute(stmt).yield_per(batch_size):
        if (
            row.actual_qty is None or row.measured_avg_gram is None
            or row.standard_gram is None or row.lower_gram_limit is None or row.upper_gram_limit is None
        ):
            skipped += 1
            continue
        result = derive_agir_gitme(
            float(row.measured_avg_gram), float(row.standard_gram),
            float(row.lower_gram_limit), float(row.upper_gram_limit), float(row.actual_qty),
        )
        if result is None:
            skipped += 1
            continue
        actual_value, numerator, denominator = result
        batch.append({
            "pid": row.id, "actual_value": actual_value,
            "numerator_value": numerator, "denominator_value": denominator,
        })
        if len(batch) >= batch_size:
            flush()
    flush()
    return {"updated": updated, "skipped": skipped}


class _InkitaOnlyProvider(PerformanceDataProvider):

    source_system = SourceSystem.SYNTHETIC

    def __init__(self, db: Session) -> None:
        self._db = db

    def fetch(self, date_from, date_to, plant_codes=None):
        for raw in derive_raw_performance_records(self._db, date_from, date_to, plant_codes):
            if raw.kpi_code == "INKITA":
                yield raw


def ingest_inkita_backfill(db: Session) -> dict:
    date_from = db.scalar(select(ProductionRecord.production_date).order_by(ProductionRecord.production_date.asc()))
    date_to = db.scalar(select(ProductionRecord.production_date).order_by(ProductionRecord.production_date.desc()))
    if date_from is None or date_to is None:
        return {"processed": 0, "success": 0, "error": 0, "skipped": 0}

    provider = _InkitaOnlyProvider(db)
    run = run_ingestion(db, provider, date_from, date_to)
    return {
        "processed": run.processed_count, "success": run.success_count,
        "error": run.error_count, "skipped": run.skipped_count,
    }


def rescore_all(db: Session, batch_size: int = BATCH_SIZE) -> dict:
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    rules_by_kpi_id: dict = {}
    rules_stmt = select(KpiCalculationRule).order_by(KpiCalculationRule.valid_from.desc(), KpiCalculationRule.id)
    for rule in db.scalars(rules_stmt):
        rules_by_kpi_id.setdefault(rule.kpi_id, []).append(rule)

    stmt = (
        select(
            PerformanceScore.id.label("score_id"),
            PerformanceRecord.kpi_id,
            PerformanceRecord.performance_date,
            PerformanceRecord.actual_value,
            PerformanceRecord.target_value,
            PerformanceRecord.numerator_value,
            PerformanceRecord.denominator_value,
        )
        .join(PerformanceRecord, PerformanceRecord.id == PerformanceScore.performance_record_id)
        .where(
            PerformanceRecord.data_quality_status == DataQualityStatus.COMPLETE,
            PerformanceRecord.target_value.isnot(None),
        )
    )

    updated = skipped = 0
    batch: list[dict] = []
    now = datetime.now(timezone.utc)

    def flush() -> None:
        nonlocal batch, updated
        if not batch:
            return
        upd = (
            update(PerformanceScore)
            .where(PerformanceScore.id == bindparam("sid"))
            .values(
                raw_score=bindparam("raw_score"),
                capped_score=bindparam("capped_score"),
                kpi_weight=bindparam("kpi_weight"),
                weighted_contribution=bindparam("weighted_contribution"),
                calculation_rule_id=bindparam("calculation_rule_id"),
                calculation_version=bindparam("calculation_version"),
                calculated_at=bindparam("calculated_at"),
            )
        )
        db.connection().execute(upd, batch)
        db.commit()
        updated += len(batch)
        batch = []

    for row in db.execute(stmt).yield_per(batch_size):
        kpi = kpis_by_id.get(row.kpi_id)
        if kpi is None or row.actual_value is None or row.target_value is None:
            skipped += 1
            continue
        try:
            rule = resolve_rule(rules_by_kpi_id.get(row.kpi_id, []), row.performance_date)
        except NoRuleFoundError:
            skipped += 1
            continue
        try:
            score = compute_score_for_rule(
                rule.calculation_type, rule.parameters,
                actual=float(row.actual_value), target=float(row.target_value),
                numerator=float(row.numerator_value) if row.numerator_value is not None else None,
                denominator=float(row.denominator_value) if row.denominator_value is not None else None,
                min_score=float(kpi.min_score), max_score=float(kpi.max_score),
            )
        except KpiCalculationError:
            skipped += 1
            continue
        weight = float(kpi.weight)
        batch.append({
            "sid": row.score_id, "raw_score": score.raw_score, "capped_score": score.capped_score,
            "kpi_weight": weight, "weighted_contribution": score.capped_score * (weight / 100.0),
            "calculation_rule_id": rule.id, "calculation_version": rule.version, "calculated_at": now,
        })
        if len(batch) >= batch_size:
            flush()
    flush()
    return {"updated": updated, "skipped": skipped}


def apply_scoring_model_v2(db: Session) -> dict:
    agir_gitme_result = recalculate_agir_gitme_actuals(db)
    inkita_result = ingest_inkita_backfill(db)
    rescore_result = rescore_all(db)
    return {
        "agir_gitme_actuals": agir_gitme_result,
        "inkita_backfill": inkita_result,
        "rescore_all": rescore_result,
    }
