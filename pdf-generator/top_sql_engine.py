from dataclasses import dataclass

@dataclass
class SqlInsight:
    sql_id: str
    severity: str
    title: str
    finding: str
    likely_cause: str
    business_impact: str
    estimated_gain: str
    evidence: list[str]
    recommendation: list[str]

def analyze_top_sql(metrics):

    pct = metrics.top_sql_db_time_pct

    if pct >= 50:
        severity = "High"
        gain = "30-50%"
    elif pct >= 25:
        severity = "Medium"
        gain = "15-30%"
    else:
        severity = "Low"
        gain = "5-15%"

    wait_event = (metrics.top_wait_event or "").lower()

    likely_cause = (
        "Execution plan review required."
    )

    if "sequential read" in wait_event:
        likely_cause = (
            "Possible missing index causing excessive single block reads."
        )

    elif "scattered read" in wait_event:
        likely_cause = (
            "Full table scans detected."
        )

    elif "cpu" in wait_event:
        likely_cause = (
            "CPU intensive SQL execution."
        )

    return SqlInsight(
        sql_id=metrics.top_sql_id,

        severity=severity,

        title="Dominant SQL Statement",

        finding=(
            f"SQL_ID {metrics.top_sql_id} contributes "
            f"{pct:.1f}% of total database time."
        ),

        likely_cause=likely_cause,

        business_impact=(
            "A single SQL statement dominates workload "
            "and may impact response times."
        ),

        estimated_gain=gain,

        evidence=[
            f"SQL_ID: {metrics.top_sql_id}",
            f"DB Time Contribution: {pct:.1f}%",
            f"Top Wait Event: {metrics.top_wait_event}",
        ],

        recommendation=[
            "Review execution plan",
            "Validate indexing strategy",
            "Check stale optimizer statistics",
            "Evaluate SQL rewrite opportunities",
        ],
    )