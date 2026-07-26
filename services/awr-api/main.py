"""
AI DBA Assistant — AWR Analysis API (FastAPI)

Exposes Oracle AWR engines to the Next.js application.
Run: uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# pdf-generator engines
_CURRENT = Path(__file__).resolve().parent
_ROOT = _CURRENT.parent.parent      # /app
_PDF_GEN = _ROOT / "pdf-generator"

if str(_PDF_GEN) not in sys.path:
    sys.path.insert(0, str(_PDF_GEN))

from awr_analysis_json import run_awr_analysis  # noqa: E402
from awr_parser import parse_awr_html  # noqa: E402
from awr_pdf import generate_awr_pdf  # noqa: E402
from awr_report_builder import build_awr_report_data  # noqa: E402
from awr_rules import run_awr_rules  # noqa: E402
from bottleneck_engine import classify_bottleneck  # noqa: E402
from health_score_engine import calculate_health_score  # noqa: E402

from dashboard_mapper import dict_to_analyze_response  # noqa: E402
from models import AnalyzeResponse  # noqa: E402
from storage import load_analysis, load_html, save_analysis  # noqa: E402

app = FastAPI(
    title="AI DBA Assistant AWR API",
    description="Parse Oracle AWR HTML and run health, bottleneck, and executive summary engines.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
PDF_DIR = Path(__file__).resolve().parent / "data" / "reports"


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "awr-api"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_awr(file: UploadFile = File(...)) -> AnalyzeResponse:
    """Upload Oracle AWR HTML; parse metrics and run all analysis engines."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file name.")

    lower = file.filename.lower()
    if not (lower.endswith(".html") or lower.endswith(".htm")):
        raise HTTPException(
            status_code=400,
            detail="File must be an Oracle AWR HTML export (.html).",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit.")

    payload = run_awr_analysis(raw)
    if not payload.get("success"):
        raise HTTPException(
            status_code=422,
            detail=payload.get("errors") or ["AWR parse failed."],
        )

    record = save_analysis(payload, file_name=file.filename, html_bytes=raw)
    response = dict_to_analyze_response(record)
    return response


@app.get("/analyze/{analysis_id}", response_model=AnalyzeResponse)
def get_analysis(analysis_id: str) -> AnalyzeResponse:
    """Retrieve a saved analysis by ID."""
    record = load_analysis(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Upload a new AWR report.",
        )
    return dict_to_analyze_response(record)


@app.get("/report/{analysis_id}/pdf")
def download_awr_pdf(analysis_id: str):
    """Generate PDF from saved analysis using awr_pdf.py (parsed metrics only)."""
    record = load_analysis(analysis_id)
    if not record or not record.get("success"):
        raise HTTPException(status_code=404, detail="Analysis not found.")

    html_bytes = load_html(analysis_id)
    if not html_bytes:
        raise HTTPException(
            status_code=404,
            detail="Source HTML not stored for this analysis; re-upload to generate PDF.",
        )
    parsed = parse_awr_html(html_bytes)

    if not parsed.success or parsed.metrics is None:
        raise HTTPException(status_code=422, detail="Could not re-parse stored AWR HTML.")

    metrics = parsed.metrics
    health_result = calculate_health_score(metrics)
    bottleneck_result = classify_bottleneck(metrics)
    analysis = run_awr_rules(metrics)
    report_data = build_awr_report_data(
        parsed, metrics, health_result, bottleneck_result, analysis
    )

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PDF_DIR / f"{analysis_id}.pdf"
    generate_awr_pdf(report_data, output_path=str(out_path))

    safe_name = f"AWR_Report_{metrics.database_name.replace(' ', '_')}.pdf"
    return FileResponse(
        path=out_path,
        media_type="application/pdf",
        filename=safe_name,
    )
