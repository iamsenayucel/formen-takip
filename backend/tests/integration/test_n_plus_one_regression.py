
import uuid
from tests.helpers import legacy_json
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, event, select

from app.db.session import engine
from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.contribution import ContributionWork
from app.models.enums import (
    AnalysisMode,
    AnomalyAnalysisStatus,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    ReportFormat,
    ReportStatus,
    ReportType,
)
from app.models.foreman import Foreman
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant
from app.models.report import ReportExport
from app.services.synthetic import world


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


class TestReportListQueryCount:
    def test_query_count_does_not_scale_with_distinct_requesters(self, client, auth_headers, db_session):
        now = datetime.now(timezone.utc)
        new_ids = []
        for i in range(6):
            export = ReportExport(
                id=uuid.uuid4(), report_type=ReportType.COMPANY_SUMMARY, format=ReportFormat.CSV,
                filters_json={}, requested_by_subject=f"n1-report-test-{uuid.uuid4().hex[:8]}",
                file_name=f"n1-test-{i}.csv", file_content=b"x", row_count=0,
                status=ReportStatus.COMPLETED, completed_at=now,
            )
            db_session.add(export)
            new_ids.append(export.id)
        db_session.commit()

        try:
            with count_queries() as counter:
                resp = client.get("/api/v1/reports", params={"limit": 200}, headers=auth_headers)
            assert resp.status_code == 200
            returned_ids = {i["id"] for i in legacy_json(resp)["items"]}
            assert all(str(eid) in returned_ids for eid in new_ids)
            assert counter["n"] <= 6, f"Beklenenden fazla sorgu: {counter['n']}"
        finally:
            db_session.execute(ReportExport.__table__.delete().where(ReportExport.id.in_(new_ids)))
            db_session.commit()


class TestContributionListQueryCount:
    def test_query_count_stays_flat_as_work_count_grows(self, client, auth_headers, db_session):
        foremen = list(db_session.scalars(select(Foreman).where(Foreman.is_active.is_(True)).limit(3)))
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(3)))
        assert len(foremen) >= 3 and len(plants) >= 3

        token = uuid.uuid4().hex[:8]
        new_ids: list[str] = []

        def _create(n: int):
            for i in range(n):
                resp = client.post(
                    "/api/v1/contribution-works",
                    json={
                        "title": f"N+1 liste testi {token} #{len(new_ids)}", "status": "published", "work_type": "kaizen",
                        "summary": "s", "problem_description": "p", "solution_description": "s",
                        "foreman_ids": [str(f.id) for f in foremen], "plant_ids": [str(p.id) for p in plants],
                        "work_date": date.today().isoformat(), "impact_level": "medium",
                        "gains": [{"gain_type": "scrap_reduction", "previous_value": 100, "next_value": 80, "unit": "%"}],
                    },
                    headers=auth_headers,
                )
                assert resp.status_code == 201, resp.text
                new_ids.append(legacy_json(resp)["id"])

        try:
            query_counts: dict[int, int] = {}
            for target in (1, 10, 25):
                _create(target - len(new_ids))
                with count_queries() as counter:
                    resp = client.get(
                        "/api/v1/contribution-works",
                        params={"search": f"N+1 liste testi {token}", "limit": target, "sort_by": "date"},
                        headers=auth_headers,
                    )
                assert resp.status_code == 200
                assert len(legacy_json(resp)["items"]) == target
                query_counts[target] = counter["n"]

            assert query_counts[1] == query_counts[10] == query_counts[25], (
                f"Sorgu sayısı kayıt sayısıyla birlikte büyüyor: {query_counts}"
            )
            assert query_counts[25] <= 6, f"Beklenenden fazla sorgu: {query_counts[25]}"
        finally:
            db_session.execute(ContributionWork.__table__.delete().where(ContributionWork.id.in_(new_ids)))
            db_session.commit()

    def test_query_count_stays_flat_across_sort_modes(self, client, auth_headers, db_session):
        foremen = list(db_session.scalars(select(Foreman).where(Foreman.is_active.is_(True)).limit(2)))
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(2)))
        token = uuid.uuid4().hex[:8]
        new_ids: list[str] = []
        try:
            for i in range(6):
                resp = client.post(
                    "/api/v1/contribution-works",
                    json={
                        "title": f"Sort N+1 testi {token} #{i}", "status": "published", "work_type": "smed",
                        "summary": "s", "problem_description": "p", "solution_description": "s",
                        "foreman_ids": [str(f.id) for f in foremen], "plant_ids": [str(p.id) for p in plants],
                        "work_date": date.today().isoformat(), "impact_level": "low",
                        "gain_amount": 1000 * (i + 1), "currency": "TRY",
                    },
                    headers=auth_headers,
                )
                assert resp.status_code == 201, resp.text
                new_ids.append(legacy_json(resp)["id"])

            for sort_by in ("title", "type", "foreman", "plant", "gain", "date", "status"):
                with count_queries() as counter:
                    resp = client.get(
                        "/api/v1/contribution-works",
                        params={"search": f"Sort N+1 testi {token}", "limit": 25, "sort_by": sort_by},
                        headers=auth_headers,
                    )
                assert resp.status_code == 200
                assert counter["n"] <= 6, f"sort_by={sort_by} beklenenden fazla sorgu üretti: {counter['n']}"
        finally:
            db_session.execute(ContributionWork.__table__.delete().where(ContributionWork.id.in_(new_ids)))
            db_session.commit()


