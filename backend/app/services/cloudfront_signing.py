from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import Settings


class CloudFrontNotConfiguredError(Exception):
    pass


def cloudfront_configured(settings: Settings) -> bool:
    return bool(settings.cloudfront_domain and settings.cloudfront_key_pair_id and settings.cloudfront_private_key)


def generate_signed_url(settings: Settings, object_key: str, ttl_seconds: int | None = None) -> tuple[str, datetime]:
    if not cloudfront_configured(settings):
        raise CloudFrontNotConfiguredError(
            "CloudFront yapılandırması eksik (CLOUDFRONT_DOMAIN/CLOUDFRONT_KEY_PAIR_ID/"
            "CLOUDFRONT_PRIVATE_KEY) — IT/DevOps tarafından sağlanması gerekiyor."
        )

    from botocore.signers import CloudFrontSigner
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(
        settings.cloudfront_private_key.encode("utf-8"), password=None
    )

    def _rsa_signer(message: bytes) -> bytes:
        return private_key.sign(message, padding.PKCS1v15(), hashes.SHA1())

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds or settings.report_signed_url_ttl_seconds)
    url = f"https://{settings.cloudfront_domain}/{object_key}"
    signer = CloudFrontSigner(settings.cloudfront_key_pair_id, _rsa_signer)
    signed_url = signer.generate_presigned_url(url, date_less_than=expires_at)
    return signed_url, expires_at
