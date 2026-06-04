"""
Executive Summary Generator — business + technical narrative and top actions (Markdown).
"""

from __future__ import annotations

from dataclasses import dataclass

from bottleneck_engine import BottleneckClassificationResult
from health_score_engine import HealthScoreResult
from rule_models import AwrMetrics, RuleFinding, RuleResult, Severity


@dataclass
class ExecutiveSummaryResult:
    business_summary: str
    technical_summary: str
    top_actions: list[str]
    markdown: str


_BOTTLENECK_ACTIONS: dict[str, str] = {
    "CPU Bottleneck": "Profile top CPU-consuming SQL and sessions; validate connection pool and batch job scheduling.",
    "Random IO Bottleneck": "Tune top SQL for index-friendly access; review execution plans and missing indexes on hot objects.",
    "Sequential Scan Bottleneck": "Eliminate full-table scans on large segments; add selective indexes or partition pruning.",
    "Commit Bottleneck": "Reduce commit frequency where safe; review redo log sizing and storage write latency.",
    "Concurrency Bottleneck": "Remediate hot blocks (ASSM, partitioning, reverse-key indexes); review locking on contended tables.",
    "Memory Bottleneck": "Right-size buffer cache and PGA; address SQL driving spills and physical I/O from memory pressure.",
}


def _risk_phrase(risk: str) -> str:
    return {
        "High": "requires immediate leadership attention and a focused remediation plan",
        "Medium": "should be addressed before the next peak business window",
        "Low": "is within acceptable bounds with continued monitoring recommended",
    }.get(risk, "requires review")


def _business_impact(bottleneck: str, risk: str) -> str:
    impacts = {
        "CPU Bottleneck": "Application response times and batch throughput may degrade under sustained CPU pressure.",
        "Random IO Bottleneck": "User-facing queries and OLTP workflows may experience latency from storage read latency.",
        "Sequential Scan Bottleneck": "Reporting and scan-heavy workloads may compete with OLTP and inflate I/O wait.",
        "Commit Bottleneck": "Commit-heavy applications may see end-user latency tied to redo write performance.",
        "Concurrency Bottleneck": "Transactional hot spots can cause queueing, retries, and uneven session wait times.",
        "Memory Bottleneck": "Memory pressure increases physical I/O and temp usage, amplifying cost and tail latency.",
    }
    base = impacts.get(bottleneck, "Workload efficiency may be below target for service-level expectations.")
    if risk == "High":
        return f"{base} Elevated risk suggests potential SLA exposure if left unaddressed."
    if risk == "Medium":
        return f"{base} Moderate risk warrants proactive tuning to avoid escalation."
    return f"{base} Current risk profile supports stable operations with planned optimization."


def _build_top_actions(
    rule_results: list[RuleResult],
    bottleneck: str,
    metrics: AwrMetrics,
) -> list[str]:
    severity_order = {Severity.RED: 0, Severity.AMBER: 1, Severity.GREEN: 2}
    sorted_rules = sorted(
        rule_results,
        key=lambda r: (severity_order.get(r.severity, 9), r.rule_id),
    )

    actions: list[str] = []
    seen: set[str] = set()

    for rule in sorted_rules:
        if rule.recommendation and rule.recommendation not in seen:
            seen.add(rule.recommendation)
            actions.append(rule.recommendation)
        if len(actions) >= 5:
            return actions[:5]

    fallback = _BOTTLENECK_ACTIONS.get(bottleneck)
    if fallback and fallback not in seen:
        actions.append(fallback)
        seen.add(fallback)

    if len(actions) < 5:
        actions.append(
            f"Prioritize deep dive on SQL_ID {metrics.top_sql_id} "
            f"({metrics.top_sql_db_time_pct:.1f}% of database time)."
        )
    if len(actions) < 5:
        actions.append(
            f"Correlate top wait '{metrics.top_wait_event}' with ASH/AWR segment "
            "and SQL statistics for root-cause validation."
        )
    if len(actions) < 5:
        actions.append(
            "Schedule follow-up AWR comparison after changes to confirm health score improvement."
        )
    if len(actions) < 5:
        actions.append(
            "Engage application owners for change windows aligned to bottleneck remediation."
        )

    return actions[:5]


