"""
Enterprise Oracle SQL Performance Report — PDF generator (ReportLab).

AI DBA Assistant branded multi-section DBA assessment PDF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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

# Enterprise palette (AI DBA Assistant)
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


@dataclass
class SqlMetricRow:
    metric: str
    value: str
    status: str  # e.g. Normal, Warning, Critical


@dataclass
class SqlReportData:
    database_name: str = "Production Oracle 19c"
    instance_name: str = "PROD_ORCL"
    sql_id: str = "abc123"
    report_id: str = ""
    generated_at: datetime = field(default_factory=datetime.now)

    executive_summary: str = ""
    health_score: int = 72
    risk_level: RiskLevel = "Medium"

    performance_findings: list[str] = field(default_factory=list)
    sql_metrics: list[SqlMetricRow] = field(default_factory=list)
    index_recommendations: list[str] = field(default_factory=list)
    tuning_recommendations: list[str] = field(default_factory=list)
    expected_benefit: str = ""


def _risk_color(level: RiskLevel) -> colors.Color:
    return {"Low": GREEN, "Medium": AMBER, "High": RED}[level]


def _health_color(score: int) -> colors.Color:
    if score >= 80:
        return GREEN
    if score >= 60:
        return AMBER
    return RED


REPORT_TITLE = "SQL Performance Assessment Report"


def _color_hex(c: colors.Color) -> str:
    """ReportLab color to #RRGGBB for Paragraph markup."""
    raw = c.hexval() if hasattr(c, "hexval") else "0x334155"
    return "#" + raw.replace("0x", "")[:6]


def _draw_header_footer(canvas, _doc) -> None:
    """AI DBA Assistant branded header and footer on every page."""
    canvas.saveState()
    w, h = letter

    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 0.55 * inch, w, 0.55 * inch, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(0.65 * inch, h - 0.38 * inch, "AI DBA Assistant")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SILVER)
    canvas.drawRightString(
        w - 0.65 * inch,
        h - 0.38 * inch,
        "Enterprise Oracle Performance Intelligence",
    )

    canvas.setFillColor(NAVY_MID)
    canvas.rect(0, 0, w, 0.45 * inch, fill=1, stroke=0)
    canvas.setFillColor(SILVER)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(
        0.65 * inch,
        0.18 * inch,
        f"Confidential — {REPORT_TITLE}",
    )
    canvas.drawRightString(
        w - 0.65 * inch,
        0.18 * inch,
        f"Page {canvas.getPageNumber()}",
    )
    canvas.restoreState()


def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Heading1"],
            fontSize=22,
            textColor=NAVY,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontSize=11,
            textColor=SILVER,
            spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading2"],
            fontSize=14,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
            fontName="Helvetica-Bold",
            borderPadding=(0, 0, 4, 0),
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#334155"),
            leading=14,
            spaceAfter=8,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#334155"),
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=base["Normal"],
            fontSize=8,
            textColor=SILVER,
            fontName="Helvetica-Bold",
        ),
    }
    return styles


def _section_header(title: str, styles) -> list:
    return [
        Spacer(1, 0.15 * inch),
        Paragraph(title, styles["section"]),
        HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=10),
    ]


def _bullet_list(items: list[str], styles) -> list:
    flowables = []
    for item in items:
        flowables.append(Paragraph(f"• {item}", styles["bullet"]))
    return flowables


