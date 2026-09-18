"""KPI-koduna özel sunum (presentation) mantığı — AGIR_GITME / INKITA / PLANA_UYUM.

Saf modül: DB/Session/FastAPI'ye bağımlı değildir, yalnızca zaten hesaplanmış
primitif değerleri presentation alanlarına dönüştürür. Skorlama `kpi_engine.py`'nin
sorumluluğudur, burada tekrar edilmez.

PLANA_UYUM için dönem (`direction`) ve tek-kayıt (`status`) bağlamları kasıtlı
olarak farklı alan adı kullanır — bu iki bağlam zorla aynılaştırılmaz.
"""


def agir_gitme_presentation(avg_actual: float, avg_target: float | None, decimal_places: int) -> dict:
    """AGIR_GITME için yön/oran sunumu (yalnızca dönem bağlamında kullanılır)."""
    direction = "OVERWEIGHT" if avg_actual > 0 else ("UNDERWEIGHT" if avg_actual < 0 else "ON_TARGET")
    return {
        "signed_value": round(avg_actual, decimal_places),
        "absolute_value": round(abs(avg_actual), decimal_places),
        "direction": direction,
        "ratio_to_target": round(abs(avg_actual) / avg_target, 4) if avg_target else None,
    }


def inkita_presentation(included_total: float | None) -> dict:
    """INKITA için dahil/hariç bileşen açıklaması (yalnızca dönem bağlamında kullanılır).

    `included_total` çağıranın zaten yuvarladığı avg_actual değeridir — burada tekrar
    yuvarlanmaz.
    """
    return {
        "included_total": included_total,
        "included_components": ["TECHNICAL", "MANUFACTURING"],
        "excluded_components": ["OTHER"],
        "note": "Diğer duruş süresi puana dahil edilmez.",
    }


def _plana_uyum_deviation(actual_qty: float | None, planned_qty: float | None) -> tuple[float | None, float | None, str]:
    """kg_diff, signed_pct_deviation ve yön (ABOVE_PLAN/BELOW_PLAN/ON_PLAN) hesaplar.

    Her iki context'in de (dönem ortalaması / tek kayıt) paylaştığı ortak formül;
    çağıranlar sonucu kendi alan adlarıyla (direction vs status) sarmalar.
    """
    kg_diff = (actual_qty - planned_qty) if (planned_qty is not None and actual_qty is not None) else None
    signed_pct_deviation = (kg_diff / planned_qty * 100.0) if (kg_diff is not None and planned_qty) else None
    direction = (
        "ABOVE_PLAN" if (signed_pct_deviation or 0) > 0
        else ("BELOW_PLAN" if (signed_pct_deviation or 0) < 0 else "ON_PLAN")
    )
    return kg_diff, signed_pct_deviation, direction


def plana_uyum_period_presentation(
    avg_actual: float, planned_qty: float | None, actual_qty: float | None, decimal_places: int
) -> dict:
    """PLANA_UYUM için dönem ortalaması bağlamındaki sunum (GET /foremen/{id}/kpis).

    Alan adı `direction`dır.
    """
    kg_diff, signed_pct_deviation, direction = _plana_uyum_deviation(actual_qty, planned_qty)
    return {
        "avg_attainment_pct": round(avg_actual, decimal_places),
        "planned_qty": round(planned_qty, 2) if planned_qty is not None else None,
        "actual_qty": round(actual_qty, 2) if actual_qty is not None else None,
        "kg_diff": round(kg_diff, 2) if kg_diff is not None else None,
        "signed_pct_deviation": round(signed_pct_deviation, 2) if signed_pct_deviation is not None else None,
        "direction": direction,
    }


def plana_uyum_calculation_detail_presentation(
    planned_qty: float | None, actual_qty: float | None, formula_version: int | None
) -> dict:
    """PLANA_UYUM için tek-kayıt (calculation-detail) bağlamındaki sunum.

    Alan adı `status`tur — dönem bağlamındaki `direction` ile kasıtlı olarak
    aynılaştırılmaz (mevcut API contract'ı).
    """
    kg_diff, signed_pct_deviation, status = _plana_uyum_deviation(actual_qty, planned_qty)
    return {
        "planned_qty": round(planned_qty, 2) if planned_qty is not None else None,
        "actual_qty": round(actual_qty, 2) if actual_qty is not None else None,
        "kg_diff": round(kg_diff, 2) if kg_diff is not None else None,
        "signed_pct_deviation": round(signed_pct_deviation, 2) if signed_pct_deviation is not None else None,
        "status": status,
        "formula_version": formula_version,
    }
