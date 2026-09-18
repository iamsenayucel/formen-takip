import uuid

import pytest
from sqlalchemy import delete

from app.core.permissions import ROLE_PERMISSIONS, Permission
from app.models.contribution import ContributionWork
from app.models.enums import Role
from app.models.report import ReportExport
from tests.helpers import unwrap_error

from .conftest import TEST_SUBJECT


@pytest.fixture(autouse=True)
def _cleanup_created_rows(db_session):
    """Bu dosyadaki testler gerçek endpoint'ler üzerinden rapor/katkı çalışması
    oluşturabilir (izin testleri, mock değil gerçek create akışını kullanır) — bu satırlar
    diğer dosyalardaki (ör. test_report_list.py) sayım bazlı assertion'lara sızmasın diye
    her testten sonra temizlenir."""
    yield
    db_session.rollback()
    db_session.execute(delete(ReportExport).where(ReportExport.requested_by_subject == TEST_SUBJECT))
    db_session.execute(delete(ContributionWork).where(ContributionWork.created_by_subject == TEST_SUBJECT))
    db_session.commit()

# Formen/Şef/Operasyon Yöneticisi erişim matrisi. Path'lerdeki UUID'ler rastgele —
# permission kontrolü route handler gövdesinden önce (dependency aşamasında) çalıştığı
# için kaynağın gerçekten var olması permission-red testlerinde önemli değildir.
_RANDOM_ID = uuid.uuid4()

FOREMAN_MATRIX = [
    ("GET", "/api/v1/dashboard/summary", 200),
    ("GET", "/api/v1/plants", 200),
    ("GET", "/api/v1/foremen", 200),
    ("GET", "/api/v1/anomalies", 403),
    ("GET", "/api/v1/shift-analysis/cards", 403),
    ("GET", "/api/v1/contribution-works", 403),
    ("POST", "/api/v1/contribution-works", 403),
    ("GET", "/api/v1/reports", 403),
    ("POST", "/api/v1/reports/generate", 403),
    (
        "GET",
        f"/api/v1/reports/{_RANDOM_ID}/download",
        403,
    ),
]

SUPERVISOR_MATRIX = [
    ("GET", "/api/v1/dashboard/summary", 200),
    ("GET", "/api/v1/plants", 200),
    ("GET", "/api/v1/anomalies", 200),
    ("GET", "/api/v1/shift-analysis/cards", 200),
    ("GET", "/api/v1/contribution-works", 200),
    ("GET", "/api/v1/reports", 403),
    ("POST", "/api/v1/reports/generate", 403),
    ("GET", f"/api/v1/reports/{_RANDOM_ID}/download", 403),
]

OPERATIONS_MANAGER_MATRIX = [
    ("GET", "/api/v1/dashboard/summary", 200),
    ("GET", "/api/v1/plants", 200),
    ("GET", "/api/v1/anomalies", 200),
    ("GET", "/api/v1/shift-analysis/cards", 200),
    ("GET", "/api/v1/contribution-works", 200),
    ("GET", "/api/v1/reports", 200),
]


def _request(client, headers, method, path, json=None):
    if method == "GET":
        return client.get(path, headers=headers)
    if method == "POST":
        return client.post(path, headers=headers, json=json or {})
    if method == "PATCH":
        return client.patch(path, headers=headers, json=json or {})
    raise ValueError(method)


class TestForemanAccessMatrix:
    def test_matrix(self, client, auth_headers, role_assignment_factory):
        role_assignment_factory(role=Role.FOREMAN)
        for method, path, expected in FOREMAN_MATRIX:
            resp = _request(client, auth_headers, method, path, json={"title": "x"})
            assert resp.status_code == expected, f"{method} {path} -> {resp.status_code}, beklenen {expected}"
            if expected == 403:
                assert unwrap_error(resp)["code"] == "FORBIDDEN"


