from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.api.authz_deps import assert_plant_ids_in_scope, require_permission
from app.core.client_ip import get_client_ip
from app.core.pagination import cursor_envelope
from app.core.permissions import Permission
from app.core.rate_limit import rate_limit_pdf
from app.db.session import get_db
from app.models.enums import (
    ContributionStatus,
    ContributionWorkType,
    FinancialGainStatus,
    ImpactLevel,
)
from app.schemas.authz import AuthContext
from app.schemas.base import ApiResponse, CursorResponse
from app.schemas.common import CursorParams, cursor_params
from app.schemas.contribution import (
    ContributionSummary,
    ContributionWorkCreate,
    ContributionWorkItem,
    ContributionWorkUpdate,
)
from app.services.audit import record_audit
from app.services.contribution_work_service import ContributionWorkService

router = APIRouter(prefix="/contribution-works", tags=["contribution-works"])

_require_intelligence = require_permission(Permission.OPERATIONAL_INTELLIGENCE_VIEW)
_require_contribute = require_permission(Permission.OPERATIONAL_IMPACT_CONTRIBUTE)


def _scope_plant_ids(ctx: AuthContext) -> list[UUID] | None:
    return sorted(ctx.plant_ids, key=str) if ctx.plant_ids is not None else None


def _assert_work_in_scope(service: ContributionWorkService, ctx: AuthContext, work_id: UUID) -> None:
    if ctx.plant_ids is None:
        return
    plant_ids = service.repository.plant_ids_for_work(work_id)
    assert_plant_ids_in_scope(ctx, plant_ids)


@router.get("", response_model=CursorResponse[ContributionWorkItem])
def list_contribution_works(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    foreman_ids: str | None = Query(None, description="Virgülle ayrılmış formen ID listesi"),
    work_type: ContributionWorkType | None = Query(None),
    status_filter: ContributionStatus | None = Query(None, alias="status"),
    impact_level: ImpactLevel | None = Query(None),
    financial_gain_status: FinancialGainStatus | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("date", pattern="^(title|type|foreman|plant|date|gain|status)$"),
    sort_dir: str = Query("desc", pattern="^(asc|desc)$"),
    page: CursorParams = Depends(cursor_params),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_intelligence),
) -> CursorResponse[ContributionWorkItem]:
    service = ContributionWorkService(db)
    result = service.list_works(
        date_from=date_from, date_to=date_to, plant_ids=plant_ids, factory_ids=factory_ids,
        foreman_ids=foreman_ids, work_type=work_type, status=status_filter, impact_level=impact_level,
        financial_gain_status=financial_gain_status, search=search,
        sort_by=sort_by, sort_dir=sort_dir, page=page,
        scope_plant_ids=_scope_plant_ids(ctx),
    )
    return cursor_envelope(result)


@router.get("/summary", response_model=ApiResponse[ContributionSummary])
def contribution_summary(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    foreman_ids: str | None = Query(None, description="Virgülle ayrılmış formen ID listesi"),
    work_type: ContributionWorkType | None = Query(None),
    status_filter: ContributionStatus | None = Query(None, alias="status"),
    impact_level: ImpactLevel | None = Query(None),
    financial_gain_status: FinancialGainStatus | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_intelligence),
) -> ApiResponse[ContributionSummary]:
    service = ContributionWorkService(db)
    data = service.summary(
        date_from=date_from, date_to=date_to, plant_ids=plant_ids, factory_ids=factory_ids,
        foreman_ids=foreman_ids, work_type=work_type, status=status_filter, impact_level=impact_level,
        financial_gain_status=financial_gain_status, search=search,
        scope_plant_ids=_scope_plant_ids(ctx),
    )
    return {"data": data}


@router.post("", status_code=201, response_model=ApiResponse[ContributionWorkItem])
def create_contribution_work(
    payload: ContributionWorkCreate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_contribute),
) -> ApiResponse[ContributionWorkItem]:
    assert_plant_ids_in_scope(ctx, payload.plant_ids)
    service = ContributionWorkService(db)
    data = service.create(
        payload, subject=ctx.subject, ip_address=get_client_ip(request), record_audit=record_audit
    )
    return {"data": data}


@router.get("/{work_id}", response_model=ApiResponse[ContributionWorkItem])
def get_contribution_work(
    work_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> ApiResponse[ContributionWorkItem]:
    service = ContributionWorkService(db)
    _assert_work_in_scope(service, ctx, work_id)
    return {"data": service.get(work_id)}


@router.patch("/{work_id}", response_model=ApiResponse[ContributionWorkItem])
def update_contribution_work(
    work_id: UUID,
    payload: ContributionWorkUpdate,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_contribute),
) -> ApiResponse[ContributionWorkItem]:
    service = ContributionWorkService(db)
    _assert_work_in_scope(service, ctx, work_id)
    if payload.plant_ids is not None:
        assert_plant_ids_in_scope(ctx, payload.plant_ids)
    data = service.update(
        work_id, payload, subject=ctx.subject, ip_address=get_client_ip(request), record_audit=record_audit
    )
    return {"data": data}


@router.delete("/{work_id}", status_code=204)
def delete_contribution_work(
    work_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(_require_contribute),
) -> Response:
    service = ContributionWorkService(db)
    _assert_work_in_scope(service, ctx, work_id)
    service.delete(work_id, subject=ctx.subject, ip_address=get_client_ip(request), record_audit=record_audit)
    return Response(status_code=204)


@router.get("/{work_id}/pdf", dependencies=[Depends(rate_limit_pdf)])
def download_contribution_work_pdf(
    work_id: UUID, db: Session = Depends(get_db), ctx: AuthContext = Depends(_require_intelligence)
) -> Response:
    service = ContributionWorkService(db)
    _assert_work_in_scope(service, ctx, work_id)
    pdf_bytes, file_name = service.pdf(work_id)
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
