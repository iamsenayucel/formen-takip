import enum

from app.models.enums import Role


class Permission(str, enum.Enum):
    OVERVIEW_VIEW = "overview.view"
    PERFORMANCE_VIEW = "performance.view"
    OPERATIONAL_INTELLIGENCE_VIEW = "operational_intelligence.view"
    OPERATIONAL_IMPACT_CONTRIBUTE = "operational_impact.contribute"
    OUTPUTS_VIEW = "outputs.view"
    REPORTS_CREATE = "reports.create"
    REPORTS_DOWNLOAD = "reports.download"


# Rol, permission'ların sabit bir paketidir — inheritance zinciri yok, her rol kendi tam
# permission kümesini açıkça listeler. Yeni bir rol eklemek (ör. ileride READ_ONLY/REPORT_USER)
# sadece bu dict'e bir satır eklemekle olur; kod içinde `role == X` veya rol seviyesi
# karşılaştırması YAPILMAZ — her yetki kararı `permission in permissions` ile verilir.
ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.FOREMAN: frozenset(
        {
            Permission.OVERVIEW_VIEW,
            Permission.PERFORMANCE_VIEW,
        }
    ),
    Role.SUPERVISOR: frozenset(
        {
            Permission.OVERVIEW_VIEW,
            Permission.PERFORMANCE_VIEW,
            Permission.OPERATIONAL_INTELLIGENCE_VIEW,
            Permission.OPERATIONAL_IMPACT_CONTRIBUTE,
        }
    ),
    Role.OPERATIONS_MANAGER: frozenset(
        {
            Permission.OVERVIEW_VIEW,
            Permission.PERFORMANCE_VIEW,
            Permission.OPERATIONAL_INTELLIGENCE_VIEW,
            Permission.OPERATIONAL_IMPACT_CONTRIBUTE,
            Permission.OUTPUTS_VIEW,
            Permission.REPORTS_CREATE,
            Permission.REPORTS_DOWNLOAD,
        }
    ),
}


ROLE_LABELS_TR: dict[Role, str] = {
    Role.FOREMAN: "Formen",
    Role.SUPERVISOR: "Şef",
    Role.OPERATIONS_MANAGER: "Operasyon Yöneticisi",
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
