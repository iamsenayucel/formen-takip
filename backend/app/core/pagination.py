from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import and_, column, or_, values
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Values
from sqlalchemy.types import TypeEngine

from app.core.errors import InvalidCursorError

_CURSOR_VERSION = 1


def filter_signature(*parts: Any) -> str:
    raw = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _encode_value(value: Any) -> list[Any]:
    if value is None:
        return ["null", None]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, Enum):
        return ["str", str(value.value)]
    if isinstance(value, UUID):
        return ["str", str(value)]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, (float, Decimal)):
        return ["float", float(value)]
    return ["str", str(value)]


def _decode_value(tag: str, raw: Any) -> Any:
    if tag == "null":
        return None
    if tag in ("bool", "int", "float", "str"):
        return raw
    if tag == "date":
        return date.fromisoformat(raw)
    if tag == "datetime":
        return datetime.fromisoformat(raw)
    raise InvalidCursorError("Geçersiz sayfalama belirteci.")


@dataclass
class CursorState:
    sort_by: str
    sort_dir: str
    filter_sig: str
    sort_value: Any
    id: str


def encode_cursor(*, sort_by: str, sort_dir: str, filter_sig: str, sort_value: Any, id_: str) -> str:
    tag, raw_value = _encode_value(sort_value)
    payload = {"v": _CURSOR_VERSION, "sortBy": sort_by, "sortDir": sort_dir, "filterSig": filter_sig,
               "sortValueTag": tag, "sortValue": raw_value, "id": str(id_)}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return encoded.decode("ascii").rstrip("=")


def decode_cursor(cursor: str, *, sort_by: str, sort_dir: str, filter_sig: str) -> CursorState:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        if payload.get("v") != _CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        sort_value = _decode_value(payload["sortValueTag"], payload["sortValue"])
        state = CursorState(
            sort_by=payload["sortBy"], sort_dir=payload["sortDir"], filter_sig=payload["filterSig"],
            sort_value=sort_value, id=payload["id"],
        )
    except (
        ValueError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise InvalidCursorError("Geçersiz sayfalama belirteci.") from exc

    if state.sort_by != sort_by or state.sort_dir != sort_dir or state.filter_sig != filter_sig:
        raise InvalidCursorError(
            "Sayfalama belirteci geçerli filtre/sıralama bağlamıyla uyuşmuyor, lütfen listeyi baştan yükleyin."
        )
    return state


def keyset_after(
    col: ColumnElement, direction: str, cursor_value: Any, id_col: ColumnElement, cursor_id: Any,
) -> ColumnElement:
    id_gt = id_col > cursor_id
    if direction == "asc":
        if cursor_value is None:
            return or_(col.is_not(None), and_(col.is_(None), id_gt))
        return or_(col > cursor_value, and_(col == cursor_value, id_gt))
    if cursor_value is None:
        return and_(col.is_(None), id_gt)
    return or_(col < cursor_value, and_(col == cursor_value, id_gt), col.is_(None))


def cursor_envelope(result: dict) -> dict:
    return {
        "data": result["items"],
        "pagination": {
            "next_cursor": result.get("next_cursor"),
            "has_more": result["has_more"],
            "total": result.get("total"),
        },
    }


def sort_value_source(
    id_type: TypeEngine, value_type: TypeEngine, values_by_id: dict, *, name: str
) -> Values | None:
    if not values_by_id:
        return None
    return values(column("id", id_type), column("sort_value", value_type), name=name).data(
        list(values_by_id.items())
    )
