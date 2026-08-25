from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from app.services.storage.base import ReportObjectNotFoundError, ReportStorage, ReportStorageError


class S3ReportStorage(ReportStorage):

    def __init__(self, bucket_name: str, region: str | None = None):
        self._bucket_name = bucket_name
        self._client = boto3.client("s3", region_name=region) if region else boto3.client("s3")

    def upload(self, object_key: str, content: bytes, content_type: str) -> None:
        try:
            self._client.put_object(
                Bucket=self._bucket_name, Key=object_key, Body=content,
                ContentType=content_type, ServerSideEncryption="AES256",
            )
        except ClientError as exc:
            raise ReportStorageError(f"S3 upload başarısız: {object_key}") from exc

    def download(self, object_key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket_name, Key=object_key)
            return response["Body"].read()
        except self._client.exceptions.NoSuchKey as exc:
            raise ReportObjectNotFoundError(f"S3 nesnesi bulunamadı: {object_key}") from exc
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise ReportObjectNotFoundError(f"S3 nesnesi bulunamadı: {object_key}") from exc
            raise ReportStorageError(f"S3 download başarısız: {object_key}") from exc

    def exists(self, object_key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket_name, Key=object_key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise ReportStorageError(f"S3 head_object başarısız: {object_key}") from exc
