import re
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"
ADD_VALUE_RE = re.compile(r"ALTER TYPE\s+\S+\s+ADD VALUE", re.IGNORECASE)


def _migration_files():
    return sorted(VERSIONS_DIR.glob("*.py"))


@pytest.mark.parametrize("path", _migration_files(), ids=lambda p: p.stem)
def test_add_value_is_committed_before_use(path: Path):
    """Yeni `alembic upgrade head` migration zincirini tek transaction'da çalıştırır.

    Postgres enum değerinin eklendiği transaction içinde kullanılmasını reddeder. Bu nedenle
    her `ALTER TYPE ... ADD VALUE`, sonraki migration'dan bağımsız commit edilmesi için
    `op.get_context().autocommit_block()` içinde çalışmalıdır.
    """
    source = path.read_text(encoding="utf-8")
    if not ADD_VALUE_RE.search(source):
        pytest.skip("no ADD VALUE in this migration")

    assert "autocommit_block" in source, (
        f"{path.name} runs ALTER TYPE ... ADD VALUE without "
        "op.get_context().autocommit_block() — this will raise "
        "UnsafeNewEnumValueUsage on a fresh database if any later migration "
        "uses the new value in the same `alembic upgrade head` run."
    )
