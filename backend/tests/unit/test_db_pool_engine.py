"""DB connection pool engine wiring testleri.

`app.db.session.engine`'e dokunmaz; testi gerçek sürücüye/DSN'e bağımlı kılmamak
için `app/db/session.py::engine` ile aynı kwargs kümesiyle izole bir SQLite engine
kurulur. Amaç: (1) Settings -> create_engine kwargs eşlemesi, (2) pool_size/
max_overflow/pool_timeout üçlüsünün gerçek pool davranışını (checkout/exhaustion/
timeout) etkilediğinin davranışsal doğrulaması. Private `Pool._max_overflow`/
`_timeout`/`_recycle`/`_pre_ping` alanlarına erişilir; SQLAlchemy'de stabildirler
ve `Pool.size()` gibi public bir alternatifleri yoktur.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.pool import QueuePool

from app.core.config import Settings
from app.db.session import engine as real_engine


def _build_engine(settings: Settings):
    return create_engine(
        "sqlite://",
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        future=True,
    )


def _settings(**overrides) -> Settings:
    defaults = {"oidc_issuer_url": None, "oidc_audience": None, "auth_bypass": False, "debug": False}
    defaults.update(overrides)
    return Settings(**defaults)


class TestSettingsReachPoolConfiguration:
    def test_pool_size_and_overflow_and_timeout_and_recycle_are_wired(self):
        settings = _settings(db_pool_size=3, db_max_overflow=2, db_pool_timeout=1, db_pool_recycle=900)
        engine = _build_engine(settings)
        try:
            assert engine.pool.size() == 3
            assert engine.pool._max_overflow == 2
            assert engine.pool._timeout == 1
            assert engine.pool._recycle == 900
        finally:
            engine.dispose()

    def test_pre_ping_stays_enabled_regardless_of_pool_settings(self):
        settings = _settings(db_pool_size=1, db_max_overflow=0)
        engine = _build_engine(settings)
        try:
            assert engine.pool._pre_ping is True
        finally:
            engine.dispose()


class TestPoolBehaviorUnderExhaustion:
    """pool_size + max_overflow, checkout edilebilecek gerçek üst sınırdır; bu sınır
    aşıldığında pool_timeout kadar beklenip TimeoutError fırlatılmalıdır — "40 thread
    varsa pool 40 olsun" gibi doğrusal bir varsayım yerine, asıl garanti edilen
    davranış budur.
    """

    def test_checkouts_succeed_up_to_pool_size_plus_overflow(self):
        settings = _settings(db_pool_size=2, db_max_overflow=1, db_pool_timeout=1)
        engine = _build_engine(settings)
        try:
            conns = [engine.connect() for _ in range(3)]
            assert len(conns) == 3
        finally:
            for c in conns:
                c.close()
            engine.dispose()

    def test_checkout_beyond_pool_size_plus_overflow_times_out(self):
        settings = _settings(db_pool_size=1, db_max_overflow=0, db_pool_timeout=1)
        engine = _build_engine(settings)
        held = engine.connect()
        try:
            with pytest.raises(SATimeoutError):
                engine.connect()
        finally:
            held.close()
            engine.dispose()


class TestRealSessionEngineIsWiredFromSettings:
    """app.db.session.engine bağlantı açmadan; yalnızca Settings'ten okunan pool
    ayarlarının gerçek modülde de aynı şekilde uygulandığını doğrular.
    """

    def test_real_engine_pool_size_matches_active_settings(self):
        from app.core.config import get_settings

        assert real_engine.pool.size() == get_settings().db_pool_size

    def test_real_engine_keeps_pre_ping_enabled(self):
        assert real_engine.pool._pre_ping is True
