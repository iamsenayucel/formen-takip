from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.reporting import PDF_FONT, PDF_FONT_BOLD, _register_pdf_fonts

MUTED = colors.HexColor("#6b7280")
SURFACE = colors.HexColor("#f3f4f6")
DARK_TEXT = colors.HexColor("#111827")
BODY_TEXT = colors.HexColor("#1f2937")
CRITICAL_BG = colors.HexColor("#fef2f2")
CRITICAL_BORDER = colors.HexColor("#dc2626")
CONGRATS_BG = colors.HexColor("#f0fdf4")
CONGRATS_BORDER = colors.HexColor("#16a34a")
OUTSTANDING_COLOR = colors.HexColor("#b45309")

_BAR_WIDTH = 6 * cm
_BAR_MAX_SCORE = 120.0


def _escape(value: str | None) -> str:
    if not value:
        return ""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _progress_bar_flowable(score: float | None, color: str) -> Table:
    pct = max(0.0, min(1.0, (score or 0.0) / _BAR_MAX_SCORE))
    filled = max(2, round(_BAR_WIDTH * pct))
    remaining = max(2, round(_BAR_WIDTH - filled))
    table = Table([["", ""]], colWidths=[filled, remaining], rowHeights=[0.3 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(color)),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e5e7eb")),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return table


def _level_chip(level: dict | None, styles: dict) -> Table:
    name = level["name"] if level else "-"
    color = level["color"] if level else "#6b7280"
    chip = Table([[_escape(name)]], colWidths=[3.2 * cm])
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return chip


def _outstanding_chip() -> Table:
    chip = Table([["ÜSTÜN PERFORMANS"]], colWidths=[3.5 * cm])
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
        ("TEXTCOLOR", (0, 0), (-1, -1), OUTSTANDING_COLOR),
        ("BOX", (0, 0), (-1, -1), 1, OUTSTANDING_COLOR),
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return chip


def render_monthly_foreman_report_pdf(report_data: dict) -> bytes:
    _register_pdf_fonts()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("MFRTitle", fontName=PDF_FONT_BOLD, fontSize=18, leading=22, textColor=DARK_TEXT)
    meta_style = ParagraphStyle("MFRMeta", fontName=PDF_FONT, fontSize=9, leading=13, textColor=MUTED)
    heading_style = ParagraphStyle("MFRHeading", fontName=PDF_FONT_BOLD, fontSize=12, leading=15, textColor=DARK_TEXT, spaceBefore=12, spaceAfter=6)
    sub_heading_style = ParagraphStyle("MFRSubHeading", fontName=PDF_FONT_BOLD, fontSize=10, leading=13, textColor=DARK_TEXT, spaceBefore=6, spaceAfter=2)
    body_style = ParagraphStyle("MFRBody", fontName=PDF_FONT, fontSize=10, leading=14, textColor=BODY_TEXT)
    small_style = ParagraphStyle("MFRSmall", fontName=PDF_FONT, fontSize=9, leading=12, textColor=MUTED)
    score_style = ParagraphStyle("MFRScore", fontName=PDF_FONT_BOLD, fontSize=26, leading=30, textColor=DARK_TEXT)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title="Aylık Formen Performans Raporu",
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    elements: list = []

    foreman = report_data["foreman"]
    period = report_data["period"]
    org = report_data.get("org")

    elements.append(Paragraph(f"Aylık Bireysel Formen Değerlendirme Raporu — {_escape(period['label'])}", title_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        f"{_escape(foreman['full_name'])} &nbsp;·&nbsp; Sicil No: {_escape(foreman['employee_number'])}", meta_style
    ))
    if org:
        plants_text = ", ".join(p["name"] for p in org["plants"])
        elements.append(Paragraph(
            f"{_escape(org.get('factory_name'))} &nbsp;·&nbsp; {_escape(plants_text)} &nbsp;·&nbsp; "
            f"Şef: {_escape(org.get('chief_name'))}", meta_style
        ))
    elements.append(Paragraph(f"Rapor oluşturulma tarihi: {report_data['generated_at'][:10]}", small_style))

    organization_history = report_data.get("organization_history") or []
    if len(organization_history) > 1:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Ay içinde organizasyon değişikliği:", small_style))
        for entry in organization_history:
            plants_text = ", ".join(p["name"] for p in entry["plants"])
            elements.append(Paragraph(
                f"{_escape(entry['date_from'])} – {_escape(entry['date_to'])}: "
                f"{_escape(entry.get('factory_name'))} &nbsp;·&nbsp; {_escape(plants_text)} &nbsp;·&nbsp; "
                f"Şef: {_escape(entry.get('chief_name'))}", small_style
            ))

    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=1))

    if report_data.get("insufficient_data"):
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(report_data.get("insufficient_data_reason", ""), body_style))
        doc.build(elements)
        return buffer.getvalue()

    overall = report_data["overall"]
    elements.append(Spacer(1, 10))
    summary_table = Table(
        [[Paragraph(f"{overall['score']:.1f}", score_style), _level_chip(overall["level"], styles), Paragraph(_escape(report_data["summary_text"]), body_style)]],
        colWidths=[3.5 * cm, 3.5 * cm, 9 * cm],
    )
    summary_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elements.append(summary_table)
    if overall.get("operational_score") is not None:
        elements.append(Spacer(1, 2))
        elements.append(Paragraph(
            f"Genel Performans = Operasyonel Performans ({overall['operational_score']:.1f}) "
            f"+ Operational Impact+ Bonusu (+{overall['contribution_bonus']})",
            small_style,
        ))
    if overall.get("outstanding_performance"):
        elements.append(Spacer(1, 4))
        elements.append(_outstanding_chip())

    elements.append(Paragraph("KPI Detayları", heading_style))
    for kpi in report_data["kpis"]:
        if not kpi["has_data"]:
            continue
        elements.append(Paragraph(f"{_escape(kpi['name'])} &nbsp;·&nbsp; Puan: {kpi['score']:.1f}", sub_heading_style))
        row = [_level_chip(kpi["level"], styles), _progress_bar_flowable(kpi["score"], kpi["level"]["color"] if kpi["level"] else "#6b7280")]
        info_table = Table([row], colWidths=[3.2 * cm, _BAR_WIDTH])
        info_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        elements.append(info_table)
        detail_lines = [f"Gerçekleşen: {kpi['actual']} {kpi['unit']}"]
        pt = kpi.get("vs_personal_target")
        if pt:
            detail_lines.append(f"Kişisel/Tesis Hedefi: {pt['value']:.2f} {kpi['unit']} ({'hedefte' if pt['status'] == 'at' else ('üzerinde' if pt['status'] == 'above' else 'altında')})")
        fa = kpi.get("vs_factory_average")
        if fa:
            detail_lines.append(f"Fabrika Ortalaması: {fa['value']:.2f} {kpi['unit']} ({'ortalamada' if fa['status'] == 'at' else ('üzerinde' if fa['status'] == 'above' else 'altında')})")
        elements.append(Paragraph(" &nbsp;|&nbsp; ".join(detail_lines), small_style))
        elements.append(Spacer(1, 4))

    elements.append(PageBreak())

    if report_data.get("congratulations", {}).get("shown"):
        elements.append(Paragraph("Tebrikler!", heading_style))
        congrats_table = Table([[Paragraph(_escape(report_data["congratulations"]["text"]), body_style)]], colWidths=[16.5 * cm])
        congrats_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CONGRATS_BG),
            ("BOX", (0, 0), (-1, -1), 1, CONGRATS_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        elements.append(congrats_table)
        elements.append(Spacer(1, 8))

    if report_data["strengths"]:
        elements.append(Paragraph("Güçlü Olduğun Alanlar", heading_style))
        for item in report_data["strengths"]:
            elements.append(Paragraph(f"<b>{_escape(item['name'])}</b> — {_escape(item['text'])}", body_style))
            elements.append(Spacer(1, 2))

    if report_data["improvements"]:
        elements.append(Paragraph("Geliştirebileceğin Alanlar", heading_style))
        for item in report_data["improvements"]:
            elements.append(Paragraph(f"<b>{_escape(item['name'])}</b> — {_escape(item['text'])}", body_style))
            elements.append(Spacer(1, 2))

    if report_data["critical_attention"]:
        elements.append(Paragraph("Dikkat Gerektiren Konular", heading_style))
        for item in report_data["critical_attention"]:
            box = Table([[Paragraph(f"<b>{_escape(item['name'])}</b> — {_escape(item['text'])}<br/><b>{_escape(item['manager_prompt'])}</b>", body_style)]], colWidths=[16.5 * cm])
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CRITICAL_BG),
                ("BOX", (0, 0), (-1, -1), 1, CRITICAL_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]))
            elements.append(box)
            elements.append(Spacer(1, 6))

    trend = report_data.get("trend", {})
    if trend.get("text"):
        elements.append(Paragraph("Aylık Trend Analizi", heading_style))
        elements.append(Paragraph(_escape(trend["text"]), body_style))

    previous_month = report_data.get("previous_month", {})
    if previous_month.get("available"):
        elements.append(Paragraph(f"Geçen Aya Göre ({_escape(previous_month['label'])})", heading_style))
        rows = [["KPI", "Değişim", "Yön"]]
        for item in previous_month["per_kpi"]:
            rows.append([
                item["name"], f"{item['diff']:+.2f}",
                "İyileşme" if item["is_improvement"] else "Kötüleşme",
            ])
        prev_table = Table(rows, colWidths=[7 * cm, 4 * cm, 4 * cm])
        prev_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
            ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), PDF_FONT),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(prev_table)
        elements.append(Spacer(1, 8))

    elements.append(Paragraph("Aylık Değerlendirme", heading_style))
    elements.append(Paragraph(_escape(report_data["closing_text"]), body_style))

    doc.build(elements)
    return buffer.getvalue()
