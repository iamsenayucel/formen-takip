import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from app.core.request_id import REQUEST_ID_HEADER
from app.models.contribution import ContributionWork
from app.models.user import AuditLog

from .conftest import TEST_SUBJECT, make_test_token


@pytest.fixture(autouse=True)
def _cleanup(db_session):
    yield
    db_session.query(ContributionWork).filter(
        ContributionWork.created_by_subject.in_([TEST_SUBJECT, "other-parallel-subject"])
    ).delete(synchronize_session=False)
    db_session.commit()


def _access_records(caplog, path: str):
    return [r for r in caplog.records if r.name == "app.access" and getattr(r, "path", None) == path]


class TestRequestIdCorrelation:
    def test_valid_incoming_request_id_is_reused_in_response_and_log(self, client, caplog):
        rid = f"custom-{uuid.uuid4().hex}"
        with caplog.at_level(logging.INFO):
            resp = client.get("/api/v1/dashboard/summary", headers={REQUEST_ID_HEADER: rid})
        assert resp.status_code == 401
        assert resp.headers[REQUEST_ID_HEADER] == rid

        matches = [r for r in _access_records(caplog, "/api/v1/dashboard/summary") if r.request_id == rid]
        assert matches, "access log did not carry the incoming X-Request-Id"

    def test_missing_request_id_generates_one_used_in_response_and_log(self, client, caplog):
        with caplog.at_level(logging.INFO):
            resp = client.get("/api/v1/dashboard/summary")
        generated = resp.headers[REQUEST_ID_HEADER]
        assert generated

        matches = [r for r in _access_records(caplog, "/api/v1/dashboard/summary") if r.request_id == generated]
        assert matches

    def test_invalid_request_id_header_is_replaced(self, client, caplog):
        with caplog.at_level(logging.INFO):
            resp = client.get("/api/v1/dashboard/summary", headers={REQUEST_ID_HEADER: "not valid! id"})
        generated = resp.headers[REQUEST_ID_HEADER]
        assert generated != "not valid! id"

        matches = [r for r in _access_records(caplog, "/api/v1/dashboard/summary") if r.request_id == generated]
        assert matches


class TestSubjectInAccessLog:
    def test_authenticated_request_logs_subject(self, client, auth_headers, caplog):
        with caplog.at_level(logging.INFO):
            resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200

        matches = [r for r in _access_records(caplog, "/api/v1/auth/me") if r.subject == TEST_SUBJECT]
        assert matches

    def test_auth_bypass_dev_mode_logs_dev_demo_user(self, client, caplog, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "auth_bypass", True)
        monkeypatch.setattr(settings, "environment", "development")

        with caplog.at_level(logging.INFO):
            resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200

        matches = [r for r in _access_records(caplog, "/api/v1/auth/me") if r.subject == "dev-demo-user"]
        assert matches


class TestAccessLogAndAuditLogShareRequestId:
    def test_contribution_create_access_and_audit_logs_share_request_id(
        self, client, auth_headers, db_session, caplog
    ):
        title = f"Logging Correlation {uuid.uuid4()}"
        rid = f"correlate-{uuid.uuid4().hex}"
        headers = {**auth_headers, REQUEST_ID_HEADER: rid}

        with caplog.at_level(logging.INFO):
            resp = client.post("/api/v1/contribution-works", json={"title": title}, headers=headers)
        assert resp.status_code == 201, resp.text

        access_matches = [r for r in _access_records(caplog, "/api/v1/contribution-works") if r.request_id == rid]
        assert access_matches
        assert access_matches[0].subject == TEST_SUBJECT

        audit_matches = [
            r for r in caplog.records
            if r.name == "app.audit" and getattr(r, "action", None) == "operational_impact.created"
            and r.request_id == rid
        ]
        assert audit_matches
        assert audit_matches[0].subject == TEST_SUBJECT

        audit_row = db_session.scalar(
            select(AuditLog).where(AuditLog.action == "operational_impact.created", AuditLog.new_value == title)
        )
        assert audit_row is not None
        assert audit_row.subject == TEST_SUBJECT


class TestErrorResponsesAreLogged:
    def test_401_is_logged_with_request_id_and_warning_level(self, client, caplog):
        rid = f"unauth-{uuid.uuid4().hex}"
        with caplog.at_level(logging.INFO):
            resp = client.get("/api/v1/dashboard/summary", headers={REQUEST_ID_HEADER: rid})
        assert resp.status_code == 401

        matches = [r for r in _access_records(caplog, "/api/v1/dashboard/summary") if r.request_id == rid]
        assert matches
        assert matches[0].levelno == logging.WARNING
        assert matches[0].status_code == 401

    def test_422_validation_error_is_logged_with_request_id(self, client, auth_headers, caplog):
        rid = f"invalid-{uuid.uuid4().hex}"
        headers = {**auth_headers, REQUEST_ID_HEADER: rid}
        with caplog.at_level(logging.INFO):
            resp = client.post("/api/v1/contribution-works", json={}, headers=headers)
        assert resp.status_code == 422

        matches = [r for r in _access_records(caplog, "/api/v1/contribution-works") if r.request_id == rid]
        assert matches
        assert matches[0].levelno == logging.WARNING
        assert matches[0].status_code == 422


class TestNoSensitiveDataInLogs:
    def test_token_and_authorization_header_never_appear_in_logs(self, client, caplog):
        token = make_test_token()
        with caplog.at_level(logging.DEBUG):
            resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        for record in caplog.records:
            rendered = record.getMessage()
            assert token not in rendered
            assert f"Bearer {token}" not in rendered
            for value in vars(record).values():
                if isinstance(value, str):
                    assert token not in value

    def test_expired_token_failure_does_not_leak_token(self, client, caplog):
        token = make_test_token(expires_in=-60)
        with caplog.at_level(logging.DEBUG):
            resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        for record in caplog.records:
            assert token not in record.getMessage()


class TestParallelRequestsDoNotLeakContext:
    def test_two_concurrent_requests_keep_distinct_request_id_and_subject(self, client, caplog):
        token_a = make_test_token(subject=TEST_SUBJECT)
        token_b = make_test_token(subject="other-parallel-subject")
        rid_a = f"parallel-a-{uuid.uuid4().hex}"
        rid_b = f"parallel-b-{uuid.uuid4().hex}"

        def call(token, rid):
            return client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}", REQUEST_ID_HEADER: rid},
            )

        with caplog.at_level(logging.INFO):
            with ThreadPoolExecutor(max_workers=2) as pool:
                future_a = pool.submit(call, token_a, rid_a)
                future_b = pool.submit(call, token_b, rid_b)
                resp_a = future_a.result()
                resp_b = future_b.result()

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.headers[REQUEST_ID_HEADER] == rid_a
        assert resp_b.headers[REQUEST_ID_HEADER] == rid_b

        records = _access_records(caplog, "/api/v1/auth/me")
        by_request_id = {r.request_id: r.subject for r in records if r.request_id in (rid_a, rid_b)}
        assert by_request_id.get(rid_a) == TEST_SUBJECT
        assert by_request_id.get(rid_b) == "other-parallel-subject"
