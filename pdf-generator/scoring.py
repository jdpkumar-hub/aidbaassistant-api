"""Health score, risk, bottleneck, and KPI assembly from rule results."""

from __future__ import annotations

from rule_models import (
    AwrMetrics,
    BottleneckClass,
    KpiCard,
    RiskLevel,
    RuleResult,
    Severity,
)

HEALTH_GREEN_MIN = 80
HEALTH_AMBER_MIN = 60

def severity_cpu(pct: float) -> Severity:
    if pct >= 85:
        return Severity.RED
    if pct >= 70:
        return Severity.AMBER
    return Severity.GREEN


def severity_wait_pct(pct: float) -> Severity:
    if pct >= 40:
        return Severity.RED
    if pct >= 25:
        return Severity.AMBER
    return Severity.GREEN


def severity_sql_pct(pct: float) -> Severity:
    if pct >= 25:
        return Severity.RED
    if pct >= 15:
        return Severity.AMBER
    return Severity.GREEN


def severity_db_time_aas(aas: float) -> Severity:
    if aas >= 16:
        return Severity.RED
    if aas >= 8:
        return Severity.AMBER
    return Severity.GREEN


def classify_bottleneck(
    metrics: AwrMetrics,
    results: list[RuleResult] | None = None,
) -> BottleneckClass:
    """Delegate to Bottleneck Classification Engine."""
    from bottleneck_engine import classify_bottleneck as classify

    return classify(metrics).classification


def compute_health_score(metrics: AwrMetrics, results: list[RuleResult] | None = None) -> int:
    """Build database health score (0-100) via AWR Health Score Engine."""
    from health_score_engine import calculate_health_score

    return calculate_health_score(metrics).health_score


def risk_from_health(
    score: int,
    results: list[RuleResult] | None = None,
    metrics: AwrMetrics | None = None,
) -> RiskLevel:
    """Risk level from health score engine (optionally aligned with metrics)."""
    from health_score_engine import calculate_health_score

    if metrics is not None:
        return calculate_health_score(metrics).risk_level
    if score < HEALTH_AMBER_MIN:
        return "High"
    if score < HEALTH_GREEN_MIN:
        return "Medium"
    return "Low"


def build_kpi_cards(
    metrics: AwrMetrics,
    health: int,
    risk: RiskLevel,
    bottleneck: BottleneckClass,
) -> list[KpiCard]:
    def health_sev(s: int) -> Severity:
        if s >= HEALTH_GREEN_MIN:
            return Severity.GREEN
        if s >= HEALTH_AMBER_MIN:
            return Severity.AMBER
        return Severity.RED

    def risk_sev(r: RiskLevel) -> Severity:
        return {
            "Low": Severity.GREEN,
            "Medium": Severity.AMBER,
            "High": Severity.RED,
        }[r]

    return [
        KpiCard(
            "Database Health Score",
            f"{health} / 100",
            health_sev(health),
            "AWR Health Score Engine (6 dimensions)",
        ),
        KpiCard(
            "Risk Level",
            risk,
            risk_sev(risk),
            "Derived from health score and rule severities",
        ),
        KpiCard(
            "Top Wait Event",
            metrics.top_wait_event,
            severity_wait_pct(metrics.top_wait_event_pct),
            f"{metrics.top_wait_event_pct:.1f}% of DB time",
        ),
        KpiCard(
            "CPU Usage",
            f"{metrics.cpu_usage_pct:.1f}%",
            severity_cpu(metrics.cpu_usage_pct),
            "Peak host/DB CPU utilization",
        ),
        KpiCard(
            "DB Time",
            f"{metrics.db_time_aas:.1f} AAS",
            severity_db_time_aas(metrics.db_time_aas),
            f"{metrics.db_time_minutes:.0f} min snapshot",
        ),
        KpiCard(
            "Top SQL",
            metrics.top_sql_id,
            severity_sql_pct(metrics.top_sql_db_time_pct),
            f"{metrics.top_sql_db_time_pct:.1f}% of DB time",
        ),
        KpiCard(
            "Bottleneck Classification",
            bottleneck,
            Severity.AMBER,
            "Bottleneck Classification Engine",
        ),
    ]


def aggregate_recommendations(results: list[RuleResult]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for r in results:
        if r.recommendation and r.recommendation not in seen:
            seen.add(r.recommendation)
            unique.append(r.recommendation)
    return unique[:12]
