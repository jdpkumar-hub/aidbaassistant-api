"""Map engine JSON dict to dashboard Pydantic model."""

from __future__ import annotations

from models import (
    AnalyzeResponse,
    BottleneckModel,
    DashboardModel,
    HealthModel,
    MetricsModel,
    RulesModel,
    SummaryModel,
    TopSqlModel,
    WaitEventModel,
)


def payload_to_dashboard(payload: dict) -> DashboardModel | None:
    if not payload.get("success"):
        return None
    metrics = payload.get("metrics")
    health = payload.get("health")
    bottleneck = payload.get("bottleneck")
    summary = payload.get("summary")
    if not metrics or not health or not bottleneck:
        return None

    top_sql = [
        TopSqlModel(
            sqlId=row["sqlId"],
            pctDbTime=row["pctDbTime"],
            executions=row.get("executions") or "—",
            elapsedSec=row.get("elapsedSec") or "—",
        )
        for row in payload.get("topSql") or []
    ]

    recommendations = payload.get("recommendations") or []
    if not recommendations and summary:
        recommendations = summary.get("topActions") or []

    return DashboardModel(
        databaseName=metrics["databaseName"],
        instanceName=metrics["instanceName"],
        snapWindow=payload.get("snapWindow")
        or f"{metrics.get('dbTimeMinutes', 60):.0f} min snapshot",
        healthScore=health["healthScore"],
        riskLevel=health["riskLevel"],
        bottleneck=bottleneck["classification"],
        confidence=bottleneck["confidence"],
        bottleneckRationale=bottleneck["rationale"],
        businessSummary=(summary or {}).get("businessSummary", ""),
        technicalSummary=(summary or {}).get("technicalSummary", ""),
        waitEvents=[
            WaitEventModel(event=w["event"], pctDbTime=w["pctDbTime"])
            for w in payload.get("waitEvents") or []
        ],
        topSql=top_sql,
        recommendations=recommendations,
        warnings=payload.get("warnings") or [],
    )


def dict_to_analyze_response(record: dict) -> AnalyzeResponse:
    dashboard = payload_to_dashboard(record)
    metrics = record.get("metrics")
    health = record.get("health")
    bottleneck = record.get("bottleneck")
    summary = record.get("summary")
    rules = record.get("rules")

    return AnalyzeResponse(
        success=True,
        analysisId=record.get("analysisId"),
        fileName=record.get("fileName"),
        createdAt=record.get("createdAt"),
        warnings=record.get("warnings") or [],
        extractionNotes=record.get("extractionNotes") or {},
        metrics=MetricsModel(**metrics) if metrics else None,
        snapWindow=record.get("snapWindow"),
        health=HealthModel(**health) if health else None,
        bottleneck=BottleneckModel(**bottleneck) if bottleneck else None,
        summary=SummaryModel(**summary) if summary else None,
        waitEvents=[
            WaitEventModel(**w) for w in record.get("waitEvents") or []
        ],
        topSql=[
            TopSqlModel(
                sqlId=s["sqlId"],
                pctDbTime=s["pctDbTime"],
                executions=s.get("executions") or "—",
                elapsedSec=s.get("elapsedSec") or "—",
            )
            for s in record.get("topSql") or []
        ],
        recommendations=record.get("recommendations") or [],
        rules=RulesModel(**rules) if rules else None,
        dashboard=dashboard,
    )
