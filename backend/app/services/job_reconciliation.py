"""Aylık rapor e-postası ve anomali analizi için stale-job watchdog/reconciliation.

Her iki watchdog normal worker ile aynı koşullu UPDATE modelini kullanır. Worker
tamamlanması ile stale sweep'ten hangisi önce commit ederse satırı o kazanır; diğer
UPDATE sıfır satırla eşleşir ve no-op olur.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.enums import AnomalyAnalysisStatus, ReportEmailStatus
from app.models.foreman_report import ForemanMonthlyReport
from app.services.anomaly_job_claim import IN_PROGRESS_STATUSES

logger = logging.getLogger("app.job_reconciliation")


@dataclass
class ReconciliationResult:
    scanned_candidates: int = 0
    recovered_ids: list = field(default_factory=list)


def reconcile_stale_email_jobs(db: Session, settings: Settings | None = None) -> ReconciliationResult:
    """Stale timeout'u aşan SENDING e-postaları RECONCILIATION_REQUIRED durumuna taşır.

    SMTP idempotency garantisi vermediğinden otomatik PENDING durumuna dönmez. Gönderim
    öncesi çökme ile gönderim sonrası commit öncesi çökme ayırt edilemez; operatör her
    kaydı `resolve-stale-email-job` ile açıkça çözmelidir.
    """
    settings = settings or get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.email_stale_claim_timeout_seconds)

    candidate_ids = list(
        db.scalars(
            select(ForemanMonthlyReport.id).where(
                ForemanMonthlyReport.email_status == ReportEmailStatus.SENDING,
                ForemanMonthlyReport.claimed_at < cutoff,
            )
        )
    )

    recovered: list[UUID] = []
    for report_id in candidate_ids:
        stmt = (
            update(ForemanMonthlyReport)
            .where(
                ForemanMonthlyReport.id == report_id,
                ForemanMonthlyReport.email_status == ReportEmailStatus.SENDING,
                ForemanMonthlyReport.claimed_at < cutoff,
            )
            .values(email_status=ReportEmailStatus.RECONCILIATION_REQUIRED, claim_token=None)
        )
        result = db.execute(stmt)
        db.commit()
        if result.rowcount == 1:
            recovered.append(report_id)
            logger.warning(
                "report_email_marked_stale report_id=%s timeout_seconds=%s — SENDING -> "
                "RECONCILIATION_REQUIRED; resolve manually with `resolve-stale-email-job`",
                report_id, settings.email_stale_claim_timeout_seconds,
            )
    return ReconciliationResult(scanned_candidates=len(candidate_ids), recovered_ids=recovered)


def resolve_email_reconciliation(db: Session, report_id: UUID, resolution: str) -> ForemanMonthlyReport:
    """RECONCILIATION_REQUIRED e-postasını operatör kararıyla çözer.

    resolution="sent" teslimat doğrulandıysa SENT yapar ve yeniden denemez.
    resolution="retry" teslim edilmediği doğrulandıysa sonraki job için PENDING yapar.
    """
    if resolution not in ("sent", "retry"):
        raise ValueError(f"Bilinmeyen resolution: {resolution!r} (sent|retry olmalı)")

    now = datetime.now(timezone.utc)
    if resolution == "sent":
        values = {
            "email_status": ReportEmailStatus.SENT, "emailed_at": now,
            "email_last_error": None, "claim_token": None,
        }
    else:
        values = {
            "email_status": ReportEmailStatus.PENDING,
            "email_last_error": "manual_reconciliation_retry", "claim_token": None,
        }

    stmt = (
        update(ForemanMonthlyReport)
        .where(
            ForemanMonthlyReport.id == report_id,
            ForemanMonthlyReport.email_status == ReportEmailStatus.RECONCILIATION_REQUIRED,
        )
        .values(**values)
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount != 1:
        raise ValueError(f"report_id={report_id} RECONCILIATION_REQUIRED durumunda değil (zaten çözülmüş olabilir).")

    report = db.get(ForemanMonthlyReport, report_id)
    logger.warning("report_email_reconciliation_resolved report_id=%s resolution=%s", report_id, resolution)
    return report


def reconcile_stale_anomaly_jobs(db: Session, settings: Settings | None = None) -> ReconciliationResult:
    """Stale timeout'u aşan aktif AnomalyAnalysis denemelerini FAILED yapar.

    Böylece anomali manuel Reanalyze veya sonraki scheduler çalışması için serbest kalır.
    E-postadan farklı olarak retry yalnızca LLM API maliyeti doğurur; gerçek dünyada
    mükerrer işlem üretmediği için güvenli varsayılan FAILED durumudur.
    """
    settings = settings or get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.anomaly_stale_claim_timeout_seconds)

    candidate_ids = list(
        db.scalars(
            select(AnomalyAnalysis.id).where(
                AnomalyAnalysis.status.in_(IN_PROGRESS_STATUSES),
                AnomalyAnalysis.started_at < cutoff,
            )
        )
    )

    recovered: list[UUID] = []
    for analysis_id in candidate_ids:
        stmt = (
            update(AnomalyAnalysis)
            .where(
                AnomalyAnalysis.id == analysis_id,
                AnomalyAnalysis.status.in_(IN_PROGRESS_STATUSES),
                AnomalyAnalysis.started_at < cutoff,
            )
            .values(
                status=AnomalyAnalysisStatus.FAILED, error_message="stale_watchdog_timeout",
                completed_at=datetime.now(timezone.utc),
            )
            .returning(AnomalyAnalysis.anomaly_id)
        )
        result = db.execute(stmt)
        row = result.first()
        db.commit()
        if row is None:
            continue

        anomaly_id = row[0]
        anomaly_stmt = (
            update(Anomaly)
            .where(Anomaly.id == anomaly_id, Anomaly.current_analysis_id == analysis_id)
            .values(analysis_status=AnomalyAnalysisStatus.FAILED)
        )
        anomaly_result = db.execute(anomaly_stmt)
        db.commit()
        recovered.append(analysis_id)
        logger.warning(
            "anomaly_analysis_marked_stale analysis_id=%s anomaly_id=%s timeout_seconds=%s anomaly_status_updated=%s",
            analysis_id, anomaly_id, settings.anomaly_stale_claim_timeout_seconds, anomaly_result.rowcount == 1,
        )
    return ReconciliationResult(scanned_candidates=len(candidate_ids), recovered_ids=recovered)
