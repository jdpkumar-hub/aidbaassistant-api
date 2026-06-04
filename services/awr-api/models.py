"""Pydantic models for AWR analysis API (dashboard + engines)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["Low", "Medium", "High"]


class MetricsModel(BaseModel):
    databaseName: str
    instanceName: str
    cpuUsagePct: float
    dbTimeAas: float
    dbTimeMinutes: float
    topWaitEvent: str
    topWaitEventPct: float
    topSqlId: str
    topSqlDbTimePct: float
    bufferBusyWaitsPct: float
    activeSessionsAvg: float
    physicalReadsPerSec: float
    logFileSyncPct: float
    bufferCacheHitRatioPct: float
    pgaAllocatedMb: float
    pgaTargetMb: float
    sharedPoolFreePct: float


class DimensionModel(BaseModel):
    name: str
    score: float
    penalty: float
    maxPenalty: float
    detail: str


class HealthModel(BaseModel):
    healthScore: int
    riskLevel: RiskLevel
    dimensions: list[DimensionModel] = Field(default_factory=list)


class BottleneckModel(BaseModel):
    classification: str
    confidence: float
    rationale: str
    scores: dict[str, float] = Field(default_factory=dict)


class SummaryModel(BaseModel):
    businessSummary: str
    technicalSummary: str
    topActions: list[str]
    markdown: str = ""


class WaitEventModel(BaseModel):
    event: str
    pctDbTime: float


class TopSqlModel(BaseModel):
    sqlId: str
    pctDbTime: float
    executions: str | None = None
    elapsedSec: str | None = None


class RuleFindingModel(BaseModel):
    ruleId: str
    category: str
    message: str
    severity: str
    recommendation: str


class RulesModel(BaseModel):
    rulesEvaluated: int
    rulesTriggered: int
    findings: list[RuleFindingModel] = Field(default_factory=list)


class DashboardModel(BaseModel):
    databaseName: str
    instanceName: str
    snapWindow: str
    healthScore: int
    riskLevel: RiskLevel
    bottleneck: str
    confidence: float
    bottleneckRationale: str
    businessSummary: str
    technicalSummary: str
    waitEvents: list[WaitEventModel]
    topSql: list[TopSqlModel]
    recommendations: list[str]
    warnings: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    success: bool
    analysisId: str | None = None
    fileName: str | None = None
    createdAt: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    extractionNotes: dict[str, str] = Field(default_factory=dict)
    metrics: MetricsModel | None = None
    snapWindow: str | None = None
    health: HealthModel | None = None
    bottleneck: BottleneckModel | None = None
    summary: SummaryModel | None = None
    waitEvents: list[WaitEventModel] = Field(default_factory=list)
    topSql: list[TopSqlModel] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    rules: RulesModel | None = None
    dashboard: DashboardModel | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    errors: list[str]
