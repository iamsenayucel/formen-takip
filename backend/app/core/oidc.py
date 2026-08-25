from __future__ import annotations

import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.core.config import get_settings


class OIDCConfigError(Exception):
    pass


class TokenValidationError(Exception):
    pass


_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _discover_jwks_uri(issuer_url: str) -> str:
    settings = get_settings()
    if settings.oidc_jwks_uri:
        return settings.oidc_jwks_uri
    discovery_url = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
    resp = httpx.get(discovery_url, timeout=5.0)
    resp.raise_for_status()
    jwks_uri = resp.json().get("jwks_uri")
    if not jwks_uri:
        raise OIDCConfigError("OIDC discovery belgesi jwks_uri içermiyor.")
    return jwks_uri


def fetch_jwks(jwks_uri: str) -> dict[str, Any]:
    resp = httpx.get(jwks_uri, timeout=5.0)
    resp.raise_for_status()
    return resp.json()


def _get_jwks(issuer_url: str, *, force_refresh: bool = False) -> dict[str, Any]:
    settings = get_settings()
    cached = _jwks_cache.get(issuer_url)
    now = time.monotonic()
    if not force_refresh and cached and now - cached[0] < settings.oidc_jwks_cache_seconds:
        return cached[1]
    jwks_uri = _discover_jwks_uri(issuer_url)
    jwks = fetch_jwks(jwks_uri)
    _jwks_cache[issuer_url] = (now, jwks)
    return jwks


def _find_key(jwks: dict[str, Any], kid: str | None) -> dict[str, Any] | None:
    for key in jwks.get("keys", []):
        if kid is None or key.get("kid") == kid:
            return key
    return None


def verify_access_token(token: str) -> dict[str, Any]:
    """Doğrular: signature, issuer, audience, expiration. Başarısızlıkta TokenValidationError fırlatır."""
    settings = get_settings()
    if not settings.oidc_issuer_url or not settings.oidc_audience:
        raise OIDCConfigError("OIDC yapılandırması eksik (OIDC_ISSUER_URL / OIDC_AUDIENCE).")

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise TokenValidationError("Geçersiz jeton formatı.") from exc

    kid = header.get("kid")
    jwks = _get_jwks(settings.oidc_issuer_url)
    key = _find_key(jwks, kid)
    if key is None:
        # Anahtar rotasyonu olabilir: JWKS'i zorla yenileyip tekrar dene.
        jwks = _get_jwks(settings.oidc_issuer_url, force_refresh=True)
        key = _find_key(jwks, kid)
    if key is None:
        raise TokenValidationError("Jeton imzası doğrulanamadı: eşleşen anahtar bulunamadı.")

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[key.get("alg", "RS256")],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer_url,
            options={"require_exp": True, "require_iat": True},
        )
    except JWTError as exc:
        raise TokenValidationError("Jeton doğrulanamadı: imza, issuer, audience veya süre geçersiz.") from exc

    return claims
