from app.core.permissions import ROLE_PERMISSIONS, Permission, permissions_for_role
from app.models.enums import Role

EXPECTED = {
    Role.FOREMAN: {
        Permission.OVERVIEW_VIEW,
        Permission.PERFORMANCE_VIEW,
    },
    Role.SUPERVISOR: {
        Permission.OVERVIEW_VIEW,
        Permission.PERFORMANCE_VIEW,
        Permission.OPERATIONAL_INTELLIGENCE_VIEW,
        Permission.OPERATIONAL_IMPACT_CONTRIBUTE,
    },
    Role.OPERATIONS_MANAGER: {
        Permission.OVERVIEW_VIEW,
        Permission.PERFORMANCE_VIEW,
        Permission.OPERATIONAL_INTELLIGENCE_VIEW,
        Permission.OPERATIONAL_IMPACT_CONTRIBUTE,
        Permission.OUTPUTS_VIEW,
        Permission.REPORTS_CREATE,
        Permission.REPORTS_DOWNLOAD,
    },
}


class TestRolePermissionTable:
    def test_every_role_has_an_entry(self):
        for role in Role:
            assert role in ROLE_PERMISSIONS

    def test_matches_spec_truth_table(self):
        for role, expected in EXPECTED.items():
            assert ROLE_PERMISSIONS[role] == frozenset(expected), role

    def test_permissions_for_role_matches_table(self):
        for role in Role:
            assert permissions_for_role(role) == ROLE_PERMISSIONS[role]


class TestContributeImpliesView:
    """Şu invariant korunmalı: operational_impact.contribute'a sahip her rol,
    operational_intelligence.view'a da sahiptir. Bu, contributions.py'daki yazma
    uçlarının yalnızca contribute permission'ını kontrol etmesinin (view'ı ayrıca
    kontrol etmeden) güvenli olmasının temelidir."""

    def test_contribute_implies_view_for_every_role(self):
        for role, permissions in ROLE_PERMISSIONS.items():
            if Permission.OPERATIONAL_IMPACT_CONTRIBUTE in permissions:
                assert Permission.OPERATIONAL_INTELLIGENCE_VIEW in permissions, role


class TestNoRoleHierarchyLeakage:
    """Formen'in hiçbir permission'ı, Şef'in bir alt kümesi olmayan bir şey içermemeli
    (permission'lar açık setlerdir, sayısal bir rol seviyesi karşılaştırması yoktur —
    ama pratikte bu üç rol arasında görünürlük artan bir zincir oluşturur)."""

    def test_foreman_is_subset_of_supervisor(self):
        assert ROLE_PERMISSIONS[Role.FOREMAN] <= ROLE_PERMISSIONS[Role.SUPERVISOR]

    def test_supervisor_is_subset_of_operations_manager(self):
        assert ROLE_PERMISSIONS[Role.SUPERVISOR] <= ROLE_PERMISSIONS[Role.OPERATIONS_MANAGER]
