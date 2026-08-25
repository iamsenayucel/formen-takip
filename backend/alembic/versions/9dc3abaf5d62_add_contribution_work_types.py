"""add contribution work types (5S, variety changeover efficiency, staff saving, customer complaint, poka yoke)

Revision ID: 9dc3abaf5d62
Revises: e3a5c7f9b1d0
Create Date: 2026-08-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = '9dc3abaf5d62'
down_revision: Union[str, None] = 'e3a5c7f9b1d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Yalnızca ekleme yapılır: Mevcut contribution_works satırlarının doğru okunması için
# TIME_SAVING ve QUALITY_IMPROVEMENT enum içinde kalır; frontend create form yalnızca
# bu seçenekleri sunmayı bırakır. Enum etiketi yeniden adlandırılmadığı veya silinmediği
# için 6ad63dbc115b içindeki rename->recreate->cast->drop akışı gerekmez.
NEW_VALUES = ('FIVE_S', 'VARIETY_CHANGEOVER_EFFICIENCY', 'STAFF_SAVING', 'CUSTOMER_COMPLAINT', 'POKA_YOKE')


def upgrade() -> None:
    # Ayrı commit edilir (gerekçe için a4c8e0b2d6f1'e bakın): Yeni `alembic upgrade head`
    # tüm migration'ları tek transaction içinde çalıştırır ve Postgres yeni enum değerinin
    # eklendiği transaction içinde kullanılmasını yasaklar. Aksi halde bu değerleri
    # filtreleyen sonraki migration, b9f2d4a6c8e1'in 'QUEUED' hatası gibi başarısız olur.
    with op.get_context().autocommit_block():
        for value in NEW_VALUES:
            op.execute(f"ALTER TYPE contribution_work_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    raise NotImplementedError(
        "Postgres enums cannot drop individual values. Rolling this back would require the "
        "rename -> create -> ALTER COLUMN ... USING -> drop-old sequence used in 6ad63dbc115b, "
        "and by then contribution_works rows may already reference these new values."
    )
