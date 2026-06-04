"""CPU utilization rules for Oracle AWR analysis."""

from rule_models import AwrMetrics, RuleResult, Severity

CPU_AMBER_PCT = 70.0
CPU_RED_PCT = 85.0
DB_TIME_AAS_AMBER = 8.0
DB_TIME_AAS_RED = 16.0

RULES_COUNT = 4


def evaluate_cpu(metrics: AwrMetrics) -> list[RuleResult]:
    results: list[RuleResult] = []
    cpu = metrics.cpu_usage_pct
    aas = metrics.db_time_aas

    if cpu >= CPU_RED_PCT:
        results.append(
            RuleResult(
                "CPU-001",
                "CPU",
                Severity.RED,
                f"CPU utilization critical at {cpu:.1f}% (threshold {CPU_RED_PCT:.0f}%).",
                "Profile top CPU sessions and SQL; reduce parse/execute overhead and review runaway queries.",
            )
        )
    elif cpu >= CPU_AMBER_PCT:
        results.append(
            RuleResult(
                "CPU-002",
                "CPU",
                Severity.AMBER,
                f"CPU utilization elevated at {cpu:.1f}% (threshold {CPU_AMBER_PCT:.0f}%).",
                "Monitor CPU trend across snapshots; validate top SQL and connection pool sizing.",
            )
        )

    if aas >= DB_TIME_AAS_RED:
        results.append(
            RuleResult(
                "CPU-003",
                "Load",
                Severity.RED,
                f"Average Active Sessions {aas:.1f} exceeds critical threshold ({DB_TIME_AAS_RED:.0f}).",
                "Review connection storms, job scheduling, and consider resource manager limits.",
            )
        )
    elif aas >= DB_TIME_AAS_AMBER:
        results.append(
            RuleResult(
                "CPU-004",
                "Load",
                Severity.AMBER,
                f"Average Active Sessions {aas:.1f} above warning threshold ({DB_TIME_AAS_AMBER:.0f}).",
                "Validate application concurrency and queue depth during peak windows.",
            )
        )

    return results
