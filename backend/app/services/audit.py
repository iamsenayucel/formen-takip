
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import AuditLog

logger = logging.getLogger("app.audit")


def record_audit(
    db: Session,
    subject: str | None,
    action: str,
    entity: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    ip_address: str | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> AuditLog:
    audit = AuditLog(
        subject=subject, action=action, entity=entity,
        old_value=old_value, new_value=new_value, ip_address=ip_address,
        success=success, error_message=error_message, created_at=datetime.now(timezone.utc),
    )
    db.add(audit)

    log = logger.info if success else logger.warning
    log(
        "audit action=%s entity=%s success=%s",
        action,
        entity,
        success,
        extra={
            "action": action,
            "entity": entity,
            "subject": subject,
            "success": success,
            "client_ip": ip_address,
        },
    )
    return audit
