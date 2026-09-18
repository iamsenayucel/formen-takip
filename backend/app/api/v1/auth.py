from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.core.permissions import permissions_for_role
from app.db.session import get_db
from app.models.authorization import UserRoleAssignment
from app.schemas.auth import AuthMeResponse, Identity
from app.schemas.base import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=ApiResponse[AuthMeResponse])
def me(
    identity: Identity = Depends(get_current_identity),
    db: Session = Depends(get_db),
) -> ApiResponse[AuthMeResponse]:
    # Bu uç kasıtlı olarak permission-gate'siz: rolü/izinleri olmayan bir kullanıcı da
    # kendi durumunu (role=None, permissions=[]) öğrenebilmeli — frontend'in nav/route
    # gizleme mekanizmasının tek doğruluk kaynağı budur.
    assignment = db.get(UserRoleAssignment, identity.subject)
    role = assignment.role if assignment else None
    permissions = sorted(p.value for p in permissions_for_role(role)) if role else []
    return {
        "data": {
            "subject": identity.subject,
            "display_name": identity.display_name,
            "email": identity.email,
            "role": role.value if role else None,
            "permissions": permissions,
        }
    }
