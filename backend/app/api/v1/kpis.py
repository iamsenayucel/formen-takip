from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.db.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.common import Filters, common_filters
from app.schemas.kpi import KpiAnalysis, KpiDetail, KpiListItem
from app.services.kpi_service import KpiService

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("", response_model=ApiResponse[list[KpiListItem]])
def list_kpis(db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[list[KpiListItem]]:
    result = KpiService(db).get_list()
    return {"data": result["items"]}


@router.get("/{kpi_id}", response_model=ApiResponse[KpiDetail])
def get_kpi(kpi_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_identity)) -> ApiResponse[KpiDetail]:
    return {"data": KpiService(db).get_detail(kpi_id)}


@router.get("/{kpi_id}/analysis", response_model=ApiResponse[KpiAnalysis])
def kpi_analysis(
    kpi_id: UUID, filters: Filters = Depends(common_filters), db: Session = Depends(get_db), _=Depends(get_current_identity)
) -> ApiResponse[KpiAnalysis]:
    return {"data": KpiService(db).get_analysis(kpi_id, filters)}
