"""Her audit event'inin gerçekten `audit_logs`'a yazıldığını, mock değil doğrudan DB
sorgusuyla doğrular. `permission.override.changed` bilerek yok: sistemde per-user
permission override mekanizması yok; `TestPermissionOverrideEventDoesNotExist` bunu
olumsuz iddia olarak test eder.
"""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.authorization import UserRoleAssignment, UserScopeAssignment
from app.models.contribution import ContributionWork
from app.models.enums import Role, ScopeType
from app.models.user import AuditLog
from app.services.authz_admin import assign_role, revoke_role
from tests.helpers import unwrap

from .conftest import TEST_SUBJECT

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _last_audit(db_session, *, action: str, entity: str | None = None) -> AuditLog | None:
    stmt = select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.created_at.desc())
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    return db_session.execute(stmt).scalars().first()


class TestReportCreatedAudit:
    def test_generate_report_writes_report_created_audit(self, client, auth_headers, db_session):
        resp = client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"reportType": "company_summary", "format": "csv"},
        )
        assert resp.status_code == 201
        file_name = unwrap(resp)["fileName"]

        row = _last_audit(db_session, action="report.created", entity="report_export")
        assert row is not None
        assert row.subject == TEST_SUBJECT
        assert row.new_value == file_name
        assert row.success is True


class TestReportDownloadedAudit:
    def test_download_report_writes_report_downloaded_audit(self, client, auth_headers, report_export_factory, db_session):
        export = report_export_factory()

        resp = client.get(f"/api/v1/reports/{export.id}/download", headers=auth_headers)
        assert resp.status_code == 200

        row = _last_audit(db_session, action="report.downloaded", entity="report_export")
        assert row is not None
        assert row.subject == TEST_SUBJECT
        assert row.new_value == export.file_name


class TestOperationalImpactAudits:
    def test_create_writes_operational_impact_created_audit(self, client, auth_headers, db_session):
        title = f"Audit kanit testi olustur {uuid.uuid4()}"
        resp = client.post("/api/v1/contribution-works", headers=auth_headers, json={"title": title})
        assert resp.status_code == 201
        work_id = unwrap(resp)["id"]

        try:
            row = _last_audit(db_session, action="operational_impact.created", entity="contribution_work")
            assert row is not None
            assert row.subject == TEST_SUBJECT
            assert row.new_value == title
        finally:
            db_session.execute(ContributionWork.__table__.delete().where(ContributionWork.id == uuid.UUID(work_id)))
            db_session.commit()

    def test_update_writes_operational_impact_updated_audit(self, client, auth_headers, db_session):
        title = f"Audit kanit testi guncelle {uuid.uuid4()}"
        create_resp = client.post("/api/v1/contribution-works", headers=auth_headers, json={"title": title})
        assert create_resp.status_code == 201
        work_id = unwrap(create_resp)["id"]

        try:
            new_title = f"{title} (guncellendi)"
            update_resp = client.patch(
                f"/api/v1/contribution-works/{work_id}", headers=auth_headers, json={"title": new_title}
            )
            assert update_resp.status_code == 200

            row = _last_audit(db_session, action="operational_impact.updated", entity="contribution_work")
            assert row is not None
            assert row.subject == TEST_SUBJECT
            assert "title" in row.new_value
        finally:
            db_session.execute(ContributionWork.__table__.delete().where(ContributionWork.id == uuid.UUID(work_id)))
            db_session.commit()

    def test_delete_writes_operational_impact_deleted_audit(self, client, auth_headers, db_session):
        title = f"Audit kanit testi sil {uuid.uuid4()}"
        create_resp = client.post("/api/v1/contribution-works", headers=auth_headers, json={"title": title})
        assert create_resp.status_code == 201
        work_id = unwrap(create_resp)["id"]

        delete_resp = client.delete(f"/api/v1/contribution-works/{work_id}", headers=auth_headers)
        assert delete_resp.status_code == 204

        row = _last_audit(db_session, action="operational_impact.deleted", entity="contribution_work")
        assert row is not None
        assert row.subject == TEST_SUBJECT
        assert row.old_value == title


