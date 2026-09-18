import uuid
from tests.helpers import legacy_json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.models.anomaly import Anomaly, AnomalyAnalysis, AnomalyToolCall
from app.models.enums import (
    AnalysisMode,
    AnomalyAnalysisStatus,
    AnomalySeverity,
    AnomalyStatus,
    AnomalyType,
    TargetScopeType,
)
from app.models.foreman import Foreman
from app.models.kpi import Kpi, KpiTarget
from app.models.organization import Factory, Plant, Shift
from app.models.user import AuditLog
from app.services.anomaly_investigation import resolve_company_kpi_target, resolve_kpi_target
from app.services.synthetic import world

from .conftest import TEST_SUBJECT


def _sample_anomaly(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    return anomaly


def _fresh_anomaly(db_session) -> Anomaly:
    anomaly = _sample_anomaly(db_session)
    db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.anomaly_id == anomaly.id))
    anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
    db_session.commit()
    return anomaly


class TestAnomalyList:
    def test_requires_auth(self, client):
        assert client.get("/api/v1/anomalies").status_code == 401

    def test_list_returns_at_least_20_items_with_expected_fields(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"limit": 100}, headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        assert body["total"] >= 20
        item = body["items"][0]
        for key in (
            "id", "code", "title", "factory_code", "plant_name", "kpi_name", "anomaly_type",
            "detected_at", "period_start", "period_end", "deviation_percent", "ml_confidence",
            "severity", "status", "analysis_status",
        ):
            assert key in item

    def test_pagination(self, client, auth_headers):
        first = legacy_json(client.get("/api/v1/anomalies", params={"limit": 5}, headers=auth_headers))
        assert first["has_more"] is True
        assert first["next_cursor"]
        second = legacy_json(client.get(
            "/api/v1/anomalies",
            params={"limit": 5, "cursor": first["next_cursor"]},
            headers=auth_headers,
        ))
        assert len(first["items"]) == 5
        assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})

    def test_filter_by_factory(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"factory": "K1", "limit": 100}, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert items
        assert all(i["factory_code"] == "K1" for i in items)

    def test_filter_by_severity(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"severity": "critical", "limit": 100}, headers=auth_headers)
        assert resp.status_code == 200
        items = legacy_json(resp)["items"]
        assert items
        assert all(i["severity"] == "critical" for i in items)

    def test_search(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies", params={"search": "Tesis", "limit": 100}, headers=auth_headers)
        assert resp.status_code == 200
        assert legacy_json(resp)["total"] > 0


class TestAnomalySummary:
    def test_summary_shape(self, client, auth_headers):
        resp = client.get("/api/v1/anomalies/summary", headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        for key in (
            "total_active", "critical_count", "high_count", "pending_analysis_count",
            "opened_last_7_days", "resolved_count",
        ):
            assert key in body
            assert body[key] >= 0


class TestAnomalyDetail:
    def test_unknown_id_returns_404(self, client, auth_headers):
        assert client.get(f"/api/v1/anomalies/{uuid.uuid4()}", headers=auth_headers).status_code == 404

    def test_detail_shape(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = legacy_json(resp)
        for key in (
            "description", "observed_value", "expected_value", "target_value", "comparison", "related_signals",
            "evidence", "daily_history", "kpi_definition", "latest_analysis", "analysis_history",
        ):
            assert key in body
        assert isinstance(body["target_value"], (int, float))


class TestAnomalyInvestigation:
    def test_unknown_id_returns_404(self, client, auth_headers):
        assert client.get(f"/api/v1/anomalies/{uuid.uuid4()}/investigation", headers=auth_headers).status_code == 404

    def test_investigation_shape(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.get(f"/api/v1/anomalies/{anomaly.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        for key in (
            "responsible_foreman", "baseline_comparison", "related_kpi_changes",
            "downtime_breakdown", "impact", "similar_cases",
            "shift_comparison", "factory_comparison", "previous_month", "comparison_target_value",
        ):
            assert key in body
        assert isinstance(body["comparison_target_value"], (int, float))

        foreman = body["responsible_foreman"]
        assert "resolved" in foreman and "shift_specific" in foreman

        baseline = body["baseline_comparison"]
        assert "available" in baseline

        impact = body["impact"]
        assert "production_loss_note" in impact
        assert "cost_note" in impact

        shift_comparison = body["shift_comparison"]
        assert len(shift_comparison) == 2
        for entry in shift_comparison:
            assert {"shift_id", "code", "name", "value", "is_anomaly_shift"} <= entry.keys()

        factory_comparison = body["factory_comparison"]
        assert {"K1", "K2"} == {f["code"] for f in factory_comparison}
        for entry in factory_comparison:
            assert isinstance(entry["value"], (int, float))

        previous_month = body["previous_month"]
        assert previous_month["available"] is True
        assert previous_month["label"]
        assert isinstance(previous_month["value"], (int, float))

    def test_inkita_anomaly_includes_downtime_breakdown(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly)).all()
        inkita = next((a for a in anomaly if a.unit and _kpi_code(db_session, a) == "INKITA"), None)
        if inkita is None:
            return
        resp = client.get(f"/api/v1/anomalies/{inkita.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200
        assert legacy_json(resp)["downtime_breakdown"] is not None


class TestFactoryShiftComparisonNumericParity:
    """Bilinen seed anomalisi için factory/shift karşılaştırma çıktılarını kilitler.
    Güncel seed UUID'lerine bağlıdır; reseed sonrasında geçerli olmaz.
    """

    def test_anm_2026_0001_factory_and_shift_comparison_exact_values(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == "ANM-2026-0001")).first()
        assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."

        resp = client.get(f"/api/v1/anomalies/{anomaly.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)

        self._assert_comparisons_match_world(db_session, anomaly, body)

    def test_anm_2026_0009_factory_and_shift_comparison_exact_values(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == "ANM-2026-0009")).first()
        assert anomaly is not None

        resp = client.get(f"/api/v1/anomalies/{anomaly.id}/investigation", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)

        self._assert_comparisons_match_world(db_session, anomaly, body)

    @staticmethod
    def _assert_comparisons_match_world(db_session, anomaly: Anomaly, body: dict) -> None:
        plant = db_session.get(Plant, anomaly.plant_id)
        kpi = db_session.get(Kpi, anomaly.kpi_id)
        factory = db_session.get(Factory, plant.factory_id)
        factory_values = world.compare_factories(db_session, kpi, anomaly.period_start, anomaly.period_end)
        factories = list(db_session.scalars(select(Factory).order_by(Factory.code)))
        assert body["factory_comparison"] == [
            {
                "code": item.code,
                "name": item.name,
                "value": factory_values[item.code],
                "is_anomaly_factory": item.id == factory.id,
            }
            for item in factories
        ]

        shift_values = world.compare_shifts(db_session, plant, kpi, anomaly.period_start, anomaly.period_end)
        shifts = list(db_session.scalars(select(Shift).where(Shift.is_active.is_(True)).order_by(Shift.sequence)))
        assert body["shift_comparison"] == [
            {
                "shift_id": str(item.id),
                "code": item.code,
                "name": item.name,
                "value": shift_values.per_shift[item.code],
                "is_anomaly_shift": item.id == anomaly.shift_id,
            }
            for item in shifts
        ]


class TestComparisonTargetResolution:
    def test_company_target_ignores_plant_override(self, db_session):
        kpi = db_session.scalars(select(Kpi).where(Kpi.code == "PLANA_UYUM")).first()
        company_row = db_session.scalar(
            select(KpiTarget).where(KpiTarget.kpi_id == kpi.id, KpiTarget.scope_type == TargetScopeType.COMPANY)
        )
        plant_row = db_session.scalar(
            select(KpiTarget).where(
                KpiTarget.kpi_id == kpi.id, KpiTarget.scope_type == TargetScopeType.PLANT,
                KpiTarget.target_value != company_row.target_value,
            )
        )
        assert company_row is not None and plant_row is not None
        plant = db_session.get(Plant, plant_row.scope_id)

        plant_scoped = resolve_kpi_target(db_session, kpi, plant, plant_row.valid_from)
        company_scoped = resolve_company_kpi_target(db_session, kpi, company_row.valid_from)

        assert plant_scoped == float(plant_row.target_value)
        assert company_scoped == float(company_row.target_value)
        assert company_scoped != plant_scoped


def _kpi_code(db_session, anomaly: Anomaly) -> str | None:
    from app.models.kpi import Kpi

    kpi = db_session.get(Kpi, anomaly.kpi_id)
    return kpi.code if kpi else None


class TestAnomalyAnalysis:
    def test_analysis_before_any_run_returns_404(self, client, auth_headers, db_session):
        anomaly = _fresh_anomaly(db_session)
        resp = client.get(f"/api/v1/anomalies/{anomaly.id}/analysis", headers=auth_headers)
        assert resp.status_code == 404

    def test_analyze_uses_demo_fallback_when_llm_disabled(self, client, auth_headers, db_session):
        anomaly = _fresh_anomaly(db_session)
        resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = legacy_json(resp)
        assert body["analysis_status"] == "completed"
        latest = body["latest_analysis"]
        assert latest["is_demo"] is True
        assert latest["status"] == "completed"
        result = latest["result"]
        assert result["requires_human_review"] is True
        assert 0.0 <= result["analysis_confidence"] <= 1.0
        assert result["executive_summary"]

        analysis_resp = client.get(f"/api/v1/anomalies/{anomaly.id}/analysis", headers=auth_headers)
        assert analysis_resp.status_code == 200
        assert legacy_json(analysis_resp)["id"] == latest["id"]

    def test_double_submit_returns_409(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        anomaly.analysis_status = AnomalyAnalysisStatus.ANALYZING
        db_session.commit()
        resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
        assert resp.status_code == 409
        anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
        db_session.commit()


class TestAnomalyStatusUpdate:
    def test_update_status(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "in_review"}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert legacy_json(resp)["status"] == "in_review"

    def test_invalid_status_value_returns_422(self, client, auth_headers, db_session):
        anomaly = _sample_anomaly(db_session)
        resp = client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "not-a-real-status"}, headers=auth_headers
        )
        assert resp.status_code == 422


def _anomaly_without_analyses(db_session) -> Anomaly:
    analyzed_ids = set(db_session.scalars(select(AnomalyAnalysis.anomaly_id)))
    anomaly = db_session.scalars(
        select(Anomaly).where(Anomaly.id.not_in(analyzed_ids)).order_by(Anomaly.code)
    ).first()
    assert anomaly is not None, "Analiz kaydı olmayan bir tespit bulunamadı."
    return anomaly


def _make_analysis(db_session, anomaly: Anomaly, started_at: datetime, **overrides) -> AnomalyAnalysis:
    defaults = dict(
        code=f"AAN-TEST-{uuid.uuid4().hex[:10]}",
        anomaly_id=anomaly.id,
        model="demo",
        is_demo=True,
        mode=AnalysisMode.SINGLE_CONTEXT,
        status=AnomalyAnalysisStatus.COMPLETED,
        investigation_plan=None,
        result={"executive_summary": "test", "requires_human_review": True, "analysis_confidence": 0.5},
        input_snapshot=None,
        error_message=None,
        error_code=None,
        started_at=started_at,
        completed_at=started_at + timedelta(minutes=2),
    )
    defaults.update(overrides)
    analysis = AnomalyAnalysis(**defaults)
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return analysis


def _make_tool_call(db_session, analysis: AnomalyAnalysis, step_number: int, started_at: datetime) -> AnomalyToolCall:
    tc = AnomalyToolCall(
        code=f"ATC-TEST-{uuid.uuid4().hex[:10]}",
        analysis_id=analysis.id,
        anomaly_id=analysis.anomaly_id,
        step_number=step_number,
        tool_name="get_kpi_history",
        arguments={},
        status="completed",
        result={"ok": True},
        record_count=1,
        started_at=started_at,
        completed_at=started_at + timedelta(seconds=5),
        duration_ms=5000,
    )
    db_session.add(tc)
    db_session.commit()
    db_session.refresh(tc)
    return tc


def _make_synthetic_anomaly(db_session, template: Anomaly, foreman_ids: list[str]) -> Anomaly:
    anomaly = Anomaly(
        code=f"ANM-4B1-{uuid.uuid4().hex[:10]}",
        title="4B-1 characterization test anomaly",
        description="4B-1 characterization test anomaly",
        anomaly_type=AnomalyType.SINGLE_DAY_SPIKE,
        severity=AnomalySeverity.MEDIUM,
        status=AnomalyStatus.NEW,
        analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED,
        detected_at=datetime.now(timezone.utc),
        plant_id=template.plant_id,
        shift_id=template.shift_id,
        kpi_id=template.kpi_id,
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
        foreman_ids=foreman_ids,
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)
    return anomaly


class TestAnomalyDetailMultiAnalysisHistory:
    def test_latest_analysis_and_history_ordering(self, client, auth_headers, db_session):
        anomaly = _anomaly_without_analyses(db_session)
        now = datetime.now(timezone.utc)
        older = _make_analysis(db_session, anomaly, now - timedelta(hours=2))
        newer = _make_analysis(db_session, anomaly, now - timedelta(hours=1))
        try:
            resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)

            history_ids = [x["id"] for x in body["analysis_history"]]
            assert history_ids == [str(newer.id), str(older.id)], "analysis_history started_at DESC sırasında olmalı"

            assert body["latest_analysis"] is not None
            assert body["latest_analysis"]["id"] == str(newer.id)
            assert body["latest_analysis"]["id"] == body["analysis_history"][0]["id"], (
                "Mevcut davranış: distinct started_at durumunda latest_analysis == analysis_history[0]. "
                "Aynı started_at durumunda tie-break garanti edilmez — bu test yalnızca distinct "
                "timestamp senaryosunu karakterize eder, yeni bir garanti icat etmez."
            )
            for entry in body["analysis_history"]:
                assert entry["tool_call_count"] == 0
        finally:
            db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.id.in_([older.id, newer.id])))
            db_session.commit()


