from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.authz_deps import get_auth_context
from app.db.session import get_db
from app.schemas.authz import AuthContext
from app.schemas.base import ApiResponse
from app.schemas.common import narrow_ids, parse_uuid_list
from app.schemas.meta import FilterOptionsResponse
from app.services.meta_service import MetaService

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/filters", response_model=ApiResponse[FilterOptionsResponse])
def get_filter_options(
    plant_ids: str | None = Query(None, description="Virgülle ayrılmış tesis ID listesi"),
    factory_ids: str | None = Query(None, description="Virgülle ayrılmış fabrika ID listesi"),
    db: Session = Depends(get_db),
    ctx: AuthContext = Depends(get_auth_context),
) -> ApiResponse[FilterOptionsResponse]:
    # Permission gate yok (herkes filtre çubuğunu görebilir) ama scope dışı tesislerin
    # filtre çubuğunda görünmemesi için `plant_ids` her zaman scope ile daraltılır —
    # `list_active_for_factories`/`list_active_for_filter_options` ikisini de AND'ler,
    # bu yüzden `factory_ids` ayrıca sıfırlanmaya gerek yok.
    resolved_plant_ids = narrow_ids(parse_uuid_list(plant_ids), ctx.plant_ids)
    data = MetaService(db).get_filter_options(
        plant_ids=resolved_plant_ids,
        factory_ids=parse_uuid_list(factory_ids),
    )
    return {"data": data}
