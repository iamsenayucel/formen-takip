"""Entegrasyon testi veritabanı bootstrap akışı.

Geçici PostgreSQL container hazırlar ve herhangi bir `app.*` importundan önce DATABASE_URL
değerini buna yönlendirir. Böylece module-level engine/SessionLocal ilk importtan itibaren
geçici DB'ye bağlanır; normal DATABASE_URL kullanılmaz.

İzolasyon import sırasına bağlıdır; bu module conftest.py içindeki ilk import olmalıdır.
Docker/settings/migration hatasında fail-closed davranır ve gerçek/bilinmeyen DB'ye fallback yapmaz.
"""

from __future__ import annotations

import atexit
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]

_TEST_DB_NAME = "formen_integration_test"
_TEST_DB_USER = "formen_test"
_TEST_DB_PASSWORD = "formen_test"
_SEED = 42
_SEED_SUBJECT = "integration-test-seed"
_FIXED_PERIOD_END = date(2026, 8, 19)


def _fail(message: str) -> None:
    raise RuntimeError(f"[integration test DB bootstrap] {message}")


if "app.db.session" in sys.modules or "app.main" in sys.modules:
    _fail(
        "app.db.session/app.main was imported before the ephemeral test database was "
        "provisioned. This would bind the SQLAlchemy engine to the application's normal "
        "DATABASE_URL. Make sure `import tests.integration._ephemeral_db` (or the relative "
        "equivalent) is the very first import in tests/integration/conftest.py."
    )

try:
    from testcontainers.community.postgres import PostgresContainer
except Exception as exc:  # pragma: no cover - environment/setup sorunu, app logic değil
    _fail(
        "testcontainers[postgres] is required to run the integration test suite "
        "(pip install -r requirements-dev.txt). Docker is required too — integration "
        f"tests never fall back to a real database. Import failed: {exc}"
    )

try:
    _container = PostgresContainer(
        image="postgres:16-alpine",
        username=_TEST_DB_USER,
        password=_TEST_DB_PASSWORD,
        dbname=_TEST_DB_NAME,
        driver="psycopg",
    )
    _container.start()
except Exception as exc:
    _fail(
        "Could not start an ephemeral PostgreSQL container via Docker. Integration tests "
        "require a running Docker daemon and NEVER fall back to the application's configured "
        "DATABASE_URL. Start Docker and retry, or run `pytest tests/unit` for DB-free tests. "
        f"Underlying error: {exc}"
    )

atexit.register(_container.stop)

_TEST_DATABASE_URL = _container.get_connection_url()

# Derinlemesine savunmanın ikincil katmanı. Asıl garanti, bu URL'nin configuration'dan
# değil, doğrudan oluşturduğumuz container'dan gelmesidir.
_host = _container.get_container_host_ip()
if _host not in ("localhost", "127.0.0.1"):
    _fail(f"Refusing to run integration tests against unexpected container host {_host!r}.")
if _TEST_DB_NAME not in _TEST_DATABASE_URL or "test" not in _TEST_DATABASE_URL.lower():
    _fail("Ephemeral test database URL does not carry an explicit test marker; refusing to proceed.")

os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ["AUTH_BYPASS"] = "false"

from app.core.config import get_settings  # noqa: E402 (ertelendi; önce env değerleri ayarlanmalı)

get_settings.cache_clear()
_settings = get_settings()  # re-validates Settings; raises (fail-closed) if misconfigured

if _settings.database_url != _TEST_DATABASE_URL or _settings.environment != "test":
    _fail("Settings did not pick up the ephemeral test database after cache_clear().")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

_alembic_cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
command.upgrade(_alembic_cfg, "head")

# Yalnızca şimdi import edilir: app.db.session içindeki module-level engine/SessionLocal
# bu import sırasında oluşturulur ve migration uygulanmış geçici container'a bağlanır.
from app.db.session import SessionLocal  # noqa: E402
from app.services.ingestion import run_ingestion  # noqa: E402
from app.services.providers.synthetic_provider import SyntheticDataProvider  # noqa: E402
from app.services.synthetic.anomaly_generator import seed_anomalies  # noqa: E402
from app.services.synthetic.contribution_generator import seed_contribution_works  # noqa: E402
from app.services.synthetic.production_generator import GenerationParams, seed_production_data  # noqa: E402
from app.services.synthetic.reference_data import seed_reference_data  # noqa: E402


def _seed_test_data() -> None:
    """Entegrasyon testlerinin local seed ile aynı organizasyon/personel/üretim biçimini
    görmesi için `app.cli cmd_seed` varsayılan sırasını uygular.
    """
    rng = random.Random(_SEED)
    # Karakterizasyon testleri sabit takvim pencereleri kullanır. Üretilen dataset'i sabit
    # tutmak, testler daha sonra çalıştırıldığında random stream'in ve tüm KPI değerlerinin
    # bir gün kaymasını önler.
    period_end = _FIXED_PERIOD_END
    period_start = period_end - timedelta(days=365)
    db = SessionLocal()
    try:
        ref = seed_reference_data(
            db, rng,
            min_plants_per_foreman=2, max_plants_per_foreman=4,
            period_start=period_start, period_end=period_end,
        )
        params = GenerationParams(missing_rate=0.02, error_rate=0.01, anomaly_rate=0.015, duplicate_rate=0.005)
        seed_production_data(db, rng, ref, period_start, period_end, params)
        provider = SyntheticDataProvider(db, rng, duplicate_rate=0.005)
        run_ingestion(db, provider, period_start, period_end, plant_codes=[p.code for p in ref.plants])
        seed_contribution_works(db, rng, _SEED_SUBJECT, count=40)
        seed_anomalies(db, rng)
    finally:
        db.close()


_seed_test_data()

TEST_DATABASE_URL = _TEST_DATABASE_URL
container = _container
