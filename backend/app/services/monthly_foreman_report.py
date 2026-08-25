from __future__ import annotations

import calendar
import logging
from datetime import date
from statistics import pstdev
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import Settings, get_settings
from app.models.enums import ReportEmailStatus, ReportGenerationStatus, ReportStorageProvider
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.foreman_report import ForemanMonthlyReport
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant
from app.schemas.common import Filters
from app.services import analytics, contribution_bonus
from app.services.kpi_engine import PerformanceLevel, is_outstanding_performance, resolve_performance_level
from app.services.level_lookup import foreman_level_payload, get_performance_levels, level_to_dict
from app.services.monthly_foreman_report_pdf import render_monthly_foreman_report_pdf
from app.services.shift_analysis import month_label
from app.services.storage import ReportStorageError, get_report_storage

logger = logging.getLogger("app.monthly_foreman_report")

INSUFFICIENT_DATA_MESSAGE = "Bu dönem için değerlendirme oluşturmak adına yeterli veri bulunmamaktadır."

STRONG_LEVEL_NAMES = {"Başarılı"}
IMPROVEMENT_LEVEL_NAMES = {"Geliştirilmeli", "Kritik"}
CRITICAL_LEVEL_NAMES = {"Kritik"}

_EPSILON_ABS = 1e-4
_EPSILON_REL = 0.001

_TREND_FLAT_STDEV = 3.0
_TREND_FLAT_DIFF = 3.0
_TREND_MIN_RELIABLE_WEEKS = 3


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def is_month_completed(year: int, month: int) -> bool:
    _, period_end = _month_bounds(year, month)
    return period_end < clock.today_local()


def _compare_to_reference(
    actual: float | None, reference: float | None, success_direction_higher: bool
) -> dict | None:
    if actual is None or reference is None:
        return None
    diff = actual - reference
    tolerance = max(_EPSILON_ABS, abs(reference) * _EPSILON_REL)
    if abs(diff) <= tolerance:
        status = "at"
        is_favorable = True
    else:
        status = "above" if diff > 0 else "below"
        is_favorable = (status == "above") == success_direction_higher
    diff_pct = (diff / reference * 100.0) if reference else None
    return {
        "value": round(reference, 4),
        "diff": round(diff, 4),
        "diff_pct": round(diff_pct, 2) if diff_pct is not None else None,
        "status": status,
        "is_favorable": is_favorable,
    }


def _classify_trend_shape(weekly_scores: list[float]) -> str | None:
    if len(weekly_scores) < _TREND_MIN_RELIABLE_WEEKS:
        return None
    half = len(weekly_scores) // 2
    first_half_avg = sum(weekly_scores[:half]) / half
    second_half_avg = sum(weekly_scores[-half:]) / half
    diff = second_half_avg - first_half_avg
    stdev = pstdev(weekly_scores)
    if stdev < _TREND_FLAT_STDEV and abs(diff) < _TREND_FLAT_DIFF:
        return "stabil"
    if diff > _TREND_FLAT_DIFF:
        return "iyileşme"
    if diff < -_TREND_FLAT_DIFF:
        return "kötüleşme"
    return "dalgalı"


_TREND_TEXT = {
    "iyileşme": "Operasyonel performansınız ay boyunca istikrarlı bir iyileşme göstermiştir.",
    "kötüleşme": "Operasyonel performansınızda ay içerisinde bir gerileme gözlenmektedir.",
    "stabil": "Operasyonel performansınız ay boyunca istikrarlı bir şekilde seyretmiştir.",
    "dalgalı": "Operasyonel performansınız ay içerisinde dalgalı bir seyir izlemiştir.",
}


def assignments_overlapping_period(
    db: Session, foreman_id: UUID, period_start: date, period_end: date
) -> list[ForemanAssignment]:
    return list(
        db.scalars(
            select(ForemanAssignment)
            .where(ForemanAssignment.foreman_id == foreman_id, ForemanAssignment.start_date <= period_end)
            .where((ForemanAssignment.end_date.is_(None)) | (ForemanAssignment.end_date >= period_start))
            .order_by(ForemanAssignment.start_date, ForemanAssignment.plant_id)
        )
    )


def group_assignment_episodes(assignments: list[ForemanAssignment]) -> list[list[ForemanAssignment]]:
    episodes: dict[tuple[date, date | None], list[ForemanAssignment]] = {}
    for assignment in assignments:
        episodes.setdefault((assignment.start_date, assignment.end_date), []).append(assignment)
    ordered_keys = sorted(episodes.keys(), key=lambda key: key[0])
    for prev_key, next_key in zip(ordered_keys, ordered_keys[1:]):
        if prev_key[1] is None:
            logger.warning(
                "foreman_assignment_overlap_detected foreman_id=%s open_ended_episode_start=%s next_episode_start=%s",
                assignments[0].foreman_id, prev_key[0], next_key[0],
            )
    return [episodes[key] for key in ordered_keys]


