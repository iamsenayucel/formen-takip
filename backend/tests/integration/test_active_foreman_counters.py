import uuid
from tests.helpers import legacy_json
from datetime import date

import pytest
from sqlalchemy import select

from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.organization import Factory, Plant, Shift
from app.services import assignment_resolver

AS_OF = date(2026, 8, 14)


def _suffix() -> str:
    return uuid.uuid4().hex[:8]


def _make_chief(zone_seq: int) -> Chief:
    suffix = _suffix()
    return Chief(
        id=uuid.uuid4(),
        employee_number=f"TST-SEF-{zone_seq}-{suffix}",
        first_name="Test",
        last_name=f"Sef{suffix}",
        hire_date=date(2020, 1, 1),
        is_active=True,
        email=f"test-chief-{suffix}@formen-test.local",
    )


def _make_plant(factory_id, chief_id, sequence_number: int) -> Plant:
    suffix = _suffix()
    return Plant(
        id=uuid.uuid4(),
        code=f"TST-{suffix}",
        name=f"Test Tesis {suffix}",
        sequence_number=sequence_number,
        factory_id=factory_id,
        chief_id=chief_id,
        is_active=True,
    )


def _make_foreman(*, is_active: bool = True) -> Foreman:
    suffix = _suffix()
    return Foreman(
        id=uuid.uuid4(),
        employee_number=f"TST-FRM-{suffix}",
        first_name="Test",
        last_name=f"Formen{suffix}",
        hire_date=date(2020, 1, 1),
        is_active=is_active,
        email=f"test-foreman-{suffix}@formen-test.local",
    )


def _make_assignment(foreman, plant, chief_id, shift, *, start_date, end_date, is_active) -> ForemanAssignment:
    return ForemanAssignment(
        id=uuid.uuid4(),
        foreman_id=foreman.id,
        plant_id=plant.id,
        chief_id=chief_id,
        shift_id=shift.id,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )


