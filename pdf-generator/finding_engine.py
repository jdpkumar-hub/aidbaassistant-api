from dataclasses import dataclass


@dataclass
class IntelligentFinding:
    title: str
    finding: str
    likely_cause: str
    evidence: list[str]
    business_impact: str
    recommendation: str
#================================================================
#==================IO Bottleneck Logic ==========================
#================================================================
def build_io_finding(metrics) -> IntelligentFinding:

    return IntelligentFinding(
        title="Random IO Bottleneck",

        finding=(
            f"{metrics.top_wait_event_pct:.1f}% of database time "
            f"was spent waiting on "
            f"'{metrics.top_wait_event}'."
        ),

        likely_cause=(
            "Single-block index lookups are dominating "
            "database activity."
        ),

        evidence=[
            f"Top Wait Event: {metrics.top_wait_event}",
            f"Wait Contribution: {metrics.top_wait_event_pct:.1f}%",
            f"Physical Reads/sec: {metrics.physical_reads_per_sec:,.0f}",
            f"Top SQL: {metrics.top_sql_id}",
            f"Top SQL Contribution: {metrics.top_sql_db_time_pct:.1f}%"
        ],

        business_impact=(
            "Transaction response times may increase due "
            "to excessive index-driven I/O."
        ),

        recommendation=(
            f"Review SQL_ID {metrics.top_sql_id}, "
            "execution plan, index selectivity, and storage latency."
        ),
    )
#=================================================================
#==================CPU Bottleneck Logic ==========================
#=================================================================

def build_cpu_finding(metrics) -> IntelligentFinding:

    return IntelligentFinding(
        title="CPU Bottleneck",

        finding=(
            f"CPU utilization reached "
            f"{metrics.cpu_usage_pct:.1f}%."
        ),

        likely_cause=(
            "High SQL execution volume or inefficient execution plans."
        ),

        evidence=[
            f"CPU Usage: {metrics.cpu_usage_pct:.1f}%",
            f"AAS: {metrics.db_time_aas:.2f}",
            f"Top SQL: {metrics.top_sql_id}",
            f"Top SQL Contribution: {metrics.top_sql_db_time_pct:.1f}%"
        ],

        business_impact=(
            "Database throughput may be constrained by CPU saturation."
        ),

        recommendation=(
            "Review CPU-intensive SQL statements and execution plans."
        ),
    )

#=================================================================
#==================Main Dispatcher ===============================
#=================================================================
def generate_intelligent_finding(
    bottleneck_type: str,
    metrics,
):

    bottleneck_type = bottleneck_type.lower()

    if "cpu" in bottleneck_type:
        return build_cpu_finding(metrics)

    if "io" in bottleneck_type:
        return build_io_finding(metrics)

    return IntelligentFinding(
        title="General Observation",
        finding="No dominant bottleneck detected.",
        likely_cause="Mixed workload.",
        evidence=[],
        business_impact="Low risk.",
        recommendation="Monitor workload trends.",
    )
    










































