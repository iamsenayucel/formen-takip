
from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import reportlab
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.turkish import turkish_sort_key
from app.models.enums import ReportType
from app.models.foreman import Chief, Foreman, ForemanAssignment
from app.models.integration import DataQualityIssue
from app.models.kpi import Kpi
from app.models.organization import Factory, Plant, Shift
from app.models.performance import PerformanceRecord
from app.schemas.common import Filters
from app.services import analytics, contribution_bonus
from app.services.kpi_engine import resolve_performance_level
from app.services.level_lookup import get_performance_levels


PDF_FONT = "Vera"
PDF_FONT_BOLD = "Vera-Bold"
_PDF_FONT_FILES = {
    PDF_FONT: "Vera.ttf",
    PDF_FONT_BOLD: "VeraBd.ttf",
    "Vera-Italic": "VeraIt.ttf",
    "Vera-BoldItalic": "VeraBI.ttf",
}


def _register_pdf_fonts() -> None:
    if PDF_FONT in pdfmetrics.getRegisteredFontNames():
        return
    fonts_dir = Path(reportlab.__file__).parent / "fonts"
    for name, file_name in _PDF_FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, str(fonts_dir / file_name)))
    addMapping(PDF_FONT, 0, 0, PDF_FONT)
    addMapping(PDF_FONT, 1, 0, PDF_FONT_BOLD)
    addMapping(PDF_FONT, 0, 1, "Vera-Italic")
    addMapping(PDF_FONT, 1, 1, "Vera-BoldItalic")


MAX_SUMMARY_ITEMS = 5


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _summarize(values: list[str]) -> str:
    shown = [_escape(v) for v in values[:MAX_SUMMARY_ITEMS]]
    remaining = len(values) - len(shown)
    text = ", ".join(shown)
    return f"{text} (+{remaining} diğer)" if remaining > 0 else text


def build_filters_summary(db: Session, filters: Filters) -> str:
    parts = [f"<b>Dönem:</b> {filters.date_from} — {filters.date_to}"]

    if filters.factory_ids:
        names = [
            f.name for f in db.scalars(
                select(Factory).where(Factory.id.in_(filters.factory_ids)).order_by(Factory.code)
            )
        ]
        parts.append(f"<b>Fabrika:</b> {_summarize(names)}")

    if filters.plant_ids:
        names = [
            p.name for p in db.scalars(
                select(Plant).where(Plant.id.in_(filters.plant_ids)).order_by(Plant.sequence_number)
            )
        ]
        parts.append(f"<b>Tesis:</b> {_summarize(names)}")

    if filters.chief_ids:
        chiefs = db.scalars(select(Chief).where(Chief.id.in_(filters.chief_ids)))
        names = sorted((f"{c.first_name} {c.last_name}" for c in chiefs), key=turkish_sort_key)
        parts.append(f"<b>Şef:</b> {_summarize(names)}")

    if filters.shift_ids:
        names = [
            s.name for s in db.scalars(
                select(Shift).where(Shift.id.in_(filters.shift_ids)).order_by(Shift.sequence)
            )
        ]
        parts.append(f"<b>Vardiya:</b> {_summarize(names)}")

    if filters.kpi_ids:
        names = [
            k.name for k in db.scalars(
                select(Kpi).where(Kpi.id.in_(filters.kpi_ids)).order_by(Kpi.display_order)
            )
        ]
        parts.append(f"<b>KPI:</b> {_summarize(names)}")

    if len(parts) == 1:
        parts.append("<b>Kapsam:</b> Şirket geneli (filtre uygulanmadı)")

    return "&nbsp;&nbsp;|&nbsp;&nbsp;".join(parts)


def _current_plant_by_foreman(db: Session) -> dict:
    result: dict = {}
    for a in db.scalars(select(ForemanAssignment).order_by(ForemanAssignment.start_date)):
        result[a.foreman_id] = a.plant_id
    plants_by_id = {p.id: p.name for p in db.scalars(select(Plant))}
    return {fid: plants_by_id.get(pid) for fid, pid in result.items()}


