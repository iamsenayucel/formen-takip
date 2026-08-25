import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    ContributionRole,
    ContributionStatus,
    ContributionWorkType,
    Currency,
    FinancialGainStatus,
    GainPeriod,
    HighlightedGainMode,
    ImpactLevel,
    OtherGainType,
    RepeatPeriod,
    TimeUnit,
)


class ContributionWork(TimestampMixin, Base):

    __tablename__ = "contribution_works"
    __table_args__ = (
        CheckConstraint(
            "work_date IS NULL OR work_date_end IS NULL OR work_date_end >= work_date",
            name="ck_contribution_works_date_range",
        ),
        CheckConstraint("gain_amount IS NULL OR gain_amount >= 0", name="ck_contribution_works_gain_amount_non_negative"),
        CheckConstraint(
            "previous_duration IS NULL OR previous_duration >= 0",
            name="ck_contribution_works_previous_duration_non_negative",
        ),
        CheckConstraint(
            "new_duration IS NULL OR new_duration >= 0", name="ck_contribution_works_new_duration_non_negative"
        ),
        CheckConstraint(
            "per_occurrence_saving IS NULL OR per_occurrence_saving >= 0",
            name="ck_contribution_works_per_occurrence_saving_non_negative",
        ),
        CheckConstraint(
            "repeat_count IS NULL OR repeat_count >= 0", name="ck_contribution_works_repeat_count_non_negative"
        ),
        CheckConstraint(
            "monthly_total_saving_minutes IS NULL OR monthly_total_saving_minutes >= 0",
            name="ck_contribution_works_monthly_total_saving_non_negative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    work_type: Mapped[ContributionWorkType | None] = mapped_column(
        Enum(ContributionWorkType, name="contribution_work_type")
    )
    work_type_other_note: Mapped[str | None] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(String(500))
    detailed_description: Mapped[str | None] = mapped_column(Text)
    problem_description: Mapped[str | None] = mapped_column(Text)
    solution_description: Mapped[str | None] = mapped_column(Text)
    result_description: Mapped[str | None] = mapped_column(Text)

    work_date: Mapped[date | None] = mapped_column(Date)
    work_date_end: Mapped[date | None] = mapped_column(Date)

    impact_level: Mapped[ImpactLevel | None] = mapped_column(Enum(ImpactLevel, name="contribution_impact_level"))
    status: Mapped[ContributionStatus] = mapped_column(
        Enum(ContributionStatus, name="contribution_status"), nullable=False, default=ContributionStatus.DRAFT
    )
    # OIDC access token'ındaki stabil kimlik claim'i (bkz. Settings.oidc_user_id_claim) —
    # kasıtlı olarak users tablosuna FK değil; kimlik doğrulama otoritesi SSO'dur.
    created_by_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_standardized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_applicable_other_plants: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_permanent_solution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    work_instruction_updated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    financial_gain_status: Mapped[FinancialGainStatus] = mapped_column(
        Enum(FinancialGainStatus, name="financial_gain_status"),
        nullable=False,
        default=FinancialGainStatus.NOT_CALCULATED,
    )
    gain_amount: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[Currency | None] = mapped_column(Enum(Currency, name="contribution_currency"))
    gain_period: Mapped[GainPeriod | None] = mapped_column(Enum(GainPeriod, name="contribution_gain_period"))
    calculation_method: Mapped[str | None] = mapped_column(Text)

    previous_duration: Mapped[float | None] = mapped_column(Numeric(10, 2))
    new_duration: Mapped[float | None] = mapped_column(Numeric(10, 2))
    duration_unit: Mapped[TimeUnit | None] = mapped_column(Enum(TimeUnit, name="contribution_time_unit"))
    per_occurrence_saving: Mapped[float | None] = mapped_column(Numeric(10, 2))
    repeat_period: Mapped[RepeatPeriod | None] = mapped_column(Enum(RepeatPeriod, name="contribution_repeat_period"))
    repeat_count: Mapped[float | None] = mapped_column(Numeric(10, 2))
    monthly_total_saving_minutes: Mapped[float | None] = mapped_column(Numeric(12, 2))

    highlighted_gain_mode: Mapped[HighlightedGainMode] = mapped_column(
        Enum(HighlightedGainMode, name="contribution_highlighted_gain_mode"),
        nullable=False,
        default=HighlightedGainMode.AUTO,
    )
    highlighted_gain_ref: Mapped[str | None] = mapped_column(String(80))

    # Sistem tarafından etki/kapsam/kalıcılık/doğrulanabilirlik kriterlerinden otomatik hesaplanır (1-5).
    contribution_score: Mapped[int | None] = mapped_column(Integer)


class ContributionWorkForeman(Base):

    __tablename__ = "contribution_work_foremen"

    work_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contribution_works.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), primary_key=True, index=True)
    role: Mapped[ContributionRole] = mapped_column(
        Enum(ContributionRole, name="contribution_role"), nullable=False, default=ContributionRole.CONTRIBUTOR
    )


class ContributionWorkPlant(Base):

    __tablename__ = "contribution_work_plants"

    work_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contribution_works.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plants.id"), primary_key=True, index=True)


class ContributionGain(TimestampMixin, Base):

    __tablename__ = "contribution_gains"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("contribution_works.id", ondelete="CASCADE"), nullable=False, index=True
    )

    gain_type: Mapped[OtherGainType] = mapped_column(Enum(OtherGainType, name="contribution_other_gain_type"), nullable=False)
    gain_type_other_note: Mapped[str | None] = mapped_column(String(300))
    previous_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    next_value: Mapped[float | None] = mapped_column(Numeric(14, 4))
    change_amount: Mapped[float | None] = mapped_column(Numeric(14, 4))
    change_percent: Mapped[float | None] = mapped_column(Numeric(8, 3))
    unit: Mapped[str | None] = mapped_column(String(50))
    measurement_period: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
