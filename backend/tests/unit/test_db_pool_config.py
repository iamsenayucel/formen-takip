import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    defaults = {"oidc_issuer_url": None, "oidc_audience": None, "auth_bypass": False, "debug": False}
    defaults.update(overrides)
    return Settings(**defaults)


class TestDbPoolDefaults:
    def test_defaults_match_sqlalchemy_defaults(self):
        settings = Settings()
        assert settings.db_pool_size == 5
        assert settings.db_max_overflow == 10
        assert settings.db_pool_timeout == 30
        assert settings.db_pool_recycle == 1800


class TestDbPoolEnvironmentOverride:
    def test_env_vars_override_defaults(self, monkeypatch):
        monkeypatch.setenv("DB_POOL_SIZE", "20")
        monkeypatch.setenv("DB_MAX_OVERFLOW", "5")
        monkeypatch.setenv("DB_POOL_TIMEOUT", "10")
        monkeypatch.setenv("DB_POOL_RECYCLE", "900")
        settings = _settings()
        assert settings.db_pool_size == 20
        assert settings.db_max_overflow == 5
        assert settings.db_pool_timeout == 10
        assert settings.db_pool_recycle == 900


class TestDbPoolValidation:
    def test_rejects_zero_pool_size(self):
        with pytest.raises(ValidationError, match="DB_POOL_SIZE"):
            _settings(db_pool_size=0)

    def test_rejects_negative_pool_size(self):
        with pytest.raises(ValidationError, match="DB_POOL_SIZE"):
            _settings(db_pool_size=-1)

    def test_rejects_negative_max_overflow(self):
        with pytest.raises(ValidationError, match="DB_MAX_OVERFLOW"):
            _settings(db_max_overflow=-1)

    def test_allows_zero_max_overflow(self):
        settings = _settings(db_max_overflow=0)
        assert settings.db_max_overflow == 0

    def test_rejects_zero_pool_timeout(self):
        with pytest.raises(ValidationError, match="DB_POOL_TIMEOUT"):
            _settings(db_pool_timeout=0)

    def test_rejects_negative_pool_timeout(self):
        with pytest.raises(ValidationError, match="DB_POOL_TIMEOUT"):
            _settings(db_pool_timeout=-5)

    def test_rejects_zero_pool_recycle(self):
        with pytest.raises(ValidationError, match="DB_POOL_RECYCLE"):
            _settings(db_pool_recycle=0)

    def test_rejects_arbitrary_negative_pool_recycle(self):
        with pytest.raises(ValidationError, match="DB_POOL_RECYCLE"):
            _settings(db_pool_recycle=-5)

    def test_allows_minus_one_pool_recycle_to_disable(self):
        settings = _settings(db_pool_recycle=-1)
        assert settings.db_pool_recycle == -1

    def test_allows_positive_pool_recycle(self):
        settings = _settings(db_pool_recycle=3600)
        assert settings.db_pool_recycle == 3600