def _kpi_entry(
    kpi: Kpi,
    row: dict | None,
    factory_rows_by_kpi: dict[UUID, dict],
    levels: list[PerformanceLevel],
) -> dict:
    avg_actual = float(row["avg_actual"]) if row and row["avg_actual"] is not None else None
    avg_target = float(row["avg_target"]) if row and row["avg_target"] is not None else None
    capped_score = float(row["avg_capped_score"]) if row else 0.0
    record_count = row["record_count"] if row else 0
    factory_row = factory_rows_by_kpi.get(kpi.id)
    factory_actual = float(factory_row["avg_actual"]) if factory_row and factory_row["avg_actual"] is not None else None

    level = resolve_performance_level(capped_score, levels) if row else None
    dp = kpi.decimal_places
    return {
        "kpi_id": str(kpi.id),
        "code": kpi.code,
        "name": kpi.name,
        "unit": kpi.unit,
        "weight": float(kpi.weight),
        "success_direction_higher": kpi.success_direction_higher,
        "has_data": record_count > 0,
        "record_count": record_count,
        "actual": round(avg_actual, dp) if avg_actual is not None else None,
        "score": round(capped_score, 2) if row else None,
        "level": level_to_dict(level) if level else None,
        "outstanding_performance": is_outstanding_performance(capped_score) if row else False,
        "vs_personal_target": _compare_to_reference(avg_actual, avg_target, kpi.success_direction_higher),
        "vs_factory_average": _compare_to_reference(avg_actual, factory_actual, kpi.success_direction_higher),
    }


def _build_summary_text(period_label: str, total_with_data: int, strong: list[dict], improve: list[dict]) -> str:
    if total_with_data == 0:
        return f"{period_label} için değerlendirilebilir KPI verisi bulunmamaktadır."
    parts = [f"{period_label} ayında değerlendirilen {total_with_data} KPI'dan {len(strong)}'inde hedef seviyesinde veya üzerinde performans gösterdiniz."]
    if strong:
        names = ", ".join(k["name"] for k in strong)
        parts.append(f"{names} alanlarında güçlü bir performans sergilediniz.")
    if improve:
        names = ", ".join(k["name"] for k in improve)
        parts.append(f"{names} alanında/alanlarında ise gelişim fırsatı bulunmaktadır.")
    return " ".join(parts)


def _investigation_hint(kpi_code: str) -> str:
    if kpi_code == "INKITA":
        return "Duruş nedenlerinin detaylı incelenmesi önerilir."
    return "Performansı etkileyen faktörlerin ayrıntılı incelenmesi önerilir."


def _build_closing_text(
    period_label: str, overall_level: PerformanceLevel, strong: list[dict], improve: list[dict], critical: list[dict]
) -> str:
    sentences = [f"{period_label} ayında genel performansınız \"{overall_level.name}\" seviyesinde gerçekleşmiştir."]
    if strong:
        names = ", ".join(k["name"] for k in strong)
        sentences.append(f"Özellikle {names} KPI'larında güçlü sonuçlar elde ettiniz.")
    if improve:
        names = ", ".join(k["name"] for k in improve)
        sentences.append(f"{names} KPI'larında ise hedef seviyesinden uzaklaşma görülmektedir.")
    if critical:
        sentences.append("Önümüzdeki ay bu alanlara odaklanmanız ve yöneticinizle birlikte değerlendirmeniz önerilir.")
    sentences.append("Genel olarak performansınızı sürdürmeniz ve geliştirmeniz önemlidir.")
    return " ".join(sentences)


def _build_organization_history(
    db: Session, episodes: list[list[ForemanAssignment]], period_start: date, period_end: date
) -> list[dict]:
    history = []
    for episode in episodes:
        episode_start, episode_end = episode[0].start_date, episode[0].end_date
        effective_start = max(period_start, episode_start)
        effective_end = min(period_end, episode_end) if episode_end is not None else period_end

        plants_by_id = {p.id: p for p in db.scalars(select(Plant).where(Plant.id.in_({a.plant_id for a in episode})))}
        chief = db.get(Chief, episode[0].chief_id)
        factory_id = next(iter(plants_by_id.values())).factory_id
        factory = db.get(Factory, factory_id)
        history.append({
            "date_from": effective_start.isoformat(),
            "date_to": effective_end.isoformat(),
            "factory_name": factory.name if factory else None,
            "plants": [{"id": str(p.id), "name": p.name} for p in sorted(plants_by_id.values(), key=lambda p: p.sequence_number)],
            "chief_name": f"{chief.first_name} {chief.last_name}" if chief else None,
        })
    return history


