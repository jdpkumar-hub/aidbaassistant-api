"""Memory (SGA/PGA/buffer cache) rules for Oracle AWR analysis."""

from rule_models import AwrMetrics, RuleResult, Severity

BUFFER_HIT_AMBER = 90.0
BUFFER_HIT_RED = 85.0
PGA_UTIL_AMBER = 75.0
PGA_UTIL_RED = 90.0
SHARED_POOL_FREE_AMBER = 10.0

RULES_COUNT = 6


def evaluate_memory(metrics: AwrMetrics) -> list[RuleResult]:
    results: list[RuleResult] = []
    hit = metrics.buffer_cache_hit_ratio_pct
    pga_util = (
        (metrics.pga_allocated_mb / metrics.pga_target_mb * 100)
        if metrics.pga_target_mb > 0
        else 0
    )

    if hit < BUFFER_HIT_RED:
        results.append(
            RuleResult(
                "MEM-001",
                "Memory",
                Severity.RED,
                f"Buffer cache hit ratio {hit:.1f}% below critical threshold ({BUFFER_HIT_RED:.0f}%).",
                "Increase buffer cache if justified; reduce physical I/O via SQL tuning and indexing.",
            )
        )
    elif hit < BUFFER_HIT_AMBER:
        results.append(
            RuleResult(
                "MEM-002",
                "Memory",
                Severity.AMBER,
                f"Buffer cache hit ratio {hit:.1f}% below target ({BUFFER_HIT_AMBER:.0f}%).",
                "Review top segments driving physical reads; validate buffer pool sizing.",
            )
        )

    if pga_util >= PGA_UTIL_RED:
        results.append(
            RuleResult(
                "MEM-003",
                "Memory",
                Severity.RED,
                f"PGA allocation {pga_util:.0f}% of PGA_AGGREGATE_TARGET — risk of spills to temp.",
                "Increase PGA_AGGREGATE_TARGET; tune hash/sort operations in top SQL.",
            )
        )
    elif pga_util >= PGA_UTIL_AMBER:
        results.append(
            RuleResult(
                "MEM-004",
                "Memory",
                Severity.AMBER,
                f"PGA allocation {pga_util:.0f}% of target — elevated memory pressure.",
                "Review PGA advisory and workarea statistics for large sorts/hash joins.",
            )
        )

    if metrics.shared_pool_free_pct < SHARED_POOL_FREE_AMBER:
        results.append(
            RuleResult(
                "MEM-005",
                "Memory",
                Severity.AMBER,
                f"Shared pool free memory low ({metrics.shared_pool_free_pct:.1f}% free).",
                "Check for shared pool fragmentation; review cursor sharing and literal SQL usage.",
            )
        )

    wait = metrics.top_wait_event.lower()
    if "pga" in wait or "memory" in wait or "direct path temp" in wait:
        results.append(
            RuleResult(
                "MEM-006",
                "Memory",
                Severity.AMBER,
                f"Memory-related wait in top events: '{metrics.top_wait_event}'.",
                "Review temp tablespace usage and PGA/UGA allocation for top sessions.",
            )
        )

    return results
