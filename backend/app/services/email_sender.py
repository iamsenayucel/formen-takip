from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import Settings


class EmailSendError(Exception):
    pass


def send_email_with_attachment(
    settings: Settings,
    *,
    to_addr: str,
    cc_addrs: list[str],
    subject: str,
    body: str,
    attachment_bytes: bytes,
    attachment_filename: str,
) -> None:
    """Kurumsal SMTP üzerinden PDF ekli e-posta gönderir.

    Standart kütüphane (`smtplib`) kullanır — yeni bir bağımlılık gerektirmez. Bu
    fonksiyon yalnızca transport'tur; alıcı çözümleme, retry/idempotency mantığı
    `app/services/monthly_report_email.py`'dedir.
    """
    if not settings.smtp_available:
        raise EmailSendError("SMTP yapılandırılmamış (SMTP_ENABLED/SMTP_HOST/SMTP_FROM eksik).")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = to_addr
    if cc_addrs:
        message["Cc"] = ", ".join(cc_addrs)
    message.set_content(body)
    message.add_attachment(
        attachment_bytes, maintype="application", subtype="pdf", filename=attachment_filename
    )

    all_recipients = [to_addr, *cc_addrs]
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message, from_addr=settings.smtp_from, to_addrs=all_recipients)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(str(exc)) from exc