class TestAnomalyDetailForemanOrdering:
    def test_foreman_codes_preserve_input_order(self, client, auth_headers, db_session):
        template = _sample_anomaly(db_session)
        foremen = list(db_session.scalars(select(Foreman).order_by(Foreman.employee_number).limit(2)))
        assert len(foremen) >= 2
        # Batch lookup'ın DB/PK sırasına göre sessizce yeniden sıralamadığını kanıtlamak
        # için doğal employee_number sırasının tersi kullanılır.
        ordered_ids = [str(foremen[1].id), str(foremen[0].id)]
        anomaly = _make_synthetic_anomaly(db_session, template, ordered_ids)
        try:
            resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)
            assert body["foreman_codes"] == [foremen[1].employee_number, foremen[0].employee_number]
        finally:
            db_session.delete(db_session.get(Anomaly, anomaly.id))
            db_session.commit()


class TestAnomalyAnalysisFoundPath:
    def test_get_latest_analysis_found_path_shape(self, client, auth_headers, db_session):
        anomaly = _anomaly_without_analyses(db_session)
        now = datetime.now(timezone.utc)
        analysis = _make_analysis(db_session, anomaly, now, model="demo-model", result={"x": 1})
        _make_tool_call(db_session, analysis, 1, now)
        _make_tool_call(db_session, analysis, 2, now + timedelta(seconds=10))
        try:
            resp = client.get(f"/api/v1/anomalies/{anomaly.id}/analysis", headers=auth_headers)
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)
            assert body["id"] == str(analysis.id)
            assert body["code"] == analysis.code
            assert body["mode"] == "single_context"
            assert body["status"] == "completed"
            assert body["is_demo"] is True
            assert body["model"] == "demo-model"
            assert body["result"] == {"x": 1}
            assert body["investigation_plan"] is None
            assert body["tool_call_count"] == 2
            assert body["error_code"] is None
            assert body["error_message"] is None
            assert body["started_at"]
            assert body["completed_at"]
        finally:
            db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.id == analysis.id))
            db_session.commit()

    def test_get_analyses_by_id_matches_same_shape(self, client, auth_headers, db_session):
        anomaly = _anomaly_without_analyses(db_session)
        analysis = _make_analysis(db_session, anomaly, datetime.now(timezone.utc))
        try:
            via_anomaly = legacy_json(client.get(f"/api/v1/anomalies/{anomaly.id}/analysis", headers=auth_headers))
            via_analyses = client.get(f"/api/v1/analyses/{analysis.id}", headers=auth_headers)
            assert via_analyses.status_code == 200
            assert legacy_json(via_analyses) == via_anomaly
        finally:
            db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.id == analysis.id))
            db_session.commit()

    def test_get_analyses_unknown_id_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/analyses/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp)["detail"] == "Analiz bulunamadı."


