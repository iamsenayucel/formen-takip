
from __future__ import annotations

import logging
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import bindparam, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.enums import DataQualityStatus, IntegrationStatus, TargetScopeType
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import DataQualityIssue, IntegrationRun
from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord, PerformanceScore
from app.services.assignment_resolver import NoActiveAssignmentError, resolve_assignment
from app.services.kpi_engine import compute_score_for_rule
from app.services.providers.base import PerformanceDataProvider, RawPerformanceRecord
from app.services.rule_resolver import NoRuleFoundError, resolve_rule
from app.services.target_resolver import NoTargetFoundError, resolve_target

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


class _Lookups:
    def __init__(self, db: Session) -> None:
        self.plants = {p.code: p for p in db.scalars(select(Plant))}
        self.chiefs = {c.employee_number: c for c in db.scalars(select(Chief))}
        self.shifts = {s.code: s for s in db.scalars(select(Shift))}
        self.foremen = {f.employee_number: f for f in db.scalars(select(Foreman))}
        self.kpis = {k.code: k for k in db.scalars(select(Kpi))}
        self.shift_list = list(self.shifts.values())
        self.assignments = list(db.scalars(select(ForemanAssignment)))

        self.rules_by_kpi: dict[uuid.UUID, list[KpiCalculationRule]] = {}
        rules_stmt = select(KpiCalculationRule).order_by(KpiCalculationRule.valid_from.desc(), KpiCalculationRule.id)
        for rule in db.scalars(rules_stmt):
            self.rules_by_kpi.setdefault(rule.kpi_id, []).append(rule)

        self.targets_by_kpi: dict[uuid.UUID, list[KpiTarget]] = {}
        targets_stmt = select(KpiTarget).order_by(KpiTarget.valid_from.desc(), KpiTarget.id)
        for target in db.scalars(targets_stmt):
            self.targets_by_kpi.setdefault(target.kpi_id, []).append(target)


_ISSUE_DESCRIPTIONS = {
    DataQualityStatus.MISSING: "Gerçekleşen değer kaynaktan gelmedi (boş).",
    DataQualityStatus.INVALID: "Gerçekleşen değer KPI için tanımlı geçerli aralığın dışında.",
    DataQualityStatus.NEEDS_SOURCE_CORRECTION: "Bu KPI/tarih/kapsam için geçerli bir hedef bulunamadı — kaynak sistemde düzeltilmesi gerekiyor.",
    DataQualityStatus.DUPLICATE: "Aynı formen/KPI/şef/vardiya/tarih için zaten işlenmiş bir kayıtla çakışıyor (doğal anahtar tekrarı).",
    DataQualityStatus.SUSPICIOUS: "Formen bu tesise bu tarihte atanmış değil ya da bildirilen şef/vardiya atamayla uyuşmuyor.",
    DataQualityStatus.REPROCESSED: "Aynı kaynak kayıt (source_record_id) daha önce işlenenden farklı değerle yeniden geldi; kayıt güncellendi ve yeniden puanlandı.",
}


def _issue_description(status: DataQualityStatus, source_record_id: str) -> str:
    base = _ISSUE_DESCRIPTIONS.get(status, "Veri kalitesi sorunu tespit edildi.")
    return f"{base} (kaynak kayıt: {source_record_id})"


_MUTABLE_VALUE_FIELDS = (
    "target_value", "actual_value", "numerator_value", "denominator_value",
    "unit", "data_quality_status", "source_updated_at", "production_record_id",
)

_NATURAL_KEY_FIELDS = ("foreman_id", "kpi_id", "chief_id", "shift_id", "performance_date", "plant_id")


def _values_differ(existing_value: object, new_value: object) -> bool:
    if existing_value is None or new_value is None:
        return existing_value != new_value
    if isinstance(existing_value, (int, float, Decimal)) or isinstance(new_value, (int, float, Decimal)):
        try:
            return abs(float(existing_value) - float(new_value)) > 1e-6
        except (TypeError, ValueError):
            return existing_value != new_value
    return existing_value != new_value


def _record_content_changed(existing: PerformanceRecord, new_values: dict) -> bool:
    return any(_values_differ(getattr(existing, field), new_values[field]) for field in _MUTABLE_VALUE_FIELDS)


