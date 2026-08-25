import pytest
from pydantic import ValidationError

from app.core.config import Settings

_REAL_LOOKING_URL = "postgresql+psycopg://formen:formen@localhost:5433/formen_takip"
_TEST_LOOKING_URL = "postgresql+psycopg://formen_test:formen_test@localhost:55432/formen_integration_test"


def _settings(**overrides) -> Settings:
    defaults = {"oidc_issuer_url": None, "oidc_audience": None, "auth_bypass": False}
    defaults.update(overrides)
    return Settings(**defaults)


class TestEnvironmentTestRequiresExplicitTestDatabase:
    def test_fails_closed_against_real_looking_database_url(self):
        with pytest.raises(ValidationError):
            _settings(environment="test", database_url=_REAL_LOOKING_URL)

    def test_fails_closed_against_production_hostname_database_url(self):
        with pytest.raises(ValidationError):
            _settings(
                environment="test",
                database_url="postgresql+psycopg://prod_user:prod_pass@prod-db.internal:5432/formen_takip",
            )

    def test_passes_with_explicit_test_database_name(self):
        settings = _settings(environment="test", database_url=_TEST_LOOKING_URL)
        assert settings.environment == "test"
        assert settings.database_url == _TEST_LOOKING_URL


class TestNonTestEnvironmentsUnaffected:
    def test_development_does_not_require_test_marker(self):
        settings = _settings(environment="development", database_url=_REAL_LOOKING_URL)
        assert settings.database_url == _REAL_LOOKING_URL

    def test_production_does_not_require_test_marker_by_itself(self):
        settings = _settings(
            environment="production",
            database_url=_REAL_LOOKING_URL,
            oidc_issuer_url="https://sso.example.com/realms/formen",
            oidc_audience="formen-backend",
        )
        assert settings.database_url == _REAL_LOOKING_URL
