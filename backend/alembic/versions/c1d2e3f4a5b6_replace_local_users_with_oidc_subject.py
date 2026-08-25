"""replace local users table with OIDC subject identifiers

Authentication authority moves to Red Hat SSO (Keycloak) via OIDC; the backend
becomes a pure resource server and no longer issues or stores local credentials.
This migration is intentionally destructive, in the same spirit as
`6ad63dbc115b_karaman_factory_chief_hierarchy`:

- Drops the `users` table (email, password_hash, lockout state — all local-auth
  concerns that no longer exist; per KVKK, name/e-mail must not be persisted for
  identity purposes going forward).
- Replaces `contribution_works.created_by_user_id`, `report_exports.requested_by_user_id`
  and `audit_logs.user_id` (UUID FKs into `users`) with plain, non-FK
  `*_subject` / `subject` string columns holding the OIDC access token's stable
  identity claim (see `Settings.oidc_user_id_claim`). There is no way to recover
  a real OIDC subject for historical local-auth users, so existing attribution
  rows are backfilled with a `legacy-unknown` placeholder rather than lost
  silently — the row itself (and all other data) is preserved.

Downgrade is not implemented: there is no way to reconstruct the removed
password hashes or FK relationships, matching the precedent set by
`6ad63dbc115b`.
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
    # --- contribution_works.created_by_user_id alanını created_by_subject yap ---
    op.drop_constraint('contribution_works_created_by_user_id_fkey', 'contribution_works', type_='foreignkey')
    op.drop_column('contribution_works', 'created_by_user_id')
    op.add_column(
        'contribution_works',
        sa.Column('created_by_subject', sa.String(length=255), nullable=False, server_default=_LEGACY_PLACEHOLDER),
    )
    op.alter_column('contribution_works', 'created_by_subject', server_default=None)

    # --- report_exports.requested_by_user_id alanını requested_by_subject yap ---
    op.drop_constraint('report_exports_requested_by_user_id_fkey', 'report_exports', type_='foreignkey')
    op.drop_column('report_exports', 'requested_by_user_id')
    op.add_column(
        'report_exports',
        sa.Column('requested_by_subject', sa.String(length=255), nullable=False, server_default=_LEGACY_PLACEHOLDER),
    )
    op.alter_column('report_exports', 'requested_by_subject', server_default=None)

    # --- audit_logs.user_id alanını audit_logs.subject yap ---
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.alter_column('audit_logs', 'user_id', new_column_name='subject', type_=sa.String(length=255))
    op.create_index('ix_audit_logs_subject', 'audit_logs', ['subject'], unique=False)

    # --- local-auth users tablosunu tamamen kaldır ---
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')


def downgrade() -> None:
    raise NotImplementedError(
        "Bu migration geri alınamaz: kaldırılan password_hash/users verisi ve "
        "created_by/requested_by/audit ilişkilendirmeleri kurtarılamaz."
    )
