from __future__ import annotations

from datetime import date
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import (
    ContributionWorkNotFoundError,
    ContributionWorkValidationError,
    ForemanNotFoundError,
    fields_from_errors,
)
from app.core.pagination import decode_cursor, encode_cursor, filter_signature
from app.models.contribution import ContributionGain, ContributionWork
from app.models.enums import ContributionRole, ContributionStatus, ContributionWorkType
from app.models.foreman import Foreman
from app.models.organization import Plant
from app.repositories.contribution_work_repository import (
    WORK_TYPE_LABELS,
    ContributionWorkFilters,
    ContributionWorkRepository,
)
from app.schemas.common import CursorParams
from app.schemas.contribution import (
    DATE_RANGE_ERROR,
    ContributionWorkCreate,
    ContributionWorkUpdate,
    check_date_range,
)
from app.services import contribution_calc as calc
from app.services.contribution_pdf import render_contribution_pdf

RecordAudit = Callable[..., object]


def _num(value) -> float | None:
    return float(value) if value is not None else None


class ContributionWorkService:
    """Contribution Works / Operational Impact+ için orkestrasyon.

    Business kararlarını (publish validation, status transition, override,
    audit içeriği) verir ve transaction sınırını (commit) yönetir. Persistence
    işlemlerini `ContributionWorkRepository`'ye, saf hesaplamaları
    `contribution_calc`'a devreder — algoritmaları burada tekrar yazmaz.
    """

    def __init__(self, db: Session, repository: ContributionWorkRepository | None = None):
        self.db = db
        self.repository = repository or ContributionWorkRepository(db)

    # ------------------------------------------------------------------
    # Serialization (mevcut _to_dict ve yardımcıları — API contract birebir korunur)
    # ------------------------------------------------------------------

    def _foreman_ref_dict(self, f: Foreman, role: ContributionRole) -> dict:
        return {"id": str(f.id), "name": f"{f.first_name} {f.last_name}", "employee_number": f.employee_number, "role": role.value}

    def _plant_ref_dict(self, p: Plant) -> dict:
        return {
            "id": str(p.id), "name": p.name, "code": p.code,
            "factory_id": str(p.factory_id), "factory_name": p.factory.name, "factory_code": p.factory.code,
        }

    def _gain_to_dict(self, g: ContributionGain) -> dict:
        return {
            "id": str(g.id),
            "gain_type": g.gain_type.value,
            "gain_type_label": calc.gain_type_label(g.gain_type),
            "gain_type_other_note": g.gain_type_other_note,
            "previous_value": _num(g.previous_value),
            "next_value": _num(g.next_value),
            "change_amount": _num(g.change_amount),
            "change_percent": _num(g.change_percent),
            "is_improvement": calc.is_improvement(g.gain_type, g.change_amount),
            "unit": g.unit,
            "measurement_period": g.measurement_period,
            "description": g.description,
        }

    def _before_after(self, work: ContributionWork) -> dict | None:
        if work.previous_duration is None or work.new_duration is None:
            return None
        unit_label = {"second": "saniye", "minute": "dakika", "hour": "saat"}.get(
            work.duration_unit.value if work.duration_unit else "minute", "dakika"
        )
        previous_duration, new_duration = float(work.previous_duration), float(work.new_duration)
        saving = calc.compute_time_saving(previous_duration, new_duration)
        return {
            "metric_label": "Süre Karşılaştırması",
            "before": f"{previous_duration} {unit_label}",
            "after": f"{new_duration} {unit_label}",
            "change": f"-{saving} {unit_label}" if saving is not None else "İyileşme yok",
            "is_improvement": saving is not None,
        }

    def to_dict(
        self,
        work: ContributionWork,
        gains: list[ContributionGain] | None = None,
        foremen: list[dict] | None = None,
        plants: list[dict] | None = None,
    ) -> dict:
        if gains is None:
            gains = self.repository.get_gains(work.id)
        if foremen is None:
            foremen = [self._foreman_ref_dict(f, role) for f, role in self.repository.foreman_refs(work.id)]
        if plants is None:
            plants = [self._plant_ref_dict(p) for p in self.repository.plant_refs(work.id)]

        return {
            "id": str(work.id),
            "title": work.title,
            "status": work.status.value,
            "work_type": work.work_type.value if work.work_type else None,
            "work_type_label": WORK_TYPE_LABELS.get(work.work_type) if work.work_type else None,
            "work_type_other_note": work.work_type_other_note,
            "summary": work.summary,
            "detailed_description": work.detailed_description,
            "problem_description": work.problem_description,
            "solution_description": work.solution_description,
            "result_description": work.result_description,
            "foremen": foremen,
            "plants": plants,
            "work_date": work.work_date.isoformat() if work.work_date else None,
            "work_date_end": work.work_date_end.isoformat() if work.work_date_end else None,
            "impact_level": work.impact_level.value if work.impact_level else None,
            "created_by": work.created_by_subject,
            "published_at": work.published_at.isoformat() if work.published_at else None,
            "is_standardized": work.is_standardized,
            "is_applicable_other_plants": work.is_applicable_other_plants,
            "is_permanent_solution": work.is_permanent_solution,
            "work_instruction_updated": work.work_instruction_updated,
            "financial_gain_status": work.financial_gain_status.value,
            "gain_amount": _num(work.gain_amount),
            "currency": work.currency.value if work.currency else None,
            "gain_period": work.gain_period.value if work.gain_period else None,
            "calculation_method": work.calculation_method,
            "previous_duration": _num(work.previous_duration),
            "new_duration": _num(work.new_duration),
            "duration_unit": work.duration_unit.value if work.duration_unit else None,
            "per_occurrence_saving": _num(work.per_occurrence_saving),
            "repeat_period": work.repeat_period.value if work.repeat_period else None,
            "repeat_count": _num(work.repeat_count),
            "monthly_total_saving_minutes": _num(work.monthly_total_saving_minutes),
            "gains": [self._gain_to_dict(g) for g in gains],
            "highlighted_gain_mode": work.highlighted_gain_mode.value,
            "highlighted_gain_ref": work.highlighted_gain_ref,
            "highlighted_gain": calc.resolve_highlighted_gain(work, gains),
            "before_after": self._before_after(work),
            "badges": calc.resolve_badges(work),
            "contribution_score": work.contribution_score,
            "contribution_score_label": calc.CONTRIBUTION_SCORE_LABELS.get(work.contribution_score) if work.contribution_score else None,
            "contribution_score_breakdown": calc.compute_contribution_score(work, gains)[1],
            "created_at": work.created_at.isoformat(),
            "updated_at": work.updated_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Business helpers (mevcut davranış, yalnızca taşındı)
    # ------------------------------------------------------------------

    def _publish_check_data(self, work: ContributionWork, foreman_ids: list[UUID], plant_ids: list[UUID]) -> dict:
        return {
            "title": work.title,
            "foreman_ids": foreman_ids,
            "plant_ids": plant_ids,
            "work_date": work.work_date,
            "work_date_end": work.work_date_end,
            "work_type": work.work_type,
            "work_type_other_note": work.work_type_other_note,
            "summary": work.summary,
            "problem_description": work.problem_description,
            "solution_description": work.solution_description,
        }

    def _apply_derived_fields(self, work: ContributionWork, overridden_fields: set[str]) -> None:
        if "per_occurrence_saving" not in overridden_fields:
            work.per_occurrence_saving = calc.compute_time_saving(work.previous_duration, work.new_duration)
        if "monthly_total_saving_minutes" not in overridden_fields:
            per_occurrence_minutes = calc.duration_to_minutes(work.per_occurrence_saving, work.duration_unit)
            work.monthly_total_saving_minutes = calc.compute_monthly_total(
                per_occurrence_minutes, work.repeat_period, work.repeat_count
            )

    def _recompute_score(self, work: ContributionWork) -> None:
        gains = self.repository.get_gains(work.id)
        work.contribution_score = calc.compute_contribution_score(work, gains)[0]

    @staticmethod
    def _overridden_duration_fields(payload) -> set[str]:
        return {
            f for f in ("per_occurrence_saving", "monthly_total_saving_minutes")
            if f in payload.model_fields_set and getattr(payload, f) is not None
        }

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def list_works(
        self,
        *,
        date_from, date_to, plant_ids, factory_ids, foreman_ids,
        work_type, status, impact_level, financial_gain_status, search,
        sort_by: str, sort_dir: str, page: CursorParams,
    ) -> dict:
        filters = ContributionWorkFilters(
            date_from=date_from, date_to=date_to, plant_ids=plant_ids, factory_ids=factory_ids,
            foreman_ids=foreman_ids, work_type=work_type, status=status, impact_level=impact_level,
            financial_gain_status=financial_gain_status, search=search,
        )
        filter_sig = filter_signature(
            date_from, date_to, plant_ids, factory_ids, foreman_ids,
            work_type, status, impact_level, financial_gain_status, search,
        )
        cursor_value = None
        cursor_id = None
        if page.cursor is not None:
            state = decode_cursor(page.cursor, sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig)
            cursor_value = state.sort_value
            cursor_id = UUID(state.id)

        rows = self.repository.list_page(
            filters, sort_by=sort_by, sort_dir=sort_dir,
            cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit,
        )
        has_more = len(rows) > page.limit
        page_rows = rows[: page.limit]
        page_works = [w for w, _ in page_rows]

        work_ids = [w.id for w in page_works]
        gains_by_work = self.repository.batch_gains(work_ids)
        foremen_by_work = self.repository.batch_foreman_refs(work_ids)
        plants_by_work = self.repository.batch_plant_refs(work_ids)

        next_cursor = None
        if has_more and page_rows:
            last_work, last_sort_value = page_rows[-1]
            next_cursor = encode_cursor(
                sort_by=sort_by, sort_dir=sort_dir, filter_sig=filter_sig,
                sort_value=last_sort_value, id_=str(last_work.id),
            )

        return {
            "items": [
                self.to_dict(
                    w,
                    gains=gains_by_work.get(w.id, []),
                    foremen=[self._foreman_ref_dict(f, role) for f, role in foremen_by_work.get(w.id, [])],
                    plants=[self._plant_ref_dict(p) for p in plants_by_work.get(w.id, [])],
                )
                for w in page_works
            ],
            "next_cursor": next_cursor, "has_more": has_more,
        }

    def summary(
        self,
        *,
        date_from, date_to, plant_ids, factory_ids, foreman_ids,
        work_type, status, impact_level, financial_gain_status, search,
    ) -> dict:
        filters = ContributionWorkFilters(
            date_from=date_from, date_to=date_to, plant_ids=plant_ids, factory_ids=factory_ids,
            foreman_ids=foreman_ids, work_type=work_type, status=status, impact_level=impact_level,
            financial_gain_status=financial_gain_status, search=search,
        )
        agg = self.repository.summary_aggregates(filters)

        by_type: dict[str, int] = {}
        for work_type_value, count in agg.by_type:
            wt = work_type_value if isinstance(work_type_value, ContributionWorkType) else ContributionWorkType(work_type_value)
            by_type[WORK_TYPE_LABELS[wt]] = count

        total = agg.total
        standardized_ratio = round((agg.standardized_count / total) * 100, 1) if total else 0.0

        return {
            "total_works": total,
            "added_this_month": agg.this_month,
            "total_gain_amount": round(float(agg.total_gain_amount), 2),
            "total_monthly_time_saving_minutes": round(float(agg.total_monthly_time_saving), 2),
            "by_plant": [
                {"name": name, "count": count} for name, count in sorted(agg.by_plant, key=lambda row: row[1], reverse=True)
            ],
            "by_work_type": [
                {"label": k, "count": v} for k, v in sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)
            ],
            "top_foremen": [
                {"id": str(fid), "name": f"{first} {last}", "count": count} for fid, first, last, count in agg.top_foremen
            ],
            "applicable_other_plants_count": agg.applicable_other_plants_count,
            "standardized_ratio": standardized_ratio,
        }

    def get(self, work_id: UUID) -> dict:
        work = self.repository.get(work_id)
        if work is None:
            raise ContributionWorkNotFoundError("Çalışma kaydı bulunamadı.")
        return self.to_dict(work)

    def pdf(self, work_id: UUID) -> tuple[bytes, str]:
        work = self.repository.get(work_id)
        if work is None:
            raise ContributionWorkNotFoundError("Çalışma kaydı bulunamadı.")
        pdf_bytes = render_contribution_pdf(self.to_dict(work))
        file_name = f"operational-impact-plus_{work.id}.pdf"
        return pdf_bytes, file_name

    # ------------------------------------------------------------------
    # Writes — transaction sınırı burada: mutation -> flush -> audit -> commit
    # ------------------------------------------------------------------

    def create(
        self, payload: ContributionWorkCreate, *, subject: str, ip_address: str | None, record_audit: RecordAudit
    ) -> dict:
        if payload.status == ContributionStatus.PUBLISHED:
            errors = calc.validate_for_publish(payload.model_dump())
            if errors:
                raise ContributionWorkValidationError(
                    "Yayımlamak için zorunlu alanlar eksik.", details=fields_from_errors(errors),
                )

        work = ContributionWork(
            title=payload.title, status=payload.status,
            work_type=payload.work_type, work_type_other_note=payload.work_type_other_note,
            summary=payload.summary, detailed_description=payload.detailed_description,
            problem_description=payload.problem_description, solution_description=payload.solution_description,
            result_description=payload.result_description,
            work_date=payload.work_date, work_date_end=payload.work_date_end,
            impact_level=payload.impact_level, created_by_subject=subject,
            is_standardized=payload.is_standardized, is_applicable_other_plants=payload.is_applicable_other_plants,
            is_permanent_solution=payload.is_permanent_solution, work_instruction_updated=payload.work_instruction_updated,
            financial_gain_status=payload.financial_gain_status,
            gain_amount=payload.gain_amount,
            currency=payload.currency, gain_period=payload.gain_period, calculation_method=payload.calculation_method,
            previous_duration=payload.previous_duration, new_duration=payload.new_duration,
            duration_unit=payload.duration_unit, repeat_period=payload.repeat_period, repeat_count=payload.repeat_count,
            per_occurrence_saving=payload.per_occurrence_saving, monthly_total_saving_minutes=payload.monthly_total_saving_minutes,
            highlighted_gain_mode=payload.highlighted_gain_mode, highlighted_gain_ref=payload.highlighted_gain_ref,
            published_at=clock.now_utc() if payload.status == ContributionStatus.PUBLISHED else None,
        )
        self._apply_derived_fields(work, self._overridden_duration_fields(payload))
        self.repository.add(work)
        self.repository.flush()

        self.repository.sync_foremen(work.id, payload.foreman_ids)
        self.repository.sync_plants(work.id, payload.plant_ids)
        self.repository.sync_gains(work.id, payload.gains)
        self.repository.flush()
        self._recompute_score(work)

        record_audit(
            self.db, subject, "contribution_work_created", entity="contribution_work",
            new_value=payload.title, ip_address=ip_address,
        )

        self.db.commit()
        self.repository.refresh(work)
        return self.to_dict(work)

    def update(
        self,
        work_id: UUID,
        payload: ContributionWorkUpdate,
        *,
        subject: str,
        ip_address: str | None,
        record_audit: RecordAudit,
    ) -> dict:
        work = self.repository.get(work_id)
        if work is None:
            raise ContributionWorkNotFoundError("Çalışma kaydı bulunamadı.")

        updates = payload.model_dump(exclude_unset=True, exclude={"foreman_ids", "plant_ids", "gains"})

        if "work_date" in updates or "work_date_end" in updates:
            merged_work_date = updates.get("work_date", work.work_date)
            merged_work_date_end = updates.get("work_date_end", work.work_date_end)
            try:
                check_date_range(merged_work_date, merged_work_date_end)
            except ValueError:
                raise ContributionWorkValidationError(
                    DATE_RANGE_ERROR, details=fields_from_errors({"work_date_end": DATE_RANGE_ERROR}),
                )

        is_publishing = updates.get("status") == ContributionStatus.PUBLISHED and work.status != ContributionStatus.PUBLISHED
        if updates.get("status") == ContributionStatus.PUBLISHED:
            current_foreman_ids = (
                payload.foreman_ids if payload.foreman_ids is not None
                else self.repository.foreman_ids(work_id)
            )
            current_plant_ids = (
                payload.plant_ids if payload.plant_ids is not None
                else self.repository.plant_ids(work_id)
            )
            relevant_keys = set(calc.REQUIRED_FOR_PUBLISH_MESSAGES) | {"work_date_end"}
            merged = {
                **self._publish_check_data(work, current_foreman_ids, current_plant_ids),
                **{k: v for k, v in updates.items() if k in relevant_keys},
            }
            merged["foreman_ids"] = current_foreman_ids
            merged["plant_ids"] = current_plant_ids
            errors = calc.validate_for_publish(merged)
            if errors:
                raise ContributionWorkValidationError(
                    "Yayımlamak için zorunlu alanlar eksik.", details=fields_from_errors(errors),
                )

        changes: list[str] = []
        for field, new_value in updates.items():
            old_value = getattr(work, field)
            old_str = old_value.value if hasattr(old_value, "value") else str(old_value)
            new_str = new_value.value if hasattr(new_value, "value") else str(new_value)
            if old_str != new_str:
                changes.append(f"{field}: {old_str} -> {new_str}")
            setattr(work, field, new_value)

        if is_publishing:
            work.published_at = clock.now_utc()

        self.repository.sync_foremen(work.id, payload.foreman_ids)
        self.repository.sync_plants(work.id, payload.plant_ids)
        self.repository.sync_gains(work.id, payload.gains)
        self._apply_derived_fields(work, self._overridden_duration_fields(payload))
        self.repository.flush()
        self._recompute_score(work)

        if changes or payload.foreman_ids is not None or payload.plant_ids is not None or payload.gains is not None:
            record_audit(
                self.db, subject, "contribution_work_updated", entity="contribution_work",
                old_value=None, new_value="; ".join(changes) or "foremen/gains updated",
                ip_address=ip_address,
            )

        self.db.commit()
        self.repository.refresh(work)
        return self.to_dict(work)

    def delete(self, work_id: UUID, *, subject: str, ip_address: str | None, record_audit: RecordAudit) -> None:
        work = self.repository.get(work_id)
        if work is None:
            raise ContributionWorkNotFoundError("Çalışma kaydı bulunamadı.")

        title = work.title
        self.repository.delete(work)
        self.repository.flush()

        record_audit(
            self.db, subject, "contribution_work_deleted", entity="contribution_work",
            old_value=title, ip_address=ip_address,
        )

        self.db.commit()

    # ------------------------------------------------------------------
    # Formen kapsamlı Operational Impact+ özeti; read-only, transaction yok
    # ------------------------------------------------------------------

    def foreman_summary(self, foreman_id: UUID) -> dict:
        if self.db.get(Foreman, foreman_id) is None:
            raise ForemanNotFoundError("Formen bulunamadı.")

        rows = self.repository.published_works_for_foreman(foreman_id)

        empty = {
            "total_contributions": 0, "smed_count": 0, "led_contributions": 0,
            "financial_gain": {},
            "total_time_saving_minutes": 0.0, "last_contribution_date": None,
        }
        if not rows:
            return empty

        work_ids = [work.id for work, _ in rows]
        participant_counts = self.repository.participant_counts(work_ids)

        smed_count = 0
        led_count = 0
        financial: dict[str, float] = {}
        total_time_saving = 0.0
        last_date: date | None = None

        for work, role in rows:
            share = 1 / participant_counts.get(work.id, 1)
            if work.work_type == ContributionWorkType.SMED:
                smed_count += 1
            if role == ContributionRole.LEAD:
                led_count += 1
            if work.gain_amount is not None and work.currency is not None:
                key = work.currency.value
                financial[key] = financial.get(key, 0.0) + float(work.gain_amount) * share
            if work.monthly_total_saving_minutes is not None:
                total_time_saving += float(work.monthly_total_saving_minutes) * share
            work_date = work.work_date or (work.published_at.date() if work.published_at else None)
            if work_date and (last_date is None or work_date > last_date):
                last_date = work_date

        return {
            "total_contributions": len(rows),
            "smed_count": smed_count,
            "led_contributions": led_count,
            "financial_gain": {k: round(v, 2) for k, v in financial.items()},
            "total_time_saving_minutes": round(total_time_saving, 2),
            "last_contribution_date": last_date.isoformat() if last_date else None,
        }
