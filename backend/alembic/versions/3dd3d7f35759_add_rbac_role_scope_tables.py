"""add rbac role scope tables

Subject-keyed rol/scope atama tabloları; "DB'de PII yok, sadece OIDC subject"
mimarisinin devamı. c1d2e3f4a5b6/6ad63dbc115b'nin aksine tamamen additive-only:
iki yeni boş tablo ve iki yeni enum, mevcut hiçbir tabloya dokunmaz, tam geri alınabilir.

Revision ID: 3dd3d7f35759
Revises: 3b43eeec9028
Create Date: 2026-09-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3dd3d7f35759'
down_revision: Union[str, None] = '3b43eeec9028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

USER_ROLE = ('FOREMAN', 'SUPERVISOR', 'OPERATIONS_MANAGER')
USER_SCOPE_TYPE = ('ALL', 'FACTORY', 'PLANT')


def upgrade() -> None:
    bind = op.get_bind()

    user_role_enum = postgresql.ENUM(*USER_ROLE, name='user_role', create_type=False)
    user_role_enum.create(bind, checkfirst=True)
    user_scope_type_enum = postgresql.ENUM(*USER_SCOPE_TYPE, name='user_scope_type', create_type=False)
    user_scope_type_enum.create(bind, checkfirst=True)

    op.create_table(
        'user_role_assignments',
        sa.Column('subject', sa.String(length=255), primary_key=True),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        'user_scope_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'subject', sa.String(length=255),
            sa.ForeignKey('user_role_assignments.subject', ondelete='CASCADE'), nullable=False,
        ),
        sa.Column('scope_type', user_scope_type_enum, nullable=False),
        sa.Column('factory_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('factories.id', ondelete='CASCADE')),
        sa.Column('plant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plants.id', ondelete='CASCADE')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(scope_type = 'ALL' AND factory_id IS NULL AND plant_id IS NULL) OR "
            "(scope_type = 'FACTORY' AND factory_id IS NOT NULL AND plant_id IS NULL) OR "
            "(scope_type = 'PLANT' AND plant_id IS NOT NULL AND factory_id IS NULL)",
            name='ck_user_scope_assignments_type_columns',
        ),
        sa.UniqueConstraint(
            'subject', 'scope_type', 'factory_id', 'plant_id', name='uq_user_scope_assignments_subject_scope'
        ),
    )
    op.create_index('ix_user_scope_assignments_subject', 'user_scope_assignments', ['subject'])


def downgrade() -> None:
    op.drop_index('ix_user_scope_assignments_subject', table_name='user_scope_assignments')
    op.drop_table('user_scope_assignments')
    op.drop_table('user_role_assignments')
    postgresql.ENUM(name='user_scope_type').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='user_role').drop(op.get_bind(), checkfirst=True)