@pytest.fixture
def zone(db_session):
    factory_id = db_session.scalar(select(Factory.id).limit(1))
    shifts = list(db_session.scalars(select(Shift).order_by(Shift.sequence)))
    v1, v2 = shifts[0], shifts[1]

    boundary_chief = _make_chief(1)
    bp_valid = _make_plant(factory_id, boundary_chief.id, sequence_number=9001)
    bp_expired = _make_plant(factory_id, boundary_chief.id, sequence_number=9002)
    bp_future = _make_plant(factory_id, boundary_chief.id, sequence_number=9003)
    bp_inactive_override = _make_plant(factory_id, boundary_chief.id, sequence_number=9004)
    bp_foreman_inactive = _make_plant(factory_id, boundary_chief.id, sequence_number=9005)
    bp_boundary_end = _make_plant(factory_id, boundary_chief.id, sequence_number=9006)

    scope_chief = _make_chief(2)
    sp_a = _make_plant(factory_id, scope_chief.id, sequence_number=9007)
    sp_b = _make_plant(factory_id, scope_chief.id, sequence_number=9008)

    f_valid = _make_foreman()
    f_expired = _make_foreman()
    f_future = _make_foreman()
    f_inactive_override = _make_foreman()
    f_foreman_inactive = _make_foreman(is_active=False)
    f_boundary_end = _make_foreman()
    f_scope_a1 = _make_foreman()
    f_scope_a2 = _make_foreman()
    f_scope_b1 = _make_foreman()

    assignments = [
        _make_assignment(f_valid, bp_valid, boundary_chief.id, v1, start_date=date(2026, 1, 1), end_date=None, is_active=True),
        _make_assignment(f_expired, bp_expired, boundary_chief.id, v1, start_date=date(2026, 1, 1), end_date=date(2026, 6, 30), is_active=False),
        _make_assignment(f_future, bp_future, boundary_chief.id, v1, start_date=date(2026, 9, 1), end_date=None, is_active=True),
        _make_assignment(f_inactive_override, bp_inactive_override, boundary_chief.id, v1, start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), is_active=False),
        _make_assignment(f_foreman_inactive, bp_foreman_inactive, boundary_chief.id, v1, start_date=date(2026, 1, 1), end_date=None, is_active=True),
        _make_assignment(f_boundary_end, bp_boundary_end, boundary_chief.id, v1, start_date=date(2026, 1, 1), end_date=AS_OF, is_active=True),
        _make_assignment(f_scope_a1, sp_a, scope_chief.id, v1, start_date=date(2026, 1, 1), end_date=None, is_active=True),
        _make_assignment(f_scope_a2, sp_a, scope_chief.id, v2, start_date=date(2026, 1, 1), end_date=None, is_active=True),
        _make_assignment(f_scope_b1, sp_b, scope_chief.id, v1, start_date=date(2026, 1, 1), end_date=None, is_active=True),
    ]

    foremen = [
        f_valid, f_expired, f_future, f_inactive_override,
        f_foreman_inactive, f_boundary_end, f_scope_a1, f_scope_a2, f_scope_b1,
    ]
    plants = [bp_valid, bp_expired, bp_future, bp_inactive_override, bp_foreman_inactive, bp_boundary_end, sp_a, sp_b]
    chiefs = [boundary_chief, scope_chief]

    db_session.add_all(chiefs)
    db_session.flush()
    db_session.add_all(plants)
    db_session.flush()
    db_session.add_all(foremen)
    db_session.flush()
    db_session.add_all(assignments)
    db_session.commit()

    try:
        yield {
            "bp_valid": bp_valid, "bp_expired": bp_expired, "bp_future": bp_future,
            "bp_inactive_override": bp_inactive_override, "bp_foreman_inactive": bp_foreman_inactive,
            "bp_boundary_end": bp_boundary_end, "sp_a": sp_a, "sp_b": sp_b,
            "boundary_chief": boundary_chief, "scope_chief": scope_chief,
            "f_valid": f_valid, "f_expired": f_expired, "f_future": f_future,
            "f_inactive_override": f_inactive_override, "f_foreman_inactive": f_foreman_inactive,
            "f_boundary_end": f_boundary_end,
            "f_scope_a1": f_scope_a1, "f_scope_a2": f_scope_a2, "f_scope_b1": f_scope_b1,
        }
    finally:
        db_session.rollback()
        assignment_ids = [a.id for a in assignments]
        foreman_ids = [f.id for f in foremen]
        plant_ids = [p.id for p in plants]
        chief_ids = [c.id for c in chiefs]
        db_session.execute(ForemanAssignment.__table__.delete().where(ForemanAssignment.id.in_(assignment_ids)))
        db_session.execute(Foreman.__table__.delete().where(Foreman.id.in_(foreman_ids)))
        db_session.execute(Plant.__table__.delete().where(Plant.id.in_(plant_ids)))
        db_session.execute(Chief.__table__.delete().where(Chief.id.in_(chief_ids)))
        db_session.commit()


