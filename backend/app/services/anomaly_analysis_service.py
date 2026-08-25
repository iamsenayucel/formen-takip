from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import get_settings
from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.enums import AnalysisMode, AnomalyAnalysisStatus
from app.schemas.anomaly_analysis import AnalysisResult, strict_json_schema
from app.services import llm_service
from app.services.anomaly_context import SYSTEM_PROMPT, build_analysis_package, build_user_message
from app.services.anomaly_demo_fallback import generate_demo_analysis
from app.services.anomaly_demo_tool_calling import run_demo_tool_calling
from app.services.anomaly_job_claim import (
    IN_PROGRESS_STATUSES,
    AnalysisInProgressError,
    claim_analysis,
    set_anomaly_status_if_current,
)
from app.services.anomaly_orchestrator import AnomalyAnalysisOrchestrator, build_initial_context

logger = logging.getLogger("app.anomaly_analysis")

_ANALYSIS_RESULT_SCHEMA = strict_json_schema(AnalysisResult)


def _new_code() -> str:
    return f"ANA-{clock.today_local().year}-{uuid.uuid4().hex[:8].upper()}"


_TOP_LEVEL_FIELD = "executive_summary"


def _unwrap_llm_payload(raw: dict) -> dict:
    current = raw
    for _ in range(3):
        if not isinstance(current, dict) or _TOP_LEVEL_FIELD in current:
            return current
        if len(current) != 1:
            return current
        (only_value,) = current.values()
        if not isinstance(only_value, dict):
            return current
        current = only_value
    return current


@dataclass
class _RunResult:
    result_payload: dict | None = None
    model_name: str = "unknown"
    is_demo: bool = True
    error_message: str | None = None
    error_code: str | None = None
    investigation_plan: list | None = None
    input_snapshot: dict | None = None
    mode: AnalysisMode = AnalysisMode.SINGLE_CONTEXT
    warnings: list[str] = field(default_factory=list)


def _attempt_single_context(anomaly: Anomaly, package: dict, user_message: str, use_llm: bool) -> tuple[dict, str]:
    if use_llm:
        raw = llm_service.call_llm(
            SYSTEM_PROMPT, user_message, json_schema=_ANALYSIS_RESULT_SCHEMA, schema_name="anomaly_analysis_result"
        )
        raw = _unwrap_llm_payload(raw)
        model_name = get_settings().llm_model
    else:
        raw = generate_demo_analysis(anomaly, package)
        model_name = "demo-fallback-v1"
    result = AnalysisResult.model_validate(raw)
    return result.model_dump(mode="json"), model_name


def _run_single_context(db: Session, anomaly: Anomaly, analysis: AnomalyAnalysis) -> _RunResult:
    analysis.status = AnomalyAnalysisStatus.ANALYZING
    db.commit()
    set_anomaly_status_if_current(db, anomaly, analysis, AnomalyAnalysisStatus.ANALYZING)

    use_llm = llm_service.is_configured()
    package = build_analysis_package(db, anomaly)
    user_message = build_user_message(package)

    result_payload: dict | None = None
    model_name = "demo-fallback-v1" if not use_llm else "unknown"
    error_message: str | None = None

    for attempt in (1, 2):
        try:
            result_payload, model_name = _attempt_single_context(anomaly, package, user_message, use_llm)
            error_message = None
            break
        except llm_service.LLMNotConfiguredError:
            use_llm = False
            try:
                result_payload, model_name = _attempt_single_context(anomaly, package, user_message, use_llm=False)
                break
            except Exception as demo_exc:
                error_message = "Demo analiz üretimi başarısız oldu."
                logger.warning("Demo analiz üretimi başarısız (anomaly=%s): %s", anomaly.code, demo_exc)
                break
        except (llm_service.LLMTimeoutError, llm_service.LLMRequestError, llm_service.LLMResponseInvalidError) as exc:
            error_message = str(exc)
            logger.warning("LLM analiz denemesi %s başarısız (anomaly=%s): %s", attempt, anomaly.code, type(exc).__name__)
            continue
        except ValidationError as exc:
            error_message = "LLM cevabı beklenen şemayla eşleşmiyor (eksik/hatalı alan)."
            logger.warning("LLM analiz cevabı doğrulanamadı (anomaly=%s, deneme=%s): %s", anomaly.code, attempt, exc)
            continue

    return _RunResult(
        result_payload=result_payload, model_name=model_name, is_demo=not use_llm,
        error_message=None if result_payload is not None else (
            error_message and "Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz."
        ),
        input_snapshot=package, mode=AnalysisMode.SINGLE_CONTEXT,
    )


