from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c4a99f861289'
down_revision: Union[str, None] = 'f1a3c5e7b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_DESCRIPTION = (
    'Bir vardiyanın (720 dk) ya da tesis/dönem toplamının gerçekleşen çalışma süresinin, '
    'ilgili toplam süreye oranı. Formen düzeyinde kendi vardiyasını, tesis/dönem düzeyinde '
    'vardiyaların toplamını kapsar.'
)


def upgrade() -> None:
    bind = op.get_bind()

    op.drop_constraint('ck_production_records_working_time_minutes_range', 'production_records', type_='check')

    # Mevcut working_time_minutes değerleri fabrika-gün ölçeğindeydi: 0-1440 ve date-parity
    # atamasıyla her fabrika-gün için tek canonical kayıt. Yeni anlam vardiya ölçeğidir:
    # 0-720 ve her V1/V2 kaydının kendi değeri vardır. Ölçekler dönüştürülemediğinden stale
    # değerleri clamp/rescale etmek yerine NULL (eksik) yapmak daha güvenlidir.
    bind.execute(sa.text("UPDATE production_records SET working_time_minutes = NULL WHERE working_time_minutes IS NOT NULL"))

    op.create_check_constraint(
        'ck_production_records_working_time_minutes_range',
        'production_records',
        'working_time_minutes IS NULL OR (working_time_minutes >= 0 AND working_time_minutes <= 720)',
    )

    oee_kpi_id = bind.execute(sa.text("SELECT id FROM kpis WHERE code = 'OEE'")).scalar()
    if oee_kpi_id is None:
        return

    bind.execute(
        sa.text(
            """
            UPDATE kpis
            SET unit = '%', default_target_value = 100, max_valid_value = 100,
                description = :description, updated_at = now()
            WHERE id = :kpi_id
            """
        ),
        {"kpi_id": oee_kpi_id, "description": _NEW_DESCRIPTION},
    )
    bind.execute(
        sa.text(
            "UPDATE kpi_targets SET target_value = 100, updated_at = now() "
            "WHERE kpi_id = :kpi_id AND scope_type = 'COMPANY'::target_scope_type"
        ),
        {"kpi_id": oee_kpi_id},
    )

    # Mevcut OEE performance_records/scores eski raw-minutes ve 1440 hedefiyle hesaplandı;
    # yeni yüzde/720 hedefiyle uyumlu değildir. Stale anlamlı satırları yenileriyle
    # karıştırmamak için silinir ve sonraki ingestion vardiya verisinden doğru üretir.
    bind.execute(
        sa.text(
            "DELETE FROM performance_scores WHERE performance_record_id IN "
            "(SELECT id FROM performance_records WHERE kpi_id = :kpi_id)"
        ),
        {"kpi_id": oee_kpi_id},
    )
    bind.execute(
        sa.text(
            "DELETE FROM data_quality_issues WHERE performance_record_id IN "
            "(SELECT id FROM performance_records WHERE kpi_id = :kpi_id)"
        ),
        {"kpi_id": oee_kpi_id},
    )
    bind.execute(sa.text("DELETE FROM performance_records WHERE kpi_id = :kpi_id"), {"kpi_id": oee_kpi_id})


def downgrade() -> None:
    raise NotImplementedError(
        "OEE shift-level migration is not downgradable: stale plant-day working_time_minutes "
        "values and old-semantic OEE performance_records are deleted, not archived. Restore "
        "from a pre-migration backup and reseed synthetic data instead."
    )
