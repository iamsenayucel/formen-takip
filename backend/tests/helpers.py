from __future__ import annotations

from typing import Any
import re


def unwrap(resp) -> Any:
    body = resp.json()
    assert "error" not in body, f"expected success envelope, got error: {body.get('error')}"
    return body["data"]


def unwrap_page(resp) -> tuple[Any, dict]:
    body = resp.json()
    assert "error" not in body, f"expected success envelope, got error: {body.get('error')}"
    return body["data"], body["pagination"]


def unwrap_error(resp) -> dict:
    body = resp.json()
    assert "error" in body, f"expected error envelope, got: {body}"
    return body["error"]


def _snake_key(value: str) -> str:
    # Map benzeri response alanlarında UUID anahtarları geçerlidir (ör. KPI score
    # sözlükleri); bunlar JSON property adı değil, veridir.
    if re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        value,
    ):
        return value
    value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", value)
    value = re.sub(r"([0-9])([A-Za-z])", r"\1_\2", value)
    value = re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
    return re.sub(r"_+", "_", value)


def _legacy_keys(value: Any) -> Any:
    """Yeni wire contract'ı eski business-karakterizasyon assertion'larına uyarlar.

    Contract testleri doğrudan ``resp.json()`` incelemelidir. Bu adapter yalnızca
    tarihsel snake_case fixture kullanan sayısal/business parity testleri içindir.
    """
    if isinstance(value, list):
        return [_legacy_keys(item) for item in value]
    if isinstance(value, dict):
        return {_snake_key(key): _legacy_keys(item) for key, item in value.items()}
    return value


def legacy_json(resp) -> Any:
    body = resp.json()
    if "error" in body:
        return {"detail": body["error"]["message"]}
    if "data" not in body:
        return _legacy_keys(body)

    data = _legacy_keys(body["data"])
    if "pagination" in body:
        pagination = _legacy_keys(body["pagination"])
        total = pagination.get("total")
        if total is None and not pagination.get("has_more", False):
            total = len(data)
        return {
            "items": data,
            "total": total,
            "next_cursor": pagination.get("next_cursor"),
            "has_more": pagination.get("has_more", False),
        }
    if isinstance(data, list):
        if resp.request.url.path.endswith("/tool-calls"):
            return {"items": data, "total": len(data)}
        return {"items": data}
    return data
