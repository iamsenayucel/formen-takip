
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import SourceSystem


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    standard_gram: Mapped[float | None] = mapped_column(Numeric(10, 3))
    lower_gram_limit: Mapped[float | None] = mapped_column(Numeric(10, 3))
    upper_gram_limit: Mapped[float | None] = mapped_column(Numeric(10, 3))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sap_material_code: Mapped[str | None] = mapped_column(String(30))


class ProductionLine(TimestampMixin, Base):

    __tablename__ = "production_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CompanyCalendarDay(TimestampMixin, Base):

    __tablename__ = "company_calendar"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))


class ForemanWorkCalendar(TimestampMixin, Base):

    __tablename__ = "foreman_work_calendar"
    __table_args__ = (
        UniqueConstraint("foreman_id", "work_date", "plant_id", name="uq_foreman_work_calendar_foreman_date_plant"),
        ForeignKeyConstraint(["plant_id", "chief_id"], ["plants.id", "plants.chief_id"], name="fk_foreman_work_calendar_plant_chief"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), nullable=False, index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    chief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chiefs.id"), nullable=False, index=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id"), nullable=False, index=True)
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("production_lines.id"), nullable=False, index=True)
    is_working: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProductionRecord(TimestampMixin, Base):

    __tablename__ = "production_records"
    __table_args__ = (
        UniqueConstraint("source_system", "source_record_id", name="uq_production_record_source"),
        UniqueConstraint(
            "foreman_id", "production_date", "shift_id", "plant_id", name="uq_production_record_natural_key"
        ),
        ForeignKeyConstraint(["plant_id", "chief_id"], ["plants.id", "plants.chief_id"], name="fk_production_records_plant_chief"),
        CheckConstraint(
            "working_time_minutes IS NULL OR (working_time_minutes >= 0 AND working_time_minutes <= 720)",
            name="ck_production_records_working_time_minutes_range",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_system: Mapped[SourceSystem] = mapped_column(Enum(SourceSystem, name="production_source_system"), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    production_order_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    batch_number: Mapped[str] = mapped_column(String(50), nullable=False)

    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), nullable=False, index=True)
    line_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("production_lines.id"), nullable=False, index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), nullable=False, index=True)
    chief_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chiefs.id"), nullable=False, index=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id"), nullable=False, index=True)

    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    planned_qty: Mapped[float | None] = mapped_column(Numeric(14, 4))
    actual_qty: Mapped[float | None] = mapped_column(Numeric(14, 4))

    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    standard_speed: Mapped[float | None] = mapped_column(Numeric(14, 4))
    actual_speed: Mapped[float | None] = mapped_column(Numeric(14, 4))

    measured_avg_gram: Mapped[float | None] = mapped_column(Numeric(10, 3))
    gram_sample_count: Mapped[int | None] = mapped_column(Integer)

    gsf_qty: Mapped[float | None] = mapped_column(Numeric(14, 4))
    iskarta_qty: Mapped[float | None] = mapped_column(Numeric(14, 4))

    technical_downtime_minutes: Mapped[float | None] = mapped_column(Numeric(10, 2))
    manufacturing_downtime_minutes: Mapped[float | None] = mapped_column(Numeric(10, 2))
    other_downtime_minutes: Mapped[float | None] = mapped_column(Numeric(10, 2))

    working_time_minutes: Mapped[float | None] = mapped_column(Numeric(6, 2))

    plan_revision_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    plan_revision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
