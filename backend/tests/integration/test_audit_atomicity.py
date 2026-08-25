import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SASession

import app.api.v1.contributions as contributions_module
import app.services.anomaly_status_service as anomaly_status_service_module
import app.services.report_service as report_service_module
from app.db.session import get_db
from app.main import app
from app.models.contribution import ContributionWork
from app.models.enums import AnomalyStatus
from app.models.report import ReportExport
from app.models.user import AuditLog
from tests.helpers import legacy_json

from .conftest import TEST_SUBJECT


def _raise(*args, **kwargs):
    raise RuntimeError("audit insert failed")


@pytest.fixture
def unraising_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.query(ContributionWork).filter(
        ContributionWork.created_by_subject == TEST_SUBJECT
    ).delete(synchronize_session=False)
    db_session.commit()


class TestContributionCreateAtomicity:
    def test_audit_failure_rolls_back_contribution(self, unraising_client, auth_headers, db_session, monkeypatch):
        title = f"Audit Atomicity Create {uuid.uuid4()}"
        monkeypatch.setattr(contributions_module, "record_audit", _raise)

        resp = unraising_client.post(
            "/api/v1/contribution-works", json={"title": title}, headers=auth_headers
        )
        assert resp.status_code == 500

        assert db_session.scalar(
            select(ContributionWork).where(ContributionWork.title == title)
        ) is None

    def test_retry_after_audit_failure_creates_exactly_one(
        self, unraising_client, auth_headers, db_session, monkeypatch
    ):
        title = f"Audit Atomicity Retry {uuid.uuid4()}"
        monkeypatch.setattr(contributions_module, "record_audit", _raise)

        failed = unraising_client.post(
            "/api/v1/contribution-works", json={"title": title}, headers=auth_headers
        )
        assert failed.status_code == 500

        monkeypatch.undo()

        retried = unraising_client.post(
            "/api/v1/contribution-works", json={"title": title}, headers=auth_headers
        )
        assert retried.status_code == 201, retried.text

        works = list(db_session.scalars(select(ContributionWork).where(ContributionWork.title == title)))
        assert len(works) == 1

        audits = list(db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == "contribution_work_created", AuditLog.new_value == title
            )
        ))
        assert len(audits) == 1
        assert audits[0].subject == TEST_SUBJECT

    def test_successful_create_persists_contribution_and_audit_together(
        self, unraising_client, auth_headers, db_session
    ):
        title = f"Audit Atomicity Success {uuid.uuid4()}"
        resp = unraising_client.post(
            "/api/v1/contribution-works", json={"title": title}, headers=auth_headers
        )
        assert resp.status_code == 201, resp.text

        work = db_session.scalar(select(ContributionWork).where(ContributionWork.title == title))
        assert work is not None

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "contribution_work_created", AuditLog.new_value == title
            )
        )
        assert audit is not None
        assert audit.entity == "contribution_work"
        assert audit.subject == TEST_SUBJECT


class TestContributionUpdateAtomicity:
    def test_audit_failure_rolls_back_update(self, unraising_client, auth_headers, db_session, monkeypatch):
        title = f"Audit Atomicity Update {uuid.uuid4()}"
        created_response = unraising_client.post(
            "/api/v1/contribution-works", json={"title": title}, headers=auth_headers
        )
        created = legacy_json(created_response)

        monkeypatch.setattr(contributions_module, "record_audit", _raise)
        resp = unraising_client.patch(
            f"/api/v1/contribution-works/{created['id']}",
            json={"summary": "Rollback edilmesi gereken özet"},
            headers=auth_headers,
        )
        assert resp.status_code == 500
        monkeypatch.undo()

        refetched_response = unraising_client.get(
            f"/api/v1/contribution-works/{created['id']}", headers=auth_headers
        )
        refetched = legacy_json(refetched_response)
        assert refetched["summary"] is None


class TestContributionDeleteAtomicity:
    def test_audit_failure_rolls_back_delete(self, unraising_client, auth_headers, db_session, monkeypatch):
        title = f"Audit Atomicity Delete {uuid.uuid4()}"
        created_response = unraising_client.post(
            "/api/v1/contribution-works", json={"title": title}, headers=auth_headers
        )
        created = legacy_json(created_response)

        monkeypatch.setattr(contributions_module, "record_audit", _raise)
        resp = unraising_client.delete(
            f"/api/v1/contribution-works/{created['id']}", headers=auth_headers
        )
        assert resp.status_code == 500
        monkeypatch.undo()

        still_there = unraising_client.get(
            f"/api/v1/contribution-works/{created['id']}", headers=auth_headers
        )
        assert still_there.status_code == 200