def _identity_changed(existing: PerformanceRecord, new_values: dict) -> bool:
    return any(_values_differ(getattr(existing, field), new_values[field]) for field in _NATURAL_KEY_FIELDS)


def run_ingestion(
    db: Session,
    provider: PerformanceDataProvider,
    date_from: date,
    date_to: date,
    plant_codes: list[str] | None = None,
) -> IntegrationRun:
    run = IntegrationRun(
        source_system=provider.source_system,
        started_at=datetime.now(timezone.utc),
        status=IntegrationStatus.RUNNING,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    lookups = _Lookups(db)

    processed = success = errors = skipped = 0
    target_fallback_counts: Counter[tuple[str, str]] = Counter()
    record_batch: list[dict] = []
    score_batch: list[dict] = []
    quality_meta_batch: list[dict] = []

    def flush() -> None:
        nonlocal record_batch, score_batch, quality_meta_batch, success, skipped
        if not record_batch:
            return

        source_keys = {(r["source_system"], r["source_record_id"]) for r in record_batch}
        existing_by_source: dict[tuple, PerformanceRecord] = {}
        if source_keys:
            existing_stmt = select(PerformanceRecord).where(
                tuple_(PerformanceRecord.source_system, PerformanceRecord.source_record_id).in_(source_keys)
            )
            for row in db.scalars(existing_stmt):
                existing_by_source[(row.source_system, row.source_record_id)] = row

        to_insert: list[dict] = []
        to_update: list[tuple[PerformanceRecord, dict]] = []
        unchanged_ids: set = set()
        identity_conflict_ids: set = set()
        id_remap: dict = {}

        for rec in record_batch:
            existing_row = existing_by_source.get((rec["source_system"], rec["source_record_id"]))
            if existing_row is None:
                to_insert.append(rec)
            elif _identity_changed(existing_row, rec):
                identity_conflict_ids.add(rec["id"])
            elif _record_content_changed(existing_row, rec):
                to_update.append((existing_row, rec))
                id_remap[rec["id"]] = existing_row.id
            else:
                unchanged_ids.add(rec["id"])

        inserted_ids: set = set()
        if to_insert:
            stmt = pg_insert(PerformanceRecord.__table__).values(to_insert)
            stmt = stmt.on_conflict_do_nothing(
                constraint="uq_perf_record_natural_key"
            ).returning(PerformanceRecord.__table__.c.id)
            inserted_ids = {row[0] for row in db.execute(stmt)}

        updated_ids: set = set()
        if to_update:
            now_ts = datetime.now(timezone.utc)
            upd = (
                update(PerformanceRecord)
                .where(PerformanceRecord.id == bindparam("_id"))
                .values(**{f: bindparam(f) for f in _MUTABLE_VALUE_FIELDS}, updated_at=bindparam("_updated_at"))
            )
            update_params = [
                {"_id": existing_row.id, "_updated_at": now_ts, **{f: rec[f] for f in _MUTABLE_VALUE_FIELDS}}
                for existing_row, rec in to_update
            ]
            db.connection().execute(upd, update_params)
            updated_ids = {p["_id"] for p in update_params}
            for existing_row, _ in to_update:
                db.expire(existing_row)

        skipped += (len(to_insert) - len(inserted_ids)) + len(identity_conflict_ids)
        success += len(inserted_ids) + len(updated_ids) + len(unchanged_ids)

        relevant_scores = []
        for s in score_batch:
            pid = s["performance_record_id"]
            if pid in inserted_ids:
                relevant_scores.append(s)
            elif pid in id_remap:
                s = dict(s)
                s["performance_record_id"] = id_remap[pid]
                relevant_scores.append(s)
        if relevant_scores:
            score_stmt = pg_insert(PerformanceScore.__table__).values(relevant_scores)
            score_stmt = score_stmt.on_conflict_do_update(
                index_elements=["performance_record_id"],
                set_={
                    "raw_score": score_stmt.excluded.raw_score,
                    "capped_score": score_stmt.excluded.capped_score,
                    "kpi_weight": score_stmt.excluded.kpi_weight,
                    "weighted_contribution": score_stmt.excluded.weighted_contribution,
                    "calculation_rule_id": score_stmt.excluded.calculation_rule_id,
                    "calculation_version": score_stmt.excluded.calculation_version,
                    "calculated_at": score_stmt.excluded.calculated_at,
                },
            )
            db.execute(score_stmt)

        scored_updated_ids = {s["performance_record_id"] for s in relevant_scores if s["performance_record_id"] in id_remap.values()}
        stale_score_ids = set(id_remap.values()) - scored_updated_ids
        if stale_score_ids:
            db.execute(PerformanceScore.__table__.delete().where(PerformanceScore.performance_record_id.in_(stale_score_ids)))

        issue_rows = []
        now = datetime.now(timezone.utc)
        for meta in quality_meta_batch:
            pid = meta["id"]
            if pid in unchanged_ids:
                continue
            if pid in inserted_ids:
                if meta["status"] != DataQualityStatus.COMPLETE:
                    issue_rows.append(
                        {
                            "id": uuid.uuid4(),
                            "performance_record_id": pid,
                            "issue_type": meta["status"],
                            "description": _issue_description(meta["status"], meta["source_record_id"]),
                            "detected_at": now,
                            "status": "open",
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
            elif pid in id_remap:
                issue_type = meta["status"] if meta["status"] != DataQualityStatus.COMPLETE else DataQualityStatus.REPROCESSED
                issue_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "performance_record_id": id_remap[pid],
                        "issue_type": issue_type,
                        "description": _issue_description(issue_type, meta["source_record_id"]),
                        "detected_at": now,
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                    }
                )
            elif pid in identity_conflict_ids:
                issue_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "performance_record_id": None,
                        "issue_type": DataQualityStatus.SUSPICIOUS,
                        "description": (
                            "Aynı kaynak kayıt (source_record_id) daha önce farklı formen/KPI/şef/vardiya/"
                            "tarih/tesis ile işlenmiş; kimlik alanları otomatik güncellenmez, manuel "
                            f"inceleme gerekir (kaynak kayıt: {meta['source_record_id']})."
                        ),
                        "detected_at": now,
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                    }
                )
            else:
                issue_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "performance_record_id": None,
                        "issue_type": DataQualityStatus.DUPLICATE,
                        "description": _issue_description(DataQualityStatus.DUPLICATE, meta["source_record_id"]),
                        "detected_at": now,
                        "status": "open",
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        if issue_rows:
            db.execute(pg_insert(DataQualityIssue.__table__).values(issue_rows))

        db.commit()
        record_batch = []
        score_batch = []
        quality_meta_batch = []

    for raw in provider.fetch(date_from, date_to, plant_codes):
        processed += 1
        try:
            plant = lookups.plants[raw.plant_code]
            chief = lookups.chiefs[raw.chief_employee_number]
            shift = lookups.shifts[raw.shift_code]
            foreman = lookups.foremen[raw.foreman_employee_number]
            kpi = lookups.kpis[raw.kpi_code]
        except KeyError:
            errors += 1
            continue

        record_id = uuid.uuid4()
        status = DataQualityStatus.COMPLETE
        target_value = raw.target_value

        if chief.id != plant.chief_id:
            status = DataQualityStatus.SUSPICIOUS

        try:
            resolved_assignment = resolve_assignment(
                lookups.assignments, raw.performance_date, foreman.id, plant.id, lookups.shift_list
            )
            if resolved_assignment.expected_shift_id != shift.id:
                status = DataQualityStatus.SUSPICIOUS
        except NoActiveAssignmentError:
            status = DataQualityStatus.SUSPICIOUS

        if status == DataQualityStatus.COMPLETE and raw.actual_value is None:
            status = DataQualityStatus.MISSING
        elif status == DataQualityStatus.COMPLETE and (
            raw.actual_value < float(kpi.min_valid_value) or raw.actual_value > float(kpi.max_valid_value)
        ):
            status = DataQualityStatus.INVALID

        if status == DataQualityStatus.COMPLETE and target_value is None:
            try:
                resolved = resolve_target(
                    lookups.targets_by_kpi.get(kpi.id, []),
                    raw.performance_date,
                    foreman.id,
                    plant.chief_id,
                    plant.id,
                )
                target_value = resolved.target_value
                if resolved.resolved_scope != TargetScopeType.PLANT:
                    target_fallback_counts[(kpi.code, resolved.resolved_scope.value)] += 1
            except NoTargetFoundError:
                status = DataQualityStatus.NEEDS_SOURCE_CORRECTION

        record_batch.append(
            {
                "id": record_id,
                "source_system": provider.source_system,
                "source_record_id": raw.source_record_id,
                "integration_run_id": run.id,
                "performance_date": raw.performance_date,
                "plant_id": plant.id,
                "chief_id": plant.chief_id,
                "shift_id": shift.id,
                "foreman_id": foreman.id,
                "kpi_id": kpi.id,
                "production_record_id": raw.production_record_id,
                "target_value": target_value,
                "actual_value": raw.actual_value,
                "numerator_value": raw.numerator_value,
                "denominator_value": raw.denominator_value,
                "unit": raw.unit,
                "data_quality_status": status,
                "source_updated_at": raw.source_updated_at,
                "imported_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        quality_meta_batch.append(
            {"id": record_id, "status": status, "source_record_id": raw.source_record_id}
        )

        if status == DataQualityStatus.COMPLETE and target_value is not None:
            try:
                rule = resolve_rule(lookups.rules_by_kpi.get(kpi.id, []), raw.performance_date)
            except NoRuleFoundError:
                rule = None
            if rule is not None:
                score = compute_score_for_rule(
                    rule.calculation_type, rule.parameters,
                    actual=float(raw.actual_value), target=float(target_value),
                    numerator=raw.numerator_value, denominator=raw.denominator_value,
                    min_score=float(kpi.min_score), max_score=float(kpi.max_score),
                )
                weight = float(kpi.weight)
                score_batch.append(
                    {
                        "id": uuid.uuid4(),
                        "performance_record_id": record_id,
                        "calculation_rule_id": rule.id,
                        "raw_score": score.raw_score,
                        "capped_score": score.capped_score,
                        "kpi_weight": weight,
                        "weighted_contribution": score.capped_score * (weight / 100.0),
                        "calculation_version": rule.version,
                        "calculated_at": datetime.now(timezone.utc),
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )

        if len(record_batch) >= BATCH_SIZE:
            flush()

    flush()

    if target_fallback_counts:
        logger.warning(
            "run_ingestion: %d kayıt PLANT seviyesinde hedef bulamadı, daha geniş kapsama (COMPANY/CHIEF/FOREMAN) "
            "düştü — tesis bazlı hedef kapsaması eksik olabilir: %s",
            sum(target_fallback_counts.values()),
            dict(target_fallback_counts),
        )

    run.finished_at = datetime.now(timezone.utc)
    run.processed_count = processed
    run.success_count = success
    run.error_count = errors
    run.skipped_count = skipped
    run.status = IntegrationStatus.SUCCESS if errors == 0 else IntegrationStatus.PARTIAL_SUCCESS
    db.commit()
    db.refresh(run)
    return run


def backfill_data_quality_issues(db: Session, batch_size: int = 2000) -> int:
    existing_ids = {
        row for row in db.scalars(
            select(DataQualityIssue.performance_record_id).where(DataQualityIssue.performance_record_id.isnot(None))
        )
    }

    query = select(
        PerformanceRecord.id, PerformanceRecord.data_quality_status, PerformanceRecord.source_record_id
    ).where(PerformanceRecord.data_quality_status != DataQualityStatus.COMPLETE)

    now = datetime.now(timezone.utc)
    to_insert: list[dict] = []
    total = 0
    for rec_id, status, source_record_id in db.execute(query):
        if rec_id in existing_ids:
            continue
        to_insert.append(
            {
                "id": uuid.uuid4(),
                "performance_record_id": rec_id,
                "issue_type": status,
                "description": _issue_description(status, source_record_id),
                "detected_at": now,
                "status": "open",
                "created_at": now,
                "updated_at": now,
            }
        )
        if len(to_insert) >= batch_size:
            db.execute(pg_insert(DataQualityIssue.__table__).values(to_insert))
            db.commit()
            total += len(to_insert)
            to_insert = []

    if to_insert:
        db.execute(pg_insert(DataQualityIssue.__table__).values(to_insert))
        db.commit()
        total += len(to_insert)

    return total
