"""kpi target rule overlap integrity

Revision ID: 8305552555b2
Revises: c2e4f6a8b0d5
Create Date: 2026-08-14 12:25:34.298795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8305552555b2'
down_revision: Union[str, None] = 'c2e4f6a8b0d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TARGET_OVERLAP_QUERY = """
    SELECT a.id, b.id FROM kpi_targets a
    JOIN kpi_targets b ON a.kpi_id = b.kpi_id
        AND a.scope_type = b.scope_type
        AND COALESCE(a.scope_id, '00000000-0000-0000-0000-000000000000'::uuid)
            = COALESCE(b.scope_id, '00000000-0000-0000-0000-000000000000'::uuid)
        AND a.id < b.id
        AND daterange(a.valid_from, a.valid_to, '[]') && daterange(b.valid_from, b.valid_to, '[]')
    LIMIT 5
"""

_RULE_OVERLAP_QUERY = """
    SELECT a.id, b.id FROM kpi_calculation_rules a
    JOIN kpi_calculation_rules b ON a.kpi_id = b.kpi_id AND a.id < b.id
        AND daterange(a.valid_from, a.valid_to, '[]') && daterange(b.valid_from, b.valid_to, '[]')
    LIMIT 5
"""

_INVALID_RANGE_QUERY = """
    SELECT id FROM {table} WHERE valid_to IS NOT NULL AND valid_to < valid_from LIMIT 5
"""


def _fail_if_dirty() -> None:
    bind = op.get_bind()
    conflicts = bind.execute(sa.text(_TARGET_OVERLAP_QUERY)).fetchall()
    if conflicts:
        raise RuntimeError(
            "kpi_targets tablosunda çakışan geçerlilik aralıkları bulundu, migration güvenle uygulanamıyor. "
            f"Örnek çakışan kayıt çiftleri (id, id): {conflicts}. "
            "Önce bu kayıtları inceleyip (version/created_at/valid_from bilgisine göre canonical kaydı belirleyip "
            "diğerini kapatarak) düzeltin."
        )
    conflicts = bind.execute(sa.text(_RULE_OVERLAP_QUERY)).fetchall()
    if conflicts:
        raise RuntimeError(
            "kpi_calculation_rules tablosunda çakışan geçerlilik aralıkları bulundu, migration güvenle "
            f"uygulanamıyor. Örnek çakışan kayıt çiftleri (id, id): {conflicts}."
        )
    for table in ("kpi_targets", "kpi_calculation_rules"):
        invalid = bind.execute(sa.text(_INVALID_RANGE_QUERY.format(table=table))).fetchall()
        if invalid:
            raise RuntimeError(
                f"{table} tablosunda valid_to < valid_from olan geçersiz kayıtlar bulundu: {invalid}."
            )


def upgrade() -> None:
    _fail_if_dirty()

    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_check_constraint(
        'ck_kpi_targets_date_range',
        'kpi_targets',
        'valid_to IS NULL OR valid_to >= valid_from',
    )
    op.create_check_constraint(
        'ck_kpi_calculation_rules_date_range',
        'kpi_calculation_rules',
        'valid_to IS NULL OR valid_to >= valid_from',
    )

    op.execute(
        """
        ALTER TABLE kpi_targets
        ADD CONSTRAINT excl_kpi_targets_overlap
        EXCLUDE USING gist (
            kpi_id WITH =,
            scope_type WITH =,
            COALESCE(scope_id, '00000000-0000-0000-0000-000000000000'::uuid) WITH =,
            daterange(valid_from, valid_to, '[]') WITH &&
        )
        """
    )
    op.execute(
        """
        ALTER TABLE kpi_calculation_rules
        ADD CONSTRAINT excl_kpi_calculation_rules_overlap
        EXCLUDE USING gist (
            kpi_id WITH =,
            daterange(valid_from, valid_to, '[]') WITH &&
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE kpi_calculation_rules DROP CONSTRAINT excl_kpi_calculation_rules_overlap")
    op.execute("ALTER TABLE kpi_targets DROP CONSTRAINT excl_kpi_targets_overlap")
    op.drop_constraint('ck_kpi_calculation_rules_date_range', 'kpi_calculation_rules', type_='check')
    op.drop_constraint('ck_kpi_targets_date_range', 'kpi_targets', type_='check')
