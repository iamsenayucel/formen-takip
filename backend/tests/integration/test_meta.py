import uuid
from contextlib import contextmanager

from sqlalchemy import event, select

from app.db.session import engine
from app.models.foreman import Chief
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from tests.helpers import unwrap


@contextmanager
def count_queries():
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


class TestMetaFilters:
    def test_response_field_contract_and_ordering(self, client, auth_headers, db_session):
        resp = client.get("/api/v1/meta/filters", headers=auth_headers)
        assert resp.status_code == 200
        body = unwrap(resp)
        assert set(body.keys()) == {"factories", "plants", "chiefs", "shifts", "kpis"}

        expected_factories = [
            {"id": str(f.id), "code": f.code, "name": f.name, "location": f.location}
            for f in db_session.scalars(select(Factory).where(Factory.is_active.is_(True)).order_by(Factory.code))
        ]
        assert body["factories"] == expected_factories
        assert set(expected_factories[0].keys()) == {"id", "code", "name", "location"}

        expected_plants = [
            {
                "id": str(p.id), "code": p.code, "name": p.name,
                "sequenceNumber": p.sequence_number, "factoryId": str(p.factory_id),
            }
            for p in db_session.scalars(select(Plant).where(Plant.is_active.is_(True)).order_by(Plant.sequence_number))
        ]
        assert body["plants"] == expected_plants
        assert set(expected_plants[0].keys()) == {"id", "code", "name", "sequenceNumber", "factoryId"}

        expected_chief_order = [
            c.employee_number
            for c in db_session.scalars(select(Chief).where(Chief.is_active.is_(True)).order_by(Chief.employee_number))
        ]
        assert [c["employeeNumber"] for c in body["chiefs"]] == expected_chief_order
        assert set(body["chiefs"][0].keys()) == {"id", "employeeNumber", "name", "plantIds"}

        expected_shifts = [
            {"id": str(s.id), "code": s.code, "name": s.name, "sequence": s.sequence, "unit": None, "weight": None}
            for s in db_session.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence))
        ]
        assert body["shifts"] == expected_shifts
        assert len(expected_shifts) == 2

        expected_kpis = [
            {
                "id": str(k.id), "code": k.code, "name": k.name, "unit": k.unit, "weight": float(k.weight),
                "sequence": None,
            }
            for k in db_session.scalars(select(Kpi).where(Kpi.is_active.is_(True)).order_by(Kpi.display_order))
        ]
        assert body["kpis"] == expected_kpis
        assert set(expected_kpis[0].keys()) == {"id", "code", "name", "unit", "weight", "sequence"}

    def test_factory_ids_narrows_plants_and_chiefs(self, client, auth_headers, db_session):
        factory = db_session.scalars(select(Factory).where(Factory.is_active.is_(True)).order_by(Factory.code)).first()

        expected_plants = [
            str(p.id) for p in db_session.scalars(
                select(Plant).where(Plant.is_active.is_(True), Plant.factory_id == factory.id)
                .order_by(Plant.sequence_number)
            )
        ]
        expected_chief_ids = {
            str(c.id) for c in db_session.scalars(
                select(Chief).where(
                    Chief.is_active.is_(True),
                    Chief.id.in_(select(Plant.chief_id).where(Plant.factory_id == factory.id)),
                )
            )
        }

        resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"factory_ids": str(factory.id)})
        assert resp.status_code == 200
        body = unwrap(resp)
        assert [p["id"] for p in body["plants"]] == expected_plants
        assert {c["id"] for c in body["chiefs"]} == expected_chief_ids

    def test_plant_ids_narrows_chiefs_but_not_top_level_plants(self, client, auth_headers, db_session):
        all_active_plant_ids = [
            str(p.id) for p in db_session.scalars(select(Plant).where(Plant.is_active.is_(True)).order_by(Plant.sequence_number))
        ]

        chief_with_multiple_plants = None
        for c in db_session.scalars(select(Chief).where(Chief.is_active.is_(True))):
            zone_plants = list(db_session.scalars(select(Plant).where(Plant.chief_id == c.id)))
            if len(zone_plants) > 1:
                chief_with_multiple_plants = (c, zone_plants)
                break
        assert chief_with_multiple_plants is not None, "seed'de birden fazla tesisli bir şef bulunamadı"
        chief, zone_plants = chief_with_multiple_plants
        filtering_plant = zone_plants[0]
        expected_full_zone_plant_ids = {str(p.id) for p in zone_plants}

        resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"plant_ids": str(filtering_plant.id)})
        assert resp.status_code == 200
        body = unwrap(resp)

        assert [p["id"] for p in body["plants"]] == all_active_plant_ids

        assert [c["id"] for c in body["chiefs"]] == [str(chief.id)]
        assert set(body["chiefs"][0]["plantIds"]) == expected_full_zone_plant_ids
        assert len(body["chiefs"][0]["plantIds"]) == len(zone_plants)

    def test_conflicting_factory_and_plant_ids_precedence(self, client, auth_headers, db_session):
        factories = list(db_session.scalars(select(Factory).where(Factory.is_active.is_(True)).order_by(Factory.code)))
        assert len(factories) >= 2, "test iki farklı fabrika gerektiriyor"
        factory_a, factory_b = factories[0], factories[1]

        plant_in_a = db_session.scalars(
            select(Plant).where(Plant.is_active.is_(True), Plant.factory_id == factory_a.id)
        ).first()
        expected_chief_id = str(plant_in_a.chief_id)

        expected_plants_b = [
            str(p.id) for p in db_session.scalars(
                select(Plant).where(Plant.is_active.is_(True), Plant.factory_id == factory_b.id)
                .order_by(Plant.sequence_number)
            )
        ]

        resp = client.get(
            "/api/v1/meta/filters", headers=auth_headers,
            params={"factory_ids": str(factory_b.id), "plant_ids": str(plant_in_a.id)},
        )
        assert resp.status_code == 200
        body = unwrap(resp)

        assert [p["id"] for p in body["plants"]] == expected_plants_b
        assert [c["id"] for c in body["chiefs"]] == [expected_chief_id]

    def test_nonexistent_factory_id_returns_empty_plants_and_chiefs(self, client, auth_headers):
        nonexistent = str(uuid.uuid4())
        resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"factory_ids": nonexistent})
        assert resp.status_code == 200
        body = unwrap(resp)
        assert body["plants"] == []
        assert body["chiefs"] == []
        assert len(body["factories"]) >= 1
        assert len(body["shifts"]) == 2

    def test_nonexistent_plant_id_returns_empty_chiefs_but_full_plants(self, client, auth_headers, db_session):
        nonexistent = str(uuid.uuid4())
        all_active_plant_ids = [
            str(p.id) for p in db_session.scalars(select(Plant).where(Plant.is_active.is_(True)).order_by(Plant.sequence_number))
        ]

        resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"plant_ids": nonexistent})
        assert resp.status_code == 200
        body = unwrap(resp)
        assert [p["id"] for p in body["plants"]] == all_active_plant_ids
        assert body["chiefs"] == []

    def test_query_count_no_filter(self, client, auth_headers):
        with count_queries() as counter:
            resp = client.get("/api/v1/meta/filters", headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] == 6

    def test_query_count_with_filters(self, client, auth_headers, db_session):
        factories = list(db_session.scalars(select(Factory).where(Factory.is_active.is_(True)).order_by(Factory.code)))
        factory = factories[0]
        plant = db_session.scalars(select(Plant).where(Plant.is_active.is_(True))).first()

        with count_queries() as counter:
            resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"factory_ids": str(factory.id)})
        assert resp.status_code == 200
        assert counter["n"] == 6

        with count_queries() as counter:
            resp = client.get(
                "/api/v1/meta/filters", headers=auth_headers,
                params={"factory_ids": str(factory.id), "plant_ids": str(plant.id)},
            )
        assert resp.status_code == 200
        assert counter["n"] == 6

    def test_comma_only_factory_ids_matches_nothing_not_everything(self, client, auth_headers):
        for raw in (",", ",,", " "):
            resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"factory_ids": raw})
            assert resp.status_code == 200
            body = unwrap(resp)
            assert body["plants"] == [], f"raw={raw!r}"
            assert body["chiefs"] == [], f"raw={raw!r}"

    def test_comma_only_plant_ids_matches_nothing_not_everything(self, client, auth_headers, db_session):
        all_active_plant_ids = [
            str(p.id) for p in db_session.scalars(select(Plant).where(Plant.is_active.is_(True)).order_by(Plant.sequence_number))
        ]
        for raw in (",", ",,", " "):
            resp = client.get("/api/v1/meta/filters", headers=auth_headers, params={"plant_ids": raw})
            assert resp.status_code == 200
            body = unwrap(resp)
            assert body["chiefs"] == [], f"raw={raw!r}"
            assert [p["id"] for p in body["plants"]] == all_active_plant_ids, f"raw={raw!r}"

    def test_comma_only_plant_ids_wins_precedence_over_valid_factory_ids(self, client, auth_headers, db_session):
        factory = db_session.scalars(select(Factory).where(Factory.is_active.is_(True))).first()
        resp = client.get(
            "/api/v1/meta/filters", headers=auth_headers,
            params={"plant_ids": ",", "factory_ids": str(factory.id)},
        )
        assert resp.status_code == 200
        assert unwrap(resp)["chiefs"] == []
