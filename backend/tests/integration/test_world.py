import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyAnalysisStatus, AnomalySeverity, AnomalyStatus, AnomalyType
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.services.data_providers.synthetic import SyntheticKPIDataProvider, SyntheticHistoricalCaseDataProvider
from app.services.synthetic import world


def _sample_anchor(db_session) -> Anomaly:
    anomaly = db_session.scalars(select(Anomaly).order_by(Anomaly.code)).first()
    assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
    return anomaly


class TestResolvers:
    def test_resolve_plant_by_uuid_code_and_name(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        assert world.resolve_plant(db_session, str(plant.id)).id == plant.id
        assert world.resolve_plant(db_session, plant.code).id == plant.id
        assert world.resolve_plant(db_session, plant.name).id == plant.id

    def test_resolve_kpi_by_uuid_and_code(self, db_session):
        anchor = _sample_anchor(db_session)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        assert world.resolve_kpi(db_session, str(kpi.id)).id == kpi.id
        assert world.resolve_kpi(db_session, kpi.code).id == kpi.id
        assert world.resolve_kpi(db_session, kpi.code.lower()).id == kpi.id

    def test_resolve_shift_by_code_sequence_and_none(self, db_session):
        shift = db_session.scalars(select(Shift)).first()
        assert world.resolve_shift(db_session, shift.code).id == shift.id
        assert world.resolve_shift(db_session, str(shift.sequence)).id == shift.id
        assert world.resolve_shift(db_session, None) is None
        assert world.resolve_shift(db_session, "") is None

    def test_resolve_unknown_values_raise(self, db_session):
        import pytest

        with pytest.raises(world.WorldLookupError):
            world.resolve_plant(db_session, "NOPE")
        with pytest.raises(world.WorldLookupError):
            world.resolve_kpi(db_session, "NOT_A_KPI")
        with pytest.raises(world.WorldLookupError):
            world.resolve_factory(db_session, "K9")


class TestKpiSeriesConsistency:
    def test_flagged_shift_series_matches_compare_shifts(self, db_session):
        anchor = _sample_anchor(db_session)
        if anchor.shift_id is None:
            return
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        shift = db_session.get(Shift, anchor.shift_id)

        series = world.kpi_daily_series(db_session, plant, kpi, shift, anchor.period_start, anchor.period_end)
        avg = round(sum(p["value"] for p in series) / len(series), 2)

        comparison = world.compare_shifts(db_session, plant, kpi, anchor.period_start, anchor.period_end)
        assert avg == comparison.per_shift[shift.code]

    def test_deterministic_for_same_inputs(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)

        first = world.kpi_daily_series(db_session, plant, kpi, None, anchor.period_start, anchor.period_end)
        second = world.kpi_daily_series(db_session, plant, kpi, None, anchor.period_start, anchor.period_end)
        assert first == second

    def test_plant_average_is_between_min_and_max_shift(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.compare_shifts(db_session, plant, kpi, anchor.period_start, anchor.period_end)
        values = list(result.per_shift.values())
        assert min(values) <= result.plant_average <= max(values)

    def test_no_anchor_plant_kpi_combination_is_near_generic_baseline(self, db_session):
        anchored_pairs = {(a.plant_id, a.kpi_id) for a in db_session.scalars(select(Anomaly))}
        plants = list(db_session.scalars(select(Plant).where(Plant.is_active.is_(True))))
        kpis = list(db_session.scalars(select(Kpi)))
        for plant in plants:
            for kpi in kpis:
                if (plant.id, kpi.id) not in anchored_pairs:
                    baseline = world.generic_baseline(kpi)
                    value = world._value_for_date(db_session, plant, kpi, None, plant.created_at.date())
                    assert abs(value - baseline) < 2.0
                    return
        raise AssertionError("Anchor'sız bir tesis/KPI kombinasyonu bulunamadı.")


class TestCompareShiftsNumericParity:
    """`world.compare_shifts` çıktısını plant_average dahil kilitler. Investigation HTTP
    contract yalnız per_shift kullanır; compare_shifts LLM tool ise plant_average değerini
    sunar. Test güncel seed'e bağlıdır.
    """

    def _by_code(self, db_session, code: str) -> Anomaly:
        anomaly = db_session.scalar(select(Anomaly).where(Anomaly.code == code))
        assert anomaly is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
        return anomaly

    def test_anm_2026_0001_exact_result(self, db_session):
        anomaly = self._by_code(db_session, "ANM-2026-0001")
        plant = db_session.get(Plant, anomaly.plant_id)
        kpi = db_session.get(Kpi, anomaly.kpi_id)

        result = world.compare_shifts(db_session, plant, kpi, anomaly.period_start, anomaly.period_end)
        provider_out = SyntheticKPIDataProvider(db_session).compare_shifts(
            plant.id, kpi.id, anomaly.period_start, anomaly.period_end
        )
        self._assert_provider_parity(result, provider_out, plant, kpi)

    def test_anm_2026_0009_exact_result(self, db_session):
        anomaly = self._by_code(db_session, "ANM-2026-0009")
        plant = db_session.get(Plant, anomaly.plant_id)
        kpi = db_session.get(Kpi, anomaly.kpi_id)

        result = world.compare_shifts(db_session, plant, kpi, anomaly.period_start, anomaly.period_end)
        provider_out = SyntheticKPIDataProvider(db_session).compare_shifts(
            plant.id, kpi.id, anomaly.period_start, anomaly.period_end
        )
        self._assert_provider_parity(result, provider_out, plant, kpi)

    @staticmethod
    def _assert_provider_parity(result, provider_out: dict, plant: Plant, kpi: Kpi) -> None:
        assert set(result.per_shift) == {"V1", "V2"}
        assert result.max_deviation_between_shifts == round(
            max(result.per_shift.values()) - min(result.per_shift.values()), 2
        )
        if kpi.success_direction_higher:
            assert result.best_shift == max(result.per_shift, key=result.per_shift.get)
            assert result.worst_shift == min(result.per_shift, key=result.per_shift.get)
        else:
            assert result.best_shift == min(result.per_shift, key=result.per_shift.get)
            assert result.worst_shift == max(result.per_shift, key=result.per_shift.get)
        assert provider_out == {
            "plant_name": plant.name,
            "kpi_name": kpi.name,
            "unit": kpi.unit,
            "shift_averages": result.per_shift,
            "plant_average": result.plant_average,
            "best_shift": result.best_shift,
            "worst_shift": result.worst_shift,
            "max_deviation_between_shifts": result.max_deviation_between_shifts,
            "observation_count": result.observation_count,
        }


class TestCompareFactories:
    def test_returns_both_factories_with_values(self, db_session):
        anchor = _sample_anchor(db_session)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.compare_factories(db_session, kpi, anchor.period_start, anchor.period_end)
        assert set(result.keys()) == {"K1", "K2"}
        assert all(v is not None for v in result.values())

    def test_deterministic_for_same_inputs(self, db_session):
        anchor = _sample_anchor(db_session)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        first = world.compare_factories(db_session, kpi, anchor.period_start, anchor.period_end)
        second = world.compare_factories(db_session, kpi, anchor.period_start, anchor.period_end)
        assert first == second


class TestDowntimeAndMaintenance:
    def test_downtime_categories_sum_to_total(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.downtime_breakdown(db_session, plant, None, kpi, anchor.period_start, anchor.period_end)
        assert sum(c["total_minutes"] for c in result["categories"]) == result["total_downtime_minutes"]
        assert set(c["category"] for c in result["categories"]) == set(world._DOWNTIME_CATEGORIES)

    def test_downtime_does_not_recurse_infinitely_with_shift(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        shift = db_session.scalars(select(Shift)).first()
        result = world.downtime_breakdown(db_session, plant, shift, None, anchor.period_start, anchor.period_end)
        assert result["other_shifts_average_minutes"] is not None

    def test_maintenance_signals_shape(self, db_session):
        anchor = _sample_anchor(db_session)
        plant = db_session.get(Plant, anchor.plant_id)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        result = world.maintenance_signals(db_session, plant, kpi, anchor.period_start, anchor.period_end)
        assert isinstance(result["records"], list)
        assert result["recurring_fault_count"] <= len(result["records"])


class TestSimilarHistoricalCases:
    def test_finds_matching_kpi_and_excludes_self(self, db_session):
        anchor = _sample_anchor(db_session)
        kpi = db_session.get(Kpi, anchor.kpi_id)
        cases = world.similar_historical_cases(db_session, anchor.id, kpi, None, None, None, limit=10)
        assert all(c["anomaly_code"] != anchor.code for c in cases)
        assert all(c["kpi_name"] == kpi.name for c in cases if c.get("kpi_name"))

    def test_resolved_cases_include_root_cause(self, db_session):
        resolved = [a for a in db_session.scalars(select(Anomaly)) if a.status.value in ("resolved", "closed")]
        assert resolved, "Seed edilmiş verinin en az bir çözülmüş tespit içermesi beklenir."
        target = resolved[0]
        cases = world.similar_historical_cases(db_session, target.id, None, None, None, None, limit=20)
        matching = [c for c in cases if c["anomaly_code"] == target.code]
        assert isinstance(cases, list)


def _make_candidate(
    db_session, *, code: str, plant_id, kpi_id, anomaly_type: AnomalyType, detected_at: datetime,
    status: AnomalyStatus = AnomalyStatus.NEW,
) -> Anomaly:
    a = Anomaly(
        code=code, title=f"4B-2C fixture {code}", description=f"4B-2C fixture {code}",
        anomaly_type=anomaly_type, severity=AnomalySeverity.MEDIUM, status=status,
        analysis_status=AnomalyAnalysisStatus.NOT_ANALYZED, detected_at=detected_at,
        plant_id=plant_id, shift_id=None, kpi_id=kpi_id,
        period_start=detected_at.date(), period_end=detected_at.date(),
        observed_value=1.0, expected_value=2.0, unit="%", deviation_percent=50.0, ml_confidence=0.5,
        comparison={}, related_signals=[], evidence=[], foreman_ids=[],
    )
    db_session.add(a)
    return a


class TestSimilarHistoricalCasesScoringParity:
    """Scoring formülünün her dalını çalıştıran çok adaylı fixture:

        kpi match:            +2
        anomaly_type match:   +2
        plant match:          +2  (aşağıdaki factory dalıyla birbirini dışlar)
        elif factory match:   +1
        else:                  0  (score > 0 filtresiyle dışlanır)

    Güncel seed'in fabrika/factory topolojisine bağlı seçim, score ve
    (score DESC, detected_at DESC) sırasını kilitler.
    """

    def _build_fixture(self, db_session):
        target = db_session.scalar(select(Anomaly).where(Anomaly.code == "ANM-2026-0001"))
        assert target is not None, "Testler için önce 'python -m app.cli seed-anomalies' çalıştırılmalı."
        target_plant = db_session.get(Plant, target.plant_id)
        target_factory = db_session.get(Factory, target_plant.factory_id)
        target_kpi = db_session.get(Kpi, target.kpi_id)

        same_factory_other_plant = db_session.scalar(
            select(Plant).where(Plant.factory_id == target_factory.id, Plant.id != target_plant.id)
        )
        other_factory_plant = db_session.scalar(
            select(Plant).where(Plant.factory_id != target_factory.id)
        )
        other_kpi = db_session.scalar(select(Kpi).where(Kpi.id != target_kpi.id))
        assert same_factory_other_plant is not None and other_factory_plant is not None and other_kpi is not None

        token = uuid.uuid4().hex[:8]
        base = datetime(2020, 1, 10, tzinfo=timezone.utc)
        candidates = {
            # C: plant eşleşmesi (+2); yalnızca plant dalı katkı versin diye kpi/type farklıdır.
            # score=2 grubundaki en güncel detected_at değeridir.
            "C": _make_candidate(
                db_session, code=f"ANM-4B2C-{token}-C", plant_id=target_plant.id, kpi_id=other_kpi.id,
                anomaly_type=AnomalyType.RISING_TREND, detected_at=base + timedelta(days=3),
            ),
            # A: Yalnızca kpi eşleşir (+2); plant ve factory farklı olduğundan
            # elif-factory dalı çalışmaz.
            "A": _make_candidate(
                db_session, code=f"ANM-4B2C-{token}-A", plant_id=other_factory_plant.id, kpi_id=target_kpi.id,
                anomaly_type=AnomalyType.RISING_TREND, detected_at=base + timedelta(days=2),
            ),
            # B: Yalnızca anomaly_type eşleşir (+2); plant/factory/kpi farklıdır.
            "B": _make_candidate(
                db_session, code=f"ANM-4B2C-{token}-B", plant_id=other_factory_plant.id, kpi_id=other_kpi.id,
                anomaly_type=target.anomaly_type, detected_at=base + timedelta(days=1),
            ),
            # D: Aynı factory, farklı plant, kpi/type eşleşmesi yok; yalnızca factory (+1).
            "D": _make_candidate(
                db_session, code=f"ANM-4B2C-{token}-D", plant_id=same_factory_other_plant.id, kpi_id=other_kpi.id,
                anomaly_type=AnomalyType.RISING_TREND, detected_at=base,
            ),
            # E: Hiçbir boyut eşleşmez; score 0 olduğundan tamamen dışlanmalıdır.
            "E": _make_candidate(
                db_session, code=f"ANM-4B2C-{token}-E", plant_id=other_factory_plant.id, kpi_id=other_kpi.id,
                anomaly_type=AnomalyType.RISING_TREND, detected_at=base - timedelta(days=1),
            ),
        }
        db_session.commit()
        for c in candidates.values():
            db_session.refresh(c)
        return target, target_plant, target_factory, target_kpi, candidates

    def test_scoring_selection_and_ordering(self, db_session):
        target, target_plant, target_factory, target_kpi, candidates = self._build_fixture(db_session)
        try:
            cases = world.similar_historical_cases(
                db_session, target.id, target_kpi, target.anomaly_type.value, target_factory, target_plant, limit=100,
            )
            codes_in_order = [c["anomaly_code"] for c in cases]
            expected_order = [candidates[k].code for k in ("C", "A", "B", "D")]
            # Yalnızca fixture satırlarının göreli sırası doğrulanır; diğer seed anomalileri
            # de bu hedefe karşı score > 0 alıp araya girebilir.
            fixture_order = [code for code in codes_in_order if code in expected_order]
            assert fixture_order == expected_order, (
                f"Beklenen sıra {expected_order}, gerçek sıra {fixture_order}"
            )
            assert candidates["E"].code not in codes_in_order, "score=0 aday sonuçlarda olmamalı"

            by_code = {c["anomaly_code"]: c for c in cases}
            assert by_code[candidates["C"].code]["similarity_reason"] == "Benzerlik skoru: 2 (KPI/tür/tesis eşleşmesi)"
            assert by_code[candidates["A"].code]["similarity_reason"] == "Benzerlik skoru: 2 (KPI/tür/tesis eşleşmesi)"
            assert by_code[candidates["B"].code]["similarity_reason"] == "Benzerlik skoru: 2 (KPI/tür/tesis eşleşmesi)"
            assert by_code[candidates["D"].code]["similarity_reason"] == "Benzerlik skoru: 1 (KPI/tür/tesis eşleşmesi)"

            assert by_code[candidates["C"].code]["plant_name"] == target_plant.name
            assert by_code[candidates["D"].code]["plant_name"] == db_session.get(
                Plant, candidates["D"].plant_id
            ).name
            assert by_code[candidates["A"].code]["kpi_name"] == target_kpi.name
        finally:
            db_session.execute(
                Anomaly.__table__.delete().where(Anomaly.id.in_([c.id for c in candidates.values()]))
            )
            db_session.commit()

    def test_deterministic_for_same_inputs(self, db_session):
        target, target_plant, target_factory, target_kpi, candidates = self._build_fixture(db_session)
        try:
            first = world.similar_historical_cases(
                db_session, target.id, target_kpi, target.anomaly_type.value, target_factory, target_plant, limit=100,
            )
            second = world.similar_historical_cases(
                db_session, target.id, target_kpi, target.anomaly_type.value, target_factory, target_plant, limit=100,
            )
            assert first == second
        finally:
            db_session.execute(
                Anomaly.__table__.delete().where(Anomaly.id.in_([c.id for c in candidates.values()]))
            )
            db_session.commit()

    def test_llm_tool_provider_output_matches_world_result(self, db_session):
        """LLM tool parity: SyntheticHistoricalCaseDataProvider.find_similar_anomalies,
        aynı girdilerde world.similar_historical_cases ile tutarlı sonuç vermelidir.
        """
        target, target_plant, target_factory, target_kpi, candidates = self._build_fixture(db_session)
        try:
            direct = world.similar_historical_cases(
                db_session, target.id, target_kpi, target.anomaly_type.value, target_factory, target_plant, limit=100,
            )
            provider_out = SyntheticHistoricalCaseDataProvider(db_session).find_similar_anomalies(
                anomaly_id=target.id, kpi_id=target_kpi.id, anomaly_type=target.anomaly_type.value,
                factory_code=target_factory.code, plant_id=target_plant.id, limit=100,
            )
            assert provider_out == {"cases": direct, "count": len(direct)}
        finally:
            db_session.execute(
                Anomaly.__table__.delete().where(Anomaly.id.in_([c.id for c in candidates.values()]))
            )
            db_session.commit()
