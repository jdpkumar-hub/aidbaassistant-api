"""
Run full AWR analysis pipeline and emit JSON for Next.js API consumers.

Uses: awr_parser, health_score_engine, bottleneck_engine, executive_summary_generator, awr_rules.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from awr_parser import parse_awr_html
from awr_rules import run_awr_rules
from bottleneck_engine import classify_bottleneck
from health_score_engine import calculate_health_score
from rule_models import AwrMetrics, Severity


def _metrics_dict(metrics: AwrMetrics) -> dict[str, Any]:
    return {
        "databaseName": metrics.database_name,
        "instanceName": metrics.instance_name,
        "cpuUsagePct": metrics.cpu_usage_pct,
        "dbTimeAas": metrics.db_time_aas,
        "dbTimeMinutes": metrics.db_time_minutes,
        "topWaitEvent": metrics.top_wait_event,
        "topWaitEventPct": metrics.top_wait_event_pct,
        "topSqlId": metrics.top_sql_id,
        "topSqlDbTimePct": metrics.top_sql_db_time_pct,
        "bufferBusyWaitsPct": metrics.buffer_busy_waits_pct,
        "activeSessionsAvg": metrics.active_sessions_avg,
        "physicalReadsPerSec": metrics.physical_reads_per_sec,
        "logFileSyncPct": metrics.log_file_sync_pct,
        "bufferCacheHitRatioPct": metrics.buffer_cache_hit_ratio_pct,
        "pgaAllocatedMb": metrics.pga_allocated_mb,
        "pgaTargetMb": metrics.pga_target_mb,
        "sharedPoolFreePct": metrics.shared_pool_free_pct,
    }


def _health_dict(health_result) -> dict[str, Any]:
    return {
        "healthScore": health_result.health_score,
        "riskLevel": health_result.risk_level,
        "dimensions": [
            {
                "name": d.name,
                "score": d.score,
                "penalty": d.penalty,
                "maxPenalty": d.max_penalty,
                "detail": d.detail,
            }
            for d in health_result.dimensions
        ],
    }


def _bottleneck_dict(bottleneck_result) -> dict[str, Any]:
    return {
        "classification": bottleneck_result.classification,
        "confidence": bottleneck_result.confidence,
        "rationale": bottleneck_result.rationale,
        "scores": bottleneck_result.scores,
    }


def _summary_dict(analysis) -> dict[str, Any]:
    return {
        "businessSummary": analysis.business_summary,
        "technicalSummary": analysis.technical_summary,
        "topActions": analysis.top_actions,
        "markdown": analysis.executive_summary_markdown,
    }


def run_awr_analysis(html: str | bytes) -> dict[str, Any]:
    """Parse AWR HTML, run engines, return JSON-serializable payload."""
    parsed = parse_awr_html(html)
    if not parsed.success or parsed.metrics is None:
        return {
            "success": False,
            "errors": parsed.errors,
            "warnings": parsed.warnings,
        }

    metrics = parsed.metrics
    health_result = calculate_health_score(metrics)
    bottleneck_result = classify_bottleneck(metrics)
    analysis = run_awr_rules(metrics)

    snap_window = (
        f"{metrics.db_time_minutes:.0f} min snapshot"
        if metrics.db_time_minutes
        else "AWR snapshot"
    )

    wait_events = [
        {"event": row.event, "pctDbTime": row.pct_db_time}
        for row in parsed.wait_events
    ]
    top_sql = [
        {
            "sqlId": row.sql_id,
            "pctDbTime": row.pct_db_time,
            "executions": None,
            "elapsedSec": None,
        }
        for row in parsed.top_sql_rows
    ]

    recommendations = list(analysis.top_actions)
    if not recommendations:
        recommendations = list(analysis.recommendations)

    return {
        "success": True,
        "warnings": parsed.warnings,
        "extractionNotes": parsed.extraction_notes,
        "metrics": _metrics_dict(metrics),
        "snapWindow": snap_window,
        "health": _health_dict(health_result),
        "bottleneck": _bottleneck_dict(bottleneck_result),
        "summary": _summary_dict(analysis),
        "waitEvents": wait_events,
        "topSql": top_sql,
        "recommendations": recommendations,
        "rules": {
            "rulesEvaluated": analysis.rules_evaluated,
            "rulesTriggered": analysis.rules_triggered,
            "findings": [
                {
                    "ruleId": f.rule_id,
                    "category": f.category,
                    "message": f.message,
                    "severity": f.severity.value
                    if isinstance(f.severity, Severity)
                    else f.severity,
                    "recommendation": f.recommendation,
                }
                for f in analysis.findings
            ],
        },
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", ""):
        with open(sys.argv[1], "rb") as f:
            html = f.read()
    else:
        html = sys.stdin.buffer.read()

    result = run_awr_analysis(html)
    sys.stdout.write(json.dumps(result, indent=None))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
