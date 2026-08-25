from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '3b43eeec9028'
down_revision: Union[str, None] = 'c4a99f861289'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_WEIGHTS = {
    'INKITA': 22, 'OEE': 21, 'GSF': 20, 'AGIR_GITME': 13, 'ISKARTA': 12, 'PLANA_UYUM': 12,
}
_OLD_WEIGHTS = {
    'AGIR_GITME': 16.67, 'GSF': 16.67, 'ISKARTA': 16.67, 'INKITA': 16.67, 'PLANA_UYUM': 16.66, 'OEE': 16.66,
}


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
