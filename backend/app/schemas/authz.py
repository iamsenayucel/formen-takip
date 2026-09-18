from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.permissions import Permission
from app.models.enums import Role


@dataclass(frozen=True)
class AuthContext:
    """Bir isteğin yetkilendirme sonrası durumu: kimlik doğrulamadan (Identity) farklı olarak
    rolü, permission setini ve çözümlenmiş veri kapsamını (scope) taşır.

    `plant_ids`: kullanıcının erişebileceği tesislerin genişletilmiş kümesi.
    `None` = kısıtlama yok (ALL scope). FACTORY tipi scope satırları da bu kümeye
    genişletilerek dahil edilir — tek eksen, bkz. app/api/authz_deps.py::get_auth_context.
    """

    subject: str
    role: Role
    permissions: frozenset[Permission]
    plant_ids: frozenset[UUID] | None

    def has(self, permission: Permission) -> bool:
        return permission in self.permissions
