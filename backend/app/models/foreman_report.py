import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ReportEmailStatus, ReportGenerationStatus, ReportStorageProvider


class ForemanMonthlyReport(TimestampMixin, Base):

    __tablename__ = "foreman_monthly_reports"
    __table_args__ = (
        UniqueConstraint("foreman_id", "year", "month", name="uq_foreman_monthly_reports_foreman_year_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    foreman_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("foremen.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Numeric(6, 2))
    overall_level_name: Mapped[str | None] = mapped_column(String(50))
    is_reliable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # PDF kalıcı depolaması — dosya bytes'ı burada değil, yalnızca Private S3 referansı
    # tutulur (bkz. app/services/storage). CloudFront signed URL kalıcı değildir, bu
    # yüzden burada saklanan hiçbir alan yok; her erişimde yeniden üretilir.
    pdf_generation_status: Mapped[ReportGenerationStatus] = mapped_column(
        Enum(ReportGenerationStatus, name="report_generation_status"),
        nullable=False, default=ReportGenerationStatus.PENDING,
    )
    pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    storage_provider: Mapped[ReportStorageProvider | None] = mapped_column(
        Enum(ReportStorageProvider, name="report_storage_provider")
    )
    storage_bucket: Mapped[str | None] = mapped_column(String(255))
    object_key: Mapped[str | None] = mapped_column(String(500), unique=True)
    pdf_file_name: Mapped[str | None] = mapped_column(String(300))
    pdf_content_type: Mapped[str | None] = mapped_column(String(100))
    pdf_file_size: Mapped[int | None] = mapped_column(Integer)

    email_status: Mapped[ReportEmailStatus] = mapped_column(
        Enum(ReportEmailStatus, name="report_email_status"), nullable=False, default=ReportEmailStatus.PENDING
    )
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_last_error: Mapped[str | None] = mapped_column(String(500))

    # SENDING durumu için claim lease: İşi PENDING/FAILED -> SENDING geçişiyle sahiplenen
    # koşullu UPDATE tarafından atomik ayarlanır, tamamlanma veya reconciliation sırasında
    # temizlenir. claim_token son SENDING -> SENT/FAILED geçişini korur; stale-job watchdog
    # sonrası devam eden eski worker yeni denemenin sonucunun üzerine yazamaz.
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claim_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
