"""
AWR Health Score Engine — composite 0–100 score and risk from core AWR metrics.

Dimensions (weighted penalties, max 100 points deducted):
  CPU utilization, top wait event, buffer busy waits, log file sync,
  top SQL concentration, I/O pressure.
"""

from __future__ import annotations

from dataclasses import dataclass

from rule_models import AwrMetrics, RiskLevel

HEALTH_GREEN_MIN = 80
HEALTH_AMBER_MIN = 60

# Max penalty budget per dimension (sums to 100)
_MAX_CPU = 20.0
_MAX_TOP_WAIT = 20.0
_MAX_BUFFER_BUSY = 15.0
_MAX_LOG_SYNC = 12.0
_MAX_TOP_SQL = 18.0
_MAX_IO = 15.0

_IO_READS_BASE = 5000.0
_IO_READS_STRESS = 15000.0


@dataclass
class DimensionScore:
    """Per-dimension health contribution (100 = healthy, lower = worse)."""

    name: str
    score: float
    penalty: float
    max_penalty: float
    detail: str


@dataclass
class HealthScoreResult:
    health_score: int
    risk_level: RiskLevel
    dimensions: list[DimensionScore]

    @property
    def health_score_label(self) -> str:
        return f"{self.health_score} / 100"


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _penalty_to_score(penalty: float, max_penalty: float) -> float:
    if max_penalty <= 0:
        return 100.0
    return _clamp_score(100.0 - (penalty / max_penalty) * 100.0)


def _cpu_penalty(cpu_pct: float) -> float:
    return min(_MAX_CPU, max(0.0, (cpu_pct - 60.0) * 0.25))


def _top_wait_penalty(wait_pct: float) -> float:
    return min(_MAX_TOP_WAIT, max(0.0, (wait_pct - 25.0) * 0.35))


def _buffer_busy_penalty(bb_pct: float) -> float:
    return min(_MAX_BUFFER_BUSY, max(0.0, (bb_pct - 8.0) * 0.5))


def _log_sync_penalty(log_pct: float, top_wait: str, top_wait_pct: float) -> float:
    base = min(_MAX_LOG_SYNC, max(0.0, (log_pct - 5.0) * 0.6))
    if "log file sync" in top_wait.lower():
        wait_component = min(_MAX_LOG_SYNC, max(0.0, (top_wait_pct - 10.0) * 0.4))
        return min(_MAX_LOG_SYNC, max(base, wait_component))
    return base


def _top_sql_penalty(sql_pct: float) -> float:
    return min(_MAX_TOP_SQL, max(0.0, (sql_pct - 15.0) * 0.4))


def _io_penalty(physical_reads_per_sec: float, top_wait: str, top_wait_pct: float) -> float:
    reads = physical_reads_per_sec
    if reads <= _IO_READS_BASE:
        read_penalty = 0.0
    elif reads >= _IO_READS_STRESS:
        read_penalty = _MAX_IO
    else:
        span = _IO_READS_STRESS - _IO_READS_BASE
        read_penalty = ((reads - _IO_READS_BASE) / span) * _MAX_IO

    wait = top_wait.lower()
    io_waits = ("db file sequential", "db file scattered", "direct path read", "direct path write")
    if any(k in wait for k in io_waits):
        wait_penalty = min(_MAX_IO, max(0.0, (top_wait_pct - 25.0) * 0.3))
        return min(_MAX_IO, max(read_penalty, wait_penalty))
    return read_penalty


def _classify_risk(health_score: int, dimensions: list[DimensionScore]) -> RiskLevel:
    critical_count = sum(
        1 for d in dimensions if d.penalty >= d.max_penalty * 0.7 and d.max_penalty > 0
    )
    if health_score < HEALTH_AMBER_MIN or critical_count >= 2:
        return "High"
    if health_score < HEALTH_GREEN_MIN or critical_count >= 1:
        return "Medium"
    return "Low"


def calculate_health_score(metrics: AwrMetrics) -> HealthScoreResult:
    """
    Compute AWR health score (0–100) and risk level from six metric dimensions.
    """
    dims: list[tuple[str, float, float, str]] = [
        (
            "CPU Utilization",
            _cpu_penalty(metrics.cpu_usage_pct),
            _MAX_CPU,
            f"{metrics.cpu_usage_pct:.1f}% utilization",
        ),
        (
            "Top Wait Event",
            _top_wait_penalty(metrics.top_wait_event_pct),
            _MAX_TOP_WAIT,
            f"{metrics.top_wait_event} ({metrics.top_wait_event_pct:.1f}% DB time)",
        ),
        (
            "Buffer Busy Waits",
            _buffer_busy_penalty(metrics.buffer_busy_waits_pct),
            _MAX_BUFFER_BUSY,
            f"{metrics.buffer_busy_waits_pct:.1f}% of DB time",
        ),
        (
            "Log File Sync",
            _log_sync_penalty(
                metrics.log_file_sync_pct,
                metrics.top_wait_event,
                metrics.top_wait_event_pct,
            ),
            _MAX_LOG_SYNC,
            f"{metrics.log_file_sync_pct:.1f}% DB time",
        ),
        (
            "Top SQL Concentration",
            _top_sql_penalty(metrics.top_sql_db_time_pct),
            _MAX_TOP_SQL,
            f"SQL_ID {metrics.top_sql_id} ({metrics.top_sql_db_time_pct:.1f}% DB time)",
        ),
        (
            "I/O Pressure",
            _io_penalty(
                metrics.physical_reads_per_sec,
                metrics.top_wait_event,
                metrics.top_wait_event_pct,
            ),
            _MAX_IO,
            f"{metrics.physical_reads_per_sec:,.0f} physical reads/sec",
        ),
    ]

    dimensions = [
        DimensionScore(
            name=name,
            score=round(_penalty_to_score(penalty, max_p), 1),
            penalty=round(penalty, 2),
            max_penalty=max_p,
            detail=detail,
        )
        for name, penalty, max_p, detail in dims
    ]

    total_penalty = sum(d.penalty for d in dimensions)
    health = int(round(_clamp_score(100.0 - total_penalty)))
    risk = _classify_risk(health, dimensions)

    return HealthScoreResult(
        health_score=health,
        risk_level=risk,
        dimensions=dimensions,
    )
