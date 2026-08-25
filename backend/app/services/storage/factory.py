from __future__ import annotations

from app.core.config import Settings
from app.services.storage.base import ReportStorage, ReportStorageError


def get_report_storage(settings: Settings) -> ReportStorage:
    if settings.environment == "production" and settings.report_storage_provider != "s3":
        raise ReportStorageError(
            "REPORT_STORAGE_PROVIDER production ortamında 's3' olmalıdır (fail-closed: "
            "rapor PDF'leri container filesystem'inde kalıcı tutulamaz)."
        )

    if settings.report_storage_provider == "s3":
        from app.services.storage.s3_storage import S3ReportStorage

        if not settings.reports_s3_bucket:
            raise ReportStorageError("REPORTS_S3_BUCKET yapılandırılmadan S3 storage kullanılamaz.")
        return S3ReportStorage(bucket_name=settings.reports_s3_bucket, region=settings.aws_region)

    if settings.report_storage_provider == "local":
        from app.services.storage.local_storage import LocalFilesystemReportStorage

        return LocalFilesystemReportStorage(base_dir=settings.local_report_storage_dir)

    raise ReportStorageError(f"Bilinmeyen REPORT_STORAGE_PROVIDER: {settings.report_storage_provider}")
