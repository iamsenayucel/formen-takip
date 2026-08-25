from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_identity
from app.db.session import get_db
from app.schemas.base import ApiResponse
from app.schemas.common import parse_uuid_list
from app.schemas.meta import FilterOptionsResponse
from app.services.meta_service import MetaService

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/filters", response_model=ApiResponse[FilterOptionsResponse])
def get_filter_options(
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    db: Session = Depends(get_db),
    _=Depends(get_current_identity),
) -> ApiResponse[FilterOptionsResponse]:
    data = MetaService(db).get_filter_options(
        plant_ids=parse_uuid_list(plant_ids),
        factory_ids=parse_uuid_list(factory_ids),
    )
    return {"data": data}
