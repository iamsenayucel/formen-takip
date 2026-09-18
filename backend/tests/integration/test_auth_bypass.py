import pytest
from tests.helpers import legacy_json

from app.core.config import get_settings


@pytest.fixture
def bypass_on(monkeypatch, role_assignment_factory):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_bypass", True)
    monkeypatch.setattr(settings, "environment", "development")
    # RBAC: bypass subject'i (dev-demo-user) gerçek dev/demo ortamında `cmd_seed`'in
    # otomatik atadığı rolü burada da taklit eder — aksi halde her korumalı uç 403 döner.
    from app.models.enums import Role, ScopeType

    role_assignment_factory(subject="dev-demo-user", role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.ALL)
    yield settings


class TestBypassEnabled:
    def test_protected_endpoint_without_token_returns_200(self, client, bypass_on):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 200

    def test_identity_subject_is_dev_demo_user(self, client, bypass_on):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert legacy_json(resp)["subject"] == "dev-demo-user"


class TestBypassDisabledLeavesNormalFlowIntact:
    def test_no_token_still_returns_401(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    def test_valid_oidc_token_still_returns_200(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
