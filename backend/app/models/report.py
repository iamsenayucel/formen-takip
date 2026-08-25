import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import ReportFormat, ReportStatus, ReportType


class ReportExport(TimestampMixin, Base):

    __tablename__ = "report_exports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type: Mapped[ReportType] = mapped_column(Enum(ReportType, name="report_type"), nullable=False)
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat, name="report_format"), nullable=False)
    filters_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # OIDC access token'ındaki stabil kimlik claim'i (bkz. Settings.oidc_user_id_claim) —
    # kasıtlı olarak users tablosuna FK değil; kimlik doğrulama otoritesi SSO'dur.
    requested_by_subject: Mapped[str] = mapped_column(String(255), nullable=False)

    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    file_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"), nullable=False, default=ReportStatus.COMPLETED
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
