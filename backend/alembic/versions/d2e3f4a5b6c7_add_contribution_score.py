"""add contribution_score to contribution_works

Adds the system-computed 1-5 katkı (contribution) score used to build each
foreman's rolling 3-month contribution bonus on top of their operational
performance score. Nullable and non-destructive: existing rows are left NULL
until recomputed (see `app.cli backfill-contribution-scores`).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('contribution_works', sa.Column('contribution_score', sa.Integer(), nullable=True))
    op.create_check_constraint(
        'ck_contribution_works_score_range',
        'contribution_works',
        'contribution_score IS NULL OR contribution_score BETWEEN 1 AND 5',
    )


def downgrade() -> None:
    op.drop_constraint('ck_contribution_works_score_range', 'contribution_works', type_='check')
    op.drop_column('contribution_works', 'contribution_score')