def _build_report_data(db: Session, foreman: Foreman, year: int, month: int) -> dict:
    date_from, date_to = _month_bounds(year, month)
    period_label = month_label(date_to)
    generated_at = clock.now_utc()

    header = {
        "foreman": {
            "id": str(foreman.id),
            "employee_number": foreman.employee_number,
            "full_name": f"{foreman.first_name} {foreman.last_name}",
            "hire_date": foreman.hire_date.isoformat(),
        },
        "period": {
            "year": year, "month": month, "label": period_label,
            "date_from": date_from.isoformat(), "date_to": date_to.isoformat(),
        },
        "generated_at": generated_at.isoformat(),
    }

    assignments = assignments_overlapping_period(db, foreman.id, date_from, date_to)
    if not assignments:
        return {
            **header,
            "org": None,
            "organization_history": [],
            "insufficient_data": True,
            "insufficient_data_reason": INSUFFICIENT_DATA_MESSAGE,
            "overall": None,
        }

    episodes = group_assignment_episodes(assignments)
    organization_history = _build_organization_history(db, episodes, date_from, date_to)
    org = organization_history[-1] if organization_history else None
    current_plant_ids = {a.plant_id for a in episodes[-1]}
    factory_id = db.scalar(select(Plant.factory_id).where(Plant.id.in_(current_plant_ids)).limit(1))

    filters = Filters(date_from=date_from, date_to=date_to)
    overall_scores = {s.key: s for s in analytics.foreman_scores(db, filters)}
    overall = overall_scores.get(foreman.id)

    if overall is None or not overall.is_reliable:
        return {
            **header,
            "org": org,
            "organization_history": organization_history,
            "insufficient_data": True,
            "insufficient_data_reason": INSUFFICIENT_DATA_MESSAGE,
            "overall": None,
        }

    levels = get_performance_levels(db)
    kpis_by_id = {k.id: k for k in db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))}
    personal_rows = {r["kpi_id"]: r for r in analytics.foreman_kpi_breakdown(db, filters, foreman.id)}

    factory_filters = Filters(date_from=date_from, date_to=date_to, factory_ids=[factory_id])
    factory_rows = {r["kpi_id"]: r for r in analytics.kpi_breakdown(db, factory_filters)}

    kpi_entries = [
        _kpi_entry(kpi, personal_rows.get(kpi.id), factory_rows, levels)
        for kpi in sorted(kpis_by_id.values(), key=lambda k: k.display_order)
    ]
    entries_with_data = [e for e in kpi_entries if e["has_data"]]

    strong = [e for e in entries_with_data if e["level"] and e["level"]["name"] in STRONG_LEVEL_NAMES]
    improve = [e for e in entries_with_data if e["level"] and e["level"]["name"] in IMPROVEMENT_LEVEL_NAMES]
    critical = [e for e in entries_with_data if e["level"] and e["level"]["name"] in CRITICAL_LEVEL_NAMES]

    bonus_lookup = contribution_bonus.foreman_contribution_bonuses(db, date_to, foreman_ids=[foreman.id])
    bonus_value = bonus_lookup[foreman.id].bonus if foreman.id in bonus_lookup else 0
    general_score = contribution_bonus.general_performance_score(overall.total_score, bonus_value)

    overall_level = resolve_performance_level(general_score, levels)
    overall_outstanding = is_outstanding_performance(general_score)
    show_congrats = overall_outstanding
    congrats_kpis = [e for e in strong if e["outstanding_performance"]] if show_congrats else []

    weekly_points = analytics.trend(db, filters, granularity="week", foreman_id=foreman.id)
    reliable_weekly_scores = [p.total_score for p in weekly_points if p.is_reliable]
    trend_shape = _classify_trend_shape(reliable_weekly_scores)

    prev_year, prev_month = _previous_month(year, month)
    prev_from, prev_to = _month_bounds(prev_year, prev_month)
    prev_filters = Filters(date_from=prev_from, date_to=prev_to)
    prev_overall = {s.key: s for s in analytics.foreman_scores(db, prev_filters)}.get(foreman.id)
    previous_month: dict = {"available": False}
    if prev_overall is not None and prev_overall.is_reliable:
        prev_bonus_lookup = contribution_bonus.foreman_contribution_bonuses(db, prev_to, foreman_ids=[foreman.id])
        prev_bonus_value = prev_bonus_lookup[foreman.id].bonus if foreman.id in prev_bonus_lookup else 0
        prev_general_score = contribution_bonus.general_performance_score(prev_overall.total_score, prev_bonus_value)
        prev_rows = {r["kpi_id"]: r for r in analytics.foreman_kpi_breakdown(db, prev_filters, foreman.id)}
        per_kpi = []
        for kpi in kpis_by_id.values():
            cur_row = personal_rows.get(kpi.id)
            prev_row = prev_rows.get(kpi.id)
            if not cur_row or not prev_row or cur_row["avg_actual"] is None or prev_row["avg_actual"] is None:
                continue
            diff = float(cur_row["avg_actual"]) - float(prev_row["avg_actual"])
            is_improvement = (diff > 0) == kpi.success_direction_higher if abs(diff) > _EPSILON_ABS else True
            per_kpi.append({
                "code": kpi.code, "name": kpi.name,
                "diff": round(diff, kpi.decimal_places),
                "is_improvement": is_improvement,
            })
        previous_month = {
            "available": True,
            "label": month_label(prev_to),
            "overall_diff": round(general_score - prev_general_score, 2),
            "per_kpi": per_kpi,
        }

    return {
        **header,
        "org": org,
        "organization_history": organization_history,
        "insufficient_data": False,
        "overall": {
            "score": round(general_score, 2),
            "operational_score": round(overall.total_score, 2),
            "contribution_bonus": bonus_value,
            "level": foreman_level_payload(general_score, levels),
            "outstanding_performance": overall_outstanding,
            "kpi_count": {
                "total": len(entries_with_data),
                "above_or_at_target": len(strong),
                "below_target": len(improve),
                "critical": len(critical),
            },
        },
        "summary_text": _build_summary_text(period_label, len(entries_with_data), strong, improve),
        "closing_text": _build_closing_text(period_label, overall_level, strong, improve, critical),
        "kpis": kpi_entries,
        "strengths": [
            {"kpi_code": k["code"], "name": k["name"],
             "text": f"Bu ay {k['name']} alanında hedef seviyesinde veya üzerinde performans gösterdiniz."}
            for k in strong
        ],
        "improvements": [
            {"kpi_code": k["code"], "name": k["name"],
             "text": (f"Bu ay {k['name']} performansınız hedef seviyesinin altında kaldı. "
                      f"{_investigation_hint(k['code'])}")}
            for k in improve
        ],
        "critical_attention": [
            {"kpi_code": k["code"], "name": k["name"],
             "text": (f"{k['name']} KPI'ında bu ay hedef seviyesinin belirgin şekilde altında bir performans "
                      "görülmektedir. Performansı etkileyen nedenlerin değerlendirilmesi için yöneticinizle "
                      "birlikte bu KPI'ı incelemeniz önerilir."),
             "manager_prompt": "Bu konuyu yöneticiniz ile değerlendirmeniz önerilir."}
            for k in critical
        ],
        "congratulations": {
            "shown": show_congrats,
            "text": (
                f"Bu ay {', '.join(k['name'] for k in congrats_kpis)} KPI'larında hedef seviyesinin üzerinde "
                "performans gösterdiniz. Başarılı performansınızı sürdürmenizi dileriz."
            ) if show_congrats and congrats_kpis else None,
            "kpi_codes": [k["code"] for k in congrats_kpis],
        },
        "trend": {
            "weekly_points": [
                {"bucket": p.bucket.isoformat(), "total_score": round(p.total_score, 2), "is_reliable": p.is_reliable}
                for p in weekly_points
            ],
            "shape": trend_shape,
            "text": _TREND_TEXT.get(trend_shape) if trend_shape else None,
        },
        "previous_month": previous_month,
    }


