from fastapi import APIRouter, Depends

from app.api.deps import get_current_identity
from app.schemas.auth import AuthMeResponse, Identity
from app.schemas.base import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=ApiResponse[AuthMeResponse])
def me(identity: Identity = Depends(get_current_identity)) -> ApiResponse[AuthMeResponse]:
    return {
        "data": {
            "subject": identity.subject,
            "display_name": identity.display_name,
            "email": identity.email,
        }
    }
