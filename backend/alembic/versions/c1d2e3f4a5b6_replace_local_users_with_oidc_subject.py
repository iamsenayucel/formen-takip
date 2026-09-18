"""replace local users table with OIDC subject identifiers

Auth otoritesi Red Hat SSO'ya (Keycloak) taşınıyor; backend artık local credential
tutmuyor, salt OIDC resource server. 6ad63dbc115b ile aynı ruhta kasıtlı olarak
destructive:

- `users` tablosu (email, password_hash, lockout) tamamen kaldırılır — KVKK gereği
  kimlik amaçlı isim/e-posta artık saklanmıyor.
- `contribution_works.created_by_user_id`, `report_exports.requested_by_user_id`,
  `audit_logs.user_id` (users'a FK) yerine OIDC subject claim'ini tutan, FK'sız
  `*_subject`/`subject` string kolonları gelir (bkz. `Settings.oidc_user_id_claim`).
  Eski local-auth kullanıcıları için gerçek subject kurtarılamaz; ilgili satırlar
  veri kaybı olmadan `legacy-unknown` ile backfill edilir.

Downgrade uygulanmaz: silinen password hash ve FK ilişkileri geri getirilemez,
6ad63dbc115b'deki emsal ile aynı.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = 'b1f4d6a8c0e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY_PLACEHOLDER = 'legacy-unknown'


def upgrade() -> None:
    op.drop_constraint('contribution_works_created_by_user_id_fkey', 'contribution_works', type_='foreignkey')
    op.drop_column('contribution_works', 'created_by_user_id')
    op.add_column(
        'contribution_works',
        sa.Column('created_by_subject', sa.String(length=255), nullable=False, server_default=_LEGACY_PLACEHOLDER),
    )
    op.alter_column('contribution_works', 'created_by_subject', server_default=None)

    op.drop_constraint('report_exports_requested_by_user_id_fkey', 'report_exports', type_='foreignkey')
    op.drop_column('report_exports', 'requested_by_user_id')
    op.add_column(
        'report_exports',
        sa.Column('requested_by_subject', sa.String(length=255), nullable=False, server_default=_LEGACY_PLACEHOLDER),
    )
    op.alter_column('report_exports', 'requested_by_subject', server_default=None)

    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.alter_column('audit_logs', 'user_id', new_column_name='subject', type_=sa.String(length=255))
    op.create_index('ix_audit_logs_subject', 'audit_logs', ['subject'], unique=False)

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')


def downgrade() -> None:
    raise NotImplementedError(
        "Bu migration geri alınamaz: kaldırılan password_hash/users verisi ve "
        "created_by/requested_by/audit ilişkilendirmeleri kurtarılamaz."
    )
