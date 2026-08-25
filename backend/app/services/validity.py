from __future__ import annotations

from datetime import date


def is_effective(valid_from: date, valid_to: date | None, as_of: date) -> bool:
    return valid_from <= as_of and (valid_to is None or valid_to >= as_of)
