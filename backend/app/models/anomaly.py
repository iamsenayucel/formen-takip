import uuid
from datetime import date, datetime

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import AnalysisMode, AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType


class Anomaly(TimestampMixin, Base):

    __tablename__ = "anomalies"
    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="ck_anomalies_period_range"),
        CheckConstraint("ml_confidence >= 0 AND ml_confidence <= 1", name="ck_anomalies_ml_confidence_range"),
        CheckConstraint("affected_days IS NULL OR affected_days >= 0", name="ck_anomalies_affected_days_non_negative"),
        CheckConstraint("total_days IS NULL OR total_days >= 0", name="ck_anomalies_total_days_non_negative"),
        CheckConstraint(
            "affected_days IS NULL OR total_days IS NULL OR affected_days <= total_days",
            name="ck_anomalies_affected_days_lte_total_days",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    anomaly_type: Mapped[AnomalyType] = mapped_column(Enum(AnomalyType, name="anomaly_type"), nullable=False)
    severity: Mapped[AnomalySeverity] = mapped_column(Enum(AnomalySeverity, name="anomaly_severity"), nullable=False)
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus, name="anomaly_status"), nullable=False, default=AnomalyStatus.NEW
    )
    analysis_status: Mapped[AnomalyAnalysisStatus] = mapped_column(
        Enum(AnomalyAnalysisStatus, name="anomaly_analysis_status"),
        nullable=False,
        default=AnomalyAnalysisStatus.NOT_ANALYZED,
    )
    # analysis_status değerini o anda sahiplenen AnomalyAnalysis satırını gösterir.
    # anomaly_analyses içindeki claim INSERT'iyle atomik olarak ayarlanır ve anomalinin
    # claim token'ıdır. analysis_status yalnızca current_analysis_id yazan denemeyle
    # hâlâ eşleşiyorsa güncellenir; stale-job watchdog sonrası devam eden eski worker,
    # yeni denemenin durumunun üzerine yazamaz.
    current_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("anomaly_analyses.id", ondelete="SET NULL"), nullable=True
    )

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    shift_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shifts.id"), nullable=True, index=True)
    kpi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kpis.id"), nullable=False, index=True)

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    observed_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    expected_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    deviation_percent: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False)
    ml_confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)

    affected_days: Mapped[int | None] = mapped_column(nullable=True)
    total_days: Mapped[int | None] = mapped_column(nullable=True)

    comparison: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    related_signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    foreman_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    data_quality_status: Mapped[str] = mapped_column(String(20), nullable=False, default="valid")
    data_quality_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class AnomalyAnalysis(TimestampMixin, Base):

    __tablename__ = "anomaly_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    anomaly_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("anomalies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    model: Mapped[str] = mapped_column(String(100), nullable=False)
    is_demo: Mapped[bool] = mapped_column(nullable=False, default=True)
    mode: Mapped[AnalysisMode] = mapped_column(
        Enum(AnalysisMode, name="analysis_mode"), nullable=False, default=AnalysisMode.SINGLE_CONTEXT
    )
    status: Mapped[AnomalyAnalysisStatus] = mapped_column(
        Enum(AnomalyAnalysisStatus, name="anomaly_analysis_run_status"), nullable=False
    )

    investigation_plan: Mapped[list | None] = mapped_column(JSON, nullable=True)

    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    input_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnomalyToolCall(TimestampMixin, Base):

    __tablename__ = "anomaly_tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("anomaly_analyses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    anomaly_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("anomalies.id", ondelete="CASCADE"), nullable=False, index=True)

    step_number: Mapped[int] = mapped_column(nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    record_count: Mapped[int | None] = mapped_column(nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(nullable=True)
