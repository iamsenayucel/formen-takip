import argparse
from unittest.mock import patch

from app.cli import cmd_send_monthly_report_emails
from app.core.config import Settings


def _args(**overrides) -> argparse.Namespace:
    defaults = dict(year=None, month=None, retry_failed=False)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestSendMonthlyReportEmailsSmtpGuard:
    def test_smtp_unavailable_skips_before_any_db_work(self, capsys):
        settings = Settings(_env_file=None, smtp_enabled=False)

        with (
            patch("app.cli.get_settings", return_value=settings),
            patch("app.cli.SessionLocal") as mock_session_local,
            patch("app.cli.send_monthly_report_email") as mock_send,
        ):
            cmd_send_monthly_report_emails(_args())

        mock_session_local.assert_not_called()
        mock_send.assert_not_called()
        assert "SMTP" in capsys.readouterr().out

    def test_smtp_available_proceeds_to_db_work(self, capsys):
        settings = Settings(
            _env_file=None, smtp_enabled=True, smtp_host="smtp.example.com", smtp_from="a@b.com"
        )

        with (
            patch("app.cli.get_settings", return_value=settings),
            patch("app.cli.SessionLocal") as mock_session_local,
        ):
            mock_db = mock_session_local.return_value
            mock_db.scalars.return_value = []
            cmd_send_monthly_report_emails(_args())

        mock_session_local.assert_called_once()
        mock_db.close.assert_called_once()
