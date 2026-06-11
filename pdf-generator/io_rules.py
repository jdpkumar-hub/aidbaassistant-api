"""I/O and storage wait rules for Oracle AWR analysis."""

from rule_models import AwrMetrics, RuleResult, Severity

PHYSICAL_READS_AMBER = 8000.0
PHYSICAL_READS_RED = 15000.0
LOG_SYNC_AMBER_PCT = 10.0
LOG_SYNC_RED_PCT = 20.0

RULES_COUNT = 4


def evaluate_io(metrics: AwrMetrics) -> list[RuleResult]:
    results: list[RuleResult] = []
    wait = metrics.top_wait_event.lower()

    if metrics.physical_reads_per_sec >= PHYSICAL_READS_RED:
        results.append(
            RuleResult(
                "IO-001",
                "I/O",
                Severity.RED,
                f"Physical reads {metrics.physical_reads_per_sec:,.0f}/sec — high storage throughput demand.",
                "Review ASM disk group performance, storage latency, and full scan SQL driving reads.",
            )
        )
    elif metrics.physical_reads_per_sec >= PHYSICAL_READS_AMBER:
        results.append(
            RuleResult(
                "IO-002",
                "I/O",
                Severity.AMBER,
                f"Physical reads {metrics.physical_reads_per_sec:,.0f}/sec — elevated I/O pressure.",
                "Validate buffer cache sizing and index access paths to reduce physical I/O.",
            )
        )

    if any(k in wait for k in ("db file sequential", "db file scattered", "direct path read")):
        if metrics.top_wait_event_pct >= 25:
            results.append(
                RuleResult(
                    "IO-003",
                    "I/O",
                    Severity.RED if metrics.top_wait_event_pct >= 40 else Severity.AMBER,
                    f"Top wait '{metrics.top_wait_event}' at {metrics.top_wait_event_pct:.1f}% — I/O bound workload.",
                    "Tune SQL for index-friendly access; review storage subsystem and file layout.",
                )
            )

    log_pct = metrics.log_file_sync_pct
    if log_pct >= LOG_SYNC_RED_PCT or (
        "log file sync" in wait and metrics.top_wait_event_pct >= LOG_SYNC_AMBER_PCT
    ):
        results.append(
            RuleResult(
                "IO-004",
                "I/O",
                Severity.RED if log_pct >= LOG_SYNC_RED_PCT else Severity.AMBER,
                f"Log file sync wait significant ({log_pct:.1f}% DB time or top wait).",
                "Review commit frequency, redo log sizing, and redo write latency on storage.",
            )
        )

    return results
