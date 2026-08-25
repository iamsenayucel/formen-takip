from unittest.mock import patch

import pytest

from app.core.config import Settings
from app.services.storage.base import ReportStorageError
from app.services.storage.factory import get_report_storage
from app.services.storage.local_storage import LocalFilesystemReportStorage


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


class TestGetReportStorage:
    def test_local_provider_returns_local_storage(self, tmp_path):
        settings = _settings(report_storage_provider="local", local_report_storage_dir=str(tmp_path))
        storage = get_report_storage(settings)
        assert isinstance(storage, LocalFilesystemReportStorage)

    def test_production_with_local_provider_fails_closed(self, tmp_path):
        settings = _settings(
            environment="production", report_storage_provider="local",
            local_report_storage_dir=str(tmp_path),
            oidc_issuer_url="https://issuer.example.com", oidc_audience="aud",
        )
        with pytest.raises(ReportStorageError):
            get_report_storage(settings)

    def test_s3_provider_without_bucket_raises(self):
        settings = _settings(report_storage_provider="s3", reports_s3_bucket=None)
        with pytest.raises(ReportStorageError):
            get_report_storage(settings)

    @patch("boto3.client")
    def test_production_with_s3_and_bucket_succeeds(self, mock_boto_client):
        settings = _settings(
            environment="production", report_storage_provider="s3", reports_s3_bucket="reports-bucket",
            oidc_issuer_url="https://issuer.example.com", oidc_audience="aud",
        )
        from app.services.storage.s3_storage import S3ReportStorage

        storage = get_report_storage(settings)
        assert isinstance(storage, S3ReportStorage)

    def test_unknown_provider_raises(self, tmp_path):
        settings = _settings(report_storage_provider="ftp")
        with pytest.raises(ReportStorageError):
            get_report_storage(settings)
