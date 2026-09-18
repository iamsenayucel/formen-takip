from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.authz_deps import require_permission, scoped_filters
from app.core.permissions import Permission
from app.db.session import get_db
from app.schemas.authz import AuthContext
from app.schemas.base import ApiResponse
from app.schemas.common import Filters
from app.schemas.kpi import KpiAnalysis, KpiDetail, KpiListItem
from app.services.kpi_service import KpiService

router = APIRouter(prefix="/kpis", tags=["kpis"])

_require_performance = require_permission(Permission.PERFORMANCE_VIEW)


@router.get("", response_model=ApiResponse[list[KpiListItem]])
def list_kpis(db: Session = Depends(get_db), _ctx: AuthContext = Depends(_require_performance)) -> ApiResponse[list[KpiListItem]]:
    result = KpiService(db).get_list()
    return {"data": result["items"]}


@router.get("/{kpi_id}", response_model=ApiResponse[KpiDetail])
def get_kpi(kpi_id: UUID, db: Session = Depends(get_db), _ctx: AuthContext = Depends(_require_performance)) -> ApiResponse[KpiDetail]:
    return {"data": KpiService(db).get_detail(kpi_id)}


@router.get("/{kpi_id}/analysis", response_model=ApiResponse[KpiAnalysis])
def kpi_analysis(
    kpi_id: UUID, filters: Filters = Depends(scoped_filters), db: Session = Depends(get_db),
    _ctx: AuthContext = Depends(_require_performance),
) -> ApiResponse[KpiAnalysis]:
    return {"data": KpiService(db).get_analysis(kpi_id, filters)}
