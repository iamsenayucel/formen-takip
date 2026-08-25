from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AnomalyNotFoundError
from app.repositories.anomaly_repository import AnomalyRepository
from app.services.anomaly_investigation import build_investigation


class AnomalyInvestigationService:
    """`GET /anomalies/{id}/investigation` orkestrasyonu.

    Bağımlılıkları Catalog/Detail read akışından farklı olduğu için
    `AnomalyReadService` dışında tutulur. İş kurallarını çoğaltmadan tüm hesabı
    `anomaly_investigation.build_investigation` fonksiyonuna bırakır.
    """

    def __init__(self, db: Session, repository: AnomalyRepository | None = None):
        self.db = db
        self.repository = repository or AnomalyRepository(db)

    def get_investigation(self, anomaly_id: UUID) -> dict:
        anomaly = self.repository.get_anomaly(anomaly_id)
        if anomaly is None:
            raise AnomalyNotFoundError("Tespit bulunamadı.")
        return build_investigation(self.db, anomaly)
