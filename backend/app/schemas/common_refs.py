from __future__ import annotations

from uuid import UUID

from app.schemas.base import CamelModel


class PerformanceLevel(CamelModel):
    name: str
    description: str
    color: str
    icon: str
    outstanding_performance: bool | None = None


class EntityRef(CamelModel):
    id: UUID
    name: str | None
    code: str | None = None
    score: float | None = None


class IdName(CamelModel):
    id: UUID
    name: str


class IdCodeName(CamelModel):
    id: UUID
    code: str
    name: str


class IdNameCount(CamelModel):
    id: UUID
    name: str
    count: int
