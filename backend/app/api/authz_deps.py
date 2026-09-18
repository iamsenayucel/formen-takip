from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core.errors import ForbiddenError
from app.core.permissions import Permission, permissions_for_role
from app.db.session import get_db
from app.models.authorization import UserRoleAssignment, UserScopeAssignment
from app.models.enums import ScopeType
from app.models.foreman import ForemanAssignment
from app.models.organization import Plant
from app.schemas.auth import Identity
from app.schemas.authz import AuthContext
from app.schemas.common import Filters, common_filters, narrow_filters
from app.services.audit import record_audit


def _expand_plant_ids(db: Session, scope_rows: list[UserScopeAssignment]) -> frozenset[UUID] | None:
    """Scope satırlarını tek bir `plant_ids` eksenine indirger. `None` = ALL (kısıtsız).

    FACTORY tipi satırlar üye tesislere genişletilir; aksi halde FACTORY-scope'lu bir
    kullanıcının plant_id bazlı kontrolleri (assert_plant_in_scope vb.) kısıtsız kalırdı.
    Hiç scope satırı yoksa (rol atanmış ama scope unutulmuş) boş küme dönülür — veri
    erişiminde fail-closed.
    """
    if not scope_rows:
        return frozenset()
    if any(row.scope_type == ScopeType.ALL for row in scope_rows):
        return None

    plant_ids: set[UUID] = {row.plant_id for row in scope_rows if row.scope_type == ScopeType.PLANT and row.plant_id}
    factory_ids = {row.factory_id for row in scope_rows if row.scope_type == ScopeType.FACTORY and row.factory_id}
    if factory_ids:
        plant_ids.update(db.scalars(select(Plant.id).where(Plant.factory_id.in_(factory_ids))))
    return frozenset(plant_ids)


def get_auth_context(
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
) -> AuthContext:
    assignment = db.get(UserRoleAssignment, identity.subject)
    if assignment is None:
        raise ForbiddenError(
            "Bu kullanıcı için tanımlı bir rol bulunmuyor. Erişim için sistem yöneticinizle iletişime geçin."
        )

    scope_rows = list(
        db.scalars(select(UserScopeAssignment).where(UserScopeAssignment.subject == identity.subject))
    )
    return AuthContext(
        subject=identity.subject,
        role=assignment.role,
        permissions=permissions_for_role(assignment.role),
        plant_ids=_expand_plant_ids(db, scope_rows),
    )


def scoped_filters(
    filters: Filters = Depends(common_filters),
    ctx: AuthContext = Depends(get_auth_context),
) -> Filters:
    """`common_filters`'ın scope-aware sürümü. `dashboard.py`/`plants.py`/`chiefs.py`/
    `foremen.py`/`kpis.py` gibi `Filters` tüketen tüm route'lar bunu kullanmalı; ham
    `common_filters` yalnızca zaten scope-narrow edilmiş bir `Filters`'ı türetmek
    (ör. `dataclasses.replace`) için route-içi kullanılabilir."""
    return narrow_filters(filters, ctx.plant_ids)


def require_permission(permission: Permission) -> Callable[..., AuthContext]:
    """Belirtilen permission'a sahip olmayan istekleri 403 ile reddeden bir FastAPI
    dependency'si üretir. Route'larda `Depends(require_permission(Permission.X))` olarak
    kullanılır — permission kontrolü asla route gövdesi içine dağılmaz (`if role == ...`
    deseni bu sistemde hiçbir yerde yoktur)."""

    def _dependency(
        request: Request,
        ctx: AuthContext = Depends(get_auth_context),
        db: Session = Depends(get_db),
    ) -> AuthContext:
        if not ctx.has(permission):
            if request.method != "GET":
                record_audit(
                    db,
                    subject=ctx.subject,
                    action="permission.denied",
                    entity=permission.value,
                    success=False,
                    error_message=f"{request.method} {request.url.path}",
                )
                db.commit()
            raise ForbiddenError(f"Bu işlem için '{permission.value}' yetkisi gereklidir.")
        return ctx

    return _dependency


def assert_plant_in_scope(ctx: AuthContext, plant_id: UUID) -> None:
    if ctx.plant_ids is not None and plant_id not in ctx.plant_ids:
        raise ForbiddenError("Bu tesise erişim yetkiniz bulunmuyor.")


def assert_plant_ids_in_scope(ctx: AuthContext, plant_ids: Iterable[UUID]) -> None:
    if ctx.plant_ids is None:
        return
    requested = set(plant_ids)
    if not requested.issubset(ctx.plant_ids):
        raise ForbiddenError("İstenen tesislerden bir veya daha fazlası erişim kapsamınız dışında.")


def assert_chief_in_scope(db: Session, ctx: AuthContext, chief_id: UUID) -> None:
    if ctx.plant_ids is None:
        return
    chief_plant_ids = set(db.scalars(select(Plant.id).where(Plant.chief_id == chief_id)))
    if not chief_plant_ids or chief_plant_ids.isdisjoint(ctx.plant_ids):
        raise ForbiddenError("Bu şefin sorumluluk alanına erişim yetkiniz bulunmuyor.")


def assert_foreman_in_scope(db: Session, ctx: AuthContext, foreman_id: UUID) -> None:
    if ctx.plant_ids is None:
        return
    foreman_plant_ids = set(
        db.scalars(select(ForemanAssignment.plant_id).where(ForemanAssignment.foreman_id == foreman_id))
    )
    if not foreman_plant_ids or foreman_plant_ids.isdisjoint(ctx.plant_ids):
        raise ForbiddenError("Bu formene erişim yetkiniz bulunmuyor.")
