from argparse import Namespace

import pytest

from app import cli


class _ExistingReferenceSession:
    def __init__(self) -> None:
        self.closed = False

    def scalar(self, _statement):
        return object()

    def close(self) -> None:
        self.closed = True


def test_seed_refuses_existing_reference_data_without_mutation(monkeypatch, capsys):
    session = _ExistingReferenceSession()
    monkeypatch.setattr(cli, "SessionLocal", lambda: session)

    args = Namespace(seed=42, start_date="2025-08-19", end_date="2026-08-19")
    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_seed(args)

    assert exc_info.value.code == 1
    assert session.closed is True
    output = capsys.readouterr().out
    assert "yalnızca boş veritabanında çalışır" in output
    assert "--force" not in output
