from typing import Any

from pydantic import BaseModel

from app.schemas.base import CamelModel


class AuthMeResponse(CamelModel):
    subject: str
    display_name: str | None
    email: str | None


class Identity(BaseModel):
    """Doğrulanmış OIDC access token'ından türetilen çalışma zamanı kimliği.

    `subject`, uygulama veritabanındaki tüm created_by/requested_by ilişkilendirmelerinde
    kullanılan tek stabil alandır. `claims` yalnızca çalışma zamanında (ör. arayüzde ad/e-posta
    göstermek için) kullanılır ve hiçbir yerde kalıcı olarak saklanmaz.
    """

    subject: str
    claims: dict[str, Any]

    @property
    def display_name(self) -> str | None:
        return self.claims.get("name") or self.claims.get("preferred_username")

    @property
    def email(self) -> str | None:
        return self.claims.get("email")
