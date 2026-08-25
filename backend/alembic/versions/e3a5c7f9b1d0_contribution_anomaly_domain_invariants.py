"""contribution and anomaly domain invariants

Revision ID: e3a5c7f9b1d0
Revises: b9f2d4a6c8e1
Create Date: 2026-08-14 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e3a5c7f9b1d0'
down_revision: Union[str, None] = 'b9f2d4a6c8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Her kontrol aşağıda eklenen bir CheckConstraint karşılığıdır. Sayımlardan biri sıfırdan
# büyükse constraint mevcut satırları reddeder; bu nedenle upgrade(), veriyi sessizce
# düzeltmek veya silmek yerine şemaya dokunmadan durur. Negatif/aralık dışı değerleri
# clamp etmek anlamlarını değiştirir.
_INVALID_DATA_CHECKS = {
    "contribution_works.previous_duration < 0": "SELECT count(*) FROM contribution_works WHERE previous_duration < 0",
    "contribution_works.new_duration < 0": "SELECT count(*) FROM contribution_works WHERE new_duration < 0",
    "contribution_works.per_occurrence_saving < 0": (
        "SELECT count(*) FROM contribution_works WHERE per_occurrence_saving < 0"
    ),
    "contribution_works.repeat_count < 0": "SELECT count(*) FROM contribution_works WHERE repeat_count < 0",
    "contribution_works.monthly_total_saving_minutes < 0": (
        "SELECT count(*) FROM contribution_works WHERE monthly_total_saving_minutes < 0"
    ),
    "contribution_works.gain_amount < 0": "SELECT count(*) FROM contribution_works WHERE gain_amount < 0",
    "contribution_works.work_date_end < work_date": (
        "SELECT count(*) FROM contribution_works "
        "WHERE work_date IS NOT NULL AND work_date_end IS NOT NULL AND work_date_end < work_date"
    ),
    "anomalies.ml_confidence out of [0,1]": (
        "SELECT count(*) FROM anomalies WHERE ml_confidence < 0 OR ml_confidence > 1"
    ),
    "anomalies.affected_days < 0": "SELECT count(*) FROM anomalies WHERE affected_days < 0",
    "anomalies.total_days < 0": "SELECT count(*) FROM anomalies WHERE total_days < 0",
    "anomalies.affected_days > total_days": (
        "SELECT count(*) FROM anomalies "
        "WHERE affected_days IS NOT NULL AND total_days IS NOT NULL AND affected_days > total_days"
    ),
    "anomalies.period_end < period_start": "SELECT count(*) FROM anomalies WHERE period_end < period_start",
}


def _assert_no_invalid_legacy_data(conn) -> None:
    violations = {}
    for label, query in _INVALID_DATA_CHECKS.items():
        count = conn.execute(sa.text(query)).scalar()
        if count:
            violations[label] = count
    if violations:
        details = "; ".join(f"{label}: {count} kayıt" for label, count in violations.items())
        raise RuntimeError(
            "contribution_works/anomalies tablolarında yeni domain constraint'leriyle çelişen "
            f"mevcut kayıtlar bulundu, migration güvenli değil: {details}. "
            "Bu kayıtları manuel olarak inceleyip düzelttikten sonra migration'ı tekrar çalıştırın."
        )


def upgrade() -> None:
    conn = op.get_bind()
    _assert_no_invalid_legacy_data(conn)

    op.create_check_constraint(
        'ck_contribution_works_date_range',
        'contribution_works',
        'work_date IS NULL OR work_date_end IS NULL OR work_date_end >= work_date',
    )
    op.create_check_constraint(
        'ck_contribution_works_gain_amount_non_negative',
        'contribution_works',
        'gain_amount IS NULL OR gain_amount >= 0',
    )
    op.create_check_constraint(
        'ck_contribution_works_previous_duration_non_negative',
        'contribution_works',
        'previous_duration IS NULL OR previous_duration >= 0',
    )
    op.create_check_constraint(
        'ck_contribution_works_new_duration_non_negative',
        'contribution_works',
        'new_duration IS NULL OR new_duration >= 0',
    )
    op.create_check_constraint(
        'ck_contribution_works_per_occurrence_saving_non_negative',
        'contribution_works',
        'per_occurrence_saving IS NULL OR per_occurrence_saving >= 0',
    )
    op.create_check_constraint(
        'ck_contribution_works_repeat_count_non_negative',
        'contribution_works',
        'repeat_count IS NULL OR repeat_count >= 0',
    )
    op.create_check_constraint(
        'ck_contribution_works_monthly_total_saving_non_negative',
        'contribution_works',
        'monthly_total_saving_minutes IS NULL OR monthly_total_saving_minutes >= 0',
    )

    op.create_check_constraint(
        'ck_anomalies_period_range',
        'anomalies',
        'period_end >= period_start',
    )
    op.create_check_constraint(
        'ck_anomalies_ml_confidence_range',
        'anomalies',
        'ml_confidence >= 0 AND ml_confidence <= 1',
    )
    op.create_check_constraint(
        'ck_anomalies_affected_days_non_negative',
        'anomalies',
        'affected_days IS NULL OR affected_days >= 0',
    )
    op.create_check_constraint(
        'ck_anomalies_total_days_non_negative',
        'anomalies',
        'total_days IS NULL OR total_days >= 0',
    )
    op.create_check_constraint(
        'ck_anomalies_affected_days_lte_total_days',
        'anomalies',
        'affected_days IS NULL OR total_days IS NULL OR affected_days <= total_days',
    )


def downgrade() -> None:
    op.drop_constraint('ck_anomalies_affected_days_lte_total_days', 'anomalies', type_='check')
    op.drop_constraint('ck_anomalies_total_days_non_negative', 'anomalies', type_='check')
    op.drop_constraint('ck_anomalies_affected_days_non_negative', 'anomalies', type_='check')
    op.drop_constraint('ck_anomalies_ml_confidence_range', 'anomalies', type_='check')
    op.drop_constraint('ck_anomalies_period_range', 'anomalies', type_='check')

    op.drop_constraint('ck_contribution_works_monthly_total_saving_non_negative', 'contribution_works', type_='check')
    op.drop_constraint('ck_contribution_works_repeat_count_non_negative', 'contribution_works', type_='check')
    op.drop_constraint('ck_contribution_works_per_occurrence_saving_non_negative', 'contribution_works', type_='check')
    op.drop_constraint('ck_contribution_works_new_duration_non_negative', 'contribution_works', type_='check')
    op.drop_constraint('ck_contribution_works_previous_duration_non_negative', 'contribution_works', type_='check')
    op.drop_constraint('ck_contribution_works_gain_amount_non_negative', 'contribution_works', type_='check')
    op.drop_constraint('ck_contribution_works_date_range', 'contribution_works', type_='check')
