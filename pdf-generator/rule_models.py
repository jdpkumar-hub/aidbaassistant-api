"""Shared models for Oracle AWR rule engine modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

RiskLevel = Literal["Low", "Medium", "High"]
BottleneckClass = Literal[
    "CPU Bottleneck",
    "Random IO Bottleneck",
    "Sequential Scan Bottleneck",
    "Commit Bottleneck",
    "Concurrency Bottleneck",
    "Memory Bottleneck",
]


class Severity(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


@dataclass
class AwrMetrics:
    """Normalized AWR metrics for rule evaluation."""

    database_name: str = "Production Oracle 19c"
    instance_name: str = "PROD_ORCL"
    cpu_usage_pct: float = 78.0
    db_time_aas: float = 12.4
    db_time_minutes: float = 60.0
    top_wait_event: str = "db file sequential read"
    top_wait_event_pct: float = 42.3
    top_sql_id: str = "abc123"
    top_sql_db_time_pct: float = 31.2
    buffer_busy_waits_pct: float = 18.1
    active_sessions_avg: float = 142.0
    # I/O
    physical_reads_per_sec: float = 12500.0
    log_file_sync_pct: float = 12.4
    # Memory
    buffer_cache_hit_ratio_pct: float = 86.4
    pga_allocated_mb: float = 2048.0
    pga_target_mb: float = 4096.0
    shared_pool_free_pct: float = 12.0


@dataclass
class RuleResult:
    """Single rule output: severity, finding, recommendation."""

    rule_id: str
    category: str
    severity: Severity
    finding: str
    recommendation: str


@dataclass
class KpiCard:
    label: str
    value: str
    severity: Severity
    detail: str = ""


@dataclass
class RuleFinding:
    """Legacy-compatible finding (maps from RuleResult)."""

    rule_id: str
    category: str
    message: str
    severity: Severity
    recommendation: str = ""


@dataclass
class AwrAnalysisResult:
    health_score: int
    risk_level: RiskLevel
    bottleneck_classification: BottleneckClass
    kpi_cards: list[KpiCard] = field(default_factory=list)
    findings: list[RuleFinding] = field(default_factory=list)
    rule_results: list[RuleResult] = field(default_factory=list)
    executive_summary: str = ""
    executive_summary_markdown: str = ""
    business_summary: str = ""
    technical_summary: str = ""
    top_actions: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    rules_evaluated: int = 0
    rules_triggered: int = 0
    generated_at: datetime = field(default_factory=datetime.now)


def result_to_finding(r: RuleResult) -> RuleFinding:
    return RuleFinding(
        rule_id=r.rule_id,
        category=r.category,
        message=r.finding,
        severity=r.severity,
        recommendation=r.recommendation,
    )
