from awr_parser import AwrMetrics


def generate_business_summary(metrics: AwrMetrics) -> str:

    if metrics.top_wait_event == "db file sequential read":
        return (
            f"The database is experiencing elevated transaction latency "
            f"driven by random I/O activity. Approximately "
            f"{metrics.top_wait_event_pct:.1f}% of database time was spent "
            f"waiting on '{metrics.top_wait_event}'. "
            f"A single SQL statement contributes "
            f"{metrics.top_sql_db_time_pct:.1f}% of database activity, "
            f"indicating a concentrated performance bottleneck."
        )

    if metrics.cpu_usage_pct > 80:
        return (
            f"The system is under significant CPU pressure. "
            f"CPU utilization reached {metrics.cpu_usage_pct:.1f}% "
            f"during the reporting period, increasing the risk of "
            f"application response delays and throughput degradation."
        )

    if metrics.top_wait_event == "log file sync":
        return (
            f"Transaction processing is being delayed by redo commit waits. "
            f"'{metrics.top_wait_event}' accounted for "
            f"{metrics.top_wait_event_pct:.1f}% of database time."
        )

    return (
        "The database workload completed successfully but exhibited "
        "performance characteristics requiring DBA review."
    )


def generate_technical_summary(metrics: AwrMetrics) -> str:

    return (
        f"Top wait event is '{metrics.top_wait_event}' "
        f"({metrics.top_wait_event_pct:.1f}% DB time). "
        f"Physical reads are approximately "
        f"{metrics.physical_reads_per_sec:,.0f}/sec. "
        f"SQL_ID {metrics.top_sql_id} consumes "
        f"{metrics.top_sql_db_time_pct:.1f}% of DB time. "
        f"Investigation should focus on execution plan efficiency, "
        f"index selectivity, and storage latency."
    )