class TestAnomalyStatusAtomicity:
    def _pick_anomaly(self, db_session):
        from app.models.anomaly import Anomaly

        anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
        assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
        return anomaly

    def test_audit_failure_rolls_back_status_change(self, unraising_client, auth_headers, db_session, monkeypatch):
        anomaly = self._pick_anomaly(db_session)
        original_status = anomaly.status
        new_status = AnomalyStatus.RESOLVED if original_status != AnomalyStatus.RESOLVED else AnomalyStatus.IN_REVIEW

        monkeypatch.setattr(anomaly_status_service_module, "record_audit", _raise)
        resp = unraising_client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": new_status.value}, headers=auth_headers
        )
        assert resp.status_code == 500
        monkeypatch.undo()

        db_session.expire_all()
        refetched = db_session.get(type(anomaly), anomaly.id)
        assert refetched.status == original_status

    def test_successful_status_change_persists_with_audit(self, unraising_client, auth_headers, db_session):
        anomaly = self._pick_anomaly(db_session)
        original_status = anomaly.status
        new_status = AnomalyStatus.RESOLVED if original_status != AnomalyStatus.RESOLVED else AnomalyStatus.IN_REVIEW

        resp = unraising_client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": new_status.value}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text

        db_session.expire_all()
        refetched = db_session.get(type(anomaly), anomaly.id)
        assert refetched.status == new_status

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "anomaly_status_updated",
                AuditLog.old_value == original_status.value,
                AuditLog.new_value == new_status.value,
            ).order_by(AuditLog.created_at.desc())
        )
        assert audit is not None

        refetched.status = original_status
        db_session.commit()


class TestReportDownloadAtomicity:
    def test_audit_failure_returns_500_before_commit(
        self, unraising_client, auth_headers, db_session, report_export_factory, monkeypatch
    ):
        report = report_export_factory()
        audit_count_before = db_session.scalar(select(func.count()).select_from(AuditLog))

        monkeypatch.setattr(report_service_module, "record_audit", _raise)

        commit_calls = []
        original_commit = SASession.commit

        def counting_commit(self):
            commit_calls.append(1)
            return original_commit(self)

        monkeypatch.setattr(SASession, "commit", counting_commit)

        resp = unraising_client.get(f"/api/v1/reports/{report.id}/download", headers=auth_headers)
        assert resp.status_code == 500
        assert commit_calls == []

        audit_count_after = db_session.scalar(select(func.count()).select_from(AuditLog))
        assert audit_count_after == audit_count_before

    def test_true_commit_failure_returns_500_and_writes_nothing(
        self, unraising_client, auth_headers, db_session, report_export_factory, monkeypatch
    ):
        report = report_export_factory()
        report_id = report.id
        audit_count_before = db_session.scalar(select(func.count()).select_from(AuditLog))
        file_name_before = report.file_name

        def _raise_commit(self):
            raise RuntimeError("test-commit-failure")

        with monkeypatch.context() as commit_patch:
            commit_patch.setattr(SASession, "commit", _raise_commit)
            resp = unraising_client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert resp.status_code == 500

        audit_count_after = db_session.scalar(select(func.count()).select_from(AuditLog))
        assert audit_count_after == audit_count_before

        db_session.expire(report)
        assert report.file_name == file_name_before


class _RecordingSession:
    def __init__(self, fail_on_flush=False):
        self.events = []
        self.report_exports = []
        self.audit_logs = []
        self.fail_on_flush = fail_on_flush

    def add(self, obj):
        if isinstance(obj, ReportExport):
            self.events.append("add_report")
            self.report_exports.append(obj)
        elif isinstance(obj, AuditLog):
            self.events.append("audit")
            self.audit_logs.append(obj)
        else:
            raise AssertionError(f"_RecordingSession.add called with unexpected type: {type(obj)!r}")

    def flush(self):
        self.events.append("flush")
        if self.fail_on_flush:
            raise RuntimeError("test-flush-failure")
        for export in self.report_exports:
            if export.id is None:
                export.id = uuid.uuid4()
            if export.created_at is None:
                export.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def commit(self):
        self.events.append("commit")


