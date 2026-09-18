"""Entegrasyon testi DB izolasyonu koruma testleri.

Entegrasyon testleri normal DATABASE_URL yerine _ephemeral_db.py tarafından hazırlanan
session-scoped, geçici Postgres container üzerinde çalışmalıdır.
"""

import uuid
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event, select, text

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.models.organization import Plant

_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _real_configured_database_url() -> str:
    env_path = _BACKEND_DIR / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    return ""


class TestA_IntegrationSuiteUsesEphemeralPostgres:
    def test_environment_is_test(self):
        assert get_settings().environment == "test"

    def test_database_name_carries_explicit_test_marker(self):
        assert "test" in get_settings().database_url.lower()

    def test_engine_is_bound_to_loopback_test_container(self):
        url = engine.url
        assert url.host in ("localhost", "127.0.0.1")
        assert url.database == "formen_integration_test"


class TestB_NormalApplicationDatabaseUrlNotUsed:
    def test_active_database_url_differs_from_dot_env_configured_url(self):
        configured = _real_configured_database_url()
        if not configured:
            return
        assert get_settings().database_url != configured

    def test_active_database_name_is_not_the_real_dev_database(self):
        assert engine.url.database != "formen_takip"


@contextmanager
def _rollback_scope():
    """Yazmaları outer transaction içindeki SAVEPOINT ile sınırlı session döndürür.
    Scope içinde commit() çağrılsa bile çıkışta rollback yapılır; test yazmaları izole edilir."""
    connection = engine.connect()
    outer_tx = connection.begin()
    session = SessionLocal(bind=connection)
    nested = session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = sess.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_tx.rollback()
        connection.close()


class TestD_TransactionalRollbackIsolationMechanism:
    def test_committed_write_inside_rollback_scope_does_not_leak_out(self):
        marker = f"isolation-guard-{uuid.uuid4().hex}"

        with _rollback_scope() as session:
            plant = session.scalar(select(Plant).limit(1))
            session.execute(text("UPDATE plants SET name = :name WHERE id = :id"), {"name": marker, "id": plant.id})
            session.commit()
            assert session.scalar(select(Plant).where(Plant.name == marker)) is not None

        with _rollback_scope() as session:
            assert session.scalar(select(Plant).where(Plant.name == marker)) is None

        with SessionLocal() as plain_session:
            assert plain_session.scalar(select(Plant).where(Plant.name == marker)) is None


class TestE_AlembicHeadAppliedToTestDatabase:
    def test_alembic_version_matches_head_revision(self):
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
        script = ScriptDirectory.from_config(cfg)
        expected_head = script.get_current_head()

        with SessionLocal() as session:
            actual = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

        assert actual == expected_head
