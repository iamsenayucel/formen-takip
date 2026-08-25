"""job claiming and reconciliation

Revision ID: b9f2d4a6c8e1
Revises: 8305552555b2
Create Date: 2026-08-14 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b9f2d4a6c8e1'
down_revision: Union[str, None] = '8305552555b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_IN_PROGRESS_ANALYSIS_STATUSES = ('QUEUED', 'ANALYZING', 'PLANNING', 'COLLECTING_DATA', 'GENERATING_ANALYSIS')


def upgrade() -> None:
    # --- Aylık rapor e-postası: claim lease ve reconciliation-required son durumu ---
    # NOT: Değer member.value ile değil, Python enum üye ADIYLA (uppercase) eşleşir;
    # gerekçesi için d6f8a0c2e4b7_add_report_storage_and_email_fields.py dosyasına bakın.
    # Sonraki migration'ların bu değeri güvenle filtreleyebilmesi için ayrı commit edilir.
    # Yeni `alembic upgrade head` tüm migration'ları tek transaction içinde çalıştırır;
    # Postgres, enum değerinin eklendiği transaction içinde kullanılmasını yasaklar.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE report_email_status ADD VALUE IF NOT EXISTS 'RECONCILIATION_REQUIRED'")

    op.add_column('foreman_monthly_reports', sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('foreman_monthly_reports', sa.Column('claim_token', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(
        'ix_foreman_monthly_reports_email_status_claimed_at',
        'foreman_monthly_reports', ['email_status', 'claimed_at'],
    )

    # --- Anomali analizi: Anomaly.analysis_status değerini sahiplenen deneme ---
    op.add_column('anomalies', sa.Column('current_analysis_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_anomalies_current_analysis_id', 'anomalies', 'anomaly_analyses',
        ['current_analysis_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(
        'ix_anomaly_analyses_status_started_at', 'anomaly_analyses', ['status', 'started_at'],
    )

    # Her anomali için en fazla bir devam eden deneme olabilir. Asıl claim mekanizması
    # budur: claim, ayrı bir check-then-write değil, başarılı olan veya bu indeksi ihlal
    # eden bir INSERT'tir (bkz. app/services/anomaly_job_claim.py).
    status_list = ", ".join(f"'{v}'" for v in _IN_PROGRESS_ANALYSIS_STATUSES)
    op.execute(
        f"""
        CREATE UNIQUE INDEX uq_anomaly_analyses_one_active_per_anomaly
        ON anomaly_analyses (anomaly_id)
        WHERE status IN ({status_list})
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_anomaly_analyses_one_active_per_anomaly")
    op.drop_index('ix_anomaly_analyses_status_started_at', table_name='anomaly_analyses')
    op.drop_constraint('fk_anomalies_current_analysis_id', 'anomalies', type_='foreignkey')
    op.drop_column('anomalies', 'current_analysis_id')

    op.drop_index('ix_foreman_monthly_reports_email_status_claimed_at', table_name='foreman_monthly_reports')
    op.drop_column('foreman_monthly_reports', 'claim_token')
    op.drop_column('foreman_monthly_reports', 'claimed_at')
    # report_email_status, 'reconciliation_required' değerini korur; Postgres tekil enum
    # değerlerini silemez. Bu durumu bilmeyen eski kod yeniden deploy edilecekse downgrade
    # öncesinde tüm RECONCILIATION_REQUIRED satırları `resolve-stale-email-job` ile çözülmelidir.
