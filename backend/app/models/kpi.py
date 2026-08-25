import uuid
from datetime import date

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AggregationMethod, CalculationType, TargetScopeType


class Kpi(TimestampMixin, Base):
    __tablename__ = "kpis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    calculation_type: Mapped[CalculationType] = mapped_column(Enum(CalculationType, name="calculation_type"), nullable=False)
    success_direction_higher: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_target_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    min_valid_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=0)
    max_valid_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False, default=1_000_000)
    min_score: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    max_score: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=120)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_data_field: Mapped[str | None] = mapped_column(String(100))
    aggregation_method: Mapped[AggregationMethod] = mapped_column(
        Enum(AggregationMethod, name="aggregation_method"), nullable=False, default=AggregationMethod.WEIGHTED_AVERAGE
    )
    decimal_places: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    calculation_rules: Mapped[list["KpiCalculationRule"]] = relationship(back_populates="kpi")
    targets: Mapped[list["KpiTarget"]] = relationship(back_populates="kpi")


class KpiCalculationRule(TimestampMixin, Base):

    __tablename__ = "kpi_calculation_rules"
    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_kpi_calculation_rules_date_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kpis.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    calculation_type: Mapped[CalculationType] = mapped_column(Enum(CalculationType, name="calc_rule_type"), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    kpi: Mapped[Kpi] = relationship(back_populates="calculation_rules")


class KpiTarget(TimestampMixin, Base):

    __tablename__ = "kpi_targets"
    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_kpi_targets_date_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kpis.id"), nullable=False, index=True)
    scope_type: Mapped[TargetScopeType] = mapped_column(Enum(TargetScopeType, name="target_scope_type"), nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    target_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    kpi: Mapped[Kpi] = relationship(back_populates="targets")


class PerformanceLevelRule(TimestampMixin, Base):
    __tablename__ = "performance_level_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    min_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
