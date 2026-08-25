from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a4c8e0b2d6f1'
down_revision: Union[str, None] = 'f2a4b8e6c9d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_STATUS_VALUES = (
    'QUEUED', 'PLANNING', 'COLLECTING_DATA', 'GENERATING_ANALYSIS',
    'COMPLETED_WITH_WARNINGS', 'TIMED_OUT', 'CANCELLED',
)
_STATUS_ENUM_NAMES = ('anomaly_analysis_status', 'anomaly_analysis_run_status')

ANALYSIS_MODE = ('SINGLE_CONTEXT', 'TOOL_CALLING')


def upgrade() -> None:
    # Postgres yeni enum değerini eklendiği transaction içinde kullanmayı reddeder
    # (UnsafeNewEnumValueUsage). `alembic upgrade head` varsayılan olarak tüm zinciri
    # tek transaction içinde çalıştırır; sonraki b9f2d4a6c8e1 migration'ı index koşulunda
    # 'QUEUED' gibi değerleri filtrelediğinden, ADD VALUE ifadeleri önce ayrı commit edilmezse
    # boş veritabanında migration başarısız olur.
    with op.get_context().autocommit_block():
        for enum_name in _STATUS_ENUM_NAMES:
            for value in _NEW_STATUS_VALUES:
                op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS '{value}'")

    analysis_mode_type = postgresql.ENUM(*ANALYSIS_MODE, name='analysis_mode', create_type=False)
    analysis_mode_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'anomaly_analyses',
        sa.Column('mode', analysis_mode_type, nullable=False, server_default='SINGLE_CONTEXT'),
    )
    op.add_column('anomaly_analyses', sa.Column('investigation_plan', sa.JSON(), nullable=True))
    op.add_column('anomaly_analyses', sa.Column('error_code', sa.String(length=50), nullable=True))
    op.alter_column('anomaly_analyses', 'mode', server_default=None)

    op.create_table(
        'anomaly_tool_calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=30), nullable=False, unique=True),
        sa.Column(
            'analysis_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('anomaly_analyses.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column(
            'anomaly_id', postgresql.UUID(as_uuid=True),
            sa.ForeignKey('anomalies.id', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('record_count', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_anomaly_tool_calls_code', 'anomaly_tool_calls', ['code'])
    op.create_index('ix_anomaly_tool_calls_analysis_id', 'anomaly_tool_calls', ['analysis_id'])
    op.create_index('ix_anomaly_tool_calls_anomaly_id', 'anomaly_tool_calls', ['anomaly_id'])


def downgrade() -> None:
    op.drop_table('anomaly_tool_calls')
    op.drop_column('anomaly_analyses', 'error_code')
    op.drop_column('anomaly_analyses', 'investigation_plan')
    op.drop_column('anomaly_analyses', 'mode')
    postgresql.ENUM(name='analysis_mode').drop(op.get_bind(), checkfirst=True)
