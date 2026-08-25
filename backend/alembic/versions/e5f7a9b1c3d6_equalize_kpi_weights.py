from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e5f7a9b1c3d6'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_WEIGHTS = {'AGIR_GITME': 20, 'GSF': 20, 'ISKARTA': 20, 'INKITA': 20, 'PLANA_UYUM': 20}
_OLD_WEIGHTS = {'AGIR_GITME': 20, 'GSF': 25, 'ISKARTA': 15, 'INKITA': 20, 'PLANA_UYUM': 20}


def upgrade() -> None:
    bind = op.get_bind()
    for code, weight in _NEW_WEIGHTS.items():
        bind.execute(
            sa.text("UPDATE kpis SET weight = :weight, updated_at = now() WHERE code = :code"),
            {"weight": weight, "code": code},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for code, weight in _OLD_WEIGHTS.items():
        bind.execute(
            sa.text("UPDATE kpis SET weight = :weight, updated_at = now() WHERE code = :code"),
            {"weight": weight, "code": code},
        )