def get_or_generate_monthly_report(
    db: Session, foreman_id: UUID, year: int, month: int, force: bool = False
) -> ForemanMonthlyReport:
    if not is_month_completed(year, month):
        raise ValueError("Yalnızca tamamlanmış aylar için rapor oluşturulabilir.")

    existing = db.scalar(
        select(ForemanMonthlyReport).where(
            ForemanMonthlyReport.foreman_id == foreman_id,
            ForemanMonthlyReport.year == year,
            ForemanMonthlyReport.month == month,
        )
    )
    if existing and not force:
        return existing

    foreman = db.get(Foreman, foreman_id)
    if foreman is None:
        raise ValueError("Formen bulunamadı.")

    report_data = _build_report_data(db, foreman, year, month)
    overall = report_data.get("overall")

    if existing and force:
        existing.generated_at = clock.now_utc()
        existing.overall_score = overall["score"] if overall else None
        existing.overall_level_name = overall["level"]["name"] if overall else None
        existing.is_reliable = not report_data["insufficient_data"]
        existing.report_data = report_data
        existing.version += 1
        db.commit()
        return existing

    row = ForemanMonthlyReport(
        foreman_id=foreman_id, year=year, month=month,
        generated_at=clock.now_utc(),
        overall_score=overall["score"] if overall else None,
        overall_level_name=overall["level"]["name"] if overall else None,
        is_reliable=not report_data["insufficient_data"],
        report_data=report_data,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(
            select(ForemanMonthlyReport).where(
                ForemanMonthlyReport.foreman_id == foreman_id,
                ForemanMonthlyReport.year == year,
                ForemanMonthlyReport.month == month,
            )
        )
    return row


def latest_completed_period() -> tuple[int, int]:
    today = clock.today_local()
    year, month = _previous_month(today.year, today.month)
    return year, month


def build_monthly_report_object_key(year: int, month: int, foreman_id: UUID, report_id: UUID) -> str:
    """Deterministik S3 object key.

    Filename değil, DB'deki stabil `report_id` (UUID) identity kurar — kullanıcı
    girdisi (isim vb.) hiçbir şekilde path'e karışmaz, path traversal riski yoktur.
    Aynı formen+ay için rapor `force=True` ile yeniden üretilirse aynı report satırı
    (aynı id) güncellenir, dolayısıyla aynı key'e overwrite yapılır — bilinçli tasarım.
    """
    return f"reports/{year:04d}/{month:02d}/foremen/{foreman_id}/{report_id}.pdf"


def generate_and_store_report_pdf(
    db: Session, report: ForemanMonthlyReport, settings: Settings | None = None, force: bool = False
) -> ForemanMonthlyReport:
    """Rapor PDF'ini render eder, Private S3'e (veya yerel dev storage'ına) yükler.

    Idempotent: PDF zaten READY ve object_key set edilmişse (force=False) hiçbir şey
    yapmadan döner — aynı job iki kez çalışsa da duplicate üretim/upload olmaz.
    Upload başarısız olursa DB'ye READY yazılmaz (status=FAILED), rapor verisi
    (report_data) kaybolmaz — yalnızca PDF teslimatı başarısız olmuş olur.
    """
    if not force and report.pdf_generation_status == ReportGenerationStatus.READY and report.object_key:
        return report

    settings = settings or get_settings()
    period = f"{report.year:04d}-{report.month:02d}"

    report.pdf_generation_status = ReportGenerationStatus.GENERATING
    db.commit()
    logger.info("report_generation_started report_id=%s foreman_id=%s period=%s", report.id, report.foreman_id, period)
    try:
        pdf_bytes = render_monthly_foreman_report_pdf(report.report_data)
    except Exception:
        report.pdf_generation_status = ReportGenerationStatus.FAILED
        db.commit()
        logger.exception("report_generation_failed report_id=%s foreman_id=%s period=%s", report.id, report.foreman_id, period)
        raise
    logger.info("report_generation_completed report_id=%s foreman_id=%s period=%s", report.id, report.foreman_id, period)

    object_key = build_monthly_report_object_key(report.year, report.month, report.foreman_id, report.id)
    employee_number = report.report_data["foreman"]["employee_number"]
    file_name = f"formen-performans-raporu-{employee_number}-{report.year}-{report.month:02d}.pdf"

    storage = get_report_storage(settings)
    logger.info("report_upload_started report_id=%s object_key=%s", report.id, object_key)
    try:
        storage.upload(object_key, pdf_bytes, "application/pdf")
    except ReportStorageError:
        report.pdf_generation_status = ReportGenerationStatus.FAILED
        db.commit()
        logger.exception("report_upload_failed report_id=%s object_key=%s", report.id, object_key)
        raise
    logger.info("report_upload_completed report_id=%s object_key=%s", report.id, object_key)

    report.storage_provider = ReportStorageProvider(settings.report_storage_provider)
    report.storage_bucket = settings.reports_s3_bucket if settings.report_storage_provider == "s3" else None
    report.object_key = object_key
    report.pdf_file_name = file_name
    report.pdf_content_type = "application/pdf"
    report.pdf_file_size = len(pdf_bytes)
    report.pdf_generated_at = clock.now_utc()
    report.pdf_generation_status = ReportGenerationStatus.READY
    if force:
        report.email_status = ReportEmailStatus.PENDING
        report.emailed_at = None
    db.commit()
    return report
