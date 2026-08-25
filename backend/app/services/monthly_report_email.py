from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models.enums import ReportEmailStatus, ReportGenerationStatus
from app.models.foreman import Chief, Foreman
from app.models.foreman_report import ForemanMonthlyReport
from app.services.email_sender import EmailSendError, send_email_with_attachment
from app.services.monthly_foreman_report import (
    assignments_overlapping_period,
    generate_and_store_report_pdf,
    group_assignment_episodes,
)
from app.services.storage import ReportObjectNotFoundError, ReportStorageError, get_report_storage

logger = logging.getLogger("app.monthly_report_email")

_SUBJECT_TEMPLATE = "Aylık Formen Performans Raporu — {period}"
_BODY_TEMPLATE = (
    "Merhaba,\n\n"
    "{foreman_name} için {period} dönemine ait aylık bireysel performans değerlendirme "
    "raporu ekte yer almaktadır.\n\n"
    "Bu e-posta otomatik olarak Formen Performans Takip Sistemi tarafından gönderilmiştir.\n"
)

# Bir işin claim/reclaim edilebileceği durumlar. RECONCILIATION_REQUIRED bilerek
# dışarıda tutulur; bu durumdan yalnızca açık bir `resolve-stale-email-job` operatör
# kararıyla çıkılabilir (bkz. app/services/job_reconciliation.py).
_CLAIMABLE_STATUSES = (ReportEmailStatus.PENDING, ReportEmailStatus.FAILED)


def _resolve_recipients(db: Session, report: ForemanMonthlyReport) -> tuple[Foreman | None, Chief | None]:
    from calendar import monthrange

    period_start = date(report.year, report.month, 1)
    period_end = date(report.year, report.month, monthrange(report.year, report.month)[1])

    foreman = db.get(Foreman, report.foreman_id)
    assignments = assignments_overlapping_period(db, report.foreman_id, period_start, period_end)
    chief = None
    if assignments:
        episodes = group_assignment_episodes(assignments)
        chief = db.get(Chief, episodes[-1][0].chief_id)
    return foreman, chief


