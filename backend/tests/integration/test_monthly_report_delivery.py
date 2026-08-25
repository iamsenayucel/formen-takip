import uuid
from tests.helpers import legacy_json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.api.v1.foremen as foremen_module
from app.core.config import Settings
from app.main import app
from app.models.enums import ReportEmailStatus, ReportGenerationStatus
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.foreman_report import ForemanMonthlyReport
from app.models.organization import Plant, Shift
from app.models.performance import PerformanceRecord
from app.models.user import AuditLog
from app.services.monthly_foreman_report import (
    generate_and_store_report_pdf,
    get_or_generate_monthly_report,
    latest_completed_period,
)
from app.services.monthly_report_email import _resolve_recipients, send_monthly_report_email
from app.services.storage.base import ReportStorageError


@pytest.fixture
def unraising_client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _pick_foreman_with_data(db_session, year: int, month: int):
    from datetime import date

    date_from = date(year, month, 1)
    date_to = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)
    row = db_session.execute(
        select(PerformanceRecord.foreman_id, func.count())
        .where(PerformanceRecord.performance_date >= date_from, PerformanceRecord.performance_date < date_to)
        .group_by(PerformanceRecord.foreman_id)
        .order_by(func.count().desc())
        .limit(1)
    ).first()
    return row[0] if row else None


def _test_settings(tmp_path, **overrides) -> Settings:
    defaults = dict(report_storage_provider="local", local_report_storage_dir=str(tmp_path))
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


@pytest.fixture
def report_row(db_session):
    year, month = latest_completed_period()
    foreman_id = _pick_foreman_with_data(db_session, year, month)
    assert foreman_id is not None, "seeded DB should have performance records for the latest completed month"
    report = get_or_generate_monthly_report(db_session, foreman_id, year, month)
    yield report
    db_session.query(ForemanMonthlyReport).filter(ForemanMonthlyReport.id == report.id).delete()
    db_session.commit()


class TestGenerateAndStoreReportPdf:
    def test_uploads_and_marks_ready(self, db_session, report_row, tmp_path):
        settings = _test_settings(tmp_path)
        result = generate_and_store_report_pdf(db_session, report_row, settings)

        assert result.pdf_generation_status == ReportGenerationStatus.READY
        assert result.object_key is not None
        assert result.object_key.startswith(f"reports/{report_row.year:04d}/{report_row.month:02d}/foremen/")
        assert result.pdf_file_size and result.pdf_file_size > 0
        assert result.pdf_generated_at is not None

    def test_idempotent_second_call_skips_reupload(self, db_session, report_row, tmp_path):
        settings = _test_settings(tmp_path)
        generate_and_store_report_pdf(db_session, report_row, settings)
        first_object_key = report_row.object_key
        first_generated_at = report_row.pdf_generated_at

        with patch("app.services.storage.local_storage.LocalFilesystemReportStorage.upload") as mock_upload:
            generate_and_store_report_pdf(db_session, report_row, settings)
            mock_upload.assert_not_called()

        assert report_row.object_key == first_object_key
        assert report_row.pdf_generated_at == first_generated_at

    def test_upload_failure_marks_failed_and_raises(self, db_session, report_row, tmp_path):
        settings = _test_settings(tmp_path)
        with patch(
            "app.services.storage.local_storage.LocalFilesystemReportStorage.upload",
            side_effect=ReportStorageError("boom"),
        ):
            with pytest.raises(ReportStorageError):
                generate_and_store_report_pdf(db_session, report_row, settings)

        assert report_row.pdf_generation_status == ReportGenerationStatus.FAILED
        assert report_row.object_key is None

    def test_object_key_stable_across_force_regeneration(self, db_session, report_row, tmp_path):
        settings = _test_settings(tmp_path)
        generate_and_store_report_pdf(db_session, report_row, settings)
        first_key = report_row.object_key

        regenerated = get_or_generate_monthly_report(
            db_session, report_row.foreman_id, report_row.year, report_row.month, force=True
        )
        generate_and_store_report_pdf(db_session, regenerated, settings, force=True)

        assert regenerated.id == report_row.id
        assert regenerated.object_key == first_key


