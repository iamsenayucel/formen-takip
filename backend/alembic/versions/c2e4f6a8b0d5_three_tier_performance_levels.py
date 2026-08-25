from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2e4f6a8b0d5'
down_revision: Union[str, None] = 'd6f8a0c2e4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


performance_level_rules = sa.table(
    'performance_level_rules',
    sa.column('name', sa.String),
    sa.column('min_score', sa.Numeric),
    sa.column('max_score', sa.Numeric),
    sa.column('description', sa.String),
    sa.column('color', sa.String),
    sa.column('icon', sa.String),
    sa.column('sort_order', sa.Integer),
    sa.column('created_at', sa.DateTime(timezone=True)),
    sa.column('updated_at', sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.execute(
        performance_level_rules.delete().where(
            performance_level_rules.c.name.in_(['İyi', 'Çok İyi'])
        )
    )
    op.execute(
        performance_level_rules.update()
        .where(performance_level_rules.c.name == 'Geliştirilmeli')
        .values(max_score=89.99)
    )
    op.execute(
        performance_level_rules.update()
        .where(performance_level_rules.c.name == 'Mükemmel')
        .values(
            name='Başarılı',
            min_score=90,
            max_score=9999.99,
            description='Hedef seviyesinde veya üzerinde başarılı performans.',
            color='#16A34A',
            icon='check-circle',
            sort_order=3,
        )
    )


def downgrade() -> None:
    op.execute(
        performance_level_rules.update()
        .where(performance_level_rules.c.name == 'Başarılı')
        .values(
            name='Mükemmel',
            min_score=100,
            max_score=120,
            description='Hedefi aşan üstün performans.',
            color='#16A34A',
            icon='trophy',
            sort_order=5,
        )
    )
    op.execute(
        performance_level_rules.update()
        .where(performance_level_rules.c.name == 'Geliştirilmeli')
        .values(max_score=79.99)
    )
    now = sa.func.now()
    op.execute(
        performance_level_rules.insert().values(
            [
                dict(
                    name='İyi', min_score=80, max_score=89.99,
                    description='Hedefe yakın, kabul edilebilir performans.',
                    color='#CA8A04', icon='thumbs-up', sort_order=3,
                    created_at=now, updated_at=now,
                ),
                dict(
                    name='Çok İyi', min_score=90, max_score=99.99,
                    description='Hedefin büyük ölçüde karşılandığı güçlü performans.',
                    color='#2563EB', icon='star', sort_order=4,
                    created_at=now, updated_at=now,
                ),
            ]
        )
    )
