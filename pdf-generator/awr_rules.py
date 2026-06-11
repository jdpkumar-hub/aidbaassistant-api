"""
Oracle Rule Engine orchestrator for AI DBA Assistant.

Runs modular DBA rules (CPU, I/O, waits, memory, SQL) BEFORE AI analysis.
"""

from __future__ import annotations

import cpu_rules
import io_rules
import memory_rules
import scoring
import sql_rules
import waits_rules
from rule_models import (
    AwrAnalysisResult,
    AwrMetrics,
    RuleResult,
    Severity,
    result_to_finding,
)

# Re-export for backward compatibility
from rule_models import KpiCard, RiskLevel, BottleneckClass  # noqa: F401

_EVALUATORS = (
    cpu_rules.evaluate_cpu,
    io_rules.evaluate_io,
    waits_rules.evaluate_waits,
    memory_rules.evaluate_memory,
    sql_rules.evaluate_sql,
)

_RULES_COUNTS = (
    cpu_rules.RULES_COUNT,
    io_rules.RULES_COUNT,
    waits_rules.RULES_COUNT,
    memory_rules.RULES_COUNT,
    sql_rules.RULES_COUNT,
)


def run_all_rules(metrics: AwrMetrics) -> tuple[list[RuleResult], int]:
    """Evaluate all rule modules and return combined results."""
    all_results: list[RuleResult] = []
    rules_evaluated = sum(_RULES_COUNTS)

    for evaluate in _EVALUATORS:
        all_results.extend(evaluate(metrics))

    return all_results, rules_evaluated


def run_awr_rules(metrics: AwrMetrics) -> AwrAnalysisResult:
    """
    Run Oracle Rule Engine on AWR metrics (deterministic, pre-AI).
    Returns health score, KPIs, findings with recommendations.
    """
    rule_results, rules_evaluated = run_all_rules(metrics)
    from bottleneck_engine import classify_bottleneck as classify_bottleneck_engine

    bottleneck_result = classify_bottleneck_engine(metrics)
    bottleneck = bottleneck_result.classification
    from health_score_engine import calculate_health_score

    health_result = calculate_health_score(metrics)
    health = health_result.health_score
    risk = health_result.risk_level
    kpi_cards = scoring.build_kpi_cards(metrics, health, risk, bottleneck)
    findings = [result_to_finding(r) for r in rule_results]
    recommendations = scoring.aggregate_recommendations(rule_results)

    from executive_summary_generator import generate_executive_summary

    summary_doc = generate_executive_summary(
        metrics,
        health_result,
        bottleneck_result,
        rule_results,
        findings,
    )

    return AwrAnalysisResult(
        health_score=health,
        risk_level=risk,
        bottleneck_classification=bottleneck,
        kpi_cards=kpi_cards,
        findings=findings,
        rule_results=rule_results,
        executive_summary=summary_doc.business_summary,
        executive_summary_markdown=summary_doc.markdown,
        business_summary=summary_doc.business_summary,
        technical_summary=summary_doc.technical_summary,
        top_actions=summary_doc.top_actions,
        recommendations=recommendations,
        rules_evaluated=rules_evaluated,
        rules_triggered=len(rule_results),
    )


def demo_awr_metrics() -> AwrMetrics:
    """Sample metrics aligned with demo / analyze UI."""
    return AwrMetrics(
        database_name="Production Oracle 19c",
        instance_name="PROD_ORCL",
        cpu_usage_pct=78.0,
        db_time_aas=12.4,
        db_time_minutes=60.0,
        top_wait_event="db file sequential read",
        top_wait_event_pct=42.3,
        top_sql_id="abc123",
        top_sql_db_time_pct=31.2,
        buffer_busy_waits_pct=18.1,
        active_sessions_avg=142.0,
        physical_reads_per_sec=12500.0,
        log_file_sync_pct=12.4,
        buffer_cache_hit_ratio_pct=86.4,
        pga_allocated_mb=3072.0,
        pga_target_mb=4096.0,
        shared_pool_free_pct=12.0,
    )


def analysis_to_dict(result: AwrAnalysisResult) -> dict:
    """Serialize for API / JSON consumers."""
    return {
        "health_score": result.health_score,
        "risk_level": result.risk_level,
        "bottleneck_classification": result.bottleneck_classification,
        "executive_summary": result.executive_summary,
        "executive_summary_markdown": result.executive_summary_markdown,
        "business_summary": result.business_summary,
        "technical_summary": result.technical_summary,
        "top_actions": result.top_actions,
        "rules_evaluated": result.rules_evaluated,
        "rules_triggered": result.rules_triggered,
        "kpi_cards": [
            {
                "label": k.label,
                "value": k.value,
                "severity": k.severity.value,
                "detail": k.detail,
            }
            for k in result.kpi_cards
        ],
        "findings": [
            {
                "rule_id": f.rule_id,
                "category": f.category,
                "message": f.message,
                "severity": f.severity.value,
                "recommendation": f.recommendation,
            }
            for f in result.findings
        ],
        "recommendations": result.recommendations,
    }
