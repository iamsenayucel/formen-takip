from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.oidc import OIDCConfigError, TokenValidationError, verify_access_token
from app.schemas.auth import Identity

_bearer_scheme = HTTPBearer(auto_error=False)

_DEV_BYPASS_SUBJECT = "dev-demo-user"


def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> Identity:
    settings = get_settings()

    # Yalnızca geliştirme/demo içindir. Settings, ENVIRONMENT=development dışında
    # auth_bypass=True değerini reddettiğinden production'da OIDC doğrulaması atlanamaz.
    if settings.auth_bypass and settings.environment == "development":
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

    return Identity(subject=str(subject), claims=claims)