class TestAnalysisToolCalls:
    def test_unknown_analysis_returns_404(self, client, auth_headers):
        resp = client.get(f"/api/v1/analyses/{uuid.uuid4()}/tool-calls", headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp)["detail"] == "Analiz bulunamadı."

    def test_empty_tool_calls(self, client, auth_headers, db_session):
        anomaly = _anomaly_without_analyses(db_session)
        analysis = _make_analysis(db_session, anomaly, datetime.now(timezone.utc))
        try:
            resp = client.get(f"/api/v1/analyses/{analysis.id}/tool-calls", headers=auth_headers)
            assert resp.status_code == 200
            assert legacy_json(resp) == {"items": [], "total": 0}
        finally:
            db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.id == analysis.id))
            db_session.commit()

    def test_tool_calls_ordered_by_step_number(self, client, auth_headers, db_session):
        anomaly = _anomaly_without_analyses(db_session)
        now = datetime.now(timezone.utc)
        analysis = _make_analysis(db_session, anomaly, now)
        # Bilerek step-number sırasından farklı eklenir.
        tc3 = _make_tool_call(db_session, analysis, 3, now + timedelta(seconds=30))
        tc1 = _make_tool_call(db_session, analysis, 1, now + timedelta(seconds=10))
        tc2 = _make_tool_call(db_session, analysis, 2, now + timedelta(seconds=20))
        try:
            resp = client.get(f"/api/v1/analyses/{analysis.id}/tool-calls", headers=auth_headers)
            assert resp.status_code == 200
            body = legacy_json(resp)
            assert body["total"] == 3
            assert [i["step_number"] for i in body["items"]] == [1, 2, 3]
            assert [i["id"] for i in body["items"]] == [str(tc1.id), str(tc2.id), str(tc3.id)]
            first = body["items"][0]
            for key in (
                "code", "tool_name", "tool_label", "arguments", "status", "result",
                "record_count", "error_code", "error_message", "started_at", "completed_at", "duration_ms",
            ):
                assert key in first
        finally:
            db_session.execute(delete(AnomalyAnalysis).where(AnomalyAnalysis.id == analysis.id))
            db_session.commit()


