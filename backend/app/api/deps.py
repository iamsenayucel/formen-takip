from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import log_context
from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.oidc import OIDCConfigError, TokenValidationError, verify_access_token
from app.schemas.auth import Identity

_bearer_scheme = HTTPBearer(auto_error=False)

_DEV_BYPASS_SUBJECT = "dev-demo-user"


def _bind_subject(request: Request, subject: str) -> None:
    request.state.subject = subject
    log_context.bind_subject(subject)


def get_current_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> Identity:
    settings = get_settings()

    # Yalnızca geliştirme/demo içindir. Settings, ENVIRONMENT=development dışında
    # auth_bypass=True değerini reddettiğinden production'da OIDC doğrulaması atlanamaz.
    if settings.auth_bypass and settings.environment == "development":
        _bind_subject(request, _DEV_BYPASS_SUBJECT)
        return Identity(subject=_DEV_BYPASS_SUBJECT, claims={"name": "Demo User", "sub": _DEV_BYPASS_SUBJECT})

    if credentials is None:
        raise UnauthorizedError("Kimlik doğrulama gerekli.")

    try:
        claims = verify_access_token(credentials.credentials)
    except (OIDCConfigError, TokenValidationError):
        raise UnauthorizedError("Geçersiz veya süresi dolmuş oturum.")

    subject = claims.get(settings.oidc_user_id_claim) or claims.get("sub")
    if not subject:
        raise UnauthorizedError("Jeton kimlik bilgisi içermiyor.")

    subject = str(subject)
    _bind_subject(request, subject)
    return Identity(subject=subject, claims=claims)
