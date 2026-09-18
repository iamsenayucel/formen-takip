from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.authz_deps import assert_plant_in_scope, require_permission
from app.core import clock
from app.core.client_ip import get_client_ip
from app.core.errors import AnomalyAnalysisNotFoundError, AnomalyNotFoundError
from app.core.pagination import cursor_envelope
from app.core.permissions import Permission
from app.core.rate_limit import rate_limit_llm
from app.db.session import get_db
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus
from app.repositories.anomaly_repository import AnomalyListQueryParams, AnomalyRepository
from app.schemas.anomaly import (
    AnalyzeRequest,
    AnomalyAnalysisRecord,
    AnomalyDetail,
    AnomalyListItem,
    AnomalyStatusUpdate,
    AnomalySummary,
    AnomalyToolCallItem,
)
from app.schemas.anomaly_investigation import AnomalyInvestigation
from app.schemas.authz import AuthContext
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.common import CursorParams, cursor_params
from app.services.anomaly_analysis_command_service import AnomalyAnalysisCommandService
from app.services.anomaly_investigation_service import AnomalyInvestigationService
from app.services.anomaly_read_service import AnomalyReadService
from app.services.anomaly_status_service import AnomalyStatusService

router = APIRouter(prefix="/anomalies", tags=["anomalies"])
analyses_router = APIRouter(prefix="/analyses", tags=["analyses"])

_require_intelligence = require_permission(Permission.OPERATIONAL_INTELLIGENCE_VIEW)


def _require_anomaly_scope(db: Session, ctx: AuthContext, anomaly_id: UUID) -> None:
    if ctx.plant_ids is None:
        return
    anomaly = AnomalyRepository(db).get_anomaly(anomaly_id)
    if anomaly is None:
        raise AnomalyNotFoundError("Tespit bulunamadı.")
    assert_plant_in_scope(ctx, anomaly.plant_id)


def _require_analysis_scope(db: Session, ctx: AuthContext, analysis_id: UUID) -> None:
    if ctx.plant_ids is None:
        return
    repo = AnomalyRepository(db)
    analysis = repo.get_analysis(analysis_id)
    if analysis is None:
        raise AnomalyAnalysisNotFoundError("Analiz bulunamadı.")
    anomaly = repo.get_anomaly(analysis.anomaly_id)
    if anomaly is None:
        raise AnomalyNotFoundError("Tespit bulunamadı.")
    assert_plant_in_scope(ctx, anomaly.plant_id)


@router.get("", response_model=CursorResponse[AnomalyListItem])
def list_anomalies(
    factory: str | None = Query(None, description="K1 veya K2"),
    plant_id: UUID | None = Query(None),
    shift_id: UUID | None = Query(None),
    kpi_id: UUID | None = Query(None),
    severity: AnomalySeverity | None = Query(None),
    status_filter: AnomalyStatus | None = Query(None, alias="status"),
    analysis_status: AnomalyAnalysisStatus | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    page: CursorParams = Depends(cursor_params),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_intelligence),
) -> CursorResponse[AnomalyListItem]:
    if plant_id is not None:
        assert_plant_in_scope(ctx, plant_id)
    params = AnomalyListQueryParams(
        factory=factory,
        plant_id=plant_id,
        plant_ids=(sorted(ctx.plant_ids, key=str) if plant_id is None and ctx.plant_ids is not None else None),
        shift_id=shift_id,
        kpi_id=kpi_id,
        severity=severity,
        status=status_filter,
        analysis_status=analysis_status,
        start_date_utc=clock.local_day_bounds_utc(start_date)[0] if start_date else None,
        end_date_utc=clock.local_day_bounds_utc(end_date)[1] if end_date else None,
        search=search,
    )
    service = AnomalyReadService(db)
    return cursor_envelope(service.list_anomalies(params, page))


@router.get("/summary", response_model=ApiResponse[AnomalySummary])
def anomalies_summary(db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)) -> ApiResponse[AnomalySummary]:
    plant_ids = sorted(ctx.plant_ids, key=str) if ctx.plant_ids is not None else None
    return {"data": AnomalyReadService(db).get_summary(plant_ids)}