class TestAnomalyDetailShapeCoverage:
    """`GET /anomalies/{id}` detail contract'ını dört seed anomali biçiminde kilitler:
    normal KPI, INKITA/downtime, foreman_ids içeren ve vardiyasız anomali.
    """

    _DETAIL_KEYS = {
        "id", "code", "title", "factory_code", "factory_name", "plant_id", "plant_name",
        "shift_id", "shift_name", "kpi_id", "kpi_code", "kpi_name", "anomaly_type",
        "anomaly_type_label", "detected_at", "period_start", "period_end", "deviation_percent",
        "ml_confidence", "severity", "severity_label", "status", "status_label",
        "analysis_status", "analysis_status_label", "description", "observed_value",
        "expected_value", "target_value", "unit", "affected_days", "total_days", "comparison",
        "related_signals", "evidence", "foreman_codes", "data_quality_status",
        "data_quality_warnings", "daily_history", "kpi_definition", "latest_analysis",
        "analysis_history",
    }

    def test_detail_contract_across_seed_anomaly_shapes(self, client, auth_headers, db_session):
        codes = ["ANM-2026-0001", "ANM-2026-0009", "ANM-2026-0005", "ANM-2026-0003"]

        for code in codes:
            anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == code)).first()
            assert anomaly is not None, f"Seed anomaly {code} bulunamadı."

            resp = client.get(f"/api/v1/anomalies/{anomaly.id}", headers=auth_headers)
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)

            assert set(body.keys()) == self._DETAIL_KEYS, f"{code}: detail contract key seti değişti."
            assert {
                "name", "description", "desired_direction", "warning_threshold", "critical_threshold",
            } <= body["kpi_definition"].keys()

            if code == "ANM-2026-0003":
                assert body["shift_id"] is None, "no-shift anomaly'de shift_id None olmalı."
                assert body["shift_name"] is None, "no-shift anomaly'de shift_name None olmalı."

            if code == "ANM-2026-0005":
                assert isinstance(body["foreman_codes"], list)
                assert body["foreman_codes"], "foreman_ids dolu olan anomaly'de foreman_codes boş olmamalı."


