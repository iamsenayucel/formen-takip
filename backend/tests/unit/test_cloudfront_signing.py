import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.services.cloudfront_signing import (
    CloudFrontNotConfiguredError,
    cloudfront_configured,
    generate_signed_url,
)

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode("utf-8")


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


class TestCloudfrontConfigured:
    def test_false_when_domain_missing(self):
        settings = _settings(cloudfront_key_pair_id="K1", cloudfront_private_key=_PRIVATE_PEM)
        assert cloudfront_configured(settings) is False

    def test_true_when_all_three_present(self):
        settings = _settings(
            cloudfront_domain="d123.cloudfront.net", cloudfront_key_pair_id="K1",
            cloudfront_private_key=_PRIVATE_PEM,
        )
        assert cloudfront_configured(settings) is True


class TestGenerateSignedUrl:
    def test_raises_when_not_configured(self):
        settings = _settings()
        with pytest.raises(CloudFrontNotConfiguredError):
            generate_signed_url(settings, "reports/x.pdf")

    def test_generates_url_with_expected_shape(self):
        settings = _settings(
            cloudfront_domain="d123.cloudfront.net", cloudfront_key_pair_id="K1",
            cloudfront_private_key=_PRIVATE_PEM, report_signed_url_ttl_seconds=300,
        )
        url, expires_at = generate_signed_url(settings, "reports/2026/07/foremen/x/y.pdf")

        assert url.startswith("https://d123.cloudfront.net/reports/2026/07/foremen/x/y.pdf?")
        assert "Key-Pair-Id=K1" in url
        assert "Signature=" in url
        assert "Expires=" in url
        assert expires_at is not None

    def test_custom_ttl_overrides_default(self):
        settings = _settings(
            cloudfront_domain="d123.cloudfront.net", cloudfront_key_pair_id="K1",
            cloudfront_private_key=_PRIVATE_PEM, report_signed_url_ttl_seconds=300,
        )
        _, expires_at_default = generate_signed_url(settings, "x.pdf")
        _, expires_at_custom = generate_signed_url(settings, "x.pdf", ttl_seconds=60)
        assert expires_at_custom < expires_at_default
