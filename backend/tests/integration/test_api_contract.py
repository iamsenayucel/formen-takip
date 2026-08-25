from __future__ import annotations

import re


def _assert_component_properties_are_camel_case(value):
    if isinstance(value, list):
        for item in value:
            _assert_component_properties_are_camel_case(item)
        return
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if key == "properties":
            assert all("_" not in property_name for property_name in item), item
        _assert_component_properties_are_camel_case(item)


def test_request_id_is_preserved_on_success(client):
    request_id = "contract-test-request-id"
    response = client.get("/health/live", headers={"X-Request-Id": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == request_id
    assert response.json() == {"data": {"status": "ok", "database": None}}


def test_validation_error_uses_standard_envelope_and_camel_field(client, auth_headers):
    response = client.get(
        "/api/v1/plants",
        params={"date_from": "not-a-date"},
        headers={**auth_headers, "X-Request-Id": "validation-request"},
    )

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["requestId"] == "validation-request"
    assert body["error"]["details"]["fields"][0]["field"] == "dateFrom"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T.*", body["error"]["timestamp"])


def test_cursor_is_opaque_continuation_and_rejects_filter_mismatch(client, auth_headers):
    malformed = client.get(
        "/api/v1/plants",
        params={"cursor": "a"},
        headers=auth_headers,
    )
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "INVALID_CURSOR"

    first = client.get(
        "/api/v1/plants",
        params={"limit": 2, "sort_by": "sequence", "sort_dir": "asc"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert set(first_body) == {"data", "pagination"}
    assert len(first_body["data"]) == 2
    cursor = first_body["pagination"]["nextCursor"]
    assert cursor and first_body["pagination"]["hasMore"] is True

    second = client.get(
        "/api/v1/plants",
        params={"limit": 2, "sort_by": "sequence", "sort_dir": "asc", "cursor": cursor},
        headers=auth_headers,
    )
    assert second.status_code == 200
    assert {item["id"] for item in first_body["data"]}.isdisjoint(
        {item["id"] for item in second.json()["data"]}
    )

    mismatch = client.get(
        "/api/v1/plants",
        params={"limit": 2, "sort_by": "name", "sort_dir": "asc", "cursor": cursor},
        headers=auth_headers,
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["error"]["code"] == "INVALID_CURSOR"


def test_openapi_documents_contract_models_and_headers(client):
    schema = client.get("/openapi.json").json()
    assert "ErrorEnvelope" in schema["components"]["schemas"]
    _assert_component_properties_are_camel_case(schema["components"]["schemas"])

    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            parameter_names = {parameter["name"] for parameter in operation.get("parameters", [])}
            assert "page" not in parameter_names
            assert "page_size" not in parameter_names
            for response in operation["responses"].values():
                assert "X-Request-Id" in response.get("headers", {}), (path, method)
            if path.startswith("/api/v1"):
                error_schema = operation["responses"]["422"]["content"]["application/json"]["schema"]
                assert error_schema == {"$ref": "#/components/schemas/ErrorEnvelope"}
                assert "Retry-After" in operation["responses"]["429"]["headers"]