class TestMonthlyReportAccessEndpoint:
    def test_requires_auth(self, client, report_row):
        resp = client.get(
            f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/access"
        )
        assert resp.status_code == 401

    def test_unknown_foreman_returns_404(self, client, auth_headers):
        year, month = latest_completed_period()
        resp = client.get(
            f"/api/v1/foremen/{uuid.uuid4()}/monthly-reports/{year}/{month}/access", headers=auth_headers
        )
        assert resp.status_code == 404

    def test_local_storage_falls_back_to_authenticated_proxy_url(self, client, auth_headers, report_row):
        resp = client.get(
            f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/access",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        assert body["requires_auth"] is True
        assert body["expires_at"] is None
        assert body["url"] == (
            f"/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/pdf"
        )
        # url'in kendisi authenticated bir backend path'i olmalı, hiçbir zaman ham S3/AWS bilgisi sızdırmamalı
        assert "amazonaws" not in body["url"] and "s3." not in body["url"]

    def test_access_marks_report_ready_in_db(self, client, auth_headers, db_session, report_row):
        client.get(
            f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/access",
            headers=auth_headers,
        )
        db_session.refresh(report_row)
        assert report_row.pdf_generation_status == ReportGenerationStatus.READY
        assert report_row.object_key is not None


class TestPdfVsAccessErrorPolicyDivergence:
    """Aşama 3F — pdf ve access uç noktalarının `generate_and_store_report_pdf`
    başarısızlığına KASITLI OLARAK farklı tepki verdiğini kilitler: pdf sessizce
    on-the-fly render'a düşer (200 döner), access ise 502 fırlatır. Refactor
    sırasında bu iki davranışın yanlışlıkla aynılaştırılmadığını doğrular.
    """

    def test_pdf_endpoint_falls_back_silently_on_storage_failure(self, client, auth_headers, report_row):
        with patch(
            "app.services.foreman_monthly_report_service.generate_and_store_report_pdf",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.get(
                f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/pdf",
                headers=auth_headers,
            )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_access_endpoint_raises_502_on_storage_failure(self, client, auth_headers, report_row):
        with patch(
            "app.services.foreman_monthly_report_service.generate_and_store_report_pdf",
            side_effect=RuntimeError("boom"),
        ):
            resp = client.get(
                f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/access",
                headers=auth_headers,
            )
        assert resp.status_code == 502


class TestMonthlyReportAuditIsSeparatePhase:
    """Aşama 3F — rapor state machine'i (Faz 1, `monthly_foreman_report.py`'nin kendi
    commit'i) ile audit (Faz 2, ayrı commit) arasındaki iki-fazlı transaction ayrımını
    kilitler: audit kaydı başarısız olsa bile, zaten önceden commit edilmiş rapor
    üretim/storage durumu (READY, object_key) geri alınmaz ve audit satırı hiç
    oluşmaz. Bu, tek bir mega-transaction'a birleştirilmediğinin kanıtıdır.
    """

    def test_audit_failure_does_not_roll_back_already_committed_report_state(
        self, unraising_client, auth_headers, db_session, report_row, monkeypatch
    ):
        def _raise(*args, **kwargs):
            raise RuntimeError("audit insert failed")

        monkeypatch.setattr(foremen_module, "record_audit", _raise)

        resp = unraising_client.get(
            f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/access",
            headers=auth_headers,
        )
        assert resp.status_code == 500

        db_session.refresh(report_row)
        assert report_row.pdf_generation_status == ReportGenerationStatus.READY
        assert report_row.object_key is not None

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "monthly_report_access_granted",
                AuditLog.new_value == str(report_row.id),
            )
        )
        assert audit is None

    def test_successful_access_persists_report_state_and_audit_together(
        self, client, auth_headers, db_session, report_row
    ):
        resp = client.get(
            f"/api/v1/foremen/{report_row.foreman_id}/monthly-reports/{report_row.year}/{report_row.month}/access",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text

        db_session.refresh(report_row)
        assert report_row.pdf_generation_status == ReportGenerationStatus.READY

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == "monthly_report_access_granted",
                AuditLog.new_value == str(report_row.id),
            )
        )
        assert audit is not None


