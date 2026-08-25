from unittest.mock import patch

from app.services import monthly_foreman_report as mfr_module
from app.services.monthly_foreman_report import get_or_generate_monthly_report, latest_completed_period
from app.services.monthly_foreman_report_pdf import render_monthly_foreman_report_pdf
from tests.integration.test_monthly_foreman_report import _pick_foreman_with_data


def _has_outstanding_chip(elements) -> bool:
    for element in elements:
        cellvalues = getattr(element, "_cellvalues", None)
        if cellvalues and any("ÜSTÜN PERFORMANS" in str(cell) for row in cellvalues for cell in row):
            return True
    return False


def _generate_report(db_session, foreman_id, year, month, *, outstanding: bool):
    with patch.object(mfr_module, "is_outstanding_performance", lambda score: outstanding):
        return get_or_generate_monthly_report(db_session, foreman_id, year, month, force=True)


class TestOverallOutstandingSnapshotContract:
    def test_outstanding_true_is_written_to_overall_snapshot(self, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        assert foreman_id is not None

        report = _generate_report(db_session, foreman_id, year, month, outstanding=True)
        if report.report_data.get("insufficient_data"):
            return

        assert report.report_data["overall"]["outstanding_performance"] is True

    def test_outstanding_false_is_written_to_overall_snapshot(self, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        assert foreman_id is not None

        report = _generate_report(db_session, foreman_id, year, month, outstanding=False)
        if report.report_data.get("insufficient_data"):
            return

        assert report.report_data["overall"]["outstanding_performance"] is False


class TestOutstandingBadgeRendersInPdf:
    def test_badge_shown_when_outstanding_performance_true(self, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        assert foreman_id is not None

        report = _generate_report(db_session, foreman_id, year, month, outstanding=True)
        if report.report_data.get("insufficient_data"):
            return

        with patch("app.services.monthly_foreman_report_pdf.SimpleDocTemplate.build") as mock_build:
            render_monthly_foreman_report_pdf(report.report_data)
        elements = mock_build.call_args[0][0]
        assert _has_outstanding_chip(elements) is True

    def test_badge_hidden_when_outstanding_performance_false(self, db_session):
        year, month = latest_completed_period()
        foreman_id = _pick_foreman_with_data(db_session, year, month)
        assert foreman_id is not None

        report = _generate_report(db_session, foreman_id, year, month, outstanding=False)
        if report.report_data.get("insufficient_data"):
            return

        with patch("app.services.monthly_foreman_report_pdf.SimpleDocTemplate.build") as mock_build:
            render_monthly_foreman_report_pdf(report.report_data)
        elements = mock_build.call_args[0][0]
        assert _has_outstanding_chip(elements) is False
