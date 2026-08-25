from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f4a6c8e0b2d5'
down_revision: Union[str, None] = 'e5f7a9b1c3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contribution_work_plants',
        sa.Column(
            'work_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('contribution_works.id', ondelete='CASCADE'), primary_key=True,
        ),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id'), primary_key=True),
    )
    op.create_index('ix_contribution_work_plants_work_id', 'contribution_work_plants', ['work_id'])
    op.create_index('ix_contribution_work_plants_plant_id', 'contribution_work_plants', ['plant_id'])

    op.execute(
        """
        INSERT INTO contribution_work_plants (work_id, plant_id)
        SELECT id, plant_id FROM contribution_works WHERE plant_id IS NOT NULL
        """
    )

    op.add_column('contribution_works', sa.Column('gain_amount', sa.Numeric(14, 2), nullable=True))
    op.execute(
        "UPDATE contribution_works SET gain_amount = COALESCE(verified_amount, estimated_amount)"
    )

    op.drop_index('ix_contribution_works_plant_id', table_name='contribution_works')
    op.drop_column('contribution_works', 'plant_id')
    op.drop_column('contribution_works', 'estimated_amount')
    op.drop_column('contribution_works', 'verified_amount')
    op.drop_column('contribution_works', 'is_gain_verified')
    op.drop_column('contribution_works', 'verified_by_department')
    op.drop_column('contribution_works', 'verified_by_department_other_note')
    op.drop_column('contribution_works', 'verification_date')
    op.drop_column('contribution_works', 'verification_note')

    postgresql.ENUM(name='contribution_verifying_department').drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    raise NotImplementedError(
        "Bu migration geri alınamaz: birden fazla tesise bağlı katkı çalışmaları tekil plant_id'ye, "
        "tahmini/doğrulanmış kazanç ayrımı ise tek gain_amount'a geri dönüştürülemez."
    )
