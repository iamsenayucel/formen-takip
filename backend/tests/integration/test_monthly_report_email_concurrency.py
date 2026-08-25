import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import func, select

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models.enums import ReportEmailStatus
from app.models.foreman_report import ForemanMonthlyReport
from app.models.performance import PerformanceRecord
from app.services.job_reconciliation import reconcile_stale_email_jobs, resolve_email_reconciliation
from app.services.monthly_foreman_report import get_or_generate_monthly_report, latest_completed_period
from app.services.monthly_report_email import _claim_report, _complete, send_monthly_report_email


def _pick_foreman_with_data(db_session, year: int, month: int):
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


class TestClaimRace:
    def test_two_sessions_racing_the_same_row_only_one_claims(self, db_session, report_row):
        report_id = report_row.id
        barrier = threading.Barrier(2)
        results: list = []
        lock = threading.Lock()

        def worker():
            db = SessionLocal()
            try:
                barrier.wait()
                token = _claim_report(db, report_id)
                with lock:
                    results.append(token)
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(worker) for _ in range(2)]
            for f in futures:
                f.result()

        claimed = [t for t in results if t is not None]
        assert len(claimed) == 1
        assert len(results) == 2

        db_session.refresh(report_row)
        assert report_row.email_status == ReportEmailStatus.SENDING
        assert report_row.claim_token == claimed[0]


class TestConcurrentSend:
    @patch("smtplib.SMTP")
    def test_two_workers_race_to_send_only_one_smtp_call(self, mock_smtp_cls, db_session, report_row, tmp_path):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _test_settings(tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="raporlar@formen.internal")

        report_id = report_row.id
        barrier = threading.Barrier(2)
        statuses: list = []
        lock = threading.Lock()

        def worker():
            db = SessionLocal()
            try:
                report = db.get(ForemanMonthlyReport, report_id)
                barrier.wait()
                result = send_monthly_report_email(db, report, settings)
                with lock:
                    statuses.append(result.email_status)
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(worker) for _ in range(2)]
            for f in futures:
                f.result()

        assert mock_smtp.send_message.call_count == 1
        assert statuses.count(ReportEmailStatus.SENT) == 1

        db_session.refresh(report_row)
        assert report_row.email_status == ReportEmailStatus.SENT
        assert report_row.claim_token is None


class TestStaleSendingRecovery:
    def test_stale_sending_moves_to_reconciliation_required(self, db_session, report_row):
        settings = Settings(_env_file=None, email_stale_claim_timeout_seconds=60)
        old_claimed_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        report_row.email_status = ReportEmailStatus.SENDING
        report_row.claimed_at = old_claimed_at
        db_session.commit()

        result = reconcile_stale_email_jobs(db_session, settings)

        db_session.refresh(report_row)
        assert report_row.id in result.recovered_ids
        assert report_row.email_status == ReportEmailStatus.RECONCILIATION_REQUIRED
        assert report_row.claim_token is None

    def test_fresh_sending_is_not_recovered(self, db_session, report_row):
        settings = Settings(_env_file=None, email_stale_claim_timeout_seconds=900)
        report_row.email_status = ReportEmailStatus.SENDING
        report_row.claimed_at = datetime.now(timezone.utc)
        db_session.commit()

        result = reconcile_stale_email_jobs(db_session, settings)

        db_session.refresh(report_row)
        assert report_row.id not in result.recovered_ids
        assert report_row.email_status == ReportEmailStatus.SENDING


class TestStaleWorkerCompletion:
    def test_stale_worker_completing_after_watchdog_reclaim_does_not_overwrite(self, db_session, report_row):
        settings = Settings(_env_file=None, email_stale_claim_timeout_seconds=60)

        token_a = _claim_report(db_session, report_row.id)
        assert token_a is not None
        db_session.refresh(report_row)
        report_row.claimed_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        db_session.commit()

        reconcile_stale_email_jobs(db_session, settings)
        db_session.refresh(report_row)
        assert report_row.email_status == ReportEmailStatus.RECONCILIATION_REQUIRED

        # Worker A'nın SMTP çağrısı sonunda başarılı döner ve tamamlamayı dener; claim_token
        # artık güncel reconciliation-required satırıyla eşleşmez.
        _complete(db_session, report_row, token_a, ReportEmailStatus.SENT, emailed_at=datetime.now(timezone.utc))

        db_session.refresh(report_row)
        assert report_row.email_status == ReportEmailStatus.RECONCILIATION_REQUIRED


class TestCrashBeforeSideEffect:
    @patch("smtplib.SMTP")
    def test_claim_without_completion_is_recovered_and_can_be_resent(self, mock_smtp_cls, db_session, report_row, tmp_path):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _test_settings(
            tmp_path, smtp_enabled=True, smtp_host="x", smtp_from="a@b.com",
            email_stale_claim_timeout_seconds=1,
        )

        # Claim başarılıdır; ardından process'in SMTP çalışmadan önce çöktüğü varsayılır.
        token = _claim_report(db_session, report_row.id)
        assert token is not None
        time.sleep(1.2)

        result = reconcile_stale_email_jobs(db_session, settings)
        db_session.refresh(report_row)
        assert report_row.id in result.recovered_ids
        assert report_row.email_status == ReportEmailStatus.RECONCILIATION_REQUIRED

        resolved = resolve_email_reconciliation(db_session, report_row.id, "retry")
        assert resolved.email_status == ReportEmailStatus.PENDING

        final = send_monthly_report_email(db_session, report_row, settings)
        assert final.email_status == ReportEmailStatus.SENT
        assert mock_smtp.send_message.call_count == 1


class TestResolveReconciliation:
    def test_resolve_sent_marks_sent_without_resending(self, db_session, report_row):
        report_row.email_status = ReportEmailStatus.RECONCILIATION_REQUIRED
        report_row.claim_token = None
        db_session.commit()

        resolved = resolve_email_reconciliation(db_session, report_row.id, "sent")
        assert resolved.email_status == ReportEmailStatus.SENT
        assert resolved.emailed_at is not None

    def test_resolve_on_non_reconciliation_row_raises(self, db_session, report_row):
        assert report_row.email_status == ReportEmailStatus.PENDING
        with pytest.raises(ValueError):
            resolve_email_reconciliation(db_session, report_row.id, "sent")

    def test_resolve_rejects_unknown_resolution(self, db_session, report_row):
        report_row.email_status = ReportEmailStatus.RECONCILIATION_REQUIRED
        db_session.commit()
        with pytest.raises(ValueError):
            resolve_email_reconciliation(db_session, report_row.id, "bogus")
