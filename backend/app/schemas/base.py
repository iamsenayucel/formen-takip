from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ApiResponse(CamelModel, Generic[T]):
    data: T


class CursorMeta(CamelModel):
    next_cursor: str | None = None
    has_more: bool
    total: int | None = None


class CursorResponse(CamelModel, Generic[T]):
    data: list[T]
    pagination: CursorMeta


class ApiError(CamelModel):
    code: str
    message: str
    request_id: str
    timestamp: datetime
    details: dict[str, Any] | None = None


class ErrorEnvelope(CamelModel):
    error: ApiError
