import smtplib
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.email_sender import EmailSendError, send_email_with_attachment


def _settings(**overrides) -> Settings:
    defaults = dict(
        smtp_enabled=True, smtp_host="smtp.example.com", smtp_port=587,
        smtp_from="raporlar@formen-takip.internal", smtp_use_tls=True,
    )
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


class TestSendEmailWithAttachment:
    def test_raises_when_smtp_disabled(self):
        settings = _settings(smtp_enabled=False)
        with pytest.raises(EmailSendError):
            send_email_with_attachment(
                settings, to_addr="foreman@x.com", cc_addrs=[], subject="s", body="b",
                attachment_bytes=b"%PDF", attachment_filename="r.pdf",
            )

    @patch("smtplib.SMTP")
    def test_sends_with_starttls_and_login(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _settings(smtp_username="user", smtp_password="pass")

        send_email_with_attachment(
            settings, to_addr="foreman@x.com", cc_addrs=["chief@x.com"],
            subject="Aylık Rapor", body="Merhaba", attachment_bytes=b"%PDF-fake",
            attachment_filename="rapor.pdf",
        )

        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "pass")
        assert mock_smtp.send_message.call_count == 1
        _, kwargs = mock_smtp.send_message.call_args
        assert kwargs["to_addrs"] == ["foreman@x.com", "chief@x.com"]
        assert kwargs["from_addr"] == "raporlar@formen-takip.internal"

    @patch("smtplib.SMTP")
    def test_smtp_exception_wrapped_as_email_send_error(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp.send_message.side_effect = smtplib.SMTPException("connection refused")
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _settings()

        with pytest.raises(EmailSendError):
            send_email_with_attachment(
                settings, to_addr="foreman@x.com", cc_addrs=[], subject="s", body="b",
                attachment_bytes=b"%PDF", attachment_filename="r.pdf",
            )

    @patch("smtplib.SMTP")
    def test_no_login_when_credentials_missing(self, mock_smtp_cls):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        settings = _settings()

        send_email_with_attachment(
            settings, to_addr="foreman@x.com", cc_addrs=[], subject="s", body="b",
            attachment_bytes=b"%PDF", attachment_filename="r.pdf",
        )

        mock_smtp.login.assert_not_called()