def _build_business_summary(
    metrics: AwrMetrics,
    health: HealthScoreResult,
    bottleneck: BottleneckClassificationResult,
    critical_count: int,
) -> str:
    window = f"{metrics.db_time_minutes:.0f}-minute"
    return (
        f"During the {window} AWR window, **{metrics.database_name}** "
        f"({metrics.instance_name}) recorded a database health score of "
        f"**{health.health_score}/100**, classified as **{health.risk_level} risk**. "
        f"The primary workload constraint is a **{bottleneck.classification}**, "
        f"which {_risk_phrase(health.risk_level)}. "
        f"{_business_impact(bottleneck.classification, health.risk_level)} "
        f"The assessment identified **{critical_count} critical** rule-based finding(s) "
        f"requiring DBA and application coordination."
    )


def _build_technical_summary(
    metrics: AwrMetrics,
    health: HealthScoreResult,
    bottleneck: BottleneckClassificationResult,
    rule_results: list[RuleResult],
    findings: list[RuleFinding],
) -> str:
    red = [f for f in findings if f.severity == Severity.RED]
    amber = [f for f in findings if f.severity == Severity.AMBER]
    dim_lines = [
        f"- **{d.name}:** {d.detail} (dimension score {d.score:.0f}/100)"
        for d in health.dimensions
    ]

    finding_lines = []
    for f in red[:3]:
        finding_lines.append(f"- **[{f.rule_id}]** {f.message}")
    for f in amber[:2]:
        if len(finding_lines) < 5:
            finding_lines.append(f"- **[{f.rule_id}]** {f.message}")

    return (
        f"**Snapshot:** {metrics.db_time_minutes:.0f} min · "
        f"**AAS:** {metrics.db_time_aas:.1f} · "
        f"**Active sessions (avg):** {metrics.active_sessions_avg:.0f}\n\n"
        f"**Bottleneck:** {bottleneck.classification} "
        f"(confidence {bottleneck.confidence:.0f}%) — {bottleneck.rationale}\n\n"
        f"**Core metrics:** CPU {metrics.cpu_usage_pct:.1f}% · "
        f"Top wait *{metrics.top_wait_event}* ({metrics.top_wait_event_pct:.1f}% DB time) · "
        f"Buffer busy {metrics.buffer_busy_waits_pct:.1f}% · "
        f"Log file sync {metrics.log_file_sync_pct:.1f}% · "
        f"Top SQL **{metrics.top_sql_id}** ({metrics.top_sql_db_time_pct:.1f}% DB time) · "
        f"Physical reads {metrics.physical_reads_per_sec:,.0f}/sec · "
        f"Buffer cache hit {metrics.buffer_cache_hit_ratio_pct:.1f}%\n\n"
        f"**Health score dimensions:**\n"
        + "\n".join(dim_lines)
        + "\n\n"
        f"**Rule engine:** {len(rule_results)} findings "
        f"({len(red)} critical, {len(amber)} warning). "
        f"Key signals:\n"
        + ("\n".join(finding_lines) if finding_lines else "- No critical findings triggered.")
    )


def _to_markdown(
    metrics: AwrMetrics,
    health: HealthScoreResult,
    business: str,
    technical: str,
    actions: list[str],
) -> str:
    action_block = "\n".join(f"{i}. {action}" for i, action in enumerate(actions, start=1))
    return (
        f"# Executive Summary — {metrics.database_name}\n\n"
        f"**Instance:** {metrics.instance_name} · "
        f"**Health Score:** {health.health_score}/100 · "
        f"**Risk Level:** {health.risk_level}\n\n"
        f"## Business Summary\n\n"
        f"{business}\n\n"
        f"## Technical Summary\n\n"
        f"{technical}\n\n"
        f"## Top 5 Actions\n\n"
        f"{action_block}\n"
    )


def generate_executive_summary(
    metrics: AwrMetrics,
    health: HealthScoreResult,
    bottleneck: BottleneckClassificationResult,
    rule_results: list[RuleResult],
    findings: list[RuleFinding] | None = None,
) -> ExecutiveSummaryResult:
    """Generate executive summary sections and combined Markdown output."""
    from rule_models import result_to_finding

    finding_list = findings or [result_to_finding(r) for r in rule_results]
    critical_count = sum(1 for f in finding_list if f.severity == Severity.RED)

    business = _build_business_summary(metrics, health, bottleneck, critical_count)
    technical = _build_technical_summary(
        metrics, health, bottleneck, rule_results, finding_list
    )
    actions = _build_top_actions(rule_results, bottleneck.classification, metrics)
    markdown = _to_markdown(metrics, health, business, technical, actions)

    return ExecutiveSummaryResult(
        business_summary=business,
        technical_summary=technical,
        top_actions=actions,
        markdown=markdown,
    )
