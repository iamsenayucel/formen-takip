from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import AnomalyAnalysisNotFoundError, AnomalyNotFoundError
from app.core.pagination import decode_cursor, encode_cursor, filter_signature
from app.models.anomaly import Anomaly, AnomalyAnalysis, AnomalyToolCall
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.repositories.anomaly_repository import AnomalyListQueryParams, AnomalyRepository
from app.schemas.common import CursorParams
from app.services.anomaly_context import build_analysis_package
from app.services.anomaly_investigation import resolve_kpi_target
from app.services.anomaly_kpi_defs import (
    ANALYSIS_STATUS_LABELS,
    ANOMALY_TYPE_LABELS,
    KPI_DEFINITIONS,
    SEVERITY_LABELS,
    STATUS_LABELS,
)

_TOOL_LABELS = {
    "get_anomaly_details": "Tespit Detayları", "get_kpi_history": "KPI Geçmişi",
    "compare_shifts": "Vardiya Performansı Karşılaştırması", "compare_plants": "Tesisler Arası Karşılaştırma",
    "get_related_kpis": "İlişkili KPI Değişimleri", "get_downtime_breakdown": "Duruş Nedenleri İncelemesi",
    "get_maintenance_signals": "Bakım ve Arıza Sinyalleri", "get_product_mix": "Ürün Dağılımı İncelemesi",
    "get_changeover_records": "Ürün Değişim Kayıtları", "get_shift_notes": "Vardiya Notları İncelemesi",
    "find_similar_anomalies": "Benzer Geçmiş Tespitler",
}


def _num(value) -> float | None:
    return float(value) if value is not None else None


