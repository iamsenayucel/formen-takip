import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.enums import CalculationType, TargetScopeType
from app.models.kpi import Kpi, KpiCalculationRule, KpiTarget
from app.models.organization import Plant
from app.services.target_publisher import (
    RulePublishConflictError,
    TargetPublishConflictError,
    publish_rule,
    publish_target,
)


@pytest.fixture
def temp_kpi():
    db = SessionLocal()
    kpi = Kpi(
        id=uuid.uuid4(), code=f"TEST-{uuid.uuid4().hex[:10]}", name="Test KPI (geçici)", unit="pct",
        calculation_type=CalculationType.HIGHER_IS_BETTER, default_target_value=100, weight=0,
        valid_from=date(2020, 1, 1), is_active=False,
    )
    db.add(kpi)
    db.commit()
    kpi_id = kpi.id
    try:
        yield kpi_id
    finally:
        db.rollback()
        db.execute(KpiCalculationRule.__table__.delete().where(KpiCalculationRule.kpi_id == kpi_id))
        db.execute(KpiTarget.__table__.delete().where(KpiTarget.kpi_id == kpi_id))
        db.execute(Kpi.__table__.delete().where(Kpi.id == kpi_id))
        db.commit()
        db.close()


@pytest.fixture
def other_temp_kpi():
    db = SessionLocal()
    kpi = Kpi(
        id=uuid.uuid4(), code=f"TEST-{uuid.uuid4().hex[:10]}", name="Test KPI 2 (geçici)", unit="pct",
        calculation_type=CalculationType.HIGHER_IS_BETTER, default_target_value=100, weight=0,
        valid_from=date(2020, 1, 1), is_active=False,
    )
    db.add(kpi)
    db.commit()
    kpi_id = kpi.id
    try:
        yield kpi_id
    finally:
        db.rollback()
        db.execute(KpiTarget.__table__.delete().where(KpiTarget.kpi_id == kpi_id))
        db.execute(Kpi.__table__.delete().where(Kpi.id == kpi_id))
        db.commit()
        db.close()


def _company_target(kpi_id, valid_from, valid_to, value=100):
    return KpiTarget(
        id=uuid.uuid4(), kpi_id=kpi_id, scope_type=TargetScopeType.COMPANY, scope_id=None,
        target_value=value, valid_from=valid_from, valid_to=valid_to, is_active=True,
    )


def _rule(kpi_id, version, valid_from, valid_to):
    return KpiCalculationRule(
        id=uuid.uuid4(), kpi_id=kpi_id, version=version, calculation_type=CalculationType.HIGHER_IS_BETTER,
        parameters={}, valid_from=valid_from, valid_to=valid_to, is_active=True,
    )


class TestTargetOverlapRejected:
    def test_overlapping_open_ended_targets_rejected(self, temp_kpi):
        db = SessionLocal()
        try:
            db.add(_company_target(temp_kpi, date(2026, 1, 1), date(2026, 8, 31)))
            db.commit()
            db.add(_company_target(temp_kpi, date(2026, 8, 1), date(2026, 12, 31)))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_two_open_ended_targets_rejected(self, temp_kpi):
        db = SessionLocal()
        try:
            db.add(_company_target(temp_kpi, date(2026, 1, 1), None))
            db.commit()
            db.add(_company_target(temp_kpi, date(2026, 8, 1), None))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestSequentialTargetsAccepted:
    def test_back_to_back_targets_are_accepted(self, temp_kpi):
        db = SessionLocal()
        try:
            db.add(_company_target(temp_kpi, date(2026, 1, 1), date(2026, 7, 31)))
            db.add(_company_target(temp_kpi, date(2026, 8, 1), None))
            db.commit()
            rows = list(db.scalars(select(KpiTarget).where(KpiTarget.kpi_id == temp_kpi)))
            assert len(rows) == 2
        finally:
            db.rollback()
            db.close()


class TestDifferentScopeAccepted:
    def test_same_date_range_different_plants_is_allowed(self, temp_kpi):
        db = SessionLocal()
        try:
            plants = list(db.scalars(select(Plant).limit(2)))
            assert len(plants) == 2
            db.add(KpiTarget(
                id=uuid.uuid4(), kpi_id=temp_kpi, scope_type=TargetScopeType.PLANT, scope_id=plants[0].id,
                target_value=100, valid_from=date(2026, 1, 1), valid_to=None, is_active=True,
            ))
            db.add(KpiTarget(
                id=uuid.uuid4(), kpi_id=temp_kpi, scope_type=TargetScopeType.PLANT, scope_id=plants[1].id,
                target_value=110, valid_from=date(2026, 1, 1), valid_to=None, is_active=True,
            ))
            db.commit()
        finally:
            db.rollback()
            db.close()


