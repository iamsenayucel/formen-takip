from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services.production_kpi_derivation import _kpi_components, derive_agir_gitme


def _record(**overrides):
    base = dict(
        actual_qty=1000.0,
        planned_qty=950.0,
        measured_avg_gram=42.0,
        gsf_qty=20.0,
        iskarta_qty=8.0,
        planned_start_at=datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc),
        planned_end_at=datetime(2026, 3, 5, 16, 0, tzinfo=timezone.utc),
        technical_downtime_minutes=15.0,
        manufacturing_downtime_minutes=10.0,
        other_downtime_minutes=25.0,
        working_time_minutes=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _product(**overrides):
    base = dict(standard_gram=40.0, lower_gram_limit=38.0, upper_gram_limit=41.0)
    base.update(overrides)
    return SimpleNamespace(**base)


def _by_code(components):
    return {code: (actual, num, den) for code, actual, num, den in components}


class TestDeriveAgirGitme:

    def test_within_band_is_zero_deviation_even_if_off_standard(self):
        actual, numerator, denominator = derive_agir_gitme(
            measured_gram=41.0, standard_gram=40.0, lower_limit=37.0, upper_limit=42.0, actual_qty=1000.0
        )
        assert numerator == 0.0
        assert actual == 0.0
        assert denominator == pytest.approx(40.0 * 1000.0)

    def test_above_upper_limit_is_positive_signed_deviation(self):
        actual, numerator, _ = derive_agir_gitme(
            measured_gram=43.0, standard_gram=40.0, lower_limit=37.0, upper_limit=42.0, actual_qty=1000.0
        )
        assert numerator == pytest.approx(1.0 * 1000.0)
        assert actual > 0

    def test_below_lower_limit_is_negative_signed_deviation(self):
        actual, numerator, _ = derive_agir_gitme(
            measured_gram=35.0, standard_gram=40.0, lower_limit=37.0, upper_limit=42.0, actual_qty=1000.0
        )
        assert numerator == pytest.approx(-2.0 * 1000.0)
        assert actual < 0

    def test_zero_denominator_returns_none(self):
        assert derive_agir_gitme(43.0, 40.0, 37.0, 42.0, actual_qty=0.0) is None


class TestAgirGitme:
    def test_skipped_when_standard_missing(self):
        result = _by_code(_kpi_components(_record(), _product(standard_gram=None)))
        assert "AGIR_GITME" not in result

    def test_skipped_when_band_limits_missing(self):
        result = _by_code(_kpi_components(_record(), _product(lower_gram_limit=None, upper_gram_limit=None)))
        assert "AGIR_GITME" not in result

    def test_skipped_when_product_is_none(self):
        result = _by_code(_kpi_components(_record(), None))
        assert "AGIR_GITME" not in result

    def test_skipped_when_measurement_missing(self):
        result = _by_code(_kpi_components(_record(measured_avg_gram=None), _product()))
        assert "AGIR_GITME" not in result

    def test_within_band_yields_zero_not_skip(self):
        result = _by_code(_kpi_components(_record(measured_avg_gram=41.0), _product(standard_gram=40.0, lower_gram_limit=38.0, upper_gram_limit=41.0)))
        actual, numerator, _ = result["AGIR_GITME"]
        assert numerator == 0.0
        assert actual == 0.0

    def test_above_band_is_positive(self):
        result = _by_code(_kpi_components(_record(measured_avg_gram=43.0, actual_qty=1000.0), _product(standard_gram=40.0, lower_gram_limit=38.0, upper_gram_limit=41.0)))
        actual, numerator, denominator = result["AGIR_GITME"]
        assert numerator == pytest.approx(2.0 * 1000.0)
        assert denominator == pytest.approx(40.0 * 1000.0)
        assert actual == pytest.approx(numerator / denominator * 100)
        assert actual > 0

    def test_below_band_is_negative(self):
        result = _by_code(_kpi_components(_record(measured_avg_gram=36.0, actual_qty=1000.0), _product(standard_gram=40.0, lower_gram_limit=38.0, upper_gram_limit=41.0)))
        actual, numerator, _ = result["AGIR_GITME"]
        assert numerator < 0
        assert actual < 0