class AnomalyReadService:
    """Anomalies Catalog Reads + Detail/Analysis Reads orchestration'ı.

    `GET /anomalies`, `GET /anomalies/summary`, `GET /anomalies/{id}`,
    `GET /anomalies/{id}/analysis`, `GET /analyses/{id}`,
    `GET /analyses/{id}/tool-calls` bu servis üzerinden akar. Repository
    çağrılarını koordine eder, ilişkili boyut lookup'larını (plant/factory/
    shift/KPI/foreman) toplu olarak map eder ve mevcut response şeklini üretir.
    Investigation/analyze/reanalyze/status/audit/LLM/concurrency bu servisin
    kapsamı dışındadır — target_resolver ve anomaly_context.build_analysis_package
    içindeki mevcut davranış/DB erişim şekli değiştirilmeden, olduğu gibi çağrılır.
    """

    def __init__(self, db: Session, repository: AnomalyRepository | None = None):
        self.db = db
        self.repository = repository or AnomalyRepository(db)

    def list_anomalies(self, params: AnomalyListQueryParams, page: CursorParams) -> dict:
        filter_sig = filter_signature(params)
        cursor_value = None
        cursor_id = None
        if page.cursor is not None:
            state = decode_cursor(page.cursor, sort_by="detected_at", sort_dir="desc", filter_sig=filter_sig)
            cursor_value = state.sort_value
            cursor_id = UUID(state.id)

        query = self.repository.filtered_query(params)
        rows = self.repository.paginate(query, cursor_value=cursor_value, cursor_id=cursor_id, limit=page.limit)
        has_more = len(rows) > page.limit
        items = rows[: page.limit]

        plants = self.repository.plants_by_ids({a.plant_id for a in items})
        factories = self.repository.factories_by_ids({p.factory_id for p in plants.values()})
        shifts = self.repository.shifts_by_ids({a.shift_id for a in items if a.shift_id})
        kpis = self.repository.kpis_by_ids({a.kpi_id for a in items})

        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(
                sort_by="detected_at", sort_dir="desc", filter_sig=filter_sig,
                sort_value=last.detected_at, id_=str(last.id),
            )

        return {
            "items": [self._summary_dict(a, plants, factories, shifts, kpis) for a in items],
            "next_cursor": next_cursor,
            "has_more": has_more,
        }

    def get_summary(self, plant_ids: list[UUID] | None = None) -> dict:
        now = clock.now_utc()
        week_ago = now - timedelta(days=7)
        return self.repository.summary_counts(
            active_statuses=(AnomalyStatus.NEW, AnomalyStatus.IN_REVIEW, AnomalyStatus.ACTION_PENDING),
            critical_severity=AnomalySeverity.CRITICAL,
            high_severity=AnomalySeverity.HIGH,
            not_analyzed_status=AnomalyAnalysisStatus.NOT_ANALYZED,
            week_ago=week_ago,
            resolved_statuses=(AnomalyStatus.RESOLVED, AnomalyStatus.CLOSED),
            plant_ids=plant_ids,
        )

    def get_detail(self, anomaly_id: UUID) -> dict:
        anomaly = self.repository.get_anomaly(anomaly_id)
        if anomaly is None:
            raise AnomalyNotFoundError("Tespit bulunamadı.")
        return self._detail_dict(anomaly)

    def get_latest_analysis(self, anomaly_id: UUID) -> dict:
        anomaly = self.repository.get_anomaly(anomaly_id)
        if anomaly is None:
            raise AnomalyNotFoundError("Tespit bulunamadı.")
        latest = self.repository.latest_analysis(anomaly_id)
        if latest is None:
            raise AnomalyAnalysisNotFoundError("Bu tespit için henüz analiz yapılmamış.")
        counts = self.repository.tool_call_counts_by_analysis_ids({latest.id})
        return self._analysis_dict(latest, counts.get(latest.id, 0))

    def get_analysis(self, analysis_id: UUID) -> dict:
        analysis = self.repository.get_analysis(analysis_id)
        if analysis is None:
            raise AnomalyAnalysisNotFoundError("Analiz bulunamadı.")
        counts = self.repository.tool_call_counts_by_analysis_ids({analysis.id})
        return self._analysis_dict(analysis, counts.get(analysis.id, 0))

    def get_tool_calls(self, analysis_id: UUID) -> dict:
        analysis = self.repository.get_analysis(analysis_id)
        if analysis is None:
            raise AnomalyAnalysisNotFoundError("Analiz bulunamadı.")
        calls = self.repository.tool_calls_for_analysis(analysis_id)
        return {"items": [self._tool_call_dict(c) for c in calls], "total": len(calls)}

    def _detail_dict(self, a: Anomaly) -> dict:
        plants = self.repository.plants_by_ids({a.plant_id})
        plant = plants.get(a.plant_id)
        factories = self.repository.factories_by_ids({plant.factory_id} if plant else set())
        factory = factories.get(plant.factory_id) if plant else None
        shifts = self.repository.shifts_by_ids({a.shift_id} if a.shift_id else set())
        shift = shifts.get(a.shift_id) if a.shift_id else None
        kpis = self.repository.kpis_by_ids({a.kpi_id})
        kpi = kpis.get(a.kpi_id)

        base = self._summary_dict(a, plants, factories, shifts, kpis)
        kpi_def = KPI_DEFINITIONS.get(kpi.code, {}) if kpi else {}

        foreman_uuids = [UUID(fid) for fid in a.foreman_ids]
        foremen_by_id = self.repository.foremen_by_ids(set(foreman_uuids))
        foreman_codes = [foremen_by_id[fid].employee_number for fid in foreman_uuids if fid in foremen_by_id]

        foreman_id = foreman_uuids[0] if foreman_uuids else None
        target_value = (
            resolve_kpi_target(self.db, kpi, plant, a.period_end, foreman_id)
            if kpi is not None and plant is not None else None
        )

        # LLM analiz payload builder, anomaly_analysis_service ve
        # anomaly_demo_tool_calling ile ortaktır; burada optimize edilmeden aynı biçimde çağrılır.
        package = build_analysis_package(self.db, a)

        # Bilerek iki ayrı sorgu olarak tutulur. analysis_history[0] ile latest_analysis eşit
        # görünse de ikincil ORDER BY anahtarı yokken aynı started_at değerine sahip satırların
        # kararlı tie-break davranışı kanıtlanamaz; sorguları birleştirmek davranış değişikliğidir.
        latest_analysis = self.repository.latest_analysis(a.id)
        analysis_history = self.repository.analysis_history(a.id)

        analysis_ids = {x.id for x in analysis_history}
        if latest_analysis is not None:
            analysis_ids.add(latest_analysis.id)
        tool_call_counts = self.repository.tool_call_counts_by_analysis_ids(analysis_ids)

        base.update(
            {
                "description": a.description,
                "observed_value": _num(a.observed_value),
                "expected_value": _num(a.expected_value),
                "target_value": target_value,
                "unit": a.unit,
                "affected_days": a.affected_days,
                "total_days": a.total_days,
                "comparison": a.comparison,
                "related_signals": a.related_signals,
                "evidence": a.evidence,
                "foreman_codes": foreman_codes,
                "data_quality_status": a.data_quality_status,
                "data_quality_warnings": a.data_quality_warnings,
                "daily_history": package["context"]["daily_history"],
                "kpi_definition": {
                    "name": kpi.name if kpi else None,
                    "description": kpi_def.get("description"),
                    "desired_direction": kpi_def.get("desired_direction"),
                    "warning_threshold": kpi_def.get("warning_threshold"),
                    "critical_threshold": kpi_def.get("critical_threshold"),
                },
                "latest_analysis": (
                    self._analysis_dict(latest_analysis, tool_call_counts.get(latest_analysis.id, 0))
                    if latest_analysis else None
                ),
                "analysis_history": [
                    self._analysis_dict(x, tool_call_counts.get(x.id, 0)) for x in analysis_history
                ],
            }
        )
        return base

    def _analysis_dict(self, an: AnomalyAnalysis, tool_call_count: int) -> dict:
        return {
            "id": str(an.id),
            "code": an.code,
            "mode": an.mode.value,
            "status": an.status.value,
            "status_label": ANALYSIS_STATUS_LABELS.get(an.status.value, an.status.value),
            "is_demo": an.is_demo,
            "model": an.model,
            "result": an.result,
            "investigation_plan": an.investigation_plan,
            "tool_call_count": tool_call_count,
            "error_code": an.error_code,
            "error_message": an.error_message,
            "started_at": an.started_at.isoformat(),
            "completed_at": an.completed_at.isoformat() if an.completed_at else None,
        }

    def _tool_call_dict(self, tc: AnomalyToolCall) -> dict:
        return {
            "id": str(tc.id),
            "code": tc.code,
            "step_number": tc.step_number,
            "tool_name": tc.tool_name,
            "tool_label": _TOOL_LABELS.get(tc.tool_name, tc.tool_name),
            "arguments": tc.arguments,
            "status": tc.status,
            "result": tc.result,
            "record_count": tc.record_count,
            "error_code": tc.error_code,
            "error_message": tc.error_message,
            "started_at": tc.started_at.isoformat(),
            "completed_at": tc.completed_at.isoformat() if tc.completed_at else None,
            "duration_ms": tc.duration_ms,
        }

    def _summary_dict(
        self,
        a: Anomaly,
        plants: dict,
        factories: dict,
        shifts: dict,
        kpis: dict,
    ) -> dict:
        plant: Plant | None = plants.get(a.plant_id)
        factory: Factory | None = factories.get(plant.factory_id) if plant else None
        shift: Shift | None = shifts.get(a.shift_id) if a.shift_id else None
        kpi: Kpi | None = kpis.get(a.kpi_id)

        return {
            "id": str(a.id),
            "code": a.code,
            "title": a.title,
            "factory_code": factory.code if factory else None,
            "factory_name": factory.name if factory else None,
            "plant_id": str(a.plant_id),
            "plant_name": plant.name if plant else None,
            "shift_id": str(a.shift_id) if a.shift_id else None,
            "shift_name": shift.name if shift else None,
            "kpi_id": str(a.kpi_id),
            "kpi_code": kpi.code if kpi else None,
            "kpi_name": kpi.name if kpi else None,
            "anomaly_type": a.anomaly_type.value,
            "anomaly_type_label": ANOMALY_TYPE_LABELS[a.anomaly_type],
            "detected_at": a.detected_at.isoformat(),
            "period_start": a.period_start.isoformat(),
            "period_end": a.period_end.isoformat(),
            "deviation_percent": _num(a.deviation_percent),
            "ml_confidence": _num(a.ml_confidence),
            "severity": a.severity.value,
            "severity_label": SEVERITY_LABELS[a.severity.value],
            "status": a.status.value,
            "status_label": STATUS_LABELS[a.status.value],
            "analysis_status": a.analysis_status.value,
            "analysis_status_label": ANALYSIS_STATUS_LABELS[a.analysis_status.value],
        }
