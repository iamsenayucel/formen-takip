from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.services.storage.base import ReportObjectNotFoundError, ReportStorageError
from app.services.storage.local_storage import LocalFilesystemReportStorage
from app.services.storage.s3_storage import S3ReportStorage


class TestLocalFilesystemReportStorage:
    def test_upload_then_download_roundtrip(self, tmp_path):
        storage = LocalFilesystemReportStorage(base_dir=str(tmp_path))
        storage.upload("reports/2026/07/foremen/x/y.pdf", b"%PDF-1.4 fake", "application/pdf")
        assert storage.download("reports/2026/07/foremen/x/y.pdf") == b"%PDF-1.4 fake"

    def test_exists_false_for_missing_object(self, tmp_path):
        storage = LocalFilesystemReportStorage(base_dir=str(tmp_path))
        assert storage.exists("reports/does/not/exist.pdf") is False

    def test_exists_true_after_upload(self, tmp_path):
        storage = LocalFilesystemReportStorage(base_dir=str(tmp_path))
        storage.upload("a/b.pdf", b"x", "application/pdf")
        assert storage.exists("a/b.pdf") is True

    def test_download_missing_object_raises_not_found(self, tmp_path):
        storage = LocalFilesystemReportStorage(base_dir=str(tmp_path))
        with pytest.raises(ReportObjectNotFoundError):
            storage.download("nope.pdf")

    def test_path_traversal_rejected_on_upload(self, tmp_path):
        storage = LocalFilesystemReportStorage(base_dir=str(tmp_path))
        with pytest.raises(ReportStorageError):
            storage.upload("../../etc/passwd", b"x", "application/pdf")

    def test_path_traversal_rejected_on_download(self, tmp_path):
        storage = LocalFilesystemReportStorage(base_dir=str(tmp_path))
        with pytest.raises(ReportStorageError):
            storage.download("../outside.pdf")


class TestS3ReportStorage:
    def _client_error(self, code: str) -> ClientError:
        return ClientError({"Error": {"Code": code, "Message": "boom"}}, "GetObject")

    @patch("boto3.client")
    def test_upload_calls_put_object_with_encryption(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        storage = S3ReportStorage(bucket_name="reports-bucket", region="eu-central-1")

        storage.upload("reports/2026/07/x.pdf", b"content", "application/pdf")

        mock_client.put_object.assert_called_once_with(
            Bucket="reports-bucket", Key="reports/2026/07/x.pdf", Body=b"content",
            ContentType="application/pdf", ServerSideEncryption="AES256",
        )

    @patch("boto3.client")
    def test_upload_failure_wrapped_as_storage_error(self, mock_boto_client):
        mock_client = MagicMock()
        mock_client.put_object.side_effect = self._client_error("500")
        mock_boto_client.return_value = mock_client
        storage = S3ReportStorage(bucket_name="reports-bucket")

        with pytest.raises(ReportStorageError):
            storage.upload("x.pdf", b"content", "application/pdf")

    @patch("boto3.client")
    def test_download_missing_key_raises_not_found(self, mock_boto_client):
        mock_client = MagicMock()
        mock_client.exceptions.NoSuchKey = type("NoSuchKey", (ClientError,), {})
        mock_client.get_object.side_effect = self._client_error("NoSuchKey")
        mock_boto_client.return_value = mock_client
        storage = S3ReportStorage(bucket_name="reports-bucket")

        with pytest.raises(ReportObjectNotFoundError):
            storage.download("missing.pdf")

    @patch("boto3.client")
    def test_exists_true_when_head_object_succeeds(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        storage = S3ReportStorage(bucket_name="reports-bucket")

        assert storage.exists("present.pdf") is True
        mock_client.head_object.assert_called_once_with(Bucket="reports-bucket", Key="present.pdf")

    @patch("boto3.client")
    def test_exists_false_on_404(self, mock_boto_client):
        mock_client = MagicMock()
        mock_client.head_object.side_effect = self._client_error("404")
        mock_boto_client.return_value = mock_client
        storage = S3ReportStorage(bucket_name="reports-bucket")

        assert storage.exists("missing.pdf") is False
