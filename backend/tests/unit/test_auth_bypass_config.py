import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    defaults = {"oidc_issuer_url": None, "oidc_audience": None, "auth_bypass": False, "debug": False}
    defaults.update(overrides)
    return Settings(**defaults)


class TestAuthBypassDefaultsOff:
    def test_default_is_false(self):
        assert Settings().auth_bypass is False


class TestScenarioA_DevelopmentBypassTrue:
    def test_passes_validation(self):
        settings = _settings(environment="development", auth_bypass=True)
        assert settings.auth_bypass is True
        assert settings.environment == "development"


class TestScenarioB_DevelopmentBypassFalse:
    def test_passes_without_oidc_config(self):
        settings = _settings(environment="development", auth_bypass=False)
        assert settings.auth_bypass is False


class TestScenarioC_ProductionBypassFalse:
    def test_requires_real_oidc_config(self):
        with pytest.raises(ValidationError):
            _settings(environment="production", auth_bypass=False)

    def test_passes_with_real_oidc_config(self):
        settings = _settings(
            environment="production",
            auth_bypass=False,
            oidc_issuer_url="https://sso.example.com/realms/formen",
            oidc_audience="formen-backend",
        )
        assert settings.auth_bypass is False


class TestScenarioD_ProductionBypassTrue:
    def test_fails_startup_even_with_real_oidc_config(self):
        with pytest.raises(ValidationError):
            _settings(
                environment="production",
                auth_bypass=True,
                oidc_issuer_url="https://sso.example.com/realms/formen",
                oidc_audience="formen-backend",
            )


class TestScenarioE_OtherNonDevelopmentEnvironmentBypassTrue:
    def test_fails_startup(self):
        with pytest.raises(ValidationError):
            _settings(environment="staging", auth_bypass=True)


class TestProductionHttpSafety:
    def test_debug_mode_fails_closed(self):
        with pytest.raises(ValidationError, match="DEBUG must be false"):
            _settings(
                environment="production",
                debug=True,
                oidc_issuer_url="https://sso.example.com/realms/formen",
                oidc_audience="formen-backend",
            )

    def test_wildcard_cors_fails_closed(self):
        with pytest.raises(ValidationError, match="CORS_ORIGINS cannot contain"):
            _settings(
                environment="production",
                cors_origins=["*"],
                oidc_issuer_url="https://sso.example.com/realms/formen",
                oidc_audience="formen-backend",
            )

    def test_explicit_origin_is_allowed(self):
        settings = _settings(
            environment="production",
            cors_origins=["https://formen.example.com"],
            oidc_issuer_url="https://sso.example.com/realms/formen",
            oidc_audience="formen-backend",
        )
        assert settings.cors_origins == ["https://formen.example.com"]
