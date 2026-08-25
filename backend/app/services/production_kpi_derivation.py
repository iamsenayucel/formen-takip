
from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.foreman import Chief, Foreman
from app.models.organization import Plant, Shift
from app.models.production import ForemanWorkCalendar, Product, ProductionRecord
from app.services.kpi_engine import SHIFT_MINUTES
from app.services.providers.base import RawPerformanceRecord


def derive_agir_gitme(
    measured_gram: float, standard_gram: float, lower_limit: float, upper_limit: float, actual_qty: float
) -> tuple[float, float, float] | None:
    if measured_gram > upper_limit:
        signed_deviation = measured_gram - upper_limit
    elif measured_gram < lower_limit:
        signed_deviation = measured_gram - lower_limit
    else:
        signed_deviation = 0.0
    denominator = standard_gram * actual_qty
    if denominator == 0:
        return None
    numerator = signed_deviation * actual_qty
    return numerator / denominator * 100.0, numerator, denominator


def _kpi_components(record: ProductionRecord, product: Product | None):
    actual_qty = float(record.actual_qty) if record.actual_qty is not None else None
    planned_qty = float(record.planned_qty) if record.planned_qty is not None else None

    if actual_qty is not None and actual_qty != 0:
        if (
            product is not None
            and product.standard_gram is not None
            and product.lower_gram_limit is not None
            and product.upper_gram_limit is not None
            and record.measured_avg_gram is not None
        ):
            result = derive_agir_gitme(
                float(record.measured_avg_gram), float(product.standard_gram),
                float(product.lower_gram_limit), float(product.upper_gram_limit), actual_qty,
            )
            if result is not None:
                actual_value, numerator, denominator = result
                yield ("AGIR_GITME", actual_value, numerator, denominator)

        if record.gsf_qty is not None:
            gsf_qty = float(record.gsf_qty)
            yield ("GSF", gsf_qty / actual_qty * 100.0, gsf_qty, actual_qty)

        if record.iskarta_qty is not None:
            iskarta_qty = float(record.iskarta_qty)
            yield ("ISKARTA", iskarta_qty / actual_qty * 100.0, iskarta_qty, actual_qty)

    if planned_qty is not None and planned_qty != 0 and actual_qty is not None:
        yield ("PLANA_UYUM", actual_qty / planned_qty * 100.0, actual_qty, planned_qty)

    if record.planned_start_at is not None and record.planned_end_at is not None:
        shift_minutes = (record.planned_end_at - record.planned_start_at).total_seconds() / 60.0
        if shift_minutes > 0:
            if record.technical_downtime_minutes is not None and record.manufacturing_downtime_minutes is not None:
                technical_min = float(record.technical_downtime_minutes)
                manufacturing_min = float(record.manufacturing_downtime_minutes)
                included_min = technical_min + manufacturing_min
                yield ("INKITA", included_min / shift_minutes * 100.0, included_min, shift_minutes)

    if record.working_time_minutes is not None:
        working_minutes = float(record.working_time_minutes)
        yield ("OEE", working_minutes / SHIFT_MINUTES * 100.0, working_minutes, SHIFT_MINUTES)


def derive_raw_performance_records(
    db: Session,
    date_from: date,
    date_to: date,
    plant_codes: list[str] | None = None,
    duplicate_rate: float = 0.0,
    rng: random.Random | None = None,
) -> Iterator[RawPerformanceRecord]:
    plants = {p.id: p for p in db.scalars(select(Plant))}
    if plant_codes:
        plant_ids = {p.id for p in plants.values() if p.code in plant_codes}
    else:
        plant_ids = set(plants.keys())
    if not plant_ids:
        return

    chiefs = {c.id: c for c in db.scalars(select(Chief))}
    shifts = {s.id: s for s in db.scalars(select(Shift))}
    foremen = {f.id: f for f in db.scalars(select(Foreman))}
    products = {p.id: p for p in db.scalars(select(Product))}

    working_triples = {
        (row.foreman_id, row.work_date, row.plant_id)
        for row in db.scalars(
            select(ForemanWorkCalendar).where(
                ForemanWorkCalendar.is_working.is_(True),
                ForemanWorkCalendar.work_date >= date_from,
                ForemanWorkCalendar.work_date <= date_to,
            )
        )
    }

    stmt = select(ProductionRecord).where(
        ProductionRecord.production_date >= date_from,
        ProductionRecord.production_date <= date_to,
        ProductionRecord.plant_id.in_(plant_ids),
    )

    for record in db.scalars(stmt):
        if (record.foreman_id, record.production_date, record.plant_id) not in working_triples:
            continue

        plant = plants.get(record.plant_id)
        chief = chiefs.get(record.chief_id)
        shift = shifts.get(record.shift_id)
        foreman = foremen.get(record.foreman_id)
        if not (plant and chief and shift and foreman):
            continue
        product = products.get(record.product_id)

        for kpi_code, actual_value, numerator, denominator in _kpi_components(record, product):
            raw = RawPerformanceRecord(
                source_record_id=f"{record.source_record_id}-{kpi_code}",
                performance_date=record.production_date,
                plant_code=plant.code,
                chief_employee_number=chief.employee_number,
                shift_code=shift.code,
                foreman_employee_number=foreman.employee_number,
                kpi_code=kpi_code,
                actual_value=actual_value,
                unit="%",
                target_value=None,
                numerator_value=numerator,
                denominator_value=denominator,
                source_updated_at=record.source_updated_at,
                production_record_id=record.id,
            )
            yield raw

            if kpi_code != "OEE" and rng is not None and rng.random() < duplicate_rate:
                yield RawPerformanceRecord(
                    source_record_id=f"{raw.source_record_id}-DUP",
                    performance_date=raw.performance_date,
                    plant_code=raw.plant_code,
                    chief_employee_number=raw.chief_employee_number,
                    shift_code=raw.shift_code,
                    foreman_employee_number=raw.foreman_employee_number,
                    kpi_code=raw.kpi_code,
                    actual_value=raw.actual_value,
                    unit=raw.unit,
                    target_value=None,
                    numerator_value=raw.numerator_value,
                    denominator_value=raw.denominator_value,
                    source_updated_at=raw.source_updated_at,
                    production_record_id=raw.production_record_id,
                )
