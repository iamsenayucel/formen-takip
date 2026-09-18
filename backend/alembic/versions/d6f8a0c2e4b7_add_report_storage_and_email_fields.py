from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6f8a0c2e4b7'
down_revision: Union[str, None] = 'f4a6c8e0b2d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Değerler Python enum member adlarıyla (uppercase) eşleşir — repodaki SQLAlchemy
# Enum() kolonlarının hepsi values_callable kullanmadan varsayılan davranışı
# (member.name, member.value değil) kullanır; bkz. app/models/report.py.
report_generation_status = sa.Enum(
    'PENDING', 'GENERATING', 'READY', 'FAILED', name='report_generation_status'
)
report_storage_provider = sa.Enum('S3', 'LOCAL', name='report_storage_provider')
report_email_status = sa.Enum(
    'PENDING', 'SENDING', 'SENT', 'FAILED', 'SKIPPED', name='report_email_status'
)


def upgrade() -> None:
    bind = op.get_bind()
    report_generation_status.create(bind, checkfirst=True)
    report_storage_provider.create(bind, checkfirst=True)
    report_email_status.create(bind, checkfirst=True)

    op.add_column(
        'foreman_monthly_reports',
        sa.Column(
            'pdf_generation_status', report_generation_status,
            nullable=False, server_default='PENDING',
        ),
    )
    op.add_column('foreman_monthly_reports', sa.Column('pdf_generated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('storage_provider', report_storage_provider, nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('storage_bucket', sa.String(length=255), nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('object_key', sa.String(length=500), nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('pdf_file_name', sa.String(length=300), nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('pdf_content_type', sa.String(length=100), nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('pdf_file_size', sa.Integer(), nullable=True))
    op.add_column(
        'foreman_monthly_reports',
        sa.Column('email_status', report_email_status, nullable=False, server_default='PENDING'),
    )
    op.add_column('foreman_monthly_reports', sa.Column('emailed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'foreman_monthly_reports',
        sa.Column('email_retry_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('foreman_monthly_reports', sa.Column('email_last_error', sa.String(length=500), nullable=True))

    op.create_unique_constraint(
        'uq_foreman_monthly_reports_object_key', 'foreman_monthly_reports', ['object_key']
    )

    # server_default yalnızca mevcut satırları backfill etmek için; yeni satırlar Python
    # tarafında ORM default'uyla üretilir. Var olan raporların PDF'i S3'te henüz
    # oluşmadığından pdf_generation_status=pending doğru başlangıç durumudur;
    # report_data (asıl rapor içeriği) hiç dokunulmamıştır.
    op.alter_column('foreman_monthly_reports', 'pdf_generation_status', server_default=None)
    op.alter_column('foreman_monthly_reports', 'email_status', server_default=None)
    op.alter_column('foreman_monthly_reports', 'email_retry_count', server_default=None)


def downgrade() -> None:
    op.drop_constraint('uq_foreman_monthly_reports_object_key', 'foreman_monthly_reports', type_='unique')
    op.drop_column('foreman_monthly_reports', 'email_last_error')
    op.drop_column('foreman_monthly_reports', 'email_retry_count')
    op.drop_column('foreman_monthly_reports', 'emailed_at')
    op.drop_column('foreman_monthly_reports', 'email_status')
    op.drop_column('foreman_monthly_reports', 'pdf_file_size')
    op.drop_column('foreman_monthly_reports', 'pdf_content_type')
    op.drop_column('foreman_monthly_reports', 'pdf_file_name')
    op.drop_column('foreman_monthly_reports', 'object_key')
    op.drop_column('foreman_monthly_reports', 'storage_bucket')
    op.drop_column('foreman_monthly_reports', 'storage_provider')
    op.drop_column('foreman_monthly_reports', 'pdf_generated_at')
    op.drop_column('foreman_monthly_reports', 'pdf_generation_status')

    bind = op.get_bind()
    report_email_status.drop(bind, checkfirst=True)
    report_storage_provider.drop(bind, checkfirst=True)
    report_generation_status.drop(bind, checkfirst=True)