def _run_tool_calling(db: Session, anomaly: Anomaly, analysis: AnomalyAnalysis) -> _RunResult:
    settings = get_settings()
    use_llm = llm_service.is_configured() and settings.llm_tool_calling_enabled

    if not use_llm:
        if not settings.llm_demo_tool_calling_enabled:
            return _RunResult(
                mode=AnalysisMode.TOOL_CALLING, is_demo=True,
                error_message="Yapay zekâ analizi oluşturulamadı. Daha sonra yeniden deneyebilirsiniz.",
            )
        outcome = run_demo_tool_calling(db, anomaly, analysis)
        return _RunResult(
            result_payload=outcome.result_payload, model_name="demo-tool-calling-v1", is_demo=True,
            investigation_plan=outcome.investigation_plan, mode=AnalysisMode.TOOL_CALLING,
            input_snapshot=build_initial_context(db, anomaly),
        )

    orchestrator = AnomalyAnalysisOrchestrator(db, anomaly)
    try:
        outcome = orchestrator.run(analysis)
    except llm_service.LLMToolCallingUnsupportedError as exc:
        logger.warning(
            "Model tool calling desteklemiyor (anomaly=%s), single_context moduna düşülüyor: %s", anomaly.code, exc
        )
        fallback = _run_single_context(db, anomaly, analysis)
        fallback.mode = AnalysisMode.SINGLE_CONTEXT
        fallback.warnings = ["Kullanılan model tool calling desteklemediği için single_context moduna düşüldü."]
        return fallback

    return _RunResult(
        result_payload=outcome.result_payload, model_name=get_settings().llm_model, is_demo=False,
        error_message=outcome.error_message, error_code=outcome.error_code,
        investigation_plan=outcome.investigation_plan, mode=AnalysisMode.TOOL_CALLING,
        input_snapshot=build_initial_context(db, anomaly), warnings=outcome.warnings,
    )


def run_analysis(db: Session, anomaly: Anomaly, mode: AnalysisMode | str | None = None) -> AnomalyAnalysis:
    # Yalnızca hızlı ön kontroldür; açık contention durumunda AnomalyAnalysis satırı
    # oluşturmaktan kaçınır. Asıl mutual-exclusion garantisini claim_analysis() içindeki
    # partial unique index verir; bu kontrolle yarışan ikinci çağrı yine indekse takılır.
    if anomaly.analysis_status in IN_PROGRESS_STATUSES:
        raise AnalysisInProgressError("Bu tespit için analiz zaten devam ediyor.")

    settings = get_settings()
    requested_mode = AnalysisMode(mode) if mode else AnalysisMode(settings.llm_analysis_mode)
    if requested_mode == AnalysisMode.TOOL_CALLING and not settings.llm_tool_calling_enabled:
        requested_mode = AnalysisMode.SINGLE_CONTEXT

    started_at = datetime.now(timezone.utc)
    analysis = AnomalyAnalysis(
        id=uuid.uuid4(), code=_new_code(), anomaly_id=anomaly.id, model="pending", is_demo=True, mode=requested_mode,
        status=AnomalyAnalysisStatus.QUEUED, started_at=started_at,
    )
    claim_analysis(db, anomaly, analysis)

    perf_start = time.monotonic()
    run_result = (
        _run_tool_calling(db, anomaly, analysis)
        if requested_mode == AnalysisMode.TOOL_CALLING
        else _run_single_context(db, anomaly, analysis)
    )
    response_seconds = round(time.monotonic() - perf_start, 3)

    if run_result.result_payload is not None:
        final_status = (
            AnomalyAnalysisStatus.COMPLETED_WITH_WARNINGS if run_result.warnings else AnomalyAnalysisStatus.COMPLETED
        )
    else:
        final_status = AnomalyAnalysisStatus.FAILED

    analysis.model = run_result.model_name
    analysis.is_demo = run_result.is_demo
    analysis.mode = run_result.mode
    analysis.status = final_status
    analysis.result = run_result.result_payload
    analysis.input_snapshot = run_result.input_snapshot
    analysis.investigation_plan = run_result.investigation_plan
    analysis.error_message = run_result.error_message
    analysis.error_code = run_result.error_code
    analysis.completed_at = datetime.now(timezone.utc)
    # Bu denemenin kendi satırı, aşağıdaki anomali durumunun stale olup olmamasından
    # bağımsız olarak her zaman yazılır.
    db.commit()
    db.refresh(analysis)

    set_anomaly_status_if_current(db, anomaly, analysis, final_status)

    logger.info(
        "Anomaly analysis finished anomaly=%s analysis=%s mode=%s model=%s status=%s response_seconds=%s",
        anomaly.code, analysis.code, run_result.mode.value, run_result.model_name, final_status.value, response_seconds,
    )

    return analysis
