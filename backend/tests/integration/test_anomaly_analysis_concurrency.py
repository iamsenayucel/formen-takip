import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.anomaly import Anomaly, AnomalyAnalysis
from app.models.enums import AnalysisMode, AnomalyAnalysisStatus
from app.services import llm_service
from app.services.anomaly_analysis_service import run_analysis
from app.services.anomaly_job_claim import (
    IN_PROGRESS_STATUSES,
    AnalysisInProgressError,
    claim_analysis,
    set_anomaly_status_if_current,
)
from app.services.job_reconciliation import reconcile_stale_anomaly_jobs


def _pick_anomalies(db_session, n: int) -> list[Anomaly]:
    """İlk `n` seed anomalisini deterministik sırayla seçip NOT_ANALYZED durumuna alır.

    Önceki testten kalan aktif AnomalyAnalysis satırlarını da siler; aksi halde partial
    unique index tutulur ve yeni claim bloklanır.
    """
    rows = list(db_session.scalars(select(Anomaly).order_by(Anomaly.code).limit(n)))
    assert len(rows) == n, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    ids = [a.id for a in rows]
    db_session.execute(
        delete(AnomalyAnalysis).where(
            AnomalyAnalysis.anomaly_id.in_(ids), AnomalyAnalysis.status.in_(IN_PROGRESS_STATUSES)
        )
    )
    for anomaly in rows:
        anomaly.analysis_status = AnomalyAnalysisStatus.NOT_ANALYZED
        anomaly.current_analysis_id = None
    db_session.commit()
    return rows


def _make_and_claim(db_session, anomaly: Anomaly, status: AnomalyAnalysisStatus, started_at: datetime) -> AnomalyAnalysis:
    analysis = AnomalyAnalysis(
        id=uuid.uuid4(), code=f"ANA-TEST-{uuid.uuid4().hex[:8].upper()}", anomaly_id=anomaly.id,
        model="pending", is_demo=True, mode=AnalysisMode.SINGLE_CONTEXT, status=status, started_at=started_at,
    )
    claim_analysis(db_session, anomaly, analysis)
    return analysis


def _enable_llm(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_api_key", "test-key")


_VALID_LLM_RESPONSE = {
    "executive_summary": "Test analiz özeti.",
    "verified_findings": [], "possible_causes": [], "recommended_investigations": [],
    "immediate_actions": [], "medium_term_actions": [], "missing_information": [],
    "risk_level": "medium", "analysis_confidence": 0.7, "requires_human_review": True,
    "disclaimer": "Test uyarısı.",
}


class TestClaimRace:
    def test_two_workers_race_only_one_claims_and_llm_called_once(self, db_session, monkeypatch):
        _enable_llm(monkeypatch)
        call_count = {"n": 0}
        lock = threading.Lock()

        def _counting_call_llm(*args, **kwargs):
            with lock:
                call_count["n"] += 1
            return dict(_VALID_LLM_RESPONSE)

        monkeypatch.setattr(llm_service, "call_llm", _counting_call_llm)

        anomaly_id = _pick_anomalies(db_session, 1)[0].id
        barrier = threading.Barrier(2)
        results: list = []
        results_lock = threading.Lock()

        def worker():
            db = SessionLocal()
            try:
                anomaly = db.get(Anomaly, anomaly_id)
                barrier.wait()
                try:
                    analysis = run_analysis(db, anomaly)
                    with results_lock:
                        results.append(("ok", analysis.status))
                except AnalysisInProgressError:
                    with results_lock:
                        results.append(("blocked", None))
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(worker) for _ in range(2)]
            for f in futures:
                f.result()

        oks = [r for r in results if r[0] == "ok"]
        blocked = [r for r in results if r[0] == "blocked"]
        assert len(oks) == 1, f"expected exactly one successful claim, got {results}"
        assert len(blocked) == 1
        assert oks[0][1] == AnomalyAnalysisStatus.COMPLETED
        assert call_count["n"] == 1, "LLM must be called exactly once across both workers"

    def test_insert_race_at_db_level_only_one_wins(self, db_session):
        anomaly = _pick_anomalies(db_session, 1)[0]
        anomaly_id = anomaly.id
        barrier = threading.Barrier(2)
        outcomes: list = []
        lock = threading.Lock()

        def worker():
            db = SessionLocal()
            try:
                a = db.get(Anomaly, anomaly_id)
                analysis = AnomalyAnalysis(
                    id=uuid.uuid4(), code=f"ANA-TEST-{uuid.uuid4().hex[:8].upper()}", anomaly_id=a.id,
                    model="pending", is_demo=True, mode=AnalysisMode.SINGLE_CONTEXT,
                    status=AnomalyAnalysisStatus.QUEUED, started_at=datetime.now(timezone.utc),
                )
                barrier.wait()
                try:
                    claim_analysis(db, a, analysis)
                    with lock:
                        outcomes.append("claimed")
                except AnalysisInProgressError:
                    with lock:
                        outcomes.append("rejected")
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(worker) for _ in range(2)]
            for f in futures:
                f.result()

        assert sorted(outcomes) == ["claimed", "rejected"]