class TestAnomalyListQueryCount:
    def test_query_count_stays_flat_as_anomaly_count_grows(self, client, auth_headers, db_session):
        template = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
        assert template is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(5)))
        kpis = list(db_session.scalars(select(Kpi).limit(5)))
        assert len(plants) >= 5 and len(kpis) >= 5

        token = uuid.uuid4().hex[:8]
        now = datetime.now(timezone.utc)
        created: list[Anomaly] = []

        def _make(n: int):
            for _ in range(n):
                i = len(created)
                anomaly = Anomaly(
                    code=f"ANM-N1-{token}-{i}",
                    title=f"N+1 liste testi {token}",
                    description="N+1 regression testi",
                    anomaly_type=template.anomaly_type,
                    severity=template.severity,
                    status=template.status,
                    analysis_status=template.analysis_status,
                    detected_at=now,
                    plant_id=plants[i % len(plants)].id,
                    shift_id=template.shift_id,
                    kpi_id=kpis[i % len(kpis)].id,
                    period_start=template.period_start,
                    period_end=template.period_end,
                    observed_value=1.0,
                    expected_value=1.0,
                    unit="%",
                    deviation_percent=0.0,
                    ml_confidence=0.5,
                    comparison={},
                    related_signals=[],
                    evidence=[],
                    foreman_ids=[],
                )
                db_session.add(anomaly)
                created.append(anomaly)
            db_session.commit()

        try:
            query_counts: dict[int, int] = {}
            for target in (1, 5, 20):
                _make(target - len(created))
                with count_queries() as counter:
                    resp = client.get(
                        "/api/v1/anomalies",
                        params={"search": f"N+1 liste testi {token}", "limit": 200},
                        headers=auth_headers,
                    )
                assert resp.status_code == 200
                assert legacy_json(resp)["total"] == target
                query_counts[target] = counter["n"]

            assert query_counts[1] == query_counts[5] == query_counts[20], (
                f"Sorgu sayısı kayıt sayısıyla birlikte büyüyor: {query_counts}"
            )
            assert query_counts[20] <= 6, f"Beklenenden fazla sorgu: {query_counts[20]}"
        finally:
            db_session.execute(Anomaly.__table__.delete().where(Anomaly.id.in_([a.id for a in created])))
            db_session.commit()


class TestAnomalySummaryQueryCount:
    def test_query_count_is_constant(self, client, auth_headers):
        with count_queries() as counter:
            resp = client.get("/api/v1/anomalies/summary", headers=auth_headers)
        assert resp.status_code == 200
        assert counter["n"] <= 2, f"Summary sorgu sayısı beklenenden fazla: {counter['n']}"


