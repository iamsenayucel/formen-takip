from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.contribution import ContributionWorkCreate, ContributionWorkUpdate


def _base_payload(**overrides) -> dict:
    payload = {"title": "Test Çalışması"}
    payload.update(overrides)
    return payload


class TestContributionCreateNumericBounds:
    def test_zero_duration_and_gain_are_valid(self):
        work = ContributionWorkCreate(**_base_payload(previous_duration=0, new_duration=0, gain_amount=0))
        assert work.previous_duration == 0
        assert work.gain_amount == 0

    def test_negative_previous_duration_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(**_base_payload(previous_duration=-1))

    def test_negative_new_duration_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(**_base_payload(new_duration=-1))

    def test_negative_gain_amount_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(**_base_payload(gain_amount=-10000))

    def test_negative_per_occurrence_saving_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(**_base_payload(per_occurrence_saving=-5))

    def test_negative_repeat_count_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(**_base_payload(repeat_count=-1))

    def test_negative_monthly_total_saving_minutes_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(**_base_payload(monthly_total_saving_minutes=-1))


class TestContributionCreateDateRange:
    def test_same_start_and_end_date_is_valid(self):
        work = ContributionWorkCreate(
            **_base_payload(work_date=date(2026, 8, 14), work_date_end=date(2026, 8, 14))
        )
        assert work.work_date == work.work_date_end

    def test_end_before_start_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkCreate(
                **_base_payload(work_date=date(2026, 8, 15), work_date_end=date(2026, 8, 14))
            )

    def test_end_without_start_is_not_rejected_by_schema(self):
        # work_date yalnızca publish sırasında zorunludur (bkz. validate_for_publish);
        # şema iki tarihi yalnızca ikisi de mevcutken sıralar.
        work = ContributionWorkCreate(**_base_payload(work_date_end=date(2026, 8, 14)))
        assert work.work_date is None


class TestContributionUpdateDateRange:
    def test_both_fields_reversed_in_same_patch_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkUpdate(work_date=date(2026, 8, 15), work_date_end=date(2026, 8, 14))

    def test_only_end_date_supplied_is_not_rejected_by_schema(self):
        # Kısmi PATCH mevcut DB satırının başlangıç tarihini göremez; kalıcı satırla
        # merged-state doğrulaması burada değil, API katmanında yapılır.
        update = ContributionWorkUpdate(work_date_end=date(2026, 8, 10))
        assert update.work_date_end == date(2026, 8, 10)

    def test_negative_gain_amount_rejected(self):
        with pytest.raises(ValidationError):
            ContributionWorkUpdate(gain_amount=-1)