class TestAnomalyStatusServiceCharacterization:
    """`PATCH /status` için audit biçimi, same-status no-op, 404 ve 422 davranışlarını
    kilitler. Her test seed anomalisinin durumunu geri yükler ve audit kaydını siler.
    Kalıcı mutation bırakan TestAnomalyStatusUpdate ile birlikte çalıştırılmamalıdır.
    """

    def test_status_change_creates_expected_audit_row(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == "ANM-2026-0002")).first()
        assert anomaly is not None
        assert anomaly.status.value == "new", "Bu test 'new' durumundan başlamayı varsayar."

        before_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            resp = client.patch(
                f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "in_review"}, headers=auth_headers
            )
            assert resp.status_code == 200, resp.text
            assert legacy_json(resp)["status"] == "in_review"

            new_ids = set(db_session.scalars(select(AuditLog.id))) - before_ids
            assert len(new_ids) == 1, "Status değişikliği tam olarak bir audit satırı üretmeli."
            audit = db_session.get(AuditLog, next(iter(new_ids)))
            assert audit.action == "anomaly_status_updated"
            assert audit.entity == "anomaly"
            assert audit.subject == TEST_SUBJECT
            assert audit.old_value == "new"
            assert audit.new_value == "in_review"
            assert audit.success is True
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_ids)))
            db_session.refresh(anomaly)
            anomaly.status = AnomalyStatus.NEW
            db_session.commit()

    def test_same_status_produces_no_audit_row(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == "ANM-2026-0004")).first()
        assert anomaly is not None
        assert anomaly.status.value == "new", "Bu test 'new' durumundan başlamayı varsayar."

        before_ids = set(db_session.scalars(select(AuditLog.id)))
        resp = client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "new"}, headers=auth_headers
        )
        assert resp.status_code == 200, resp.text
        assert legacy_json(resp)["status"] == "new"

        after_ids = set(db_session.scalars(select(AuditLog.id)))
        assert after_ids == before_ids, "Aynı status'a no-op update audit satırı üretmemeli."
        db_session.refresh(anomaly)
        assert anomaly.status.value == "new"

    def test_unknown_id_returns_404(self, client, auth_headers):
        resp = client.patch(
            f"/api/v1/anomalies/{uuid.uuid4()}/status", json={"status": "in_review"}, headers=auth_headers
        )
        assert resp.status_code == 404
        assert legacy_json(resp)["detail"] == "Tespit bulunamadı."

    def test_invalid_status_value_returns_422(self, client, auth_headers, db_session):
        anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == "ANM-2026-0002")).first()
        assert anomaly is not None
        resp = client.patch(
            f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "not-a-real-status"}, headers=auth_headers
        )
        assert resp.status_code == 422
        db_session.refresh(anomaly)
        assert anomaly.status.value == "new", "422 hiçbir mutation üretmemeli."

    def test_status_response_matches_read_service_detail_shape(self, client, auth_headers, db_session):
        from app.services.anomaly_read_service import AnomalyReadService

        anomaly = db_session.scalars(select(Anomaly).where(Anomaly.code == "ANM-2026-0004")).first()
        assert anomaly is not None
        assert anomaly.status.value == "new"

        before_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            resp = client.patch(
                f"/api/v1/anomalies/{anomaly.id}/status", json={"status": "action_pending"}, headers=auth_headers
            )
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)

            for key in (
                "description", "observed_value", "expected_value", "target_value", "comparison",
                "related_signals", "evidence", "daily_history", "kpi_definition", "latest_analysis",
                "analysis_history", "foreman_codes",
            ):
                assert key in body

            db_session.refresh(anomaly)
            expected = AnomalyReadService(db_session).get_detail(anomaly.id)
            assert body == expected, "Response, AnomalyReadService.get_detail ile birebir eşleşmeli."
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_ids)))
            db_session.refresh(anomaly)
            anomaly.status = AnomalyStatus.NEW
            db_session.commit()