def _make_detail_anomaly(db_session, template: Anomaly, foreman_ids: list[str]) -> Anomaly:
    anomaly = Anomaly(
        code=f"ANM-N1-DETAIL-{uuid.uuid4().hex[:8]}",
        title="N+1 detail testi", description="N+1 detail testi",
        anomaly_type=template.anomaly_type, severity=template.severity, status=template.status,
        analysis_status=template.analysis_status, detected_at=datetime.now(timezone.utc),
        plant_id=template.plant_id, shift_id=template.shift_id, kpi_id=template.kpi_id,
        period_start=template.period_start, period_end=template.period_end,
        observed_value=1.0, expected_value=1.0, unit="%", deviation_percent=0.0, ml_confidence=0.5,
        comparison={}, related_signals=[], evidence=[],
        foreman_ids=foreman_ids,
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)
    return anomaly


def _add_analysis(db_session, anomaly: Anomaly, offset_hours: int) -> AnomalyAnalysis:
    now = datetime.now(timezone.utc)
    a = AnomalyAnalysis(
        code=f"AAN-N1-{uuid.uuid4().hex[:10]}", anomaly_id=anomaly.id, model="demo", is_demo=True,
        mode=AnalysisMode.SINGLE_CONTEXT, status=AnomalyAnalysisStatus.COMPLETED,
        result={"x": offset_hours}, started_at=now - timedelta(hours=offset_hours),
        completed_at=now - timedelta(hours=offset_hours) + timedelta(minutes=1),
    )
    db_session.add(a)
    db_session.commit()
    return a


class TestAnomalyDetailQueryCount:
    def test_query_count_is_flat_as_analysis_history_grows(self, client, auth_headers, db_session):
        """foreman_ids sabitken analiz satırı 1'den 10'a çıktığında tool-call query sayısı
        büyümemelidir; GROUP BY batch sorgusu sabittir.
        """
        template = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
        assert template is not None
        foreman = db_session.scalars(select(Foreman).limit(1)).first()
        assert foreman is not None

        anomaly = _make_detail_anomaly(db_session, template, [str(foreman.id)])
        try:
            _add_analysis(db_session, anomaly, 0)
            with count_queries() as c:
                resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
            assert resp.status_code == 200
            assert len(legacy_json(resp)["analysis_history"]) == 1
            one_analysis_queries = c["n"]

            for i in range(1, 10):
                _add_analysis(db_session, anomaly, i)

            with count_queries() as c:
                resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
            assert resp.status_code == 200
            assert len(legacy_json(resp)["analysis_history"]) == 10
            ten_analyses_queries = c["n"]

            assert one_analysis_queries == ten_analyses_queries, (
                f"Sorgu sayısı analysis_history büyüklüğüyle büyüyor: 1 analiz={one_analysis_queries}, "
                f"10 analiz={ten_analyses_queries}"
            )
        finally:
            db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == anomaly.id))
            db_session.execute(delete(Anomaly).where(Anomaly.id == anomaly.id))
            db_session.commit()

    def test_foreman_batch_lookup_no_longer_scales_two_per_foreman(self, client, auth_headers, db_session):
        """Kısmi formen lookup N+1 düzeltmesini kilitler.

        Detail helper lookup'ı tek IN(...) query ile batch çalışır. Ortak LLM payload builder
        kapsam dışı olduğu ve formen başına db.get() çağırdığı için sayı tamamen sabit değildir;
        ek formen başına yaklaşık bir sorguluk bounded-linear davranış beklenir.
        """
        template = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
        assert template is not None
        foremen = list(db_session.scalars(select(Foreman).limit(3)))
        assert len(foremen) >= 3

        one = _make_detail_anomaly(db_session, template, [str(foremen[0].id)])
        three = _make_detail_anomaly(db_session, template, [str(f.id) for f in foremen])
        try:
            with count_queries() as c:
                resp = client.get(f"/api/v1/anomalies/{one.id}", headers=auth_headers)
            assert resp.status_code == 200
            one_foreman_queries = c["n"]

            with count_queries() as c:
                resp = client.get(f"/api/v1/anomalies/{three.id}", headers=auth_headers)
            assert resp.status_code == 200
            three_foremen_queries = c["n"]

            # Önceden formen başına iki unbatched sorgu vardı: detail helper içindeki foreman_codes
            # döngüsü ve build_analysis_package; iki ek formen dört sorgu ekliyordu. İlk lookup artık
            # tek IN(...) sorgusunda batch çalışır. Yalnızca dokunulmayan build_analysis_package
            # döngüsü yaklaşık formen başına bir sorgu ölçeğinde kalır. Ortamlar arası küçük farklar
            # testin konusu olmadığından tam delta yerine küçük bir üst sınır doğrulanır.
            growth = three_foremen_queries - one_foreman_queries
            assert 0 <= growth <= 2, (
                f"1 formen={one_foreman_queries}, 3 formen={three_foremen_queries} (fark={growth}); "
                "+2 formen için beklenen büyüme küçük ve sınırlı olmalı (eski davranış: +4)"
            )
        finally:
            db_session.execute(delete(Anomaly).where(Anomaly.id.in_([one.id, three.id])))
            db_session.commit()