class TestRoleAndScopeAssignmentAudits:
    """`authz_admin.assign_role`/`revoke_role` servis fonksiyonlarını doğrudan çağırır —
    CLI (`app/cli.py::cmd_assign_role`/`cmd_revoke_role`) bu fonksiyonların ince bir
    argparse sarmalayıcısıdır, iş mantığı ve audit çağrıları burada test edilir."""

    @pytest.fixture
    def target_subject(self, db_session):
        subject = f"audit-test-subject-{uuid.uuid4().hex[:8]}"
        yield subject
        db_session.rollback()
        db_session.execute(UserScopeAssignment.__table__.delete().where(UserScopeAssignment.subject == subject))
        db_session.execute(UserRoleAssignment.__table__.delete().where(UserRoleAssignment.subject == subject))
        db_session.commit()

    def test_assign_role_writes_role_assigned_and_scope_assigned(self, db_session, target_subject):
        assign_role(
            db_session, target_subject, Role.SUPERVISOR,
            scope_type=ScopeType.ALL, actor="test-operator",
        )
        db_session.commit()

        role_row = _last_audit(db_session, action="role.assigned", entity=target_subject)
        assert role_row is not None
        assert role_row.subject == "test-operator"
        assert role_row.new_value == "SUPERVISOR"

        scope_row = _last_audit(db_session, action="scope.assigned", entity=target_subject)
        assert scope_row is not None
        assert scope_row.subject == "test-operator"
        assert scope_row.new_value == "ALL"

        assert db_session.get(UserRoleAssignment, target_subject) is not None

    def test_assign_role_with_plant_scope_records_plant_ids(self, db_session, target_subject):
        from app.models.organization import Plant

        plant_id = db_session.scalar(select(Plant.id))
        assert plant_id is not None, "Testler için önce seed çalıştırılmalı."
        assign_role(
            db_session, target_subject, Role.SUPERVISOR,
            scope_type=ScopeType.PLANT, plant_ids=[plant_id], actor="test-operator",
        )
        db_session.commit()

        scope_row = _last_audit(db_session, action="scope.assigned", entity=target_subject)
        assert scope_row is not None
        assert str(plant_id) in scope_row.new_value

    def test_revoke_role_writes_role_revoked_and_scope_revoked(self, db_session, target_subject):
        assign_role(db_session, target_subject, Role.FOREMAN, scope_type=ScopeType.ALL, actor="test-operator")
        db_session.commit()

        had_assignment = revoke_role(db_session, target_subject, actor="test-operator")
        db_session.commit()

        assert had_assignment is True
        role_row = _last_audit(db_session, action="role.revoked", entity=target_subject)
        assert role_row is not None
        assert role_row.subject == "test-operator"
        assert role_row.old_value == "FOREMAN"
        assert role_row.success is True

        scope_row = _last_audit(db_session, action="scope.revoked", entity=target_subject)
        assert scope_row is not None
        assert scope_row.success is True

        assert db_session.get(UserRoleAssignment, target_subject) is None

    def test_revoke_role_on_unassigned_subject_is_idempotent_and_still_audited(self, db_session, target_subject):
        had_assignment = revoke_role(db_session, target_subject, actor="test-operator")
        db_session.commit()

        assert had_assignment is False
        role_row = _last_audit(db_session, action="role.revoked", entity=target_subject)
        assert role_row is not None
        assert role_row.success is False
        assert role_row.old_value is None

    def test_assign_role_cli_wiring_produces_same_audit_rows(self, db_session, target_subject):
        """authz_admin fonksiyonlarının değil, gerçek `python -m app.cli assign-role`
        komutunun (ayrı bir process olarak) da aynı audit satırlarını ürettiğini kanıtlar —
        CLI argparse/actor sabiti (CLI_OPERATOR_SUBJECT) kablolaması dahil."""
        result = subprocess.run(
            [sys.executable, "-m", "app.cli", "assign-role", target_subject, "SUPERVISOR", "--scope-type", "ALL"],
            cwd=str(_BACKEND_ROOT), capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr

        db_session.rollback()
        role_row = _last_audit(db_session, action="role.assigned", entity=target_subject)
        assert role_row is not None
        assert role_row.subject == "cli-operator"
        assert role_row.new_value == "SUPERVISOR"

        scope_row = _last_audit(db_session, action="scope.assigned", entity=target_subject)
        assert scope_row is not None
        assert scope_row.subject == "cli-operator"


class TestPermissionOverrideEventDoesNotExist:
    """`permission.override.changed` bilerek burada yok: sistemde per-user permission
    override mekanizması yok, bu action'ı tetikleyecek bir kod yolu yok. Test olumsuz
    iddia olarak yazılmıştır — mekanizma eklenirse kırılmalı, o noktada test silinip
    README güncellenmeli."""

    def test_no_code_path_emits_permission_override_changed(self, db_session):
        needle = "permission.override.changed"
        hits = [
            str(path)
            for path in (_BACKEND_ROOT / "app").rglob("*.py")
            if needle in path.read_text(encoding="utf-8")
        ]
        assert hits == [], (
            f"'{needle}' artık app/ içinde kullanılıyor ama bu test hâlâ 'özellik yok' "
            f"varsayıyor — bu testi ve README'yi güncelleyin: {hits}"
        )

    def test_no_existing_audit_row_uses_this_action(self, db_session):
        row = _last_audit(db_session, action="permission.override.changed")
        assert row is None