def _claim_report(db: Session, report_id) -> uuid.UUID | None:
    """Tek worker için PENDING/FAILED -> SENDING geçişini atomik yapar.

    Claim, koşullu `UPDATE ... RETURNING` ifadesidir. Sıfır satır etkilenirse işi başka
    worker/watchdog almıştır. Row lock yalnızca statement transaction'ında tutulur;
    SMTP çağrısı açık DB transaction dışında yapılır.
    """
    claim_token = uuid.uuid4()
    now = datetime.now(timezone.utc)
    stmt = (
        update(ForemanMonthlyReport)
        .where(
            ForemanMonthlyReport.id == report_id,
            ForemanMonthlyReport.email_status.in_(_CLAIMABLE_STATUSES),
        )
        .values(email_status=ReportEmailStatus.SENDING, claimed_at=now, claim_token=claim_token)
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount != 1:
        logger.info("report_email_claim_skipped report_id=%s — already claimed or in a terminal state", report_id)
        return None
    logger.info("report_email_claimed report_id=%s claim_token=%s", report_id, claim_token)
    return claim_token


def _complete(
    db: Session, report: ForemanMonthlyReport, claim_token: uuid.UUID, new_status: ReportEmailStatus,
    *, last_error: str | None = None, increment_retry: bool = False, emailed_at: datetime | None = None,
) -> None:
    """claim_token korumasıyla SENDING -> new_status geçişini koşullu yapar.

    Yeni claim veya stale-job watchdog işi ilerlettiyse WHERE sıfır satırla eşleşir
    ve çağrı log dışında no-op olur. Stale worker yeni denemenin sonucunu ezemez.
    """
    values: dict = {"email_status": new_status, "email_last_error": last_error, "claim_token": None}
    if increment_retry:
        values["email_retry_count"] = ForemanMonthlyReport.email_retry_count + 1
    if emailed_at is not None:
        values["emailed_at"] = emailed_at

    stmt = (
        update(ForemanMonthlyReport)
        .where(
            ForemanMonthlyReport.id == report.id,
            ForemanMonthlyReport.email_status == ReportEmailStatus.SENDING,
            ForemanMonthlyReport.claim_token == claim_token,
        )
        .values(**values)
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount != 1:
        logger.warning(
            "report_email_stale_completion_ignored report_id=%s attempted_status=%s claim_token=%s — "
            "this worker's claim was reclaimed (stale-job watchdog or a concurrent retry) before it finished; "
            "DB state was left untouched. If new_status=SENT, the email may have been sent twice — check "
            "RECONCILIATION_REQUIRED / operator logs for this report_id.",
            report.id, new_status.value, claim_token,
        )
        db.refresh(report)
        return
    db.refresh(report)


def send_monthly_report_email(
    db: Session, report: ForemanMonthlyReport, settings: Settings | None = None
) -> ForemanMonthlyReport:
    settings = settings or get_settings()
    period = f"{report.year:04d}-{report.month:02d}"

    if not settings.smtp_available:
        logger.info("report_email_skipped_smtp_unavailable report_id=%s period=%s", report.id, period)
        return report

    db.refresh(report)
    if report.email_status == ReportEmailStatus.SENT:
        return report

    claim_token = _claim_report(db, report.id)
    if claim_token is None:
        db.refresh(report)
        return report
    db.refresh(report)

    if not report.is_reliable:
        _complete(db, report, claim_token, ReportEmailStatus.SKIPPED, last_error="insufficient_data")
        logger.info("report_email_skipped report_id=%s period=%s reason=insufficient_data", report.id, period)
        return report

    foreman, chief = _resolve_recipients(db, report)
    if foreman is None or not foreman.email:
        _complete(db, report, claim_token, ReportEmailStatus.FAILED, last_error="missing_foreman_email", increment_retry=True)
        logger.warning("report_email_failed report_id=%s period=%s reason=missing_foreman_email", report.id, period)
        return report

    cc_addrs = []
    if chief is not None and chief.email:
        cc_addrs.append(chief.email)
    else:
        logger.warning("report_email: chief email missing, sending without CC report_id=%s period=%s", report.id, period)

    if report.pdf_generation_status != ReportGenerationStatus.READY:
        try:
            generate_and_store_report_pdf(db, report, settings)
        except Exception:
            _complete(db, report, claim_token, ReportEmailStatus.FAILED, last_error="pdf_not_ready", increment_retry=True)
            logger.exception("report_email_failed report_id=%s period=%s reason=pdf_not_ready", report.id, period)
            return report

    try:
        pdf_bytes = get_report_storage(settings).download(report.object_key)
    except (ReportObjectNotFoundError, ReportStorageError):
        _complete(db, report, claim_token, ReportEmailStatus.FAILED, last_error="pdf_download_failed", increment_retry=True)
        logger.exception("report_email_failed report_id=%s period=%s reason=pdf_download_failed", report.id, period)
        return report

    logger.info("report_email_started report_id=%s period=%s claim_token=%s", report.id, period, claim_token)

    try:
        send_email_with_attachment(
            settings,
            to_addr=foreman.email, cc_addrs=cc_addrs,
            subject=_SUBJECT_TEMPLATE.format(period=period),
            body=_BODY_TEMPLATE.format(foreman_name=f"{foreman.first_name} {foreman.last_name}", period=period),
            attachment_bytes=pdf_bytes, attachment_filename=report.pdf_file_name or f"formen-raporu-{period}.pdf",
        )
    except EmailSendError as exc:
        # Crash window: Process başarılı SMTP gönderimi ile bu exception handler veya
        # aşağıdaki tamamlanma UPDATE'i arasında çökerse satır SENDING kalır. Watchdog,
        # sessizce yeniden göndermek yerine RECONCILIATION_REQUIRED durumuna taşır.
        _complete(db, report, claim_token, ReportEmailStatus.FAILED, last_error="smtp_error", increment_retry=True)
        logger.warning("report_email_failed report_id=%s period=%s reason=smtp_error error=%s", report.id, period, exc)
        return report

    _complete(db, report, claim_token, ReportEmailStatus.SENT, emailed_at=datetime.now(timezone.utc))
    logger.info("report_email_sent report_id=%s period=%s", report.id, period)
    return report
