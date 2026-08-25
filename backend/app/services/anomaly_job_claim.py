"""Anomali analiz işleri için atomik claim ve korumalı durum geçişleri.

İki invariant DB seviyesinde korunur:

1. Bir anomalide aynı anda en fazla bir analiz ilerleyebilir. Partial unique index
   claim INSERT'ini korur; ayrı check-then-write yapılmaz.
2. `Anomaly.analysis_status` denemeler arasında ortaktır. Stale worker'ın yeni
   denemeyi ezmemesi için her UPDATE, claim token olan `current_analysis_id` ile korunur.
"""

from __future__ import annotations

import logging

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.enums import AnomalyAnalysisStatus

logger = logging.getLogger("app.anomaly_job_claim")

IN_PROGRESS_STATUSES = {
    AnomalyAnalysisStatus.ANALYZING, AnomalyAnalysisStatus.QUEUED, AnomalyAnalysisStatus.PLANNING,
    AnomalyAnalysisStatus.COLLECTING_DATA, AnomalyAnalysisStatus.GENERATING_ANALYSIS,
}


class AnalysisInProgressError(Exception):
    pass


def claim_analysis(db: Session, anomaly: Anomaly, analysis: AnomalyAnalysis) -> None:
    """Önceden açık `id` ile oluşturulan `analysis` için `anomaly` kaydını atomik sahiplenir.

    Eşzamanlı başka deneme varsa AnalysisInProgressError fırlatır. Başarılı olduğunda
    deneme satırı ile current_analysis_id/analysis_status tek transaction'da commit edilir.
    """
    db.add(analysis)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info("anomaly_analysis_claim_skipped anomaly=%s — another analysis already in progress", anomaly.code)
        raise AnalysisInProgressError("Bu tespit için analiz zaten devam ediyor.") from None

    anomaly.current_analysis_id = analysis.id
    anomaly.analysis_status = analysis.status
    db.commit()
    db.refresh(analysis)
    db.refresh(anomaly)
    logger.info("anomaly_analysis_claimed anomaly=%s analysis=%s", anomaly.code, analysis.code)


def set_anomaly_status_if_current(
    db: Session, anomaly: Anomaly, analysis: AnomalyAnalysis, status: AnomalyAnalysisStatus
) -> bool:
    """current_analysis_id hâlâ `analysis` kaydını gösteriyorsa analysis_status günceller.

    Yeni claim veya stale-job watchdog sahipliği aldıysa DB satırına dokunmadan False döner.
    `analysis.status` bu denemenin kendi geçmişidir ve sonuçtan bağımsız yazılmalıdır.
    """
    stmt = (
        update(Anomaly)
        .where(Anomaly.id == anomaly.id, Anomaly.current_analysis_id == analysis.id)
        .values(analysis_status=status)
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount != 1:
        logger.warning(
            "anomaly_status_update_stale_ignored anomaly=%s analysis=%s attempted_status=%s — this worker's "
            "claim was reclaimed before it finished; anomaly.analysis_status left untouched",
            anomaly.code, analysis.code, status.value,
        )
        db.refresh(anomaly)
        return False
    db.refresh(anomaly)
    return True
