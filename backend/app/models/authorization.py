import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow
from app.models.enums import Role, ScopeType


class UserRoleAssignment(Base):
    """OIDC `subject` -> Role ataması. `users` tablosuna değil, doğrudan subject'e bağlıdır
    (bkz. app/schemas/auth.py::Identity) — isim/e-posta gibi PII burada tutulmaz."""

    __tablename__ = "user_role_assignments"

    subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class UserScopeAssignment(Base):
    __tablename__ = "user_scope_assignments"
    __table_args__ = (
        CheckConstraint(
            "(scope_type = 'ALL' AND factory_id IS NULL AND plant_id IS NULL) OR "
            "(scope_type = 'FACTORY' AND factory_id IS NOT NULL AND plant_id IS NULL) OR "
            "(scope_type = 'PLANT' AND plant_id IS NOT NULL AND factory_id IS NULL)",
            name="ck_user_scope_assignments_type_columns",
        ),
        UniqueConstraint(
            "subject", "scope_type", "factory_id", "plant_id", name="uq_user_scope_assignments_subject_scope"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(
        String(255), ForeignKey("user_role_assignments.subject", ondelete="CASCADE"), nullable=False, index=True
    )
    scope_type: Mapped[ScopeType] = mapped_column(Enum(ScopeType, name="user_scope_type"), nullable=False)
    factory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("factories.id", ondelete="CASCADE")
    )
    plant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
