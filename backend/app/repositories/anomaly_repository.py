from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.pagination import keyset_after
from app.models.anomaly import Anomaly, AnomalyAnalysis, AnomalyToolCall
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift


@dataclass
class AnomalyListQueryParams:
    factory: str | None = None
    plant_id: UUID | None = None
    plant_ids: list[UUID] | None = None
    shift_id: UUID | None = None
    kpi_id: UUID | None = None
    severity: AnomalySeverity | None = None
    status: AnomalyStatus | None = None
    analysis_status: AnomalyAnalysisStatus | None = None
    start_date_utc: datetime | None = None
    end_date_utc: datetime | None = None
    search: str | None = None


class AnomalyRepository:
    """Anomalies Catalog Reads (liste + özet) için salt okunur persistence erişimi.

    Yalnızca sorgu ve batch lookup işlemlerini kapsar. HTTPException üretmez,
    response şeması oluşturmaz, presentation metni üretmez ve hiçbir
    yazma/transaction işlemi (add/delete/flush/commit) içermez.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def filtered_query(self, params: AnomalyListQueryParams) -> Select:
        query = select(Anomaly)

        if params.factory:
            query = query.where(
                Anomaly.plant_id.in_(select(Plant.id).join(Factory).where(Factory.code == params.factory))
            )
        if params.plant_id:
            query = query.where(Anomaly.plant_id == params.plant_id)
        if params.plant_ids is not None:
            query = query.where(Anomaly.plant_id.in_(params.plant_ids))
        if params.shift_id:
            query = query.where(Anomaly.shift_id == params.shift_id)
        if params.kpi_id:
            query = query.where(Anomaly.kpi_id == params.kpi_id)
        if params.severity:
            query = query.where(Anomaly.severity == params.severity)
        if params.status:
            query = query.where(Anomaly.status == params.status)
        if params.analysis_status:
            query = query.where(Anomaly.analysis_status == params.analysis_status)
        if params.start_date_utc:
            query = query.where(Anomaly.detected_at >= params.start_date_utc)
        if params.end_date_utc:
            query = query.where(Anomaly.detected_at < params.end_date_utc)
        if params.search:
            like = f"%{params.search}%"
            query = query.where(or_(Anomaly.title.ilike(like), Anomaly.description.ilike(like)))

        return query

    def count(self, query: Select) -> int:
        return self.db.scalar(select(func.count()).select_from(query.subquery())) or 0

    def paginate(self, query: Select, *, cursor_value, cursor_id: UUID | None, limit: int) -> list[Anomaly]:
        if cursor_id is not None:
            query = query.where(keyset_after(Anomaly.detected_at, "desc", cursor_value, Anomaly.id, cursor_id))
        paged = query.order_by(Anomaly.detected_at.desc(), Anomaly.id).limit(limit + 1)
        return list(self.db.scalars(paged))

    # ------------------------------------------------------------------
    # Batch dimension lookups (N+1 avoidance)
    # ------------------------------------------------------------------

    def plants_by_ids(self, ids: set[UUID]) -> dict[UUID, Plant]:
        if not ids:
            return {}
        return {p.id: p for p in self.db.scalars(select(Plant).where(Plant.id.in_(ids)))}

    def factories_by_ids(self, ids: set[UUID]) -> dict[UUID, Factory]:
        if not ids:
            return {}
        return {f.id: f for f in self.db.scalars(select(Factory).where(Factory.id.in_(ids)))}

    def shifts_by_ids(self, ids: set[UUID]) -> dict[UUID, Shift]:
        if not ids:
            return {}
        return {s.id: s for s in self.db.scalars(select(Shift).where(Shift.id.in_(ids)))}

    def kpis_by_ids(self, ids: set[UUID]) -> dict[UUID, Kpi]:
        if not ids:
            return {}
        return {k.id: k for k in self.db.scalars(select(Kpi).where(Kpi.id.in_(ids)))}

    def foremen_by_ids(self, ids: set[UUID]) -> dict[UUID, Foreman]:
        if not ids:
            return {}
        return {f.id: f for f in self.db.scalars(select(Foreman).where(Foreman.id.in_(ids)))}

    # ------------------------------------------------------------------
    # Detail / Analysis Reads
    # ------------------------------------------------------------------

    def get_anomaly(self, anomaly_id: UUID) -> Anomaly | None:
        return self.db.get(Anomaly, anomaly_id)

    def latest_analysis(self, anomaly_id: UUID) -> AnomalyAnalysis | None:
        return self.db.scalar(
            select(AnomalyAnalysis)
            .where(AnomalyAnalysis.anomaly_id == anomaly_id)
            .order_by(AnomalyAnalysis.started_at.desc())
        )

    def analysis_history(self, anomaly_id: UUID) -> list[AnomalyAnalysis]:
        return list(
            self.db.scalars(
                select(AnomalyAnalysis)
                .where(AnomalyAnalysis.anomaly_id == anomaly_id)
                .order_by(AnomalyAnalysis.started_at.desc())
            )
        )

    def get_analysis(self, analysis_id: UUID) -> AnomalyAnalysis | None:
        return self.db.get(AnomalyAnalysis, analysis_id)

    def tool_calls_for_analysis(self, analysis_id: UUID) -> list[AnomalyToolCall]:
        return list(
            self.db.scalars(
                select(AnomalyToolCall)
                .where(AnomalyToolCall.analysis_id == analysis_id)
                .order_by(AnomalyToolCall.step_number)
            )
        )

    def tool_call_counts_by_analysis_ids(self, ids: set[UUID]) -> dict[UUID, int]:
        if not ids:
            return {}
        rows = self.db.execute(
            select(AnomalyToolCall.analysis_id, func.count())
            .where(AnomalyToolCall.analysis_id.in_(ids))
            .group_by(AnomalyToolCall.analysis_id)
        ).all()
        return {analysis_id: count for analysis_id, count in rows}

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary_counts(
        self,
        *,
        active_statuses: tuple[AnomalyStatus, ...],
        critical_severity: AnomalySeverity,
        high_severity: AnomalySeverity,
        not_analyzed_status: AnomalyAnalysisStatus,
        week_ago: datetime,
        resolved_statuses: tuple[AnomalyStatus, ...],
        plant_ids: list[UUID] | None = None,
    ) -> dict:
        base = select(Anomaly.id)
        if plant_ids is not None:
            base = base.where(Anomaly.plant_id.in_(plant_ids))
        scoped = base.subquery()

        row = self.db.execute(
            select(
                func.count().filter(Anomaly.status.in_(active_statuses)).label("total_active"),
                func.count().filter(Anomaly.severity == critical_severity).label("critical_count"),
                func.count().filter(Anomaly.severity == high_severity).label("high_count"),
                func.count().filter(Anomaly.analysis_status == not_analyzed_status).label("pending_analysis_count"),
                func.count().filter(Anomaly.detected_at >= week_ago).label("opened_last_7_days"),
                func.count().filter(Anomaly.status.in_(resolved_statuses)).label("resolved_count"),
            ).where(Anomaly.id.in_(select(scoped.c.id)))
        ).one()
        return dict(row._mapping)
