# Tier1 API contract — reference for updating integration tests

This backend just migrated its whole `/api/v1` JSON contract. Read this fully before touching
any test file. Do not guess field names — cross-check against the actual Pydantic schema file
named for each response when unsure (paths given below).

## 1. Envelope

Every response is one of exactly two shapes, never both:

- Success: `{"data": <payload>}` — for a list endpoint, `<payload>` is itself an array (not
  wrapped in another `items` key), and there is a sibling `pagination` key (see §3).
- Error: `{"error": {"code": "...", "message": "...", "requestId": "...", "timestamp": "...",
  "details": null | {...}}}`.

`resp.json()["detail"]` no longer exists anywhere. Use the helpers in `tests/helpers.py`:

```python
from tests.helpers import unwrap, unwrap_page, unwrap_error

data = unwrap(resp)                    # non-paginated success: returns resp.json()["data"]
items, pagination = unwrap_page(resp)  # paginated success: returns (data, pagination) tuple
error = unwrap_error(resp)             # error response: returns resp.json()["error"]
```

`X-Request-Id` is present on every response (success and error) as a response header, and
matches `error["requestId"]` on error responses.

## 2. camelCase

Every JSON field in every response body (and every request body field, though request bodies
also still accept the old snake_case key as an alias — no need to change existing test
`POST`/`PATCH`/`PUT` payload dicts) is camelCase. Response field access must change from
`body["items"][0]["foreman_id"]` to `data[0]["foremanId"]`, etc. This is the single biggest
mechanical change: every snake_case dict-key access on a response body becomes camelCase.
Query string parameter *names* did NOT change (still snake_case, e.g. `?date_from=...`,
`?plant_id=...`) — only JSON body field names changed.

## 3. Pagination — cursor, not page/page_size

Query params: `cursor` (opaque string, omit for first page) and `limit` (replaces `page_size`;
default 25, max 200). `page` no longer exists as a query param.

Response `pagination` object: `{"nextCursor": str | null, "hasMore": bool, "total": int | null}`.

`total` is populated **only** for these list endpoints (bounded/cheap-to-count org data):
`GET /plants`, `GET /chiefs`, `GET /foremen`, `GET /plants/{id}/foremen`.
For all other paginated endpoints (`GET /contribution-works`, `GET /anomalies`,
`GET /reports`) `total` is always `null` — do not assert an exact total for these; assert on
`hasMore`/page contents/count of items returned instead. If an old test asserted an exact
`total` count against one of these three (contribution-works/anomalies/reports), rewrite the
assertion to not depend on total (e.g. assert the returned item count for a `limit` large
enough to cover the seeded fixture data, or assert `hasMore is False` when that's true, or
independently query total count from the DB directly in the test if the test's whole point is
counting).

`nextCursor` is an opaque base64 string — never parse or construct one by hand in a test.
Get a real one from a prior response's `pagination["nextCursor"]` and pass it back as the
`cursor` query param for a "next page" test.

Sort params (`sort_by`, `sort_dir` — still snake_case query params, unchanged names) are
whitelisted per endpoint exactly as before, no changes there.

## 4. Error codes (replace all `["detail"] == "..."` string assertions)

Assert on `error["code"]` (a stable UPPER_SNAKE_CASE string), not on `error["message"]` (a
Turkish human sentence — still assertable if a test specifically wants to check the message
text, but code is preferred and more robust). Full taxonomy, defined in
`app/core/errors.py`:

- 401: `UNAUTHORIZED`
- 404: `FOREMAN_NOT_FOUND`, `FOREMAN_KPI_RECORD_NOT_FOUND`, `CHIEF_NOT_FOUND`,
  `PLANT_NOT_FOUND`, `KPI_NOT_FOUND`, `ANOMALY_NOT_FOUND`, `ANOMALY_ANALYSIS_NOT_FOUND`,
  `CONTRIBUTION_WORK_NOT_FOUND`, `REPORT_NOT_FOUND`, `MONTHLY_REPORT_NOT_FOUND`,
  `SHIFT_ANALYSIS_NOT_FOUND`
