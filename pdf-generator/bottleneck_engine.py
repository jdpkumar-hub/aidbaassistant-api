"""
Bottleneck Classification Engine — classifies AWR workload from metrics and wait profile.

Returns exactly one of:
  CPU Bottleneck, Random IO Bottleneck, Sequential Scan Bottleneck,
  Commit Bottleneck, Concurrency Bottleneck, Memory Bottleneck
"""

from __future__ import annotations

from dataclasses import dataclass

from rule_models import AwrMetrics, BottleneckClass

BOTTLENECK_TYPES: tuple[BottleneckClass, ...] = (
    "CPU Bottleneck",
    "Random IO Bottleneck",
    "Sequential Scan Bottleneck",
    "Commit Bottleneck",
    "Concurrency Bottleneck",
    "Memory Bottleneck",
)

# Tie-break priority (most specific workload signal first)
_TIE_PRIORITY: tuple[BottleneckClass, ...] = (
    "Commit Bottleneck",
    "Concurrency Bottleneck",
    "Memory Bottleneck",
    "Sequential Scan Bottleneck",
    "Random IO Bottleneck",
    "CPU Bottleneck",
)


@dataclass
class BottleneckClassificationResult:
    classification: BottleneckClass
    confidence: float
    scores: dict[str, float]
    rationale: str


def _pga_utilization_pct(metrics: AwrMetrics) -> float:
    if metrics.pga_target_mb <= 0:
        return 0.0
    return metrics.pga_allocated_mb / metrics.pga_target_mb * 100.0


def _score_dimensions(metrics: AwrMetrics) -> dict[BottleneckClass, float]:
    wait = metrics.top_wait_event.lower()
    wait_pct = metrics.top_wait_event_pct
    scores: dict[BottleneckClass, float] = {b: 0.0 for b in BOTTLENECK_TYPES}

    # Commit Bottleneck — log file sync, commit latency
    if "log file sync" in wait:
        scores["Commit Bottleneck"] += 50.0 + wait_pct * 0.6
    scores["Commit Bottleneck"] += min(35.0, metrics.log_file_sync_pct * 2.5)
    if metrics.log_file_sync_pct >= 10.0:
        scores["Commit Bottleneck"] += 10.0

    # Concurrency Bottleneck — locking, latches, hot blocks
    concurrency_waits = (
        "buffer busy",
        "enq:",
        "latch",
        "row lock",
        "library cache lock",
        "cursor:",
        "tx index",
    )
    if any(k in wait for k in concurrency_waits):
        scores["Concurrency Bottleneck"] += 48.0 + wait_pct * 0.55
    scores["Concurrency Bottleneck"] += min(40.0, metrics.buffer_busy_waits_pct * 2.2)
    if metrics.buffer_busy_waits_pct >= 15.0:
        scores["Concurrency Bottleneck"] += 12.0

    # Memory Bottleneck — SGA/PGA pressure, cache, temp
    pga_util = _pga_utilization_pct(metrics)
    memory_waits = ("pga", "memory", "direct path temp", "swap")
    if any(k in wait for k in memory_waits):
        scores["Memory Bottleneck"] += 48.0 + wait_pct * 0.4
    if metrics.buffer_cache_hit_ratio_pct < 90.0:
        scores["Memory Bottleneck"] += (90.0 - metrics.buffer_cache_hit_ratio_pct) * 1.8
    if pga_util >= 75.0:
        scores["Memory Bottleneck"] += (pga_util - 75.0) * 1.0
    if metrics.shared_pool_free_pct < 10.0:
        scores["Memory Bottleneck"] += 12.0

    # Sequential Scan Bottleneck — multiblock / direct path reads (FTS)
    if "db file scattered" in wait:
        scores["Sequential Scan Bottleneck"] += 55.0 + wait_pct * 0.6
    if "direct path read" in wait:
        scores["Sequential Scan Bottleneck"] += 50.0 + wait_pct * 0.5
    if metrics.physical_reads_per_sec >= 10_000.0 and (
        "scattered" in wait or "direct path" in wait
    ):
        scores["Sequential Scan Bottleneck"] += 18.0

    # Random IO Bottleneck — single-block index/table lookups
    if "db file sequential read" in wait:
        scores["Random IO Bottleneck"] += 52.0 + wait_pct * 0.6
    if metrics.physical_reads_per_sec >= 8_000.0 and "sequential" in wait:
        scores["Random IO Bottleneck"] += 20.0

    # CPU Bottleneck — host/DB CPU saturation
    if "cpu" in wait or wait.strip() in ("on cpu", "cpu time"):
        scores["CPU Bottleneck"] += 45.0 + wait_pct * 0.5
    if metrics.cpu_usage_pct >= 70.0:
        scores["CPU Bottleneck"] += (metrics.cpu_usage_pct - 70.0) * 1.5
    if metrics.cpu_usage_pct >= 85.0:
        scores["CPU Bottleneck"] += 15.0
    if metrics.db_time_aas >= 12.0 and metrics.cpu_usage_pct >= 65.0:
        scores["CPU Bottleneck"] += 8.0

    return scores


