import json
import uuid
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f1a3c5e7b9d2'
down_revision: Union[str, None] = '9dc3abaf5d62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TODAY = date.today().isoformat()

_OEE_RULE_PARAMS = {
    'formula_type': 'TARGET_RATIO_LINEAR_BONUS',
    'ratio_multiplier': 1.05,
    'max_score': 105,
}

_NEW_WEIGHTS = {
    'AGIR_GITME': 16.67, 'GSF': 16.67, 'ISKARTA': 16.67, 'INKITA': 16.67, 'PLANA_UYUM': 16.66,
}
_OLD_WEIGHTS = {
    'AGIR_GITME': 20, 'GSF': 20, 'ISKARTA': 20, 'INKITA': 20, 'PLANA_UYUM': 20,
}


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column('production_records', sa.Column('working_time_minutes', sa.Numeric(6, 2), nullable=True))
    op.create_check_constraint(
        'ck_production_records_working_time_minutes_range',
        'production_records',
        'working_time_minutes IS NULL OR (working_time_minutes >= 0 AND working_time_minutes <= 1440)',
    )

    existing_kpi_count = bind.execute(sa.text("SELECT count(*) FROM kpis")).scalar()
    if not existing_kpi_count:
        return

    existing_oee = bind.execute(sa.text("SELECT id FROM kpis WHERE code = 'OEE'")).scalar()
    if existing_oee is not None:
        return

    for code, weight in _NEW_WEIGHTS.items():
        bind.execute(
            sa.text("UPDATE kpis SET weight = :weight, updated_at = now() WHERE code = :code"),
            {"weight": weight, "code": code},
        )

    oee_kpi_id = str(uuid.uuid4())
    bind.execute(sa.text(
        """
        INSERT INTO kpis (
            id, code, name, description, unit, calculation_type, success_direction_higher,
            default_target_value, min_valid_value, max_valid_value, min_score, max_score, weight,
            valid_from, is_active, source_data_field, aggregation_method, decimal_places, is_critical,
            display_order, created_at, updated_at
        ) VALUES (
            :id, 'OEE', 'OEE',
            'Bir tesisin bir gün içerisindeki toplam çalışma süresinin, günün toplam 1440 dakikasına oranı.',
            'dk', 'CUSTOM_FORMULA'::calculation_type, true,
            1440, 0, 1440, 0, 105, 16.66,
            :valid_from, true, NULL, 'RATIO_RECOMPUTE'::aggregation_method, 2, true,
            6, now(), now()
        )
        """
    ), {"id": oee_kpi_id, "valid_from": _TODAY})

    oee_rule_id = str(uuid.uuid4())
    bind.execute(sa.text(
        """
        INSERT INTO kpi_calculation_rules (
            id, kpi_id, version, calculation_type, parameters, valid_from, valid_to, is_active,
            created_at, updated_at
        ) VALUES (
            :id, :kpi_id, 1, 'CUSTOM_FORMULA'::calc_rule_type, CAST(:params AS json), :valid_from, NULL, true,
            now(), now()
        )
        """
    ), {"id": oee_rule_id, "kpi_id": oee_kpi_id, "params": json.dumps(_OEE_RULE_PARAMS), "valid_from": _TODAY})

    bind.execute(sa.text(
        """
        INSERT INTO kpi_targets (id, kpi_id, scope_type, scope_id, target_value, valid_from, valid_to, is_active, created_at, updated_at)
        VALUES (:id, :kpi_id, 'COMPANY'::target_scope_type, NULL, 1440, :valid_from, NULL, true, now(), now())
        """
    ), {"id": str(uuid.uuid4()), "kpi_id": oee_kpi_id, "valid_from": _TODAY})


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text(
        "DELETE FROM kpi_targets WHERE kpi_id = (SELECT id FROM kpis WHERE code = 'OEE')"
    ))
    bind.execute(sa.text(
        "DELETE FROM kpi_calculation_rules WHERE kpi_id = (SELECT id FROM kpis WHERE code = 'OEE')"
    ))
    bind.execute(sa.text("DELETE FROM kpis WHERE code = 'OEE'"))

    for code, weight in _OLD_WEIGHTS.items():
        bind.execute(
            sa.text("UPDATE kpis SET weight = :weight, updated_at = now() WHERE code = :code"),
            {"weight": weight, "code": code},
        )

    op.drop_constraint('ck_production_records_working_time_minutes_range', 'production_records', type_='check')
    op.drop_column('production_records', 'working_time_minutes')
