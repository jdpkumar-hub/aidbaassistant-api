"""Top SQL workload rules for Oracle AWR analysis."""

from rule_models import AwrMetrics, RuleResult, Severity

TOP_SQL_AMBER_PCT = 15.0
TOP_SQL_RED_PCT = 25.0

RULES_COUNT = 3


def evaluate_sql(metrics: AwrMetrics) -> list[RuleResult]:
    results: list[RuleResult] = []
    sql_id = metrics.top_sql_id
    pct = metrics.top_sql_db_time_pct

    if pct >= TOP_SQL_RED_PCT:
        results.append(
            RuleResult(
                "SQL-001",
                "Top SQL",
                Severity.RED,
                f"SQL_ID {sql_id} consumes {pct:.1f}% of database time — primary workload bottleneck.",
                f"Tune SQL_ID {sql_id}: review execution plan, indexes, and bind variable usage.",
            )
        )
    elif pct >= TOP_SQL_AMBER_PCT:
        results.append(
            RuleResult(
                "SQL-002",
                "Top SQL",
                Severity.AMBER,
                f"SQL_ID {sql_id} elevated at {pct:.1f}% of database time.",
                f"Profile SQL_ID {sql_id} with SQL Tuning Advisor and plan stability checks.",
            )
        )

    if pct >= TOP_SQL_AMBER_PCT and metrics.cpu_usage_pct >= 70:
        results.append(
            RuleResult(
                "SQL-003",
                "Top SQL",
                Severity.AMBER,
                f"SQL_ID {sql_id} correlates with high CPU ({metrics.cpu_usage_pct:.1f}%) and DB time share.",
                "Consider SQL rewrite, batching, or caching for repeated high-cost executions.",
            )
        )

    return results