@contextmanager
def count_matching_queries(substrings: tuple[str, ...]):
    """Tüm substring'leri içeren statement'ları sayar.

    Belirli query ailesini request içindeki diğer sorgulardan ayırmak için count_queries()
    fonksiyonundan daha dar çalışır.
    """
    counter = {"n": 0}

    def _on_execute(conn, cursor, statement, parameters, context, executemany):
        if all(s in statement for s in substrings):
            counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _on_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)


class TestInvestigationActiveShiftQueryCount:
    """4B-2A1 regresyonu: compare_factories active-shift listesini eskiden her gün x fabrika
    için yeniden yüklüyordu. Artık request başına bir kez yükler. compare_shifts içindeki
    period_days x 1 maliyeti burada bilerek korunur; 21 ve 14 günlük anomaliler arasındaki
    fark gün sayısını izlemeli, fabrika sayısıyla çarpılmamalıdır.
    """

    def test_active_shift_query_count_no_longer_scales_with_plant_count(self, client, auth_headers, db_session):
        a21 = db_session.scalar(select(Anomaly).where(Anomaly.code == "ANM-2026-0001"))
        a14 = db_session.scalar(select(Anomaly).where(Anomaly.code == "ANM-2026-0009"))
        assert a21 is not None and a14 is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
        period_21 = (a21.period_end - a21.period_start).days + 1
        period_14 = (a14.period_end - a14.period_start).days + 1
        assert period_21 == 21 and period_14 == 14, (
            f"Seed verisi beklenenden farklı (period_days: {period_21}, {period_14}); test varsayımları geçersiz."
        )

        with count_matching_queries(("FROM shifts", "is_active")) as c21:
            resp = client.get(f"/api/v1/anomalies/{a21.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200
        shift_queries_21 = c21["n"]

        with count_matching_queries(("FROM shifts", "is_active")) as c14:
            resp = client.get(f"/api/v1/anomalies/{a14.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200
        shift_queries_14 = c14["n"]

        # Önceden yaklaşık period_days * (active_plants + 1) sorgu vardı: 21*51=1071 ve
        # 14*51=714, fark yaklaşık 357 idi. Artık yalnızca compare_shifts içindeki dokunulmayan
        # period_days*1 kalır; fark fabrika sayısıyla çarpılmak yerine gün farkını (7) ve küçük
        # sabit maliyeti izlemelidir.
        day_delta = period_21 - period_14
        diff = abs(shift_queries_21 - shift_queries_14)
        assert diff <= day_delta + 5, (
            f"Active-shift sorgu sayısı hâlâ plant count ile ölçekleniyor: 21 gün={shift_queries_21} sorgu, "
            f"14 gün={shift_queries_14} sorgu (fark={diff}, beklenen üst sınır={day_delta + 5} "
            f"— yalnızca compare_shifts'in kapsam dışı bırakılan period_days×1 kalıntısı kadar olmalı)"
        )
        # Mutlak üst sınır, değeri iki mertebe büyütecek O(days*plants) regresyonunu yakalar.
        assert shift_queries_21 <= 60, f"Active-shift sorgu sayısı beklenenden çok fazla: {shift_queries_21}"
        assert shift_queries_14 <= 60, f"Active-shift sorgu sayısı beklenenden çok fazla: {shift_queries_14}"

    def test_shift_query_count_does_not_scale_with_period_days_at_all(self, client, auth_headers, db_session):
        """4B-2A2: compare_shifts plant_average düzeltmesinden sonra active-shift query sayısı
        period_days ile büyümemelidir. 21 ve 14 günlük anomaliler arasında yalnızca bir kerelik
        setup fetch'leri fark edebilir.
        """
        a21 = db_session.scalar(select(Anomaly).where(Anomaly.code == "ANM-2026-0001"))
        a14 = db_session.scalar(select(Anomaly).where(Anomaly.code == "ANM-2026-0009"))
        assert a21 is not None and a14 is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."

        with count_matching_queries(("FROM shifts", "is_active")) as c21:
            resp = client.get(f"/api/v1/anomalies/{a21.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200
        shift_queries_21 = c21["n"]

        with count_matching_queries(("FROM shifts", "is_active")) as c14:
            resp = client.get(f"/api/v1/anomalies/{a14.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200
        shift_queries_14 = c14["n"]

        diff = abs(shift_queries_21 - shift_queries_14)
        assert diff <= 5, (
            f"Active-shift sorgu sayısı hâlâ period_days ile ölçekleniyor: 21 gün={shift_queries_21} sorgu, "
            f"14 gün={shift_queries_14} sorgu (fark={diff}) — compare_shifts'in plant_average kalıntısı "
            f"düzeltilmiş olmalıydı"
        )
        assert shift_queries_21 <= 10, f"Active-shift sorgu sayısı beklenenden fazla: {shift_queries_21}"
        assert shift_queries_14 <= 10, f"Active-shift sorgu sayısı beklenenden fazla: {shift_queries_14}"


class TestSimilarHistoricalCasesQueryCount:
    """4B-2C regresyonu: similar_historical_cases içindeki Plant/Kpi lookup sorgularının
    aday sayısıyla büyümemesini doğrular. HTTP katmanından bağımsız scoring adayları üretir
    ve finally içinde temizler.
    """

    def _make_candidate(self, db_session, *, code, plant_id, kpi_id, detected_at):
        a = Anomaly(
            code=code, title=f"4B-2C N+1 fixture {code}", description=f"4B-2C N+1 fixture {code}",
            anomaly_type=AnomalyType.RISING_TREND, severity=AnomalySeverity.MEDIUM, status=AnomalyStatus.NEW,
            analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED, detected_at=detected_at,
            plant_id=plant_id, shift_id=None, kpi_id=kpi_id,
            period_start=detected_at.date(), period_end=detected_at.date(),
            observed_value=1.0, expected_value=2.0, unit="%", deviation_percent=50.0, ml_confidence=0.5,
            comparison={}, related_signals=[], evidence=[], foreman_ids=[],
        )
        db_session.add(a)
        return a

    def test_relation_query_count_does_not_scale_with_candidate_count(self, db_session):
        target = db_session.scalar(select(Anomaly).where(Anomaly.code == "ANM-2026-0001"))
        assert target is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
        target_plant = db_session.get(Plant, target.plant_id)
        target_factory = db_session.get(Factory, target_plant.factory_id)
        target_kpi = db_session.get(Kpi, target.kpi_id)

        # Farklı fabrikalar aynı factory içindedir; her aday factory-match dalından sıfırdan
        # büyük score alır ve filtrelenmez. Bu nedenle scoring her birini çözmelidir.
        other_plants = list(
            db_session.scalars(
                select(Plant).where(Plant.factory_id == target_factory.id, Plant.id != target_plant.id).limit(15)
            )
        )
        assert len(other_plants) >= 15, "Test için K1 fabrikasında yeterli tesis bulunamadı."

        token = uuid.uuid4().hex[:8]
        base = datetime(2020, 1, 1, tzinfo=timezone.utc)
        created: list[Anomaly] = []

        try:
            for i in range(3):
                a = self._make_candidate(
                    db_session, code=f"ANM-N1-SIM-{token}-{i}", plant_id=other_plants[i].id,
                    kpi_id=target_kpi.id, detected_at=base + timedelta(days=i),
                )
                created.append(a)
            db_session.commit()

            with count_matching_queries(("FROM plants",)) as p_few, count_matching_queries(("FROM kpis",)) as k_few:
                cases_few = world.similar_historical_cases(
                    db_session, target.id, target_kpi, target.anomaly_type.value, target_factory, target_plant, limit=50,
                )
            relation_queries_few = p_few["n"] + k_few["n"]

            for i in range(3, 15):
                a = self._make_candidate(
                    db_session, code=f"ANM-N1-SIM-{token}-{i}", plant_id=other_plants[i].id,
                    kpi_id=target_kpi.id, detected_at=base + timedelta(days=i),
                )
                created.append(a)
            db_session.commit()

            with count_matching_queries(("FROM plants",)) as p_many, count_matching_queries(("FROM kpis",)) as k_many:
                cases_many = world.similar_historical_cases(
                    db_session, target.id, target_kpi, target.anomaly_type.value, target_factory, target_plant, limit=50,
                )
            relation_queries_many = p_many["n"] + k_many["n"]

            fixture_codes_few = {c.code for c in created[:3]}
            fixture_codes_many = {c.code for c in created}
            assert fixture_codes_few <= {c["anomaly_code"] for c in cases_few}
            assert fixture_codes_many <= {c["anomaly_code"] for c in cases_many}

            assert relation_queries_few == relation_queries_many, (
                f"Plant+KPI relation sorgu sayısı candidate sayısıyla büyüyor: 3 candidate="
                f"{relation_queries_few}, 15 candidate={relation_queries_many}"
            )
            assert relation_queries_many <= 4, (
                f"Plant+KPI relation sorgu sayısı beklenenden fazla: {relation_queries_many}"
            )
        finally:
            db_session.execute(delete(Anomaly).where(Anomaly.id.in_([a.id for a in created])))
            db_session.commit()


class TestContributionSummaryQueryCount:
    def test_query_count_does_not_scale_with_work_count(self, client, auth_headers, db_session):
        foremen = list(db_session.scalars(select(Foreman).where(Foreman.is_active.is_(True)).limit(5)))
        plants = list(db_session.scalars(select(Plant).order_by(Plant.sequence_number).limit(5)))
        assert len(foremen) >= 5 and len(plants) >= 5

        token = uuid.uuid4().hex[:8]
        new_ids = []
        try:
            for i in range(5):
                resp = client.post(
                    "/api/v1/contribution-works",
                    json={
                        "title": f"N+1 özet testi {token} #{i}", "status": "published", "work_type": "kaizen",
                        "summary": "s", "problem_description": "p", "solution_description": "s",
                        "foreman_ids": [str(foremen[i].id)], "plant_ids": [str(plants[i].id)],
                        "work_date": date.today().isoformat(), "impact_level": "medium",
                    },
                    headers=auth_headers,
                )
                assert resp.status_code == 201, resp.text
                new_ids.append(legacy_json(resp)["id"])

            with count_queries() as counter:
                resp = client.get(
                    "/api/v1/contribution-works/summary", params={"search": f"N+1 özet testi {token}"}, headers=auth_headers
                )
            assert resp.status_code == 200
            assert legacy_json(resp)["total_works"] == 5
            assert counter["n"] <= 6, f"Beklenenden fazla sorgu: {counter['n']}"
        finally:
            db_session.execute(ContributionWork.__table__.delete().where(ContributionWork.id.in_(new_ids)))
            db_session.commit()
