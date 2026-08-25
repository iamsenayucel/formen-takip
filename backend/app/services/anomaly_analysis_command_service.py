from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AnomalyAnalysisInProgressError, AnomalyNotFoundError
from app.models.enums import AnalysisMode, AnomalyAnalysisStatus
from app.repositories.anomaly_repository import AnomalyRepository
from app.services.anomaly_analysis_service import AnalysisInProgressError, run_analysis
from app.services.anomaly_read_service import AnomalyReadService
from app.services.audit import record_audit

_COMPLETED_STATUSES = {AnomalyAnalysisStatus.COMPLETED, AnomalyAnalysisStatus.COMPLETED_WITH_WARNINGS}


class AnomalyAnalysisCommandService:
    """`POST /anomalies/{id}/analyze` ve `.../reanalyze` orkestrasyonu.

    İki endpoint bağımsız pipeline yerine ortak `_run` akışını kullanır. Claim,
    LLM/demo, tool, persistence ve CAS işlemleri mevcut `run_analysis` akışına
    bırakılır. Bu service yalnızca lookup, cache-hit, 409 dönüşümü, audit ve
    response mapping'i yönetir.
    """

    def __init__(self, db: Session, repository: AnomalyRepository | None = None):
        self.db = db
        self.repository = repository or AnomalyRepository(db)
        self.read_service = AnomalyReadService(db, self.repository)

    def analyze(
        self, anomaly_id: UUID, mode: AnalysisMode | None, force_refresh: bool, actor: str | None, ip_address: str | None
    ) -> dict:
        return self._run(
            anomaly_id, mode, force_refresh, actor, ip_address, action="anomaly_analyzed", force=False,
        )

    def reanalyze(
        self, anomaly_id: UUID, mode: AnalysisMode | None, force_refresh: bool, actor: str | None, ip_address: str | None
    ) -> dict:
        return self._run(
            anomaly_id, mode, force_refresh, actor, ip_address, action="anomaly_reanalyzed", force=True,
        )

    def _run(
        self,
        anomaly_id: UUID,
        mode: AnalysisMode | None,
        force_refresh: bool,
        actor: str | None,
        ip_address: str | None,
        *,
        action: str,
        force: bool,
    ) -> dict:
        anomaly = self.repository.get_anomaly(anomaly_id)
        if anomaly is None:
            raise AnomalyNotFoundError("Tespit bulunamadı.")

        if not force and not force_refresh and anomaly.analysis_status in _COMPLETED_STATUSES:
            existing = self.repository.latest_analysis(anomaly_id)
            if existing is not None:
                return self.read_service.get_detail(anomaly.id)

        try:
            analysis = run_analysis(self.db, anomaly, mode=mode)
        except AnalysisInProgressError as exc:
            raise AnomalyAnalysisInProgressError(str(exc)) from exc

        record_audit(
            self.db, actor, action, entity="anomaly",
            new_value=f"{anomaly.code}: {analysis.status.value}",
            ip_address=ip_address,
        )
        self.db.commit()
        return self.read_service.get_detail(anomaly.id)
