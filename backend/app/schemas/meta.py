from __future__ import annotations

from uuid import UUID

from app.schemas.base import CamelModel


class FactoryOption(CamelModel):
    id: UUID
    code: str
    name: str
    location: str


class PlantOption(CamelModel):
    id: UUID
    code: str
    name: str
    sequence_number: int
    factory_id: UUID


class ChiefOption(CamelModel):
    id: UUID
    employee_number: str
    name: str
    plant_ids: list[str]


class FilterOption(CamelModel):
    id: UUID
    code: str | None = None
    name: str
    sequence: int | None = None
    unit: str | None = None
    weight: float | None = None


class FilterOptionsResponse(CamelModel):
    factories: list[FactoryOption]
    plants: list[PlantOption]
    chiefs: list[ChiefOption]
    shifts: list[FilterOption]
    kpis: list[FilterOption]
