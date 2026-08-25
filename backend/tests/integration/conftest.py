from . import _ephemeral_db  # noqa: F401,E402 — aşağıdaki app.* importlarından önce çalışmalı

import time
import uuid
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from jose.utils import base64url_encode
from sqlalchemy import delete

import app.core.oidc as oidc_module
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.main import app
from app.models.enums import ReportFormat, ReportStatus, ReportType
from app.models.report import ReportExport
from app.models.user import AuditLog

TEST_SUBJECT = "test-integration-subject"
TEST_KID = "test-key-1"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_numbers = _private_key.public_key().public_numbers()


def _int_to_b64url(value: int) -> str:
    length = (value.bit_length() + 7) // 8 or 1
    return base64url_encode(value.to_bytes(length, "big")).decode("ascii")


TEST_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "kid": TEST_KID,
            "use": "sig",
            "alg": "RS256",
            "n": _int_to_b64url(_public_numbers.n),
            "e": _int_to_b64url(_public_numbers.e),
        }
    ]
}

_PRIVATE_PEM = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)


def make_test_token(
    *,
    subject: str = TEST_SUBJECT,
    expires_in: int = 300,
    issuer: str | None = None,
    audience: str | None = None,
    kid: str | None = TEST_KID,
    algorithm: str = "RS256",
    signing_key: bytes | None = None,
    extra_claims: dict | None = None,
) -> str:
    """OIDC access token benzeri, RS256 imzalı bir test JWT'si üretir.

    Backend'in gerçek doğrulama koduyla (signature/issuer/audience/exp) tam uyumlu
    çalışır; JWKS yalnızca ağ çağrısı seviyesinde mock'lanır (bkz. _mock_jwks).
    """
    settings = get_settings()
    now = int(time.time())
    claims = {
        "sub": subject,
        "iss": issuer if issuer is not None else settings.oidc_issuer_url,
        "aud": audience if audience is not None else settings.oidc_audience,
        "iat": now,
        "exp": now + expires_in,
        "email": f"{subject}@formen-demo.com",
        "name": "Test Entegrasyon Kullanıcısı",
    }
    if extra_claims:
        claims.update(extra_claims)
    headers = {"kid": kid} if kid else {}
    return jose_jwt.encode(claims, signing_key or _PRIVATE_PEM, algorithm=algorithm, headers=headers)


@pytest.fixture(scope="session", autouse=True)
def _mock_jwks():
    """SSO'ya gerçek bir ağ çağrısı yapmadan JWKS keşfini/getirmesini test anahtarıyla değiştirir."""
    mp = pytest.MonkeyPatch()
    mp.setattr(oidc_module, "_discover_jwks_uri", lambda issuer_url: "http://test-issuer.local/jwks")
    mp.setattr(oidc_module, "fetch_jwks", lambda jwks_uri: TEST_JWKS)
    yield
    mp.undo()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def report_export_factory(db_session):
    """Deterministik rapor export'ları üretir; ardından rapor ve audit kayıtlarını siler."""
    created: list[tuple[uuid.UUID, str]] = []

    def factory(
        *,
        report_format: ReportFormat = ReportFormat.CSV,
        report_type: ReportType = ReportType.COMPANY_SUMMARY,
        requested_by_subject: str = TEST_SUBJECT,
        created_at: datetime | None = None,
        file_content: bytes | None = None,
        row_count: int = 1,
    ) -> ReportExport:
        token = uuid.uuid4().hex
        timestamp = created_at or datetime.now(timezone.utc)
        export = ReportExport(
            report_type=report_type,
            format=report_format,
            filters_json={},
            requested_by_subject=requested_by_subject,
            file_name=f"integration-report-{token}.{report_format.value}",
            file_content=file_content if file_content is not None else f"report-{token}".encode(),
            row_count=row_count,
            status=ReportStatus.COMPLETED,
            completed_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        db_session.add(export)
        db_session.commit()
        db_session.refresh(export)
        created.append((export.id, export.file_name))
        return export

    yield factory

    db_session.rollback()
    if created:
        report_ids = [report_id for report_id, _ in created]
        file_names = [file_name for _, file_name in created]
        db_session.execute(
            delete(AuditLog).where(
                AuditLog.entity == "report_export",
                AuditLog.new_value.in_(file_names),
            )
        )
        db_session.execute(delete(ReportExport).where(ReportExport.id.in_(report_ids)))
        db_session.commit()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_test_token()}"}
