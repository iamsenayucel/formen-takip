from types import SimpleNamespace

import pytest

from app.api.authz_deps import assert_plant_ids_in_scope, assert_plant_in_scope, require_permission
from app.core.errors import ForbiddenError
from app.core.permissions import Permission
from app.models.enums import Role
from app.schemas.authz import AuthContext

import uuid


class _FakeRequest:
    def __init__(self, method: str = "GET"):
        self.method = method
        self.url = SimpleNamespace(path="/api/v1/reports")


class _FakeDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


def _ctx(permissions, plant_ids=None):
    return AuthContext(
        subject="test-subject", role=Role.OPERATIONS_MANAGER, permissions=frozenset(permissions), plant_ids=plant_ids
    )


class TestRequirePermissionIsPermissionDriven:
    """`reports.create` ve `reports.download`'ın birbirinden bağımsız kontrol edildiğini,
    mekanizmanın role değil doğrudan permission set'ine baktığını kanıtlar — bugünkü
    ROLE_PERMISSIONS tablosunda ikisi de yalnızca OPERATIONS_MANAGER'da birlikte bulunsa da,
    require_permission bu ayrımı role bakmadan uygular."""

    def test_allows_when_permission_present(self):
        dep = require_permission(Permission.REPORTS_CREATE)
        ctx = _ctx({Permission.REPORTS_CREATE})
        result = dep(_FakeRequest("POST"), ctx, _FakeDb())
        assert result is ctx

    def test_denies_when_permission_absent_even_with_a_different_permission_present(self):
        dep = require_permission(Permission.REPORTS_DOWNLOAD)
        ctx = _ctx({Permission.REPORTS_CREATE})
        with pytest.raises(ForbiddenError):
            dep(_FakeRequest("GET"), ctx, _FakeDb())

    def test_denies_and_audits_on_write_method(self):
        dep = require_permission(Permission.REPORTS_DOWNLOAD)
        ctx = _ctx(set())
        db = _FakeDb()
        with pytest.raises(ForbiddenError):
            dep(_FakeRequest("POST"), ctx, db)
        assert len(db.added) == 1

    def test_does_not_audit_on_get_denial(self):
        dep = require_permission(Permission.REPORTS_DOWNLOAD)
        ctx = _ctx(set())
        db = _FakeDb()
        with pytest.raises(ForbiddenError):
            dep(_FakeRequest("GET"), ctx, db)
        assert db.added == []


class TestScopeAssertions:
    def test_assert_plant_in_scope_allows_all_scope(self):
        assert_plant_in_scope(_ctx(set(), plant_ids=None), uuid.uuid4())

    def test_assert_plant_in_scope_allows_plant_within_scope(self):
        pid = uuid.uuid4()
        assert_plant_in_scope(_ctx(set(), plant_ids=frozenset({pid})), pid)

    def test_assert_plant_in_scope_denies_plant_outside_scope(self):
        pid, other = uuid.uuid4(), uuid.uuid4()
        with pytest.raises(ForbiddenError):
            assert_plant_in_scope(_ctx(set(), plant_ids=frozenset({pid})), other)

    def test_assert_plant_ids_in_scope_denies_partial_overlap(self):
        pid, other = uuid.uuid4(), uuid.uuid4()
        with pytest.raises(ForbiddenError):
            assert_plant_ids_in_scope(_ctx(set(), plant_ids=frozenset({pid})), [pid, other])

    def test_assert_plant_ids_in_scope_allows_full_subset(self):
        pid, pid2 = uuid.uuid4(), uuid.uuid4()
        assert_plant_ids_in_scope(_ctx(set(), plant_ids=frozenset({pid, pid2})), [pid])