@contextmanager
def _db_override(fake_session):
    app.dependency_overrides[get_db] = lambda: fake_session
    try:
        yield fake_session
    finally:
        app.dependency_overrides.pop(get_db, None)


def _patch_reporting_both(monkeypatch, name, replacement):
    monkeypatch.setattr(report_service_module, name, replacement)


def _fake_build_report_rows(db, report_type, filters):
    return ["Kolon A"], [{"Kolon A": "1"}]


class TestReportGenerateAtomicity:
    _PAYLOAD = {
        "report_type": "company_summary",
        "format": "csv",
        "date_from": "2099-01-01",
        "date_to": "2099-01-02",
    }
    _FILE_NAME = "company_summary_2099-01-01_2099-01-02.csv"

    @classmethod
    def _persisted_counts(cls, db_session):
        report_count = db_session.scalar(
            select(func.count()).select_from(ReportExport).where(ReportExport.file_name == cls._FILE_NAME)
        )
        audit_count = db_session.scalar(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.action == "report_generated",
                AuditLog.entity == "report_export",
                AuditLog.new_value == cls._FILE_NAME,
            )
        )
        return report_count, audit_count

    def test_pre_write_failure_leaves_nothing(self, unraising_client, auth_headers, monkeypatch):
        def _raise_builder(db, report_type, filters):
            raise RuntimeError("test-pre-write-failure")

        _patch_reporting_both(monkeypatch, "build_report_rows", _raise_builder)

        with _db_override(_RecordingSession()) as fake:
            resp = unraising_client.post(
                "/api/v1/reports/generate", json=self._PAYLOAD, headers=auth_headers
            )

        assert resp.status_code == 500
        assert fake.events == []

    def test_flush_failure_leaves_nothing_beyond_add(self, unraising_client, auth_headers, monkeypatch):
        _patch_reporting_both(monkeypatch, "build_report_rows", _fake_build_report_rows)
        _patch_reporting_both(monkeypatch, "render_csv", lambda headers, rows: b"CSV")

        with _db_override(_RecordingSession(fail_on_flush=True)) as fake:
            resp = unraising_client.post(
                "/api/v1/reports/generate", json=self._PAYLOAD, headers=auth_headers
            )

        assert resp.status_code == 500
        assert fake.events == ["add_report", "flush"]

    def test_audit_failure_rolls_back_real_report_insert(
        self, unraising_client, auth_headers, db_session, monkeypatch
    ):
        counts_before = self._persisted_counts(db_session)
        _patch_reporting_both(monkeypatch, "build_report_rows", _fake_build_report_rows)
        _patch_reporting_both(monkeypatch, "render_csv", lambda headers, rows: b"CSV")
        _patch_reporting_both(monkeypatch, "record_audit", _raise)

        resp = unraising_client.post(
            "/api/v1/reports/generate", json=self._PAYLOAD, headers=auth_headers
        )

        assert resp.status_code == 500
        assert self._persisted_counts(db_session) == counts_before

    def test_true_commit_failure_rolls_back_real_report_and_audit(
        self, unraising_client, auth_headers, db_session, monkeypatch
    ):
        counts_before = self._persisted_counts(db_session)
        _patch_reporting_both(monkeypatch, "build_report_rows", _fake_build_report_rows)
        _patch_reporting_both(monkeypatch, "render_csv", lambda headers, rows: b"CSV")

        def _raise_commit(self):
            raise RuntimeError("test-commit-failure")

        with monkeypatch.context() as commit_patch:
            commit_patch.setattr(SASession, "commit", _raise_commit)
            resp = unraising_client.post(
                "/api/v1/reports/generate", json=self._PAYLOAD, headers=auth_headers
            )

        assert resp.status_code == 500
        assert self._persisted_counts(db_session) == counts_before

    def test_success_has_no_database_operation_after_commit(self, unraising_client, auth_headers, monkeypatch):
        _patch_reporting_both(monkeypatch, "build_report_rows", _fake_build_report_rows)
        _patch_reporting_both(monkeypatch, "render_csv", lambda headers, rows: b"CSV")

        with _db_override(_RecordingSession()) as fake:
            resp = unraising_client.post(
                "/api/v1/reports/generate", json=self._PAYLOAD, headers=auth_headers
            )

        assert resp.status_code == 201
        assert fake.events == ["add_report", "flush", "audit", "commit"]
