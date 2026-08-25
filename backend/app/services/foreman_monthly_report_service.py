from __future__ import annotations

import logging
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    ForemanNotFoundError,
    InvalidReportPeriodError,
    MonthlyReportAccessUnavailableError,
    MonthlyReportPdfGenerationFailedError,
)
from app.models.enums import ReportGenerationStatus
from app.models.foreman import Foreman
from app.models.foreman_report import ForemanMonthlyReport
from app.services.cloudfront_signing import CloudFrontNotConfiguredError, cloudfront_configured, generate_signed_url
from app.services.monthly_foreman_report import (
    generate_and_store_report_pdf,
    get_or_generate_monthly_report,
    latest_completed_period,
)
from app.services.monthly_foreman_report_pdf import render_monthly_foreman_report_pdf
from app.services.storage import ReportObjectNotFoundError, ReportStorageError, get_report_storage

logger = logging.getLogger("app.api.foremen")

RecordAudit = Callable[..., object]


class ForemanMonthlyReportService:
    """Foreman aylık performans raporu (Monthly Reports) HTTP orkestrasyonu.

    Rapor üretimi/storage durumu tamamen `monthly_foreman_report.py`'nin
    sorumluluğunda kalır — kendi idempotency/race-recovery/çoklu-commit state
    machine'i buradan hiç çağrılmadan, değiştirilmeden kullanılır. Bu servis
    yalnızca HTTP orkestrasyonunu ve pdf/access uç noktalarındaki audit'in AYRI
    ikinci fazını (rapor state machine'i kendi commit'ini tamamladıktan sonra
    flush→audit→commit) yönetir — Aşama 2'nin "mutation→flush→audit→commit"
    deseninin, "mutation" kısmı zaten başka bir modül tarafından commit edilmiş
    durumda olduğu için hafifletilmiş bir varyantı.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _summary(report: ForemanMonthlyReport) -> dict:
        return {
            "year": report.year,
            "month": report.month,
            "generated_at": report.generated_at.isoformat(),
            "overall_score": float(report.overall_score) if report.overall_score is not None else None,
            "overall_level_name": report.overall_level_name,
            "is_reliable": report.is_reliable,
        }

    def _require_foreman(self, foreman_id: UUID) -> None:
        if self.db.get(Foreman, foreman_id) is None:
            raise ForemanNotFoundError("Formen bulunamadı.")

    # ------------------------------------------------------------------
    # Reads (audit yok, transaction yok)
    # ------------------------------------------------------------------

    def list_reports(self, foreman_id: UUID) -> dict:
        self._require_foreman(foreman_id)
        reports = list(
            self.db.scalars(
                select(ForemanMonthlyReport)
                .where(ForemanMonthlyReport.foreman_id == foreman_id)
                .order_by(ForemanMonthlyReport.year.desc(), ForemanMonthlyReport.month.desc())
            )
        )
        return {"items": [self._summary(r) for r in reports]}

    def latest_report(self, foreman_id: UUID) -> dict:
        self._require_foreman(foreman_id)
        latest = self.db.scalar(
            select(ForemanMonthlyReport)
            .where(ForemanMonthlyReport.foreman_id == foreman_id)
            .order_by(ForemanMonthlyReport.year.desc(), ForemanMonthlyReport.month.desc())
            .limit(1)
        )
        if latest is None:
            year, month = latest_completed_period()
            try:
                latest = get_or_generate_monthly_report(self.db, foreman_id, year, month)
            except ValueError:
                return {"available": False}
        return {"available": True, **self._summary(latest), "report_data": latest.report_data}

    def report_detail(self, foreman_id: UUID, year: int, month: int) -> dict:
        self._require_foreman(foreman_id)
        try:
            report = get_or_generate_monthly_report(self.db, foreman_id, year, month)
        except ValueError as exc:
            raise InvalidReportPeriodError(str(exc)) from exc
        return {**self._summary(report), "report_data": report.report_data}

    # ------------------------------------------------------------------
    # PDF / Access — rapor state machine (Faz 1) + audit (Faz 2, ayrı)
    # ------------------------------------------------------------------

    def pdf_bytes(
        self,
        foreman_id: UUID,
        year: int,
        month: int,
        *,
        subject: str,
        ip_address: str | None,
        record_audit: RecordAudit,
    ) -> tuple[bytes, str]:
        self._require_foreman(foreman_id)
        try:
            report = get_or_generate_monthly_report(self.db, foreman_id, year, month)
        except ValueError as exc:
            raise InvalidReportPeriodError(str(exc)) from exc

        settings = get_settings()
        try:
            generate_and_store_report_pdf(self.db, report, settings)
        except Exception:
            logger.warning(
                "report_pdf_endpoint: storage upload failed, falling back to on-the-fly render report_id=%s", report.id
            )

        pdf_bytes = None
        if report.pdf_generation_status == ReportGenerationStatus.READY and report.object_key:
            try:
                pdf_bytes = get_report_storage(settings).download(report.object_key)
            except (ReportObjectNotFoundError, ReportStorageError):
                pdf_bytes = None

        file_name = report.pdf_file_name or (
            f"formen-performans-raporu-{report.report_data['foreman']['employee_number']}-{year}-{month:02d}.pdf"
        )
        if pdf_bytes is None:
            pdf_bytes = render_monthly_foreman_report_pdf(report.report_data)

        record_audit(
            self.db, subject, "monthly_report_downloaded", entity="foreman_monthly_report",
            new_value=str(report.id), ip_address=ip_address,
        )
        self.db.commit()
        return pdf_bytes, file_name

    def access(
        self,
        foreman_id: UUID,
        year: int,
        month: int,
        *,
        subject: str,
        ip_address: str | None,
        record_audit: RecordAudit,
    ) -> dict:
        self._require_foreman(foreman_id)
        try:
            report = get_or_generate_monthly_report(self.db, foreman_id, year, month)
        except ValueError as exc:
            raise InvalidReportPeriodError(str(exc)) from exc

        settings = get_settings()
        try:
            generate_and_store_report_pdf(self.db, report, settings)
        except Exception as exc:
            raise MonthlyReportPdfGenerationFailedError(
                "Rapor PDF'i şu anda hazırlanamadı, lütfen daha sonra tekrar deneyin."
            ) from exc

        if cloudfront_configured(settings):
            try:
                url, expires_at = generate_signed_url(settings, report.object_key)
            except CloudFrontNotConfiguredError as exc:
                raise MonthlyReportAccessUnavailableError(str(exc)) from exc
            access = {"url": url, "expires_at": expires_at.isoformat(), "requires_auth": False}
        else:
            access = {
                # /api/v1 öneki yok — frontend'in apiClient'i baseURL="/api/v1" olduğu için bu
                # path'i doğrudan apiClient.get() ile çağırır (bkz. api/client.ts).
                "url": f"/foremen/{foreman_id}/monthly-reports/{year}/{month}/pdf",
                "expires_at": None, "requires_auth": True,
            }

        record_audit(
            self.db, subject, "monthly_report_access_granted", entity="foreman_monthly_report",
            new_value=str(report.id), ip_address=ip_address,
        )
        self.db.commit()
        return access