def _pick_winner(scores: dict[BottleneckClass, float]) -> BottleneckClass:
    max_score = max(scores.values())
    if max_score <= 0:
        return "Random IO Bottleneck"

    leaders = [b for b, s in scores.items() if s == max_score]
    if len(leaders) == 1:
        return leaders[0]

    for candidate in _TIE_PRIORITY:
        if candidate in leaders:
            return candidate
    return leaders[0]


def _build_rationale(
    classification: BottleneckClass,
    metrics: AwrMetrics,
    scores: dict[BottleneckClass, float],
) -> str:
    wait = metrics.top_wait_event
    wait_pct = metrics.top_wait_event_pct
    top_score = scores[classification]

    hints: dict[BottleneckClass, str] = {
        "CPU Bottleneck": (
            f"CPU utilization {metrics.cpu_usage_pct:.1f}% with "
            f"top wait profile indicating CPU-bound work."
        ),
        "Random IO Bottleneck": (
            f"Top wait '{wait}' ({wait_pct:.1f}% DB time) and "
            f"{metrics.physical_reads_per_sec:,.0f} physical reads/sec — "
            "typical of index/single-block I/O."
        ),
        "Sequential Scan Bottleneck": (
            f"Top wait '{wait}' ({wait_pct:.1f}% DB time) with high read throughput "
            f"({metrics.physical_reads_per_sec:,.0f}/sec) — consistent with full scans."
        ),
        "Commit Bottleneck": (
            f"Log file sync at {metrics.log_file_sync_pct:.1f}% DB time; "
            f"top wait '{wait}' ({wait_pct:.1f}%)."
        ),
        "Concurrency Bottleneck": (
            f"Buffer busy waits {metrics.buffer_busy_waits_pct:.1f}% DB time; "
            f"top wait '{wait}' ({wait_pct:.1f}%)."
        ),
        "Memory Bottleneck": (
            f"Buffer cache hit {metrics.buffer_cache_hit_ratio_pct:.1f}%; "
            f"PGA {metrics.pga_allocated_mb:.0f}/{metrics.pga_target_mb:.0f} MB; "
            f"top wait '{wait}'."
        ),
    }
    return (
        f"{classification} (score {top_score:.0f}). "
        f"{hints.get(classification, '')}"
    ).strip()


def classify_bottleneck(metrics: AwrMetrics) -> BottleneckClassificationResult:
    """
    Classify primary AWR workload bottleneck from metrics and top wait profile.
    """
    scores = _score_dimensions(metrics)
    classification = _pick_winner(scores)
    max_score = scores[classification]
    total = sum(scores.values()) or 1.0
    confidence = round(min(100.0, max(35.0, (max_score / total) * 100.0)), 1)
    rationale = _build_rationale(classification, metrics, scores)

    return BottleneckClassificationResult(
        classification=classification,
        confidence=confidence,
        scores={k: round(v, 1) for k, v in scores.items()},
        rationale=rationale,
    )