def _plant_comparison(db: Session, filters: Filters):
    scores = analytics.plant_scores(db, filters)
    plants = {p.id: p for p in db.scalars(select(Plant))}
    factories = {f.id: f for f in db.scalars(select(Factory))}
    headers = ["Tesis Kodu", "Tesis Adı", "Fabrika", "Toplam Puan", "Güvenilir", "Kayıt Sayısı"]
    rows = [
        {
            "Tesis Kodu": plants[s.key].code if s.key in plants else "-",
            "Tesis Adı": plants[s.key].name if s.key in plants else "-",
            "Fabrika": factories[plants[s.key].factory_id].name if s.key in plants and plants[s.key].factory_id in factories else "-",
            "Toplam Puan": round(s.total_score, 2),
            "Güvenilir": "Evet" if s.is_reliable else "Hayır",
            "Kayıt Sayısı": s.record_count,
        }
        for s in sorted(scores, key=lambda x: x.total_score, reverse=True)
    ]
    return headers, rows


def _shift_comparison(db: Session, filters: Filters):
    scores = analytics.shift_scores(db, filters)
    shifts = {s.id: s for s in db.scalars(select(Shift))}
    headers = ["Vardiya Kodu", "Vardiya Adı", "Toplam Puan", "Kayıt Sayısı"]
    rows = [
        {
            "Vardiya Kodu": shifts[s.key].code if s.key in shifts else "-",
            "Vardiya Adı": shifts[s.key].name if s.key in shifts else "-",
            "Toplam Puan": round(s.total_score, 2),
            "Kayıt Sayısı": s.record_count,
        }
        for s in scores
    ]
    return headers, rows


def _foreman_performance(db: Session, filters: Filters, only_critical: bool = False):
    scores = analytics.foreman_scores(db, filters)
    bonuses = contribution_bonus.foreman_contribution_bonuses(db, filters.date_to, foreman_ids=[s.key for s in scores])
    general_by_key = {
        s.key: contribution_bonus.general_performance_score(
            s.total_score, bonuses[s.key].bonus if s.key in bonuses else 0
        )
        for s in scores
    }
    foremen = {f.id: f for f in db.scalars(select(Foreman))}
    plant_by_foreman = _current_plant_by_foreman(db)
    levels = get_performance_levels(db)

    headers = ["Sicil No", "Ad Soyad", "Tesis", "Operasyonel Puan", "Operational Impact+ Bonusu", "Genel Puan", "Seviye", "Güvenilir"]
    rows = []
    for s in sorted(scores, key=lambda x: general_by_key[x.key]):
        general_score = general_by_key[s.key]
        level = resolve_performance_level(general_score, levels)
        if only_critical and level.name != "Kritik":
            continue
        f = foremen.get(s.key)
        rows.append(
            {
                "Sicil No": f.employee_number if f else "-",
                "Ad Soyad": f"{f.first_name} {f.last_name}" if f else "-",
                "Tesis": plant_by_foreman.get(s.key) or "-",
                "Operasyonel Puan": round(s.total_score, 2),
                "Operational Impact+ Bonusu": bonuses[s.key].bonus if s.key in bonuses else 0,
                "Genel Puan": round(general_score, 2),
                "Seviye": level.name,
                "Güvenilir": "Evet" if s.is_reliable else "Hayır",
            }
        )
    if not only_critical:
        rows.sort(key=lambda r: r["Genel Puan"], reverse=True)
    return headers, rows


def _kpi_analysis(db: Session, filters: Filters):
    items = analytics.kpi_summary(db, filters)
    kpis = {k.id: k for k in db.scalars(select(Kpi))}
    headers = ["KPI Kodu", "KPI Adı", "Ortalama Hedef", "Ortalama Gerçekleşen", "Ortalama Puan", "Kayıt Sayısı"]
    rows = [
        {
            "KPI Kodu": kpis[i.kpi_id].code if i.kpi_id in kpis else "-",
            "KPI Adı": kpis[i.kpi_id].name if i.kpi_id in kpis else "-",
            "Ortalama Hedef": round(i.avg_target, 2) if i.avg_target is not None else None,
            "Ortalama Gerçekleşen": round(i.avg_actual, 2) if i.avg_actual is not None else None,
            "Ortalama Puan": round(i.avg_capped_score, 2),
            "Kayıt Sayısı": i.record_count,
        }
        for i in items if i.kpi_id in kpis
    ]
    return headers, rows


