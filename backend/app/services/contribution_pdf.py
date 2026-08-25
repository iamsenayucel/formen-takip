from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.reporting import PDF_FONT, PDF_FONT_BOLD, _register_pdf_fonts

ACCENT = colors.HexColor("#e90128")
MUTED = colors.HexColor("#6b7280")
SURFACE = colors.HexColor("#f3f4f6")


def _escape(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_contribution_pdf(work: dict) -> bytes:
    _register_pdf_fonts()

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ContribTitle", fontName=PDF_FONT_BOLD, fontSize=20, leading=24, textColor=colors.HexColor("#111827"))
    meta_style = ParagraphStyle("ContribMeta", fontName=PDF_FONT, fontSize=9, leading=13, textColor=MUTED)
    heading_style = ParagraphStyle("ContribHeading", fontName=PDF_FONT_BOLD, fontSize=11, leading=14, textColor=ACCENT, spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle("ContribBody", fontName=PDF_FONT, fontSize=10, leading=14, textColor=colors.HexColor("#1f2937"))
    hero_label_style = ParagraphStyle("ContribHeroLabel", fontName=PDF_FONT, fontSize=9, leading=12, textColor=MUTED)
    hero_value_style = ParagraphStyle("ContribHeroValue", fontName=PDF_FONT_BOLD, fontSize=22, leading=26, textColor=ACCENT)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=work["title"],
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    elements: list = []

    type_label = _escape(work.get("work_type_label") or "")
    status_label = "Yayımlandı" if work["status"] == "published" else "Taslak"
    elements.append(Paragraph(f"{type_label} &nbsp;·&nbsp; {status_label}", meta_style))
    elements.append(Paragraph(_escape(work["title"]), title_style))
    if work.get("summary"):
        elements.append(Paragraph(_escape(work["summary"]), body_style))
    elements.append(Spacer(1, 6))

    foremen_names = ", ".join(f["name"] for f in work.get("foremen", []))
    plants_text = ", ".join(
        f"{p['factory_name']} / {p['name']}" if p.get("factory_name") else p["name"] for p in work.get("plants") or []
    ) or "-"
    date_text = work["work_date"] or "-"
    if work.get("work_date_end"):
        date_text = f"{work['work_date']} — {work['work_date_end']}"

    meta_table = Table(
        [
            ["İlgili Formenler", _escape(foremen_names or "-")],
            ["Fabrika / Tesis", _escape(plants_text)],
            ["Çalışma Tarihi", _escape(date_text)],
            ["Kaydeden", _escape(work.get("created_by") or "-")],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), PDF_FONT_BOLD),
                ("FONTNAME", (1, 0), (1, -1), PDF_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 8))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#e5e7eb"), thickness=1))

    highlighted = work.get("highlighted_gain")
    if highlighted:
        elements.append(Spacer(1, 10))
        unit = f" {highlighted['unit']}" if highlighted.get("unit") else ""
        elements.append(Paragraph("ÖNE ÇIKAN KAZANIM", hero_label_style))
        elements.append(Paragraph(f"{highlighted['value']}{unit}", hero_value_style))
        elements.append(Paragraph(_escape(highlighted["label"]), body_style))

    before_after = work.get("before_after")
    if before_after:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(_escape(before_after.get("metric_label") or "Önce / Sonra"), heading_style))
        ba_table = Table(
            [["Önce", "Sonra", "İyileşme"], [before_after["before"], before_after["after"], before_after["change"]]],
            colWidths=[5.33 * cm, 5.33 * cm, 5.33 * cm],
        )
        ba_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), SURFACE),
                    ("FONTNAME", (0, 0), (-1, 0), PDF_FONT_BOLD),
                    ("FONTNAME", (0, 1), (-1, 1), PDF_FONT_BOLD),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                    ("TEXTCOLOR", (2, 1), (2, 1), ACCENT),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        elements.append(ba_table)

    for heading, field in (
        ("TESPİT EDİLEN PROBLEM", "problem_description"),
        ("UYGULANAN ÇÖZÜM", "solution_description"),
        ("ELDE EDİLEN SONUÇ", "result_description"),
    ):
        if work.get(field):
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(heading, heading_style))
            elements.append(Paragraph(_escape(work[field]), body_style))

    if work.get("badges"):
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(" &nbsp;·&nbsp; ".join(_escape(b) for b in work["badges"]), meta_style))

    doc.build(elements)
    return buffer.getvalue()