class TestDifferentKpiAccepted:
    def test_same_date_range_different_kpi_is_allowed(self, temp_kpi, other_temp_kpi):
        db = SessionLocal()
        try:
            db.add(_company_target(temp_kpi, date(2026, 1, 1), None))
            db.add(_company_target(other_temp_kpi, date(2026, 1, 1), None))
            db.commit()
        finally:
            db.rollback()
            db.close()


class TestRuleOverlapRejected:
    def test_overlapping_rules_rejected(self, temp_kpi):
        db = SessionLocal()
        try:
            db.add(_rule(temp_kpi, 1, date(2026, 1, 1), None))
            db.commit()
            db.add(_rule(temp_kpi, 2, date(2026, 6, 1), None))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestInvalidRangeRejected:
    def test_valid_to_before_valid_from_rejected_for_target(self, temp_kpi):
        db = SessionLocal()
        try:
            db.add(_company_target(temp_kpi, date(2026, 8, 10), date(2026, 8, 1)))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_valid_to_before_valid_from_rejected_for_rule(self, temp_kpi):
        db = SessionLocal()
        try:
            db.add(_rule(temp_kpi, 1, date(2026, 8, 10), date(2026, 8, 1)))
            with pytest.raises(IntegrityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestDeterministicResolverAgainstRealDb:
    def test_resolution_is_independent_of_insertion_order(self, temp_kpi):
        from app.services.target_resolver import resolve_target

        db = SessionLocal()
        try:
            db.add(_company_target(temp_kpi, date(2026, 8, 1), None, value=200))
            db.add(_company_target(temp_kpi, date(2026, 1, 1), date(2026, 7, 31), value=100))
            db.commit()

            candidates = list(
                db.scalars(
                    select(KpiTarget)
                    .where(KpiTarget.kpi_id == temp_kpi)
                    .order_by(KpiTarget.valid_from.desc(), KpiTarget.id)
                )
            )
            result = resolve_target(candidates, date(2026, 9, 1), uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
            assert result.target_value == 200

            result_reversed = resolve_target(
                list(reversed(candidates)), date(2026, 9, 1), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
            )
            assert result_reversed.target_value == 200
        finally:
            db.rollback()
            db.close()


class TestPublishTransaction:
    def test_publish_closes_previous_and_opens_new(self, temp_kpi):
        db = SessionLocal()
        try:
            v1 = publish_target(
                db, kpi_id=temp_kpi, scope_type=TargetScopeType.COMPANY, scope_id=None,
                target_value=100, valid_from=date(2026, 1, 1),
            )
            v2 = publish_target(
                db, kpi_id=temp_kpi, scope_type=TargetScopeType.COMPANY, scope_id=None,
                target_value=120, valid_from=date(2026, 9, 1),
            )

            db.expire_all()
            rows = list(db.scalars(select(KpiTarget).where(KpiTarget.kpi_id == temp_kpi)))
            open_rows = [r for r in rows if r.valid_to is None]
            assert len(rows) == 2
            assert len(open_rows) == 1
            assert open_rows[0].id == v2.id
            closed = next(r for r in rows if r.id == v1.id)
            assert closed.valid_to == date(2026, 8, 31)
        finally:
            db.rollback()
            db.close()

    def test_publish_rule_assigns_incrementing_version_and_closes_previous(self, temp_kpi):
        db = SessionLocal()
        try:
            r1 = publish_rule(
                db, kpi_id=temp_kpi, calculation_type=CalculationType.HIGHER_IS_BETTER,
                parameters={}, valid_from=date(2026, 1, 1),
            )
            r2 = publish_rule(
                db, kpi_id=temp_kpi, calculation_type=CalculationType.HIGHER_IS_BETTER,
                parameters={"changed": True}, valid_from=date(2026, 9, 1),
            )
            assert r2.version == r1.version + 1

            db.expire_all()
            rows = list(db.scalars(select(KpiCalculationRule).where(KpiCalculationRule.kpi_id == temp_kpi)))
            open_rows = [r for r in rows if r.valid_to is None]
            assert len(open_rows) == 1
            assert open_rows[0].id == r2.id
        finally:
            db.rollback()
            db.close()


class TestPublishTransactionRollback:
    """Yeni publish penceresiyle çakışan kapalı legacy satırı simüle eder.

    Satır open-ended olmadığından FOR UPDATE ile kapatılamaz ve INSERT exclusion constraint'e
    takılır. Transaction temiz rollback olmalı; kısmi satır bırakmamalı ve mevcut veriye dokunmamalıdır.
    """

    def test_conflicting_publish_rolls_back_and_leaves_previous_untouched(self, temp_kpi):
        db = SessionLocal()
        try:
            historical = _company_target(temp_kpi, date(2026, 1, 1), date(2026, 8, 31))
            legacy_overlap = _company_target(temp_kpi, date(2026, 9, 1), date(2026, 12, 31), value=999)
            db.add(historical)
            db.add(legacy_overlap)
            db.commit()
            historical_id, legacy_id = historical.id, legacy_overlap.id

            with pytest.raises(TargetPublishConflictError):
                publish_target(
                    db, kpi_id=temp_kpi, scope_type=TargetScopeType.COMPANY, scope_id=None,
                    target_value=130, valid_from=date(2026, 9, 1),
                )

            verify_db = SessionLocal()
            try:
                assert verify_db.get(KpiTarget, historical_id).valid_to == date(2026, 8, 31)
                assert verify_db.get(KpiTarget, legacy_id).valid_to == date(2026, 12, 31)
                all_rows = list(verify_db.scalars(select(KpiTarget).where(KpiTarget.kpi_id == temp_kpi)))
                assert len(all_rows) == 2
            finally:
                verify_db.close()
        finally:
            db.rollback()
            db.close()

    def test_conflicting_rule_publish_rolls_back_and_leaves_previous_untouched(self, temp_kpi):
        db = SessionLocal()
        try:
            historical = _rule(temp_kpi, 1, date(2026, 1, 1), date(2026, 8, 31))
            legacy_overlap = _rule(temp_kpi, 999, date(2026, 9, 1), date(2026, 12, 31))
            db.add(historical)
            db.add(legacy_overlap)
            db.commit()
            historical_id, legacy_id = historical.id, legacy_overlap.id

            with pytest.raises(RulePublishConflictError):
                publish_rule(
                    db, kpi_id=temp_kpi, calculation_type=CalculationType.HIGHER_IS_BETTER,
                    parameters={"changed": True}, valid_from=date(2026, 9, 1),
                )

            verify_db = SessionLocal()
            try:
                assert verify_db.get(KpiCalculationRule, historical_id).valid_to == date(2026, 8, 31)
                assert verify_db.get(KpiCalculationRule, legacy_id).valid_to == date(2026, 12, 31)
                all_rows = list(
                    verify_db.scalars(select(KpiCalculationRule).where(KpiCalculationRule.kpi_id == temp_kpi))
                )
                assert len(all_rows) == 2
            finally:
                verify_db.close()
        finally:
            db.rollback()
            db.close()


class TestConcurrentPublish:
    def test_two_concurrent_publishes_never_leave_more_than_one_open_target(self, temp_kpi):
        """İki thread aynı kpi/scope için open-ended hedef publish etmeye yarışır.

        with_for_update ortak durumu serialize eder; kaybeden thread yine ikinci çakışan satırı
        eklemeyi deneyebilir. Son yarışı EXCLUDE constraint yakalar. İki çağrının da başarısı
        değil, DB'de birden fazla açık/çakışan satır kalmaması test edilir.
        """
        seed_db = SessionLocal()
        try:
            publish_target(
                seed_db, kpi_id=temp_kpi, scope_type=TargetScopeType.COMPANY, scope_id=None,
                target_value=100, valid_from=date(2026, 1, 1),
            )
        finally:
            seed_db.close()

        def _publish(valid_from, value):
            db = SessionLocal()
            try:
                publish_target(
                    db, kpi_id=temp_kpi, scope_type=TargetScopeType.COMPANY, scope_id=None,
                    target_value=value, valid_from=valid_from,
                )
                return "ok"
            except TargetPublishConflictError:
                return "conflict"
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            f1 = pool.submit(_publish, date(2026, 6, 1), 150)
            f2 = pool.submit(_publish, date(2026, 9, 1), 200)
            outcomes = {f1.result(), f2.result()}

        assert "ok" in outcomes

        verify_db = SessionLocal()
        try:
            rows = list(verify_db.scalars(select(KpiTarget).where(KpiTarget.kpi_id == temp_kpi)))
            open_rows = [r for r in rows if r.valid_to is None]
            assert len(open_rows) == 1
            ranges_overlap = False
            sorted_rows = sorted(rows, key=lambda r: r.valid_from)
            for a, b in zip(sorted_rows, sorted_rows[1:]):
                if a.valid_to is None or a.valid_to >= b.valid_from:
                    ranges_overlap = True
            assert not ranges_overlap
        finally:
            verify_db.close()
