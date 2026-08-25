from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AnomalyNotFoundError
from app.models.enums import AnomalyStatus
from app.repositories.anomaly_repository import AnomalyRepository
from app.services.anomaly_read_service import AnomalyReadService
from app.services.audit import record_audit


class AnomalyStatusService:
    """`PATCH /anomalies/{id}/status` orkestrasyonu.

    Lookup, mutation, flush, koşullu audit, tek commit, refresh ve detail response
    sırasını korur. Geçiş doğrulaması eklemez; mevcut contract her durumdan geçerli
    herhangi bir `AnomalyStatus` değerine izin verir.
    """

    def __init__(self, db: Session, repository: AnomalyRepository | None = None):
        self.db = db
        self.repository = repository or AnomalyRepository(db)

    def update_status(
        self,
        anomaly_id: UUID,
        new_status: AnomalyStatus,
        actor: str | None,
        ip_address: str | None,
    ) -> dict:
        anomaly = self.repository.get_anomaly(anomaly_id)
        if anomaly is None:
            raise AnomalyNotFoundError("Tespit bulunamadı.")

        old_status = anomaly.status.value
        anomaly.status = new_status
        self.db.flush()

        if old_status != new_status.value:
            record_audit(
                self.db, actor, "anomaly_status_updated", entity="anomaly",
                old_value=old_status, new_value=new_status.value,
                ip_address=ip_address,
            )

        self.db.commit()
        self.db.refresh(anomaly)
        return AnomalyReadService(self.db, self.repository).get_detail(anomaly.id)
