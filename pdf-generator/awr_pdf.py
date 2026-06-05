"""
Enterprise Oracle AWR Performance Report — PDF generator (ReportLab).

AI DBA Assistant branded multi-section AWR assessment with dashboard styling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RiskLevel = Literal["Low", "Medium", "High"]

# Enterprise dashboard palette
NAVY_DARK = colors.HexColor("#020617")
NAVY = colors.HexColor("#0a1628")
NAVY_MID = colors.HexColor("#0f2744")
ACCENT = colors.HexColor("#3b82f6")
SILVER = colors.HexColor("#94a3b8")
WHITE = colors.HexColor("#f8fafc")
AMBER = colors.HexColor("#f59e0b")
RED = colors.HexColor("#ef4444")
GREEN = colors.HexColor("#22c55e")
LIGHT_BG = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")
SLATE = colors.HexColor("#334155")

REPORT_TITLE = "Oracle AWR Performance Assessment Report"
BRAND = "AI DBA Assistant"
BRAND_TAGLINE = "Enterprise Oracle Performance Intelligence"


@dataclass
class WaitEventRow:
    wait_event: str
    pct_db_time: str
    waits: str
    severity: str  # Normal, Warning, Critical


@dataclass
class TopSqlRow:
    sql_id: str
    pct_db_time: str
    executions: str
    elapsed_sec: str
    module: str


@dataclass
class RuleFindingRow:
    rule_id: str
    severity: str
    finding: str
    recommendation: str


@dataclass
class AwrReportData:
    database_name: str = "Production Oracle 19c"
    instance_name: str = "PROD_ORCL"
    snap_begin: str = "26-Apr-2026 08:00"
    snap_end: str = "26-Apr-2026 09:00"
    snap_ids: str = "4520 – 4521"
    report_id: str = ""
    generated_at: datetime = field(default_factory=datetime.now)

    executive_summary: str = ""
    health_score: int = 72
    risk_level: RiskLevel = "Medium"
    risk_rationale: str = ""

    key_findings: list[str] = field(default_factory=list)
    rule_findings: list[RuleFindingRow] = field(default_factory=list)
    wait_events: list[WaitEventRow] = field(default_factory=list)
    top_sql: list[TopSqlRow] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def _risk_color(level: RiskLevel) -> colors.Color:
    return {"Low": GREEN, "Medium": AMBER, "High": RED}[level]


def _health_color(score: int) -> colors.Color:
    if score >= 80:
        return GREEN
    if score >= 60:
        return AMBER
    return RED


def _color_hex(c: colors.Color) -> str:
    raw = c.hexval() if hasattr(c, "hexval") else "0x334155"
    return "#" + raw.replace("0x", "")[:6]


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Heading1"],
            fontSize=26,
            textColor=WHITE,
            alignment=1,
            spaceAfter=12,
            fontName="Helvetica-Bold",
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontSize=12,
            textColor=SILVER,
            alignment=1,
            spaceAfter=6,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["Normal"],
            fontSize=10,
            textColor=WHITE,
            alignment=1,
            leading=14,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontSize=13,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            textColor=SLATE,
            leading=14,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=10,
            textColor=SLATE,
            leftIndent=12,
            spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontSize=8,
            textColor=SILVER,
            fontName="Helvetica-Bold",
        ),
        "card_value": ParagraphStyle(
            "CardValue",
            parent=base["Normal"],
            fontSize=20,
            textColor=NAVY,
            fontName="Helvetica-Bold",
            alignment=1,
        ),
        "footer_white": ParagraphStyle(
            "FooterWhite",
            parent=base["Normal"],
            fontSize=10,
            textColor=WHITE,
            alignment=1,
            leading=14,
        ),
    }


def _draw_cover_page(canvas, _doc) -> None:
    """Full cover page — no standard header on page 1."""
    canvas.saveState()
    w, h = letter
    canvas.setFillColor(NAVY_DARK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)

    canvas.setFillColor(ACCENT)
    canvas.rect(0, h - 1.2 * inch, w, 0.15 * inch, fill=1, stroke=0)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 28)
    canvas.drawCentredString(w / 2, h - 2.2 * inch, BRAND)

    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(SILVER)
    canvas.drawCentredString(w / 2, h - 2.55 * inch, BRAND_TAGLINE)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(w / 2, h / 2 + 0.5 * inch, "Oracle AWR Performance")
    canvas.drawCentredString(w / 2, h / 2 + 0.15 * inch, "Assessment Report")

    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(SILVER)
    canvas.drawCentredString(w / 2, h / 2 - 0.35 * inch, "Automated Diagnostic Summary")

    canvas.setFillColor(NAVY_MID)
    canvas.roundRect(1.2 * inch, 1.5 * inch, w - 2.4 * inch, 0.9 * inch, 6, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica", 9)
    canvas.drawCentredString(w / 2, 2.05 * inch, "CONFIDENTIAL — FOR AUTHORIZED DBA USE ONLY")

    canvas.setFillColor(SILVER)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(w / 2, 0.75 * inch, f"© {datetime.now().year} {BRAND}")
    canvas.restoreState()


def _draw_body_header_footer(canvas, _doc) -> None:
    """Dashboard header/footer on content pages."""
    canvas.saveState()
    w, h = letter

    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 0.5 * inch, w, 0.5 * inch, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(0.65 * inch, h - 0.33 * inch, BRAND)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SILVER)
    canvas.drawRightString(w - 0.65 * inch, h - 0.33 * inch, REPORT_TITLE)

    canvas.setFillColor(NAVY_MID)
    canvas.rect(0, 0, w, 0.4 * inch, fill=1, stroke=0)
    canvas.setFillColor(SILVER)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        0.65 * inch,
        0.15 * inch,
        f"{BRAND} · {BRAND_TAGLINE}",
    )
    canvas.drawRightString(
        w - 0.65 * inch,
        0.15 * inch,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def _section_header(title: str, styles: dict) -> list:
    return [
        Spacer(1, 0.12 * inch),
        Paragraph(title, styles["section"]),
        HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=8),
    ]


def _bullet_list(items: list[str], styles: dict) -> list:
    return [Paragraph(f"• {item}", styles["bullet"]) for item in items]


def _dashboard_table_style(header_bg: colors.Color) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def _cover_page_flowables(data: AwrReportData, styles: dict) -> list:
    """Spacer after visual cover (drawn on canvas page 1)."""
    return [PageBreak()]


def _health_score_card(data: AwrReportData, styles: dict) -> Table:
    health_c = _health_color(data.health_score)
    risk_c = _risk_color(data.risk_level)

    card = Table(
        [
            [
                Paragraph("<b>HEALTH SCORE</b>", styles["label"]),
                Paragraph("<b>RISK CLASSIFICATION</b>", styles["label"]),
                Paragraph("<b>DATABASE</b>", styles["label"]),
            ],
            [
                Paragraph(
                    f'<font size="22" color="{_color_hex(health_c)}"><b>{data.health_score}</b></font>'
                    f'<font size="10" color="#94a3b8"> /100</font>',
                    styles["body"],
                ),
                Paragraph(
                    f'<font size="16" color="{_color_hex(risk_c)}"><b>{data.risk_level}</b></font>',
                    styles["body"],
                ),
                Paragraph(
                    f"<b>{data.database_name}</b><br/>"
                    f"<font size='9'>{data.instance_name}</font>",
                    styles["body"],
                ),
            ],
        ],
        colWidths=[2.0 * inch, 2.0 * inch, 2.2 * inch],
    )
    card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, ACCENT),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return card


def _risk_classification_block(data: AwrReportData, styles: dict) -> list:
    risk_c = _risk_color(data.risk_level)
    rationale = data.risk_rationale or (
        f"The environment is classified as <b>{data.risk_level}</b> risk based on "
        "CPU utilization trends, wait event profile, and top SQL concentration during "
        "the snapshot interval."
    )
    badge = Table(
        [[Paragraph(f'<font color="{_color_hex(risk_c)}"><b>{data.risk_level} Risk</b></font>', styles["body"])]],
        colWidths=[1.5 * inch],
    )
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 1, risk_c),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [
        badge,
        Spacer(1, 0.1 * inch),
        Paragraph(rationale, styles["body"]),
    ]


def _wait_events_table(rows: list[WaitEventRow]) -> Table:
    data = [["Wait Event", "% DB Time", "Waits", "Severity"]] + [
        [r.wait_event, r.pct_db_time, r.waits, r.severity] for r in rows
    ]
    t = Table(data, colWidths=[3.0 * inch, 0.8 * inch, 1.0 * inch, 0.8 * inch])
    style = _dashboard_table_style(NAVY_MID)
    extra = []
    for i, row in enumerate(rows, start=1):
        sev = row.severity.lower()
        if sev == "critical":
            extra.append(("TEXTCOLOR", (3, i), (3, i), RED))
            extra.append(("FONTNAME", (3, i), (3, i), "Helvetica-Bold"))
        elif sev == "warning":
            extra.append(("TEXTCOLOR", (3, i), (3, i), AMBER))
    t.setStyle(TableStyle(list(style.getCommands()) + extra))
    return t


def _top_sql_table(rows: list[TopSqlRow]) -> Table:
    data = [["SQL ID", "% DB Time", "Executions", "Elapsed (s)", "Module"]] + [
        [r.sql_id, r.pct_db_time, r.executions, r.elapsed_sec, r.module] for r in rows
    ]
    t = Table(
        data,
#       colWidths=[1.1 * inch, 0.85 * inch, 0.95 * inch, 0.9 * inch, 1.6 * inch],
        colWidths=[
            1.2 * inch,
            0.8 * inch,
            0.9 * inch,
            0.9 * inch,
            2.2 * inch
        ],       
    )
    style = _dashboard_table_style(NAVY)
    extra = [("FONTNAME", (0, 1), (0, -1), "Courier"), ("FONTSIZE", (0, 1), (0, -1), 8)]
    t.setStyle(TableStyle(list(style.getCommands()) + extra))
    return t


def _rule_findings_table(rows: list[RuleFindingRow]) -> Table:
    styles = getSampleStyleSheet()

    body_style = ParagraphStyle(
        "TableBody",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        wordWrap="LTR",
    )

    data = [
        ["Severity", "Rule", "Finding", "REcommendation"]
    ]

    for r in rows:
        data.append([
            Paragraph(r.severity, body_style),
            Paragraph(r.rule_id, body_style),
            Paragraph(r.finding, body_style),
            Paragraph(r.recommendation, body_style),
        ])

    t = Table(
        data,
        colWidths=[
            0.5 * inch,   # Severity
            0.8 * inch,   # Rule
            2.5 * inch,   # Finding
            3.8 * inch,   # Recommendation
        ],
        repeatRows=1,
    )

    style = _dashboard_table_style(NAVY_MID)

    extra = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("WORDWRAP", (0, 0), (-1, -1), "LTR"),
    ]

    for i, row in enumerate(rows, start=1):
        sev = row.severity.lower()

        if sev in ("critical", "red"):
            extra.append(("TEXTCOLOR", (0, i), (0, i), RED))
            extra.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))

        elif sev in ("warning", "amber"):
            extra.append(("TEXTCOLOR", (0, i), (0, i), AMBER))
            extra.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))

        elif sev in ("green", "normal"):
            extra.append(("TEXTCOLOR", (0, i), (0, i), GREEN))

    t.setStyle(TableStyle(list(style.getCommands()) + extra))

    return t


def _recommendations_table(items: list[str]) -> Table:
    rows = [["Priority", "Recommendation"]] + [
        [str(i + 1), item] for i, item in enumerate(items)
    ]
    t = Table(rows, colWidths=[0.65 * inch, 5.15 * inch])
    t.setStyle(_dashboard_table_style(ACCENT))
    return t


def _branding_footer(styles: dict) -> list:
    footer = Table(
        [
            [
                Paragraph(
                    f"<b>{BRAND}</b><br/>{BRAND_TAGLINE}<br/>"
                    "<font size='8'>Generated by AI-assisted Oracle AWR analysis</font>",
                    styles["footer_white"],
                )
            ]
        ],
        colWidths=[6.2 * inch],
    )
    footer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY_DARK),
                ("BOX", (0, 0), (-1, -1), 0, ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ]
        )
    )
    return [Spacer(1, 0.25 * inch), footer]


def generate_awr_pdf(data: AwrReportData, output_path: str | Path) -> Path:
    """Build enterprise AWR assessment PDF. Returns output path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not data.report_id:
        data.report_id = f"AWR-{data.generated_at.strftime('%Y%m%d-%H%M')}"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = _build_styles()
    story: list = []

    # Cover (rendered on page 1 via canvas, then break)
    story.extend(_cover_page_flowables(data, styles))

    # Report metadata strip
    meta = Table(
        [
            [
                Paragraph(f"<b>Report ID</b><br/><font face='Courier' size='9'>{data.report_id}</font>", styles["body"]),
                Paragraph(f"<b>Snapshots</b><br/>{data.snap_ids}", styles["body"]),
                Paragraph(
                    f"<b>Interval</b><br/>{data.snap_begin}<br/>to {data.snap_end}",
                    styles["body"],
                ),
            ]
        ],
        colWidths=[2.1 * inch, 2.0 * inch, 2.1 * inch],
    )
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 0.2 * inch))

    # Executive Summary
    story.extend(_section_header("Executive Summary", styles))
    summary = data.executive_summary or (
        "During the reporting interval, the database exhibited elevated CPU utilization "
        "and I/O wait concentration. Top SQL and wait event analysis indicate actionable "
        "tuning opportunities prior to the next business peak."
    )
    story.append(Paragraph(summary, styles["body"]))
    meta_data = [
        ["Database", data.database_name],
        ["Instance", data.instance_name],
        ["Health Score", f"{data.health_score}/100"],
        ["Risk Level", data.risk_level],
        ["Generated", data.generated_at.strftime("%Y-%m-%d %H:%M")],
    ]

    meta_table = Table(
        meta_data,
        colWidths=[1.5 * inch, 4.5 * inch]
    )

    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_BG),
        ("BOX", (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID", (0,0), (-1,-1), 0.25, BORDER),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(meta_table)
    # Health Score Card
    story.extend(_section_header("Health Score Card", styles))
    story.append(_health_score_card(data, styles))

    # Risk Classification
    story.extend(_section_header("Risk Classification", styles))
    story.extend(_risk_classification_block(data, styles))

    # Rule Engine Findings
    story.extend(_section_header("Oracle Rule Engine Findings", styles))
    if data.rule_findings:
        story.append(_rule_findings_table(data.rule_findings))
        story.append(
            Paragraph(
                "<i>Severity, finding, and recommendation from DBA rules (pre-AI).</i>",
                styles["label"],
            )
        )
    else:
        findings = data.key_findings or ["No key findings recorded for this interval."]
        story.extend(_bullet_list(findings, styles))

    story.append(PageBreak())

    # Top Wait Event Analysis
    story.extend(_section_header("Top Wait Event Analysis", styles))
    waits = data.wait_events or [
        WaitEventRow("db file sequential read", "42.3%", "128,450", "Critical"),
        WaitEventRow("buffer busy waits", "18.1%", "45,200", "Warning"),
        WaitEventRow("log file sync", "12.4%", "89,100", "Warning"),
        WaitEventRow("CPU time", "28.0%", "—", "Critical"),
    ]
    story.append(_wait_events_table(waits))
    story.append(
        Paragraph(
            "<i>Wait events ranked by percentage of database time during snapshot window.</i>",
            styles["label"],
        )
    )

    # Top SQL Analysis
    story.extend(_section_header("Top SQL Analysis", styles))
    sql_rows = data.top_sql or [
        TopSqlRow("abc123", "31.2%", "12,450", "4,820", "JDBC Thin Client"),
        TopSqlRow("7x9k2f", "14.8%", "8,200", "2,100", "ORDER_BATCH"),
        TopSqlRow("3m4n8p", "9.1%", "22,100", "1,450", "REPORT_GEN"),
    ]
    story.append(_top_sql_table(sql_rows))

    # Recommendations
    story.extend(_section_header("Recommendations", styles))
    recs = data.recommendations or [
        "Tune SQL_ID abc123 — review execution plan and indexing on ORDERS.",
        "Add index IDX_ORDERS_01 on ORDERS (CUSTOMER_ID, ORDER_DATE).",
        "Increase PGA_AGGREGATE_TARGET to reduce hash join spills to temp.",
        "Investigate buffer busy waits — consider ASSM and hot block remediation.",
    ]
    story.append(_recommendations_table(recs))

    # AI DBA Assistant Footer
    story.extend(_section_header("Report Information", styles))
    story.extend(_branding_footer(styles))

    doc.build(
        story,
        onFirstPage=_draw_cover_page,
        onLaterPages=_draw_body_header_footer,
    )
    return output_path


def awr_report_from_rules(metrics=None) -> AwrReportData:
    """Build PDF report data from rule engine output."""
    from awr_rules import demo_awr_metrics, run_awr_rules

    m = metrics or demo_awr_metrics()
    result = run_awr_rules(m)
    return AwrReportData(
        database_name=m.database_name,
        instance_name=m.instance_name,
        executive_summary=(
            result.business_summary.replace("**", "")
            + "\n\n"
            + result.technical_summary.replace("**", "").replace("*", "")
        )[:2400],
        health_score=result.health_score,
        risk_level=result.risk_level,
        risk_rationale=(
            f"Classified as {result.risk_level} risk with bottleneck "
            f"{result.bottleneck_classification} per Oracle DBA rules."
        ),
        key_findings=[f.message for f in result.findings],
        rule_findings=[
            RuleFindingRow(
                f.rule_id,
                f.severity.value.capitalize()
                if hasattr(f.severity, "value")
                else str(f.severity).capitalize(),
                f.message,
                f.recommendation,
            )
            for f in result.findings
        ],
        wait_events=[
            WaitEventRow(m.top_wait_event, f"{m.top_wait_event_pct:.1f}%", "—", "Critical")
        ]
        + [
            WaitEventRow(
                "buffer busy waits",
                f"{m.buffer_busy_waits_pct:.1f}%",
                "—",
                "Warning" if m.buffer_busy_waits_pct < 15 else "Critical",
            )
        ],
        top_sql=[
            TopSqlRow(
                m.top_sql_id,
                f"{m.top_sql_db_time_pct:.1f}%",
                "12,450",
                "4,820",
                "JDBC Thin Client",
            )
        ],
        recommendations=result.top_actions or result.recommendations,
    )


def demo_awr_report_data() -> AwrReportData:
    """Sample AWR data aligned with demo page narrative."""
    data = awr_report_from_rules()
    data.snap_ids = "4520 – 4521"
    data.snap_begin = "26-Apr-2026 08:00"
    data.snap_end = "26-Apr-2026 09:00"
    data.wait_events = [
        WaitEventRow("db file sequential read", "42.3%", "128,450", "Critical"),
        WaitEventRow("buffer busy waits", "18.1%", "45,220", "Warning"),
        WaitEventRow("log file sync", "12.4%", "89,102", "Warning"),
        WaitEventRow("CPU time", "28.0%", "—", "Critical"),
    ]
    data.top_sql = [
        TopSqlRow("abc123", "31.2%", "12,450", "4,820", "JDBC Thin Client"),
        TopSqlRow("7x9k2f", "14.8%", "8,204", "2,108", "ORDER_BATCH"),
        TopSqlRow("3m4n8p", "9.1%", "22,180", "1,452", "REPORT_GEN"),
        TopSqlRow("9p2q1r", "5.4%", "4,890", "890", "ETL_LOADER"),
    ]
    return data