@router.get(
    "/{anomaly_id}",
    response_model=ApiResponse[AnomalyDetail],
    response_model_exclude_unset=True,
)
def get_anomaly(
    anomaly_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> ApiResponse[AnomalyDetail]:
    _require_anomaly_scope(db, ctx, anomaly_id)
    return {"data": AnomalyReadService(db).get_detail(anomaly_id)}


@router.get("/{anomaly_id}/investigation", response_model=ApiResponse[AnomalyInvestigation])
def get_anomaly_investigation(
    anomaly_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> ApiResponse[AnomalyInvestigation]:
    _require_anomaly_scope(db, ctx, anomaly_id)
    return {"data": AnomalyInvestigationService(db).get_investigation(anomaly_id)}


@router.get(
    "/{anomaly_id}/analysis",
    response_model=ApiResponse[AnomalyAnalysisRecord],
    response_model_exclude_unset=True,
)
def get_latest_analysis(
    anomaly_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> ApiResponse[AnomalyAnalysisRecord]:
    _require_anomaly_scope(db, ctx, anomaly_id)
    return {"data": AnomalyReadService(db).get_latest_analysis(anomaly_id)}


@router.post(
    "/{anomaly_id}/analyze",
    response_model=ApiResponse[AnomalyDetail],
    response_model_exclude_unset=True,
    dependencies=[Depends(rate_limit_llm)],
)
def analyze_anomaly(
    anomaly_id: UUID, request: Request, payload: AnalyzeRequest | None = None,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence),
) -> ApiResponse[AnomalyDetail]:
    _require_anomaly_scope(db, ctx, anomaly_id)
    payload = payload or AnalyzeRequest()
    service = AnomalyAnalysisCommandService(db)
    data = service.analyze(
        anomaly_id=anomaly_id,
        mode=payload.mode,
        force_refresh=payload.force_refresh,
        actor=ctx.subject,
        ip_address=get_client_ip(request),
    )
    return {"data": data}


@router.post(
    "/{anomaly_id}/reanalyze",
    response_model=ApiResponse[AnomalyDetail],
    response_model_exclude_unset=True,
    dependencies=[Depends(rate_limit_llm)],
)
def reanalyze_anomaly(
    anomaly_id: UUID, request: Request, payload: AnalyzeRequest | None = None,
    db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence),
) -> ApiResponse[AnomalyDetail]:
    _require_anomaly_scope(db, ctx, anomaly_id)
    payload = payload or AnalyzeRequest()
    service = AnomalyAnalysisCommandService(db)
    data = service.reanalyze(
        anomaly_id=anomaly_id,
        mode=payload.mode,
        force_refresh=payload.force_refresh,
        actor=ctx.subject,
        ip_address=get_client_ip(request),
    )
    return {"data": data}


@router.patch(
    "/{anomaly_id}/status",
    response_model=ApiResponse[AnomalyDetail],
    response_model_exclude_unset=True,
)
def update_anomaly_status(
    anomaly_id: UUID,
    payload: AnomalyStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_intelligence),
) -> ApiResponse[AnomalyDetail]:
    _require_anomaly_scope(db, ctx, anomaly_id)
    service = AnomalyStatusService(db)
    data = service.update_status(
        anomaly_id=anomaly_id,
        new_status=payload.status,
        actor=ctx.subject,
        ip_address=get_client_ip(request),
    )
    return {"data": data}


@analyses_router.get(
    "/{analysis_id}",
    response_model=ApiResponse[AnomalyAnalysisRecord],
    response_model_exclude_unset=True,
)
def get_analysis(
    analysis_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> ApiResponse[AnomalyAnalysisRecord]:
    _require_analysis_scope(db, ctx, analysis_id)
    return {"data": AnomalyReadService(db).get_analysis(analysis_id)}


@analyses_router.get("/{analysis_id}/tool-calls", response_model=ApiResponse[list[AnomalyToolCallItem]])
def list_tool_calls(
    analysis_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> ApiResponse[list[AnomalyToolCallItem]]:
    _require_analysis_scope(db, ctx, analysis_id)
    result = AnomalyReadService(db).get_tool_calls(analysis_id)
    return {"data": result["items"]}
