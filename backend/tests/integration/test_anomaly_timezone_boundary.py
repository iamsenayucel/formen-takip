import uuid
from tests.helpers import legacy_json
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType


def _template_anomaly(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    return anomaly


def _make_anomaly(db_session, template: Anomaly, detected_at: datetime) -> Anomaly:
    anomaly = Anomaly(
        code=f"ANM-TZ-TEST-{uuid.uuid4().hex[:10]}",
        title="TZ boundary test anomaly",
        description="TZ boundary test anomaly",
        anomaly_type=AnomalyType.SINGLE_DAY_SPIKE,
        severity=AnomalySeverity.MEDIUM,
        status=AnomalyStatus.NEW,
        analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED,
        detected_at=detected_at,
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
        foreman_ids=[],
    )
    db_session.add(anomaly)
    db_session.commit()
    db_session.refresh(anomaly)
    return anomaly


class TestAnomalyListLocalDayBoundary:
    """Europe/Istanbul iş günü sınırının detected_at filtrelemesinde doğru
    kullanıldığını doğrular (bkz. app/core/clock.py::local_day_bounds_utc).

    15 Ağustos Türkiye iş günü = [2026-08-14 21:00Z, 2026-08-15 21:00Z).
    """

    def test_start_date_end_date_use_istanbul_day_bounds(self, client, auth_headers, db_session):
        template = _template_anomaly(db_session)

        before_start = datetime(2026, 8, 14, 20, 59, tzinfo=timezone.utc)
        at_start = datetime(2026, 8, 14, 21, 0, tzinfo=timezone.utc)
        just_before_end = datetime(2026, 8, 15, 20, 59, tzinfo=timezone.utc)
        at_end = datetime(2026, 8, 15, 21, 0, tzinfo=timezone.utc)

        created = [_make_anomaly(db_session, template, dt) for dt in (before_start, at_start, just_before_end, at_end)]

        try:
            resp = client.get(
                "/api/v1/anomalies",
                params={"start_date": "2026-08-15", "end_date": "2026-08-15", "limit": 200},
                headers=auth_headers,
            )
            assert resp.status_code == 200
            ids_in_window = {i["id"] for i in legacy_json(resp)["items"]}

            assert str(created[0].id) not in ids_in_window, "20:59Z (14 Ağustos Türkiye günü) dahil edilmemeli"
            assert str(created[1].id) in ids_in_window, "21:00Z (15 Ağustos Türkiye gününün başlangıcı) dahil olmalı"
            assert str(created[2].id) in ids_in_window, "15 Ağustos 20:59Z hâlâ Türkiye'de 15 Ağustos'tur"
            assert str(created[3].id) not in ids_in_window, "21:00Z (16 Ağustos Türkiye gününün başlangıcı) hariç olmalı"
        finally:
            for a in created:
                db_session.delete(db_session.get(Anomaly, a.id))
            db_session.commit()
