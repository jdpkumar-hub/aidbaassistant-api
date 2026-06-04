"""
Build AWR PDF report data from parsed AWR HTML and rule-engine output (no demo metrics).
"""

from __future__ import annotations

from awr_parser import AwrParseResult
from awr_pdf import AwrReportData, RuleFindingRow, TopSqlRow, WaitEventRow
from bottleneck_engine import BottleneckClassificationResult
from health_score_engine import HealthScoreResult
from rule_models import AwrAnalysisResult, AwrMetrics, Severity


def _wait_severity(pct: float) -> str:
    if pct >= 25:
        return "Critical"
    if pct >= 10:
        return "Warning"
    return "Normal"


def build_awr_report_data(
    parsed: AwrParseResult,
    metrics: AwrMetrics,
    health_result: HealthScoreResult,
    bottleneck_result: BottleneckClassificationResult,
    analysis: AwrAnalysisResult,
) -> AwrReportData:
    """Map live parse + engine results into ReportLab AwrReportData."""
    elapsed = metrics.db_time_minutes
    snap_label = f"{elapsed:.0f} min" if elapsed else "AWR"

    wait_rows: list[WaitEventRow] = [
        WaitEventRow(
            row.event,
            f"{row.pct_db_time:.1f}%",
            "—",
            _wait_severity(row.pct_db_time),
        )
        for row in parsed.wait_events
    ]
    if not wait_rows and metrics.top_wait_event:
        wait_rows.append(
            WaitEventRow(
                metrics.top_wait_event,
                f"{metrics.top_wait_event_pct:.1f}%",
                "—",
                _wait_severity(metrics.top_wait_event_pct),
            )
        )

    sql_rows: list[TopSqlRow] = [
        TopSqlRow(
            row.sql_id,
            f"{row.pct_db_time:.1f}%",
            "—",
            "—",
            "—",
        )
        for row in parsed.top_sql_rows
    ]
    if not sql_rows and metrics.top_sql_id and metrics.top_sql_id != "unknown":
        sql_rows.append(
            TopSqlRow(
                metrics.top_sql_id,
                f"{metrics.top_sql_db_time_pct:.1f}%",
                "—",
                "—",
                "—",
            )
        )

    rule_rows = [
        RuleFindingRow(
            f.rule_id,
            f.severity.value.capitalize()
            if isinstance(f.severity, Severity)
            else str(f.severity).capitalize(),
            f.message,
            f.recommendation,
        )
        for f in analysis.findings
    ]

    recommendations = list(analysis.top_actions or analysis.recommendations)

    return AwrReportData(
        database_name=metrics.database_name,
        instance_name=metrics.instance_name,
        snap_begin=snap_label,
        snap_end="",
        snap_ids=parsed.extraction_notes.get("snap_ids", "—"),
        executive_summary=(
            analysis.business_summary.replace("**", "")
            + "\n\n"
            + analysis.technical_summary.replace("**", "").replace("*", "")
        )[:2400],
        health_score=health_result.health_score,
        risk_level=health_result.risk_level,
        risk_rationale=(
            f"{bottleneck_result.classification} "
            f"(confidence {bottleneck_result.confidence:.1f}%). "
            f"{bottleneck_result.rationale}"
        ),
        key_findings=[f.message for f in analysis.findings[:8]],
        rule_findings=rule_rows,
        wait_events=wait_rows,
        top_sql=sql_rows,
        recommendations=recommendations,
    )
