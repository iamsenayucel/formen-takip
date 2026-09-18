from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.authorization import UserRoleAssignment, UserScopeAssignment
from app.models.enums import Role, ScopeType
from app.services.audit import record_audit


def _scope_description(scope_type: ScopeType, factory_id: UUID | None, plant_ids: list[UUID] | None) -> str:
    if scope_type == ScopeType.ALL:
        return "ALL"
    if scope_type == ScopeType.FACTORY:
        return f"FACTORY:{factory_id}"
    return f"PLANT:{','.join(str(p) for p in (plant_ids or []))}"


def assign_role(
    db: Session,
    subject: str,
    role: Role,
    *,
    scope_type: ScopeType,
    factory_id: UUID | None = None,
    plant_ids: list[UUID] | None = None,
    actor: str,
    ip_address: str | None = None,
) -> None:
    """Bir subject'e rol + scope atar (idempotent upsert); mevcut scope satırları
    her zaman silinip yeniden yazılır, kısmi/eklemeli güncelleme desteklenmez.

    `role.assigned` ve `scope.assigned` bilerek iki ayrı audit satırı olarak yazılır
    (rol ve scope bağımsız izlenebilir kavramlar, bkz. README "Yetkilendirme (RBAC)").
    `db.commit()` yapmaz — transaction yönetimi çağıranın sorumluluğundadır.
    """
    existing = db.get(UserRoleAssignment, subject)
    if existing is None:
        db.add(UserRoleAssignment(subject=subject, role=role))
    else:
        existing.role = role
    db.flush()

    db.execute(delete(UserScopeAssignment).where(UserScopeAssignment.subject == subject))
    if scope_type == ScopeType.ALL:
        db.add(UserScopeAssignment(subject=subject, scope_type=ScopeType.ALL))
    elif scope_type == ScopeType.FACTORY:
        if factory_id is None:
            raise ValueError("FACTORY scope için factory_id gereklidir.")
        db.add(UserScopeAssignment(subject=subject, scope_type=ScopeType.FACTORY, factory_id=factory_id))
    elif scope_type == ScopeType.PLANT:
        if not plant_ids:
            raise ValueError("PLANT scope için en az bir plant_id gereklidir.")
        for pid in plant_ids:
            db.add(UserScopeAssignment(subject=subject, scope_type=ScopeType.PLANT, plant_id=pid))

    record_audit(db, subject=actor, action="role.assigned", entity=subject, new_value=role.value, ip_address=ip_address)
    record_audit(
        db, subject=actor, action="scope.assigned", entity=subject,
        new_value=_scope_description(scope_type, factory_id, plant_ids), ip_address=ip_address,
    )


def revoke_role(db: Session, subject: str, *, actor: str, ip_address: str | None = None) -> bool:
    """Bir subject'in rol ve scope atamasını tamamen kaldırır — fail-closed default-deny'e
    döner (bkz. app/api/authz_deps.py::get_auth_context). İdempotent: atama yoksa `False`
    döner, audit yine de yazılır (denenen revoke her durumda izlenebilir olmalı). `db.commit()`
    yapmaz — transaction yönetimi çağıranın sorumluluğundadır.
    """
    existing = db.get(UserRoleAssignment, subject)
    had_assignment = existing is not None
    previous_role = existing.role.value if existing else None

    if had_assignment:
        db.execute(delete(UserScopeAssignment).where(UserScopeAssignment.subject == subject))
        db.delete(existing)
        db.flush()

    record_audit(
        db, subject=actor, action="role.revoked", entity=subject,
        old_value=previous_role, success=had_assignment, ip_address=ip_address,
    )
    record_audit(db, subject=actor, action="scope.revoked", entity=subject, success=had_assignment, ip_address=ip_address)
    return had_assignment
