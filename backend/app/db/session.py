import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

_pool_logger = logging.getLogger("app.db.pool")


@event.listens_for(engine, "checkout")
def _log_pool_overflow_pressure(dbapi_connection, connection_record, connection_proxy) -> None:
    # Yalnızca havuz taban boyutunun (pool_size) üzerine taşıp overflow bağlantısı
    # kullanıldığında loglanır — normal trafikte hiç tetiklenmez, credential/connection
    # string içermez. Her sorguyu değil, gerçek bir kapasite baskısı sinyalini yakalar.
    pool = engine.pool
    overflow = pool.overflow()
    if overflow > 0:
        _pool_logger.warning(
            "DB connection pool overflow in use: checked_out=%s pool_size=%s overflow=%s",
            pool.checkedout(), pool.size(), overflow,
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