class TestStaleRecovery:
    def test_stale_queued_and_processing_recovered_but_fresh_not(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "anomaly_stale_claim_timeout_seconds", 60)
        old1, old2, fresh = _pick_anomalies(db_session, 3)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=600)

        stale_a = _make_and_claim(db_session, old1, AnomalyAnalysisStatus.QUEUED, old_time)
        stale_b = _make_and_claim(db_session, old2, AnomalyAnalysisStatus.COLLECTING_DATA, old_time)
        fresh_a = _make_and_claim(db_session, fresh, AnomalyAnalysisStatus.QUEUED, datetime.now(timezone.utc))

        result = reconcile_stale_anomaly_jobs(db_session, settings)

        for row in (stale_a, stale_b, fresh_a, old1, old2, fresh):
            db_session.refresh(row)

        assert stale_a.status == AnomalyAnalysisStatus.FAILED
        assert stale_b.status == AnomalyAnalysisStatus.FAILED
        assert fresh_a.status == AnomalyAnalysisStatus.QUEUED

        assert old1.analysis_status == AnomalyAnalysisStatus.FAILED
        assert old2.analysis_status == AnomalyAnalysisStatus.FAILED
        assert fresh.analysis_status == AnomalyAnalysisStatus.QUEUED

        assert set(result.recovered_ids) == {stale_a.id, stale_b.id}


class TestStaleWorkerCompletion:
    def test_stale_worker_completing_after_reclaim_does_not_overwrite_newer_attempt(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "anomaly_stale_claim_timeout_seconds", 60)
        anomaly = _pick_anomalies(db_session, 1)[0]
        old_time = datetime.now(timezone.utc) - timedelta(seconds=600)

        analysis_a = _make_and_claim(db_session, anomaly, AnomalyAnalysisStatus.QUEUED, old_time)

        reconcile_stale_anomaly_jobs(db_session, settings)
        db_session.refresh(analysis_a)
        db_session.refresh(anomaly)
        assert analysis_a.status == AnomalyAnalysisStatus.FAILED
        assert anomaly.analysis_status == AnomalyAnalysisStatus.FAILED

        analysis_b = _make_and_claim(db_session, anomaly, AnomalyAnalysisStatus.QUEUED, datetime.now(timezone.utc))
        assert anomaly.current_analysis_id == analysis_b.id

        # analysis_a sahibi Worker A sonunda başarılı sonuçla döner; artık anomalinin
        # claim sahibi olmadığı için yazma işlemi reddedilmelidir.
        updated = set_anomaly_status_if_current(db_session, anomaly, analysis_a, AnomalyAnalysisStatus.COMPLETED)
        db_session.refresh(anomaly)

        assert updated is False
        assert anomaly.analysis_status == AnomalyAnalysisStatus.QUEUED
        assert anomaly.current_analysis_id == analysis_b.id


class TestCrashBeforeSideEffect:
    def test_claim_without_completion_is_recovered_by_watchdog(self, db_session, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "anomaly_stale_claim_timeout_seconds", 60)
        anomaly = _pick_anomalies(db_session, 1)[0]
        old_time = datetime.now(timezone.utc) - timedelta(seconds=600)

        # Claim başarılıdır; ardından worker'ın LLM çağrısından önce çöktüğü varsayılır.
        analysis = _make_and_claim(db_session, anomaly, AnomalyAnalysisStatus.QUEUED, old_time)

        result = reconcile_stale_anomaly_jobs(db_session, settings)
        db_session.refresh(analysis)
        db_session.refresh(anomaly)

        assert analysis.id in result.recovered_ids
        assert analysis.status == AnomalyAnalysisStatus.FAILED
        assert analysis.error_message == "stale_watchdog_timeout"
        assert anomaly.analysis_status == AnomalyAnalysisStatus.FAILED

        # Anomali artık yeni bir denemeye açıktır (manuel "Reanalyze"). LLM yapılandırılmadan
        # çalışan demo fallback, claim'in bloklanmadığını kanıtlamak için yeterlidir.
        monkeypatch.setattr(settings, "llm_enabled", False)
        monkeypatch.setattr(settings, "llm_api_key", None)
        retry = run_analysis(db_session, anomaly)
        assert retry.status == AnomalyAnalysisStatus.COMPLETED
        assert retry.id != analysis.id
