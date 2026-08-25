import logging
from tests.helpers import legacy_json

from app.core.config import get_settings

from .conftest import TEST_SUBJECT, make_test_token


class TestNoToken:
    def test_protected_endpoint_without_authorization_header_returns_401(self, client):
        resp = client.get("/api/v1/dashboard/summary")
        assert resp.status_code == 401

    def test_me_requires_authentication(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestValidToken:
    def test_valid_token_is_accepted(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200

    def test_valid_token_grants_access_to_protected_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200


class TestExpiredToken:
    def test_expired_token_returns_401(self, client):
        token = make_test_token(expires_in=-60)
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestInvalidSignature:
    def test_token_signed_with_wrong_key_returns_401(self, client):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        rogue_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        rogue_pem = rogue_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        token = make_test_token(signing_key=rogue_pem)
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_tampered_token_returns_401(self, client, auth_headers):
        # Son 1-2 base64url karakteri, dolgu (padding) bitleri yüzünden değiştirmeden
        # aynı imza baytlarına decode olabilir; ortadaki bir karakteri bozmak imzayı
        # güvenilir şekilde geçersiz kılar.
        original = auth_headers["Authorization"]
        mid = len(original) // 2
        flipped = "A" if original[mid] != "A" else "B"
        tampered = original[:mid] + flipped + original[mid + 1 :]
        resp = client.get("/api/v1/auth/me", headers={"Authorization": tampered})
        assert resp.status_code == 401


class TestWrongIssuer:
    def test_wrong_issuer_returns_401(self, client):
        token = make_test_token(issuer="https://not-our-sso.example.com/realms/other")
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestWrongAudience:
    def test_wrong_audience_returns_401(self, client):
        token = make_test_token(audience="some-other-service")
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestMalformedHeader:
    def test_malformed_authorization_header_returns_401(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "not-a-bearer-token"})
        assert resp.status_code == 401

    def test_garbage_bearer_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    def test_missing_bearer_prefix_returns_401(self, client):
        token = make_test_token()
        resp = client.get("/api/v1/auth/me", headers={"Authorization": token})
        assert resp.status_code == 401


class TestIdentityExtraction:
    def test_subject_is_extracted_from_verified_token(self, client, auth_headers):
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["subject"] == TEST_SUBJECT
        assert body["email"] == f"{TEST_SUBJECT}@formen-demo.com"

    def test_configurable_user_id_claim_is_used(self, client, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "oidc_user_id_claim", "employee_id")
        token = make_test_token(extra_claims={"employee_id": "EMP-4242"})
        resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert legacy_json(resp)["subject"] == "EMP-4242"


class TestTokenNotLogged:
    def test_token_never_appears_in_logs_even_on_failure(self, client, caplog):
        token = make_test_token(expires_in=-60)
        with caplog.at_level(logging.DEBUG):
            resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        for record in caplog.records:
            assert token not in record.getMessage()
