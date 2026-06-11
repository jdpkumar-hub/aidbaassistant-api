from dataclasses import dataclass


@dataclass
class SeverityResult:
    severity: str
    confidence: float
    score: int

#Severity Logic
def calculate_severity(metrics, bottleneck_result):
    score = 0

    # Wait event pressure
    if metrics.top_wait_event_pct > 80:
        score += 40
    elif metrics.top_wait_event_pct > 50:
        score += 30
    elif metrics.top_wait_event_pct > 25:
        score += 15

    # CPU
    if metrics.cpu_usage_pct > 90:
        score += 30
    elif metrics.cpu_usage_pct > 70:
        score += 20
    elif metrics.cpu_usage_pct > 50:
        score += 10

    # SQL concentration
    if metrics.top_sql_db_time_pct > 80:
        score += 20
    elif metrics.top_sql_db_time_pct > 50:
        score += 10

    # Active sessions
    if metrics.active_sessions_avg > 20:
        score += 10

    if score >= 70:
        severity = "Critical"
    elif score >= 50:
        severity = "High"
    elif score >= 25:
        severity = "Medium"
    else:
        severity = "Low"

    confidence = calculate_confidence(metrics)

    return SeverityResult(
        severity=severity,
        confidence=confidence,
        score=score,
    )
    
#Confidence Logic
def calculate_confidence(metrics):
    confidence = 100

    if metrics.cpu_usage_pct <= 0:
        confidence -= 10

    if metrics.physical_reads_per_sec <= 0:
        confidence -= 10

    if metrics.top_wait_event_pct <= 0:
        confidence -= 20

    if metrics.top_sql_db_time_pct <= 0:
        confidence -= 20

    return max(confidence, 60)

#


























































