class TestSupervisorAccessMatrix:
    def test_matrix(self, client, auth_headers, role_assignment_factory):
        role_assignment_factory(role=Role.SUPERVISOR)
        for method, path, expected in SUPERVISOR_MATRIX:
            resp = _request(client, auth_headers, method, path, json={"title": "x"})
            assert resp.status_code == expected, f"{method} {path} -> {resp.status_code}, beklenen {expected}"

    def test_supervisor_can_create_contribution_work(self, client, auth_headers, role_assignment_factory):
        role_assignment_factory(role=Role.SUPERVISOR)
        resp = client.post("/api/v1/contribution-works", headers=auth_headers, json={"title": "Entegrasyon testi"})
        assert resp.status_code == 201


class TestOperationsManagerAccessMatrix:
    def test_matrix(self, client, auth_headers, role_assignment_factory):
        role_assignment_factory(role=Role.OPERATIONS_MANAGER)
        for method, path, expected in OPERATIONS_MANAGER_MATRIX:
            resp = _request(client, auth_headers, method, path)
            assert resp.status_code == expected, f"{method} {path} -> {resp.status_code}, beklenen {expected}"


class TestNoRoleAssigned:
    """`user_role_assignments`'ta satırı olmayan bir subject her yerde 403 almalı
    (default-deny — CLAUDE.md'nin fail-closed felsefesiyle tutarlı)."""

    def test_denied_everywhere_without_role_assignment(self, client, db_session):
        from sqlalchemy import delete

        from app.models.authorization import UserRoleAssignment, UserScopeAssignment

        db_session.execute(delete(UserScopeAssignment).where(UserScopeAssignment.subject == TEST_SUBJECT))
        db_session.execute(delete(UserRoleAssignment).where(UserRoleAssignment.subject == TEST_SUBJECT))
        db_session.commit()

        from .conftest import make_test_token

        headers = {"Authorization": f"Bearer {make_test_token()}"}
        resp = client.get("/api/v1/dashboard/summary", headers=headers)
        assert resp.status_code == 403


class TestActionLevelPermissionSplit:
    """operational_intelligence.view=true, operational_impact.contribute=false olan bir
    kullanıcı Operasyonel Zeka'yı görebilmeli ama katkı ekleyememeli. Bugünkü ROLE_PERMISSIONS
    tablosunda hiçbir rol bu ayrımı doğal olarak üretmediği için (contribute her zaman view'ı
    içerir), SUPERVISOR'ın permission setini test süresince geçici olarak daraltıyoruz."""

    def test_view_without_contribute(self, client, auth_headers, role_assignment_factory, monkeypatch):
        role_assignment_factory(role=Role.SUPERVISOR)
        monkeypatch.setitem(
            ROLE_PERMISSIONS,
            Role.SUPERVISOR,
            ROLE_PERMISSIONS[Role.SUPERVISOR] - {Permission.OPERATIONAL_IMPACT_CONTRIBUTE},
        )

        view_resp = client.get("/api/v1/contribution-works", headers=auth_headers)
        assert view_resp.status_code == 200

        create_resp = client.post(
            "/api/v1/contribution-works", headers=auth_headers, json={"title": "İzinsiz katkı denemesi"}
        )
        assert create_resp.status_code == 403


class TestReportsCreateDownloadIndependence:
    """reports.create ve reports.download birbirinden bağımsız olmalı. Bugün ikisi de
    yalnızca OPERATIONS_MANAGER'da birlikte bulunduğundan, gerçek bağımsızlığı kanıtlamak
    için OPERATIONS_MANAGER'ın permission setini test süresince geçici olarak daraltıyoruz
    (reports.download olmadan)."""

    def test_create_allowed_download_denied(self, client, auth_headers, role_assignment_factory, monkeypatch):
        role_assignment_factory(role=Role.OPERATIONS_MANAGER)
        monkeypatch.setitem(
            ROLE_PERMISSIONS,
            Role.OPERATIONS_MANAGER,
            ROLE_PERMISSIONS[Role.OPERATIONS_MANAGER] - {Permission.REPORTS_DOWNLOAD},
        )

        generate_resp = client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"reportType": "company_summary", "format": "csv"},
        )
        assert generate_resp.status_code == 201
        report_id = generate_resp.json()["data"]["id"]

        download_resp = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert download_resp.status_code == 403