- 400: `INVALID_CURSOR`, `INVALID_MONTH_PARAMETER`, `INVALID_REPORT_PERIOD`, `BAD_REQUEST`
- 409: `ANOMALY_ANALYSIS_IN_PROGRESS`, `CONFLICT`
- 422: `VALIDATION_ERROR` (both FastAPI/Pydantic request validation AND the old structured
  contribution-work publish-validation errors use this code now), `CONTRIBUTION_WORK_VALIDATION_FAILED`
- 429: `RATE_LIMIT_EXCEEDED` (response also carries a `Retry-After` header)
- 502: `MONTHLY_REPORT_PDF_GENERATION_FAILED`, `MONTHLY_REPORT_ACCESS_UNAVAILABLE`
- 500: `INTERNAL_ERROR`

For 422 validation errors (both framework-level `RequestValidationError` and the
contribution-work structured publish-validation), `error["details"]["fields"]` is a list of
`{"field": "camelCaseFieldName", "reason": "...", "code"?: "..."}` objects — this replaces the
old `resp.json()["detail"]["errors"]` dict-of-`{field: reason}`. E.g. old:
`assert resp.json()["detail"]["errors"]["foreman_ids"] == "..."` becomes checking that some
entry in `error["details"]["fields"]` has `"field": "foremanIds"` with the expected `reason`.

## 5. Rate limiting — test env is exempt

`app.core.rate_limit` disables all limiting automatically when `settings.environment == "test"`
(which the ephemeral test DB fixture already sets). No test changes needed for this; high
request-volume tests (e.g. `test_n_plus_one_regression.py`) are unaffected. Do not add
rate-limit assertions to unrelated tests — rate limiting has its own new dedicated test file
elsewhere, not your concern.

## 6. What did NOT change

- Business/computed values (scores, ranks, levels, KPI math) are byte-identical to before —
  if a test's *numeric* assertion starts failing after you update field names/envelope, that
  is a real regression, stop and flag it rather than "fixing" the expected value.
- HTTP status codes for existing scenarios (404 stays 404, 422 stays 422, etc.) are unchanged
  — only the response *body shape* and, in a few cases, which exact code fires (see §4) changed.
- Auth flow, request bodies you already send (snake_case keys still validate — see §2), test
  fixtures (`client`, `db_session`, `auth_headers`, seed data helpers) are all unchanged.

## 7. Concrete before/after example

Old:
```python
resp = client.get("/api/v1/plants", params={"page": 1, "page_size": 5})
body = resp.json()
assert body["total"] == 50
assert len(body["items"]) == 5
assert body["items"][0]["total_score"] == 94.2
```
New:
```python
resp = client.get("/api/v1/plants", params={"limit": 5})
data, pagination = unwrap_page(resp)
assert pagination["total"] == 50
assert len(data) == 5
assert data[0]["totalScore"] == 94.2
```

Old:
```python
resp = client.get(f"/api/v1/plants/{bad_id}")
assert resp.status_code == 404
assert resp.json()["detail"] == "Tesis bulunamadı."
```
New:
```python
resp = client.get(f"/api/v1/plants/{bad_id}")
assert resp.status_code == 404
assert unwrap_error(resp)["code"] == "PLANT_NOT_FOUND"
```

## 8. Response schema files (source of truth for exact field names)

If unsure whether a field exists / its exact camelCase spelling, check the matching Pydantic
model (Python field names are snake_case in the file; the JSON key is the automatic camelCase
conversion, e.g. `total_score` -> `totalScore`, `is_reliable` -> `isReliable`):

- `app/schemas/dashboard.py`, `app/schemas/plant.py`, `app/schemas/foreman.py`,
  `app/schemas/chief.py`, `app/schemas/kpi.py`, `app/schemas/report.py`,
  `app/schemas/shift_analysis.py`, `app/schemas/monthly_report.py`, `app/schemas/meta.py`,
  `app/schemas/auth.py`, `app/schemas/contribution.py`, `app/schemas/anomaly.py`,
  `app/schemas/anomaly_investigation.py`, `app/schemas/base.py` (envelope/cursor primitives).

## 9. Do not touch

Do not modify anything under `app/`, only test files. Do not change test fixtures in
`tests/integration/conftest.py` or `tests/integration/_ephemeral_db.py`. Do not change
assertions about business/numeric values — only the transport shape around them.