def _isolated_anomaly(db_session) -> Anomaly:
    template = _sample_anomaly(db_session)
    return _make_synthetic_anomaly(db_session, template, [])


def _delete_isolated_anomaly(db_session, anomaly: Anomaly) -> None:
    # anomaly_analyses.anomaly_id, anomaly_tool_calls.anomaly_id ve analysis_id üzerindeki
    # ON DELETE CASCADE, tüm child satırları DB seviyesinde kaldırır.
    db_session.execute(delete(Anomaly).where(Anomaly.id == anomaly.id))
    db_session.commit()


class TestAnalyzeCommandResponseParity:
    """Demo fallback analyze response'u aynı anomali için yeniden hesaplanan
    AnomalyReadService.get_detail ile eşleşmelidir. Mutation izole sentetik anomalide
    yapılır ve tamamen temizlenir.
    """

    def test_successful_analyze_response_matches_read_service_detail(self, client, auth_headers, db_session):
        from app.services.anomaly_read_service import AnomalyReadService

        anomaly = _isolated_anomaly(db_session)
        before_audit_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)
            assert body["analysis_status"] == "completed"
            assert body["latest_analysis"]["is_demo"] is True

            db_session.refresh(anomaly)
            expected = AnomalyReadService(db_session).get_detail(anomaly.id)
            assert body == expected

            new_audit_ids = set(db_session.scalars(select(AuditLog.id))) - before_audit_ids
            assert len(new_audit_ids) == 1
            audit = db_session.get(AuditLog, next(iter(new_audit_ids)))
            assert audit.action == "anomaly_analyzed"
            assert audit.entity == "anomaly"
            assert audit.subject == TEST_SUBJECT
            assert audit.new_value == f"{anomaly.code}: completed"
            assert audit.success is True
            assert audit.ip_address is not None
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_audit_ids)))
            _delete_isolated_anomaly(db_session, anomaly)