def _kpi_table(data: SqlReportData, styles) -> Table:
    risk_c = _risk_color(data.risk_level)
    health_c = _health_color(data.health_score)

    cells = [
        [
            Paragraph("<b>SQL Health Score</b>", styles["label"]),
            Paragraph("<b>Risk Level</b>", styles["label"]),
            Paragraph("<b>Database</b>", styles["label"]),
            Paragraph("<b>SQL ID</b>", styles["label"]),
        ],
        [
            Paragraph(
                f'<font size="18" color="{_color_hex(health_c)}"><b>{data.health_score}</b></font>'
                f' <font size="10" color="#94a3b8">/ 100</font>',
                styles["body"],
            ),
            Paragraph(
                f'<font size="14" color="{_color_hex(risk_c)}"><b>{data.risk_level}</b></font>',
                styles["body"],
            ),
            Paragraph(data.database_name, styles["body"]),
            Paragraph(f'<font face="Courier">{data.sql_id}</font>', styles["body"]),
        ],
    ]

    t = Table(cells, colWidths=[1.4 * inch, 1.2 * inch, 2.0 * inch, 1.6 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_MID),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def _sql_metrics_table(rows: list[SqlMetricRow], styles) -> Table:
    header = ["Metric", "Value", "Status"]
    data = [header] + [[r.metric, r.value, r.status] for r in rows]

    t = Table(data, colWidths=[2.4 * inch, 2.0 * inch, 1.4 * inch])
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("FONTNAME", (1, 1), (1, -1), "Courier"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for i, row in enumerate(rows, start=1):
        status = row.status.lower()
        if status == "critical":
            style_commands.append(("TEXTCOLOR", (2, i), (2, i), RED))
            style_commands.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
        elif status == "warning":
            style_commands.append(("TEXTCOLOR", (2, i), (2, i), AMBER))

    t.setStyle(TableStyle(style_commands))
    return t


def _recommendations_table(
    title: str, items: list[str], styles, accent: colors.Color
) -> list:
    flowables = _section_header(title, styles)
    if not items:
        flowables.append(Paragraph("No recommendations at this time.", styles["body"]))
        return flowables

    rows = [["#", "Recommendation"]] + [
        [str(i + 1), item] for i, item in enumerate(items)
    ]
    t = Table(rows, colWidths=[0.45 * inch, 5.35 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), accent),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flowables.append(t)
    flowables.append(Spacer(1, 0.12 * inch))
    return flowables


def generate_sql_dba_pdf(data: SqlReportData, output_path: str | Path) -> Path:
    """Build multi-section enterprise SQL DBA PDF and return output path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not data.report_id:
        data.report_id = f"SQL-{data.sql_id.upper()}-{data.generated_at.strftime('%Y%m%d')}"

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.85 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = _build_styles()
    story: list = []

    # --- Cover / title block ---
    story.append(Spacer(1, 0.35 * inch))
    story.append(
        Paragraph("SQL Performance Assessment Report", styles["cover_title"])
    )
    story.append(
        Paragraph(
            f"<b>AI DBA Assistant</b> — Automated Oracle SQL Analysis",
            styles["cover_sub"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    meta = (
        f"Report ID: <font face='Courier'>{data.report_id}</font><br/>"
        f"Generated: {data.generated_at.strftime('%d-%b-%Y %H:%M UTC')}<br/>"
        f"Instance: {data.instance_name} · Database: {data.database_name}"
    )
    story.append(Paragraph(meta, styles["body"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(_kpi_table(data, styles))
    story.append(Spacer(1, 0.25 * inch))

    # --- 1. Executive Summary ---
    story.extend(_section_header("1. Executive Summary", styles))
    summary = data.executive_summary or (
        "This report summarizes SQL performance for the target statement during the "
        "analysis window. Review health score, risk level, and prioritized recommendations."
    )
    story.append(Paragraph(summary, styles["body"]))

    # --- 2–3. Health Score & Risk (highlighted in KPI; expanded note) ---
    story.extend(_section_header("2. SQL Health Score & 3. Risk Level", styles))
    story.append(
        Paragraph(
            f"The statement received a health score of <b>{data.health_score}/100</b>, "
            f"classified as <b>{data.risk_level}</b> risk based on CPU consumption, "
            "wait profile, execution frequency, and plan stability.",
            styles["body"],
        )
    )

    # --- 4. Performance Findings ---
    story.extend(_section_header("4. Performance Findings", styles))
    findings = data.performance_findings or ["No critical findings recorded."]
    story.extend(_bullet_list(findings, styles))

    # --- 5. SQL Metrics Table ---
    story.extend(_section_header("5. SQL Metrics", styles))
    metrics = data.sql_metrics or [
        SqlMetricRow("Executions", "12,450", "Warning"),
        SqlMetricRow("Elapsed Time (s)", "4,820", "Critical"),
        SqlMetricRow("CPU Time (s)", "3,910", "Critical"),
        SqlMetricRow("Buffer Gets", "89.2M", "Critical"),
        SqlMetricRow("Disk Reads", "1.2M", "Warning"),
        SqlMetricRow("Rows Processed", "2.1M", "Normal"),
    ]
    story.append(_sql_metrics_table(metrics, styles))

    story.append(PageBreak())

    # --- 6. Index Recommendations ---
    story.extend(
        _recommendations_table(
            "6. Index Recommendations",
            data.index_recommendations,
            styles,
            NAVY_MID,
        )
    )

    # --- 7. Tuning Recommendations ---
    story.extend(
        _recommendations_table(
            "7. Tuning Recommendations",
            data.tuning_recommendations,
            styles,
            ACCENT,
        )
    )

    # --- 8. Expected Performance Benefit ---
    story.extend(_section_header("8. Expected Performance Benefit", styles))
    benefit = data.expected_benefit or (
        "Implementing index and SQL tuning recommendations is projected to reduce "
        "elapsed time by 40–55% and buffer gets by 35–45% under comparable workload."
    )
    benefit_table = Table(
        [
            ["Metric", "Current", "Projected", "Improvement"],
            ["Elapsed Time", "4,820 s", "2,100 s", "↓ 56%"],
            ["Buffer Gets", "89.2M", "48M", "↓ 46%"],
            ["CPU Time", "3,910 s", "1,750 s", "↓ 55%"],
        ],
        colWidths=[1.5 * inch, 1.2 * inch, 1.2 * inch, 1.3 * inch],
    )
    benefit_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(benefit_table)
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(benefit, styles["body"]))

    # --- 9. Branding footer block ---
    story.extend(_section_header("9. About This Report", styles))
    story.append(
        Paragraph(
            "<b>AI DBA Assistant</b> delivers enterprise Oracle performance intelligence "
            "for DBAs, consultants, and IT operations teams. This document was generated "
            "using AI-assisted analysis of AWR and SQL workload data. "
            "For questions or enterprise licensing, contact your administrator.",
            styles["body"],
        )
    )
    brand_footer = Table(
        [[Paragraph("<b>AI DBA Assistant</b><br/>Enterprise Oracle Performance Intelligence", styles["body"])]],
        colWidths=[6.2 * inch],
    )
    brand_footer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    story.append(Spacer(1, 0.2 * inch))
    story.append(brand_footer)

    doc.build(
        story,
        onFirstPage=_draw_header_footer,
        onLaterPages=_draw_header_footer,
    )
    return output_path


def demo_report_data() -> SqlReportData:
    """Sample data matching demo / analyze report narrative."""
    return SqlReportData(
        database_name="Production Oracle 19c",
        instance_name="PROD_ORCL",
        sql_id="abc123",
        executive_summary=(
            "SQL_ID abc123 is the dominant consumer of database time during the reporting "
            "interval, accounting for approximately 31% of DB time with elevated buffer gets "
            "and CPU utilization. Buffer busy waits on the orders subsystem suggest hot-block "
            "contention. Immediate index review and statement tuning are recommended before "
            "the next peak processing window."
        ),
        health_score=72,
        risk_level="Medium",
        performance_findings=[
            "High CPU utilization correlated with repeated full table scans on ORDERS.",
            "Buffer busy waits (18% of DB time) on index leaf blocks — hot row contention.",
            "Top SQL bottleneck: SQL_ID abc123 — 31% of database time, 89.2M buffer gets.",
            "Execution plan instability detected between child cursors 0 and 1.",
        ],
        sql_metrics=[
            SqlMetricRow("SQL ID", "abc123", "Normal"),
            SqlMetricRow("Executions", "12,450", "Warning"),
            SqlMetricRow("Elapsed Time (sec)", "4,820", "Critical"),
            SqlMetricRow("CPU Time (sec)", "3,910", "Critical"),
            SqlMetricRow("Buffer Gets", "89,200,000", "Critical"),
            SqlMetricRow("Disk Reads", "1,240,000", "Warning"),
            SqlMetricRow("Rows Processed", "2,100,000", "Normal"),
            SqlMetricRow("% of Total DB Time", "31.2%", "Critical"),
        ],
        index_recommendations=[
            "Create index IDX_ORDERS_01 on ORDERS (CUSTOMER_ID, ORDER_DATE) — estimated high impact.",
            "Consider composite index on ORDER_LINES (ORDER_ID, PRODUCT_ID) for nested loop joins.",
            "Review unused indexes on ORDERS_ARCHIVE to reduce DML overhead.",
        ],
        tuning_recommendations=[
            "Tune SQL abc123 — rewrite subquery to use analytic functions; avoid SELECT *.",
            "Increase PGA_AGGREGATE_TARGET if hash joins spill to temp (current pga max 512MB).",
            "Gather optimizer statistics on ORDERS and ORDER_LINES (stale > 14 days).",
            "Enable SQL Plan Baseline for stable plan after validation in QA.",
        ],
        expected_benefit=(
            "After applying IDX_ORDERS_01 and SQL rewrite, projected elapsed time reduction "
            "of 40–55% and buffer gets reduction of 35–45% based on comparable workloads."
        ),
    )