class TestGsfIskarta:
    def test_denominator_is_actual_qty(self):
        result = _by_code(_kpi_components(_record(actual_qty=500.0, gsf_qty=25.0, iskarta_qty=10.0), _product()))
        assert result["GSF"] == (5.0, 25.0, 500.0)
        assert result["ISKARTA"] == (2.0, 10.0, 500.0)

    def test_skipped_when_amount_missing(self):
        result = _by_code(_kpi_components(_record(gsf_qty=None, iskarta_qty=None), _product()))
        assert "GSF" not in result
        assert "ISKARTA" not in result

    def test_skipped_when_actual_qty_missing(self):
        result = _by_code(_kpi_components(_record(actual_qty=None), _product()))
        assert "GSF" not in result
        assert "ISKARTA" not in result
        assert "AGIR_GITME" not in result


class TestInkita:

    def test_denominator_derived_from_real_planned_window_not_hardcoded(self):
        record = _record(
            planned_start_at=datetime(2026, 3, 5, 8, 0, tzinfo=timezone.utc),
            planned_end_at=datetime(2026, 3, 5, 14, 0, tzinfo=timezone.utc),
            technical_downtime_minutes=20.0, manufacturing_downtime_minutes=10.0, other_downtime_minutes=99.0,
        )
        result = _by_code(_kpi_components(record, _product()))
        assert result["INKITA"] == (30.0 / 360 * 100, 30.0, 360.0)

    def test_other_downtime_never_included(self):
        record = _record(technical_downtime_minutes=5.0, manufacturing_downtime_minutes=5.0, other_downtime_minutes=1000.0)
        result = _by_code(_kpi_components(record, _product()))
        actual, numerator, _ = result["INKITA"]
        assert numerator == pytest.approx(10.0)

    def test_skipped_when_planned_window_missing(self):
        result = _by_code(_kpi_components(_record(planned_start_at=None), _product()))
        assert "INKITA" not in result

    def test_skipped_when_technical_missing(self):
        result = _by_code(_kpi_components(_record(technical_downtime_minutes=None), _product()))
        assert "INKITA" not in result

    def test_skipped_when_manufacturing_missing(self):
        result = _by_code(_kpi_components(_record(manufacturing_downtime_minutes=None), _product()))
        assert "INKITA" not in result

    def test_not_fabricated_from_partial_data(self):
        result = _by_code(_kpi_components(_record(technical_downtime_minutes=None, manufacturing_downtime_minutes=10.0), _product()))
        assert "INKITA" not in result


class TestPlanaUyum:
    def test_uses_this_records_own_planned_qty(self):
        result = _by_code(_kpi_components(_record(actual_qty=900.0, planned_qty=1000.0), _product()))
        assert result["PLANA_UYUM"] == (90.0, 900.0, 1000.0)

    def test_skipped_when_planned_qty_missing(self):
        result = _by_code(_kpi_components(_record(planned_qty=None), _product()))
        assert "PLANA_UYUM" not in result

    def test_skipped_when_actual_qty_missing(self):
        result = _by_code(_kpi_components(_record(actual_qty=None), _product()))
        assert "PLANA_UYUM" not in result


class TestOee:

    def test_skipped_when_working_time_not_set(self):
        result = _by_code(_kpi_components(_record(), _product()))
        assert "OEE" not in result

    def test_full_shift_yields_100_percent(self):
        result = _by_code(_kpi_components(_record(working_time_minutes=720.0), _product()))
        assert result["OEE"] == (100.0, 720.0, 720.0)

    def test_partial_shift_yields_recomputed_percent(self):
        result = _by_code(_kpi_components(_record(working_time_minutes=660.0), _product()))
        actual, numerator, denominator = result["OEE"]
        assert actual == pytest.approx(91.6667, abs=1e-3)
        assert numerator == pytest.approx(660.0)
        assert denominator == pytest.approx(720.0)

    def test_zero_working_time_yields_zero_not_skip(self):
        result = _by_code(_kpi_components(_record(working_time_minutes=0.0), _product()))
        assert result["OEE"] == (0.0, 0.0, 720.0)

    def test_independent_of_product_and_quantities(self):
        result = _by_code(
            _kpi_components(
                _record(working_time_minutes=360.0, actual_qty=None, planned_qty=None, gsf_qty=None, iskarta_qty=None),
                None,
            )
        )
        assert result["OEE"] == (50.0, 360.0, 720.0)


class TestNoDataFabrication:
    def test_all_none_yields_nothing(self):
        record = _record(
            actual_qty=None, planned_qty=None, gsf_qty=None, iskarta_qty=None,
            planned_start_at=None, planned_end_at=None,
            technical_downtime_minutes=None, manufacturing_downtime_minutes=None, other_downtime_minutes=None,
        )
        assert list(_kpi_components(record, _product())) == []