class TestReanalyzeCommandResponseParity:
    """Reanalyze eskiyi güncellemek yerine yeni history satırı oluşturmalı,
    current_analysis_id bu satıra geçmeli ve response get_detail ile eşleşmelidir.
    """

    def test_reanalyze_creates_new_history_row_and_matches_read_service(self, client, auth_headers, db_session):
        from app.services.anomaly_read_service import AnomalyReadService

        anomaly = _isolated_anomaly(db_session)
        before_audit_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            first = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert first.status_code == 200, first.text
            first_analysis_id = legacy_json(first)["latest_analysis"]["id"]

            second = client.post(f"/api/v1/anomalies/{anomaly.id}/reanalyze", headers=auth_headers)
            assert second.status_code == 200, second.text
            body = legacy_json(second)

            assert body["latest_analysis"]["id"] != first_analysis_id, "Reanalyze yeni bir analysis row oluşturmalı."
            history_ids = [x["id"] for x in body["analysis_history"]]
            assert sorted(history_ids) == sorted([first_analysis_id, body["latest_analysis"]["id"]]), (
                "Önceki analysis korunmalı, silinmemeli."
            )

            db_session.refresh(anomaly)
            assert str(anomaly.current_analysis_id) == body["latest_analysis"]["id"]

            expected = AnomalyReadService(db_session).get_detail(anomaly.id)
            assert body == expected

            new_audit_ids = set(db_session.scalars(select(AuditLog.id))) - before_audit_ids
            assert len(new_audit_ids) == 2
            actions = sorted(db_session.get(AuditLog, i).action for i in new_audit_ids)
            assert actions == ["anomaly_analyzed", "anomaly_reanalyzed"]
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_audit_ids)))
            _delete_isolated_anomaly(db_session, anomaly)


class TestAnalyzeCacheHitBehavior:
    """Analyze fast-path koşullarını kilitler: force/force_refresh yok, durum COMPLETED
    ve tamamlanmış satır varsa yeni analiz/audit oluşmaz. force_refresh ile reanalyze
    cache'i bypass etmelidir.
    """

    def test_completed_analysis_without_force_refresh_short_circuits(self, client, auth_headers, db_session):
        anomaly = _isolated_anomaly(db_session)
        before_audit_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            first = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert first.status_code == 200, first.text
            first_body = legacy_json(first)
            after_first_audit_ids = set(db_session.scalars(select(AuditLog.id)))

            second = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert second.status_code == 200, second.text
            second_body = legacy_json(second)

            assert second_body == first_body, "Cache-hit response, gerçek çalışmanın response'u ile aynı olmalı."
            assert len(second_body["analysis_history"]) == 1, "Cache-hit yeni analysis row oluşturmamalı."

            after_second_audit_ids = set(db_session.scalars(select(AuditLog.id)))
            assert after_second_audit_ids == after_first_audit_ids, "Cache-hit audit satırı üretmemeli."
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_audit_ids)))
            _delete_isolated_anomaly(db_session, anomaly)

    def test_force_refresh_bypasses_cache(self, client, auth_headers, db_session):
        anomaly = _isolated_anomaly(db_session)
        before_audit_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            first = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert first.status_code == 200, first.text
            first_analysis_id = legacy_json(first)["latest_analysis"]["id"]

            second = client.post(
                f"/api/v1/anomalies/{anomaly.id}/analyze", json={"force_refresh": True}, headers=auth_headers
            )
            assert second.status_code == 200, second.text
            second_body = legacy_json(second)
            assert second_body["latest_analysis"]["id"] != first_analysis_id, (
                "force_refresh=true cache'i bypass etmeli."
            )
            assert len(second_body["analysis_history"]) == 2
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_audit_ids)))
            _delete_isolated_anomaly(db_session, anomaly)

    def test_reanalyze_never_cache_hits_even_with_completed_analysis(self, client, auth_headers, db_session):
        anomaly = _isolated_anomaly(db_session)
        before_audit_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            first = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert first.status_code == 200, first.text
            first_analysis_id = legacy_json(first)["latest_analysis"]["id"]

            second = client.post(f"/api/v1/anomalies/{anomaly.id}/reanalyze", headers=auth_headers)
            assert second.status_code == 200, second.text
            assert legacy_json(second)["latest_analysis"]["id"] != first_analysis_id, (
                "reanalyze payload.force_refresh=False olsa bile her zaman gerçek run yapmalı."
            )
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_audit_ids)))
            _delete_isolated_anomaly(db_session, anomaly)


