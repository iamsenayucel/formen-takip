import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # OIDC access token'ındaki stabil kimlik claim'i (bkz. Settings.oidc_user_id_claim).
    # Kasıtlı olarak users tablosuna FK değildir: kimlik doğrulama otoritesi SSO'dur,
    # uygulama DB'si kullanıcı profili tutmaz.
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity: Mapped[str | None] = mapped_column(String(100))
    old_value: Mapped[str | None] = mapped_column(String(2000))
    new_value: Mapped[str | None] = mapped_column(String(2000))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    session_info: Mapped[str | None] = mapped_column(String(200))
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
