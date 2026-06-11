"""Wait event and contention rules for Oracle AWR analysis."""

from rule_models import AwrMetrics, RuleResult, Severity

WAIT_DOMINANCE_AMBER = 25.0
WAIT_DOMINANCE_RED = 40.0
BUFFER_BUSY_AMBER = 8.0
BUFFER_BUSY_RED = 15.0

RULES_COUNT = 4


def evaluate_waits(metrics: AwrMetrics) -> list[RuleResult]:
    results: list[RuleResult] = []
    wait = metrics.top_wait_event
    wait_pct = metrics.top_wait_event_pct
    bb_pct = metrics.buffer_busy_waits_pct

    if wait_pct >= WAIT_DOMINANCE_RED:
        results.append(
            RuleResult(
                "WAIT-001",
                "Wait Events",
                Severity.RED,
                f"Top wait '{wait}' dominates at {wait_pct:.1f}% of database time.",
                "Prioritize wait event analysis; correlate with top SQL and session blocking chains.",
            )
        )
    elif wait_pct >= WAIT_DOMINANCE_AMBER:
        results.append(
            RuleResult(
                "WAIT-002",
                "Wait Events",
                Severity.AMBER,
                f"Top wait '{wait}' significant at {wait_pct:.1f}% of database time.",
                "Review wait event trend and associated object-level statistics.",
            )
        )

    if bb_pct >= BUFFER_BUSY_RED:
        results.append(
            RuleResult(
                "WAIT-003",
                "Contention",
                Severity.RED,
                f"Buffer busy waits at {bb_pct:.1f}% — hot block contention on data blocks.",
                "Investigate hot rows/index blocks; consider ASSM, reverse key indexes, or hash partitioning.",
            )
        )
    elif bb_pct >= BUFFER_BUSY_AMBER:
        results.append(
            RuleResult(
                "WAIT-004",
                "Contention",
                Severity.AMBER,
                f"Buffer busy waits at {bb_pct:.1f}% — potential row-level hot spots.",
                "Identify contended objects via ASH/AWR segment statistics.",
            )
        )

    if "enq:" in wait.lower() or "latch" in wait.lower():
        results.append(
            RuleResult(
                "WAIT-005",
                "Contention",
                Severity.AMBER,
                f"Enqueue or latch wait observed: '{wait}'.",
                "Review locking patterns, TX row lock contention, and shared pool latch pressure.",
            )
        )

    return results
