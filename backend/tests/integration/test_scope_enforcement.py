import pytest
from sqlalchemy import delete, select

from app.models.contribution import ContributionWork
from app.models.enums import Role, ScopeType
from app.models.organization import Factory, Plant
from app.models.report import ReportExport
from tests.helpers import unwrap, unwrap_page

from .conftest import TEST_SUBJECT


@pytest.fixture(autouse=True)
def _cleanup_created_rows(db_session):
    """Bu dosyadaki testler gerçek rapor/katkı çalışması oluşturur — diğer dosyalardaki
    sayım bazlı assertion'lara sızmasın diye her testten sonra temizlenir."""
    yield
    db_session.rollback()
    db_session.execute(delete(ReportExport).where(ReportExport.requested_by_subject == TEST_SUBJECT))
    db_session.execute(delete(ContributionWork).where(ContributionWork.created_by_subject == TEST_SUBJECT))
    db_session.commit()


def _two_plants_in_different_factories(db_session):
    factories = list(db_session.scalars(select(Factory).order_by(Factory.code)))
    for factory in factories:
        plants = list(db_session.scalars(select(Plant).where(Plant.factory_id == factory.id)))
        if plants:
            plant_a = plants[0]
            break
    else:
        raise AssertionError("Seed edilmiş veritabanında en az bir tesis bekleniyor.")

    other_plant = db_session.scalar(select(Plant).where(Plant.factory_id != plant_a.factory_id))
    assert other_plant is not None, "Test için en az iki farklı fabrikada tesis bekleniyor."
    return plant_a, other_plant


class TestPlantScopeFilteringNarrowsSilently:
    """Scope dışı bir plant_id query param'ı ile filtreleme, hata değil, boş sonuç
    döndürmeli (`GET /plants?plant_ids=OTHER_PLANT` -> yetkisiz veri sızdırmamalı)."""

    def test_requesting_out_of_scope_plant_id_returns_empty_not_all(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, other_plant = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        resp = client.get(f"/api/v1/plants?plant_ids={other_plant.id}", headers=auth_headers)
        assert resp.status_code == 200
        items, _ = unwrap_page(resp)
        assert items == [], (
            "Scope dışı bir plant_id istendiğinde kesişim boş olmalı — truthiness bug'ı "
            "geri gelirse burada TÜM tesisler dönerdi (regresyon testi)."
        )

    def test_own_scope_plant_is_visible(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, _ = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        resp = client.get("/api/v1/plants", headers=auth_headers)
        assert resp.status_code == 200
        items, _ = unwrap_page(resp)
        assert {item["id"] for item in items} == {str(plant_a.id)}


class TestResourceByIdScopeIsForbidden:
    """IDOR: tek bir kaynağa doğrudan ID ile erişim, scope dışındaysa 403 dönmeli — liste
    filtrelemesinden farklı olarak burada sessiz daraltma değil, ret vardır."""

    def test_plant_detail_outside_scope_is_403(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, other_plant = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        resp = client.get(f"/api/v1/plants/{other_plant.id}", headers=auth_headers)
        assert resp.status_code == 403

    def test_plant_detail_inside_scope_is_200(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, _ = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        resp = client.get(f"/api/v1/plants/{plant_a.id}", headers=auth_headers)
        assert resp.status_code == 200


class TestFactoryScopeExpandsToMemberPlants:
    """FACTORY tipi bir scope satırı, üye tesislere genişletilmeli (tek eksen: plant_ids) —
    aksi halde FACTORY-scope'lu bir kullanıcının plant_id bazlı kontrolleri kısıtsız kalırdı."""

    def test_factory_scope_grants_access_to_its_plants_only(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, other_plant = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.FACTORY, factory_id=plant_a.factory_id)

        own_factory_resp = client.get(f"/api/v1/plants/{plant_a.id}", headers=auth_headers)
        assert own_factory_resp.status_code == 200

        other_factory_resp = client.get(f"/api/v1/plants/{other_plant.id}", headers=auth_headers)
        assert other_factory_resp.status_code == 403


class TestReportDownloadScopeSubsetCheck:
    """Kapsamsız (şirket geneli) bir rapor, scope-kısıtlı bir kullanıcı tarafından
    indirilememeli; raporun filtresi kendi scope'unun bir alt kümesi olmalı."""

    def test_unfiltered_report_is_not_downloadable_by_scoped_user(
        self, client, auth_headers, role_assignment_factory, db_session
    ):
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.ALL)
        generate_resp = client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"reportType": "company_summary", "format": "csv"},
        )
        assert generate_resp.status_code == 201
        report_id = unwrap(generate_resp)["id"]

        plant_a, _ = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        download_resp = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert download_resp.status_code == 403

    def test_report_within_scope_is_downloadable(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, _ = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        generate_resp = client.post(
            "/api/v1/reports/generate",
            headers=auth_headers,
            json={"reportType": "company_summary", "format": "csv", "plantIds": [str(plant_a.id)]},
        )
        assert generate_resp.status_code == 201
        report_id = unwrap(generate_resp)["id"]

        download_resp = client.get(f"/api/v1/reports/{report_id}/download", headers=auth_headers)
        assert download_resp.status_code == 200


class TestContributionWorkScopeIsForbiddenAcrossZones:
    def test_create_outside_scope_is_forbidden(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, other_plant = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.SUPERVISOR, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])

        resp = client.post(
            "/api/v1/contribution-works",
            headers=auth_headers,
            json={"title": "Scope disi calisma", "plantIds": [str(other_plant.id)]},
        )
        assert resp.status_code == 403

    def test_get_work_outside_scope_is_forbidden(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, other_plant = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.ALL)
        create_resp = client.post(
            "/api/v1/contribution-works",
            headers=auth_headers,
            json={"title": "Diger bolgeye ait calisma", "plantIds": [str(other_plant.id)]},
        )
        assert create_resp.status_code == 201
        work_id = unwrap(create_resp)["id"]

        role_assignment_factory(role=Role.SUPERVISOR, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])
        get_resp = client.get(f"/api/v1/contribution-works/{work_id}", headers=auth_headers)
        assert get_resp.status_code == 403


class TestNoOwnSubjectLeakage:
    """`TEST_SUBJECT`'in role/scope ataması diğer testlere sızmamalı — her testte
    `role_assignment_factory` çağrısı önceki atamanın üzerine yazar (idempotent upsert)."""

    def test_reassigning_role_replaces_previous_scope(self, client, auth_headers, role_assignment_factory, db_session):
        plant_a, other_plant = _two_plants_in_different_factories(db_session)
        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.PLANT, plant_ids=[plant_a.id])
        assert client.get(f"/api/v1/plants/{other_plant.id}", headers=auth_headers).status_code == 403

        role_assignment_factory(role=Role.OPERATIONS_MANAGER, scope_type=ScopeType.ALL)
        assert client.get(f"/api/v1/plants/{other_plant.id}", headers=auth_headers).status_code == 200