class TestAnalyzeFailedRunAudit:
    """FAILED durumu exception akışı değildir; run_analysis normal döner ve audit üretir.
    llm_service.call_llm her zaman hata verecek şekilde monkeypatch edilir.
    """

    def test_failed_analysis_still_produces_audit_row(self, client, auth_headers, db_session, monkeypatch):
        from app.services import llm_service

        monkeypatch.setattr(llm_service, "is_configured", lambda: True)

        def _always_timeout(*args, **kwargs):
            raise llm_service.LLMTimeoutError("simulated timeout")

        monkeypatch.setattr(llm_service, "call_llm", _always_timeout)

        anomaly = _isolated_anomaly(db_session)
        before_audit_ids = set(db_session.scalars(select(AuditLog.id)))
        try:
            resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert resp.status_code == 200, resp.text
            body = legacy_json(resp)
            assert body["analysis_status"] == "failed"
            assert body["latest_analysis"]["status"] == "failed"

            new_audit_ids = set(db_session.scalars(select(AuditLog.id))) - before_audit_ids
            assert len(new_audit_ids) == 1, "FAILED analiz de tam olarak bir audit satırı üretmeli."
            audit = db_session.get(AuditLog, next(iter(new_audit_ids)))
            assert audit.action == "anomaly_analyzed"
            assert audit.new_value == f"{anomaly.code}: failed"
        finally:
            db_session.execute(delete(AuditLog).where(AuditLog.id.not_in(before_audit_ids)))
            _delete_isolated_anomaly(db_session, anomaly)


class TestAnalyzeReanalyze409And404:
    def test_analyze_already_in_progress_returns_409(self, client, auth_headers, db_session):
        anomaly = _isolated_anomaly(db_session)
        try:
            anomaly.analysis_status = AnomalyAnalysisStatus.ANALYZING
            db_session.commit()
            resp = client.post(f"/api/v1/anomalies/{anomaly.id}/analyze", headers=auth_headers)
            assert resp.status_code == 409
            assert legacy_json(resp)["detail"] == "Bu tespit için analiz zaten devam ediyor."
        finally:
            _delete_isolated_anomaly(db_session, anomaly)

    def test_reanalyze_already_in_progress_returns_409(self, client, auth_headers, db_session):
        anomaly = _isolated_anomaly(db_session)
        try:
            anomaly.analysis_status = AnomalyAnalysisStatus.ANALYZING
            db_session.commit()
            resp = client.post(f"/api/v1/anomalies/{anomaly.id}/reanalyze", headers=auth_headers)
            assert resp.status_code == 409
            assert legacy_json(resp)["detail"] == "Bu tespit için analiz zaten devam ediyor."
        finally:
            _delete_isolated_anomaly(db_session, anomaly)

    def test_analyze_unknown_id_returns_404(self, client, auth_headers):
        resp = client.post(f"/api/v1/anomalies/{uuid.uuid4()}/analyze", headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp)["detail"] == "Tespit bulunamadı."

    def test_reanalyze_unknown_id_returns_404(self, client, auth_headers):
        resp = client.post(f"/api/v1/anomalies/{uuid.uuid4()}/reanalyze", headers=auth_headers)
        assert resp.status_code == 404
        assert legacy_json(resp)["detail"] == "Tespit bulunamadı."