def _company_summary(db: Session, filters: Filters):
    scores = analytics.foreman_scores(db, filters)
    bonuses = contribution_bonus.foreman_contribution_bonuses(db, filters.date_to, foreman_ids=[s.key for s in scores])
    levels = get_performance_levels(db)
    headers = ["Performans Seviyesi", "Formen Sayısı", "Ortalama Puan"]
    buckets: dict[str, list[float]] = {lv.name: [] for lv in levels}
    for s in scores:
        general_score = contribution_bonus.general_performance_score(
            s.total_score, bonuses[s.key].bonus if s.key in bonuses else 0
        )
        level = resolve_performance_level(general_score, levels)
        buckets[level.name].append(general_score)
    rows = [
        {
            "Performans Seviyesi": lv.name,
            "Formen Sayısı": len(buckets[lv.name]),
            "Ortalama Puan": round(sum(buckets[lv.name]) / len(buckets[lv.name]), 2) if buckets[lv.name] else None,
        }
        for lv in sorted(levels, key=lambda lv: lv.sort_order, reverse=True)
    ]
    return headers, rows


def _missing_data(db: Session, filters: Filters):
    query = (
        select(
            PerformanceRecord.performance_date, Plant.name.label("plant_name"),
            Foreman.first_name, Foreman.last_name, Kpi.name.label("kpi_name"),
            DataQualityIssue.issue_type, DataQualityIssue.description,
        )
        .select_from(DataQualityIssue)
        .join(PerformanceRecord, PerformanceRecord.id == DataQualityIssue.performance_record_id)
        .join(Plant, Plant.id == PerformanceRecord.plant_id)
        .join(Foreman, Foreman.id == PerformanceRecord.foreman_id)
        .join(Kpi, Kpi.id == PerformanceRecord.kpi_id)
        .where(PerformanceRecord.performance_date >= filters.date_from, PerformanceRecord.performance_date <= filters.date_to)
        .order_by(PerformanceRecord.performance_date.desc())
    )
    headers = ["Tarih", "Tesis", "Formen", "KPI", "Sorun Türü", "Açıklama"]
    rows = [
        {
            "Tarih": row.performance_date.isoformat(),
            "Tesis": row.plant_name,
            "Formen": f"{row.first_name} {row.last_name}",
            "KPI": row.kpi_name,
            "Sorun Türü": row.issue_type.value,
            "Açıklama": row.description,
        }
        for row in db.execute(query)
    ]
    return headers, rows


_BUILDERS = {
    ReportType.COMPANY_SUMMARY: _company_summary,
    ReportType.PLANT_COMPARISON: _plant_comparison,
    ReportType.SHIFT_COMPARISON: _shift_comparison,
    ReportType.FOREMAN_PERFORMANCE: lambda db, f: _foreman_performance(db, f, only_critical=False),
    ReportType.KPI_ANALYSIS: _kpi_analysis,
    ReportType.CRITICAL_PERFORMANCE: lambda db, f: _foreman_performance(db, f, only_critical=True),
    ReportType.MISSING_DATA: _missing_data,
}


def build_report_rows(db: Session, report_type: ReportType, filters: Filters) -> tuple[list[str], list[dict]]:
    builder = _BUILDERS[report_type]
    return builder(db, filters)


def render_csv(headers: list[str], rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def render_xlsx(title: str, headers: list[str], rows: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31] or "Rapor"
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    for col_idx, header in enumerate(headers, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = max(14, len(header) + 2)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def render_pdf(title: str, filters_summary: str, headers: list[str], rows: list[dict]) -> bytes:
    _register_pdf_fonts()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title=title)
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        current = getattr(style, "fontName", None)
        if current is None:
            continue
        style.fontName = PDF_FONT_BOLD if "Bold" in str(current) else PDF_FONT
    elements = [Paragraph(title, styles["Title"]), Paragraph(filters_summary, styles["Normal"]), Spacer(1, 12)]

    table_data = [headers] + [[str(row.get(h, "")) for h in headers] for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
                ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()


REPORT_TITLES = {
    ReportType.COMPANY_SUMMARY: "Şirket Genel Performans Raporu",
    ReportType.PLANT_COMPARISON: "Tesis Karşılaştırma Raporu",
    ReportType.SHIFT_COMPARISON: "Vardiya Karşılaştırma Raporu",
    ReportType.FOREMAN_PERFORMANCE: "Formen Performans Raporu",
    ReportType.KPI_ANALYSIS: "KPI Analiz Raporu",
    ReportType.CRITICAL_PERFORMANCE: "Kritik Performans Raporu",
    ReportType.MISSING_DATA: "Eksik Veri Raporu",
}