class TestAssignmentsAsOfBoundaries:
    def test_valid_open_ended_assignment_is_counted(self, db_session, zone):
        count = assignment_resolver.active_foreman_count(db_session, AS_OF, plant_id=zone["bp_valid"].id)
        assert count == 1
        foremen = {a.foreman_id for a in db_session.scalars(assignment_resolver.assignments_as_of(AS_OF, plant_id=zone["bp_valid"].id))}
        assert zone["f_valid"].id in foremen

    def test_expired_assignment_is_not_counted(self, db_session, zone):
        foremen = {a.foreman_id for a in db_session.scalars(assignment_resolver.assignments_as_of(AS_OF, plant_id=zone["bp_expired"].id))}
        assert zone["f_expired"].id not in foremen

    def test_future_assignment_is_not_counted_even_if_marked_active(self, db_session, zone):
        foremen = {a.foreman_id for a in db_session.scalars(assignment_resolver.assignments_as_of(AS_OF, plant_id=zone["bp_future"].id))}
        assert zone["f_future"].id not in foremen

    def test_is_active_false_excludes_assignment_within_date_range(self, db_session, zone):
        foremen = {
            a.foreman_id
            for a in db_session.scalars(assignment_resolver.assignments_as_of(AS_OF, plant_id=zone["bp_inactive_override"].id))
        }
        assert zone["f_inactive_override"].id not in foremen

    def test_foreman_inactive_excluded_from_active_count_but_assignment_still_valid(self, db_session, zone):
        plant_id = zone["bp_foreman_inactive"].id
        raw_foremen = {a.foreman_id for a in db_session.scalars(assignment_resolver.assignments_as_of(AS_OF, plant_id=plant_id))}
        assert zone["f_foreman_inactive"].id in raw_foremen

        active_count = assignment_resolver.active_foreman_count(db_session, AS_OF, plant_id=plant_id)
        assert active_count == 0
        active_foremen = {
            a.foreman_id
            for a in db_session.scalars(
                assignment_resolver.assignments_as_of(AS_OF, plant_id=plant_id, active_foreman_only=True)
            )
        }
        assert zone["f_foreman_inactive"].id not in active_foremen

    def test_end_date_equal_to_as_of_is_inclusive(self, db_session, zone):
        active_foremen = {
            a.foreman_id
            for a in db_session.scalars(
                assignment_resolver.assignments_as_of(AS_OF, plant_id=zone["bp_boundary_end"].id, active_foreman_only=True)
            )
        }
        assert zone["f_boundary_end"].id in active_foremen


class TestChiefPlantScopedCounter:
    def test_counts_are_scoped_per_plant_not_leaked_across_chief_zone(self, db_session, zone):
        chief_id = zone["scope_chief"].id
        count_a = assignment_resolver.active_foreman_count(db_session, AS_OF, plant_id=zone["sp_a"].id, chief_id=chief_id)
        count_b = assignment_resolver.active_foreman_count(db_session, AS_OF, plant_id=zone["sp_b"].id, chief_id=chief_id)
        count_chief_only = assignment_resolver.active_foreman_count(db_session, AS_OF, chief_id=chief_id)

        assert count_a == 2
        assert count_b == 1
        assert count_chief_only == 3
        assert count_a != count_chief_only
        assert count_b != count_chief_only


class TestListDetailConsistency:
    def test_list_and_detail_helpers_agree_for_same_plant_and_date(self, db_session, zone):
        plant_id = zone["bp_valid"].id
        list_count = assignment_resolver.active_foreman_counts_by_plant(db_session, AS_OF).get(plant_id, 0)
        detail_count = assignment_resolver.active_foreman_count(db_session, AS_OF, plant_id=plant_id)
        assert list_count == detail_count == 1

    def test_plant_list_and_summary_endpoints_agree(self, client, auth_headers, zone):
        plant_id = str(zone["bp_valid"].id)
        params = {"date_to": AS_OF.isoformat(), "plant_ids": plant_id}

        list_resp = client.get("/api/v1/plants", params=params, headers=auth_headers)
        assert list_resp.status_code == 200
        list_items = legacy_json(list_resp)["items"]
        assert len(list_items) == 1
        assert list_items[0]["active_foreman_count"] == 1

        summary_resp = client.get(f"/api/v1/plants/{plant_id}/summary", params=params, headers=auth_headers)
        assert summary_resp.status_code == 200
        assert legacy_json(summary_resp)["active_foreman_count"] == 1

    def test_plant_chiefs_endpoint_uses_plant_scoped_count(self, client, auth_headers, zone):
        params = {"date_to": AS_OF.isoformat()}
        resp = client.get(f"/api/v1/plants/{zone['sp_a'].id}/chiefs", params=params, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert len(items) == 1
        assert items[0]["foreman_count"] == 2

        resp_b = client.get(f"/api/v1/plants/{zone['sp_b'].id}/chiefs", params=params, headers=auth_headers)
        assert resp_b.status_code == 200
        items_b = legacy_json(resp_b)["items"]
        assert len(items_b) == 1
        assert items_b[0]["foreman_count"] == 1