class TestSendMonthlyReportEmail:
    def test_skips_insufficient_data_report(self, db_session, tmp_path):
        year, month = latest_completed_period()
        foreman_id = db_session.scalar(select(Foreman.id).where(Foreman.is_active.is_(True)))
        report = ForemanMonthlyReport(
            foreman_id=foreman_id, year=2019, month=1,
            generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            is_reliable=False, report_data={"insufficient_data": True}, version=1,
        )
        db_session.add(report)
        db_session.commit()
        try:
            settings = _test_settings(tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="a@b.com")
            result = send_monthly_report_email(db_session, report, settings)
            assert result.email_status == ReportEmailStatus.SKIPPED
        finally:
            db_session.delete(report)
            db_session.commit()

    def test_missing_foreman_email_marks_failed(self, db_session, report_row, tmp_path):
        foreman = db_session.get(Foreman, report_row.foreman_id)
        original_email = foreman.email
        foreman.email = None
        db_session.commit()
        try:
            settings = _test_settings(tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="a@b.com")
            result = send_monthly_report_email(db_session, report_row, settings)
            assert result.email_status == ReportEmailStatus.FAILED
            assert result.email_last_error == "missing_foreman_email"
            assert result.email_retry_count == 1
        finally:
            foreman.email = original_email
            db_session.commit()

    @patch("smtplib.SMTP")
    def test_successful_send_marks_sent_and_uses_stored_pdf(self, mock_smtp_cls, db_session, report_row, tmp_path):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _test_settings(tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="raporlar@formen.internal")

        result = send_monthly_report_email(db_session, report_row, settings)

        assert result.email_status == ReportEmailStatus.SENT
        assert result.emailed_at is not None
        assert mock_smtp.send_message.call_count == 1
        assert result.pdf_generation_status == ReportGenerationStatus.READY

    @patch("smtplib.SMTP")
    def test_sent_report_is_not_resent(self, mock_smtp_cls, db_session, report_row, tmp_path):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _test_settings(tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="a@b.com")

        send_monthly_report_email(db_session, report_row, settings)
        assert mock_smtp.send_message.call_count == 1

        send_monthly_report_email(db_session, report_row, settings)
        assert mock_smtp.send_message.call_count == 1

    def test_smtp_failure_marks_failed_and_increments_retry(self, db_session, report_row, tmp_path):
        settings = _test_settings(tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="a@b.com")
        with patch("smtplib.SMTP", side_effect=OSError("connection refused")):
            result = send_monthly_report_email(db_session, report_row, settings)

        assert result.email_status == ReportEmailStatus.FAILED
        assert result.email_retry_count == 1
        assert result.email_last_error == "smtp_error"

    def test_smtp_unavailable_leaves_report_pending_without_send_attempt(self, db_session, report_row, tmp_path):
        assert report_row.email_status == ReportEmailStatus.PENDING
        settings = _test_settings(tmp_path, smtp_enabled=False)

        with patch("app.services.monthly_report_email.send_email_with_attachment") as mock_send:
            result = send_monthly_report_email(db_session, report_row, settings)

        assert result.email_status == ReportEmailStatus.PENDING
        assert result.email_retry_count == 0
        assert result.email_last_error is None
        mock_send.assert_not_called()

    def test_smtp_unavailable_leaves_multiple_pending_reports_untouched(self, db_session, tmp_path):
        year, month = latest_completed_period()
        foreman_ids = list(
            db_session.scalars(select(Foreman.id).where(Foreman.is_active.is_(True)).limit(3))
        )
        assert len(foreman_ids) >= 2, "seeded DB should have at least two active foremen"

        reports = []
        for foreman_id in foreman_ids:
            report = ForemanMonthlyReport(
                foreman_id=foreman_id, year=2018, month=(month % 12) + 1,
                generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                is_reliable=True, report_data={"insufficient_data": False}, version=1,
            )
            db_session.add(report)
            reports.append(report)
        db_session.commit()

        try:
            settings = _test_settings(tmp_path, smtp_enabled=False)
            with patch("app.services.monthly_report_email.send_email_with_attachment") as mock_send:
                for report in reports:
                    send_monthly_report_email(db_session, report, settings)

            for report in reports:
                assert report.email_status == ReportEmailStatus.PENDING
                assert report.email_retry_count == 0
            mock_send.assert_not_called()
        finally:
            for report in reports:
                db_session.delete(report)
            db_session.commit()

    def test_smtp_unavailable_does_not_open_pdf_or_recipient_pipeline(self, db_session, report_row, tmp_path):
        settings = _test_settings(tmp_path, smtp_enabled=False)

        with patch("app.services.monthly_report_email._resolve_recipients") as mock_resolve:
            result = send_monthly_report_email(db_session, report_row, settings)

        assert result.email_status == ReportEmailStatus.PENDING
        mock_resolve.assert_not_called()

    def test_resolve_recipients_finds_chief_when_assignment_ended_before_month_end(self, db_session):
        chief = db_session.scalar(select(Chief).limit(1))
        shift = db_session.scalar(select(Shift).limit(1))
        plant = Plant(
            id=uuid.uuid4(), code=f"TESTEMAIL-{uuid.uuid4().hex[:6]}", name="Test Tesis Email",
            sequence_number=600_000 + (uuid.uuid4().int % 300_000),
            factory_id=chief.plants[0].factory_id, chief_id=chief.id, is_active=True,
        )
        foreman = Foreman(
            id=uuid.uuid4(), employee_number=f"TEST-EMAIL-{uuid.uuid4().hex[:8]}",
            first_name="Test", last_name="EmailFormen", hire_date=date(2020, 1, 1), is_active=False,
        )
        assignment = ForemanAssignment(
            id=uuid.uuid4(), foreman_id=foreman.id, plant_id=plant.id, chief_id=chief.id, shift_id=shift.id,
            start_date=date(2099, 8, 1), end_date=date(2099, 8, 25), is_active=False,
        )
        db_session.add_all([plant, foreman])
        db_session.flush()
        db_session.add(assignment)
        db_session.commit()

        report = ForemanMonthlyReport(
            foreman_id=foreman.id, year=2099, month=8,
            generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            is_reliable=True, report_data={"insufficient_data": False}, version=1,
        )
        try:
            resolved_foreman, resolved_chief = _resolve_recipients(db_session, report)
            assert resolved_foreman is not None and resolved_foreman.id == foreman.id
            assert resolved_chief is not None and resolved_chief.id == chief.id
        finally:
            db_session.rollback()
            db_session.execute(ForemanAssignment.__table__.delete().where(ForemanAssignment.foreman_id == foreman.id))
            db_session.execute(Foreman.__table__.delete().where(Foreman.id == foreman.id))
            db_session.execute(Plant.__table__.delete().where(Plant.id == plant.id))
            db_session.commit()
