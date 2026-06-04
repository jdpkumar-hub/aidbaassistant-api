"""Persist analysis JSON by ID (production store for FastAPI)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

DATA_DIR = Path(__file__).resolve().parent / "data" / "analyses"
HTML_DIR = Path(__file__).resolve().parent / "data" / "html"


def _safe_id(analysis_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "", analysis_id)


def _path(analysis_id: str) -> Path:
    return DATA_DIR / f"{_safe_id(analysis_id)}.json"


def save_analysis(
    payload: dict,
    file_name: str | None = None,
    html_bytes: bytes | None = None,
) -> dict:
    analysis_id = str(uuid4())
    record = {
        **payload,
        "analysisId": analysis_id,
        "fileName": file_name,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _path(analysis_id).write_text(json.dumps(record, indent=2), encoding="utf-8")
    if html_bytes:
        HTML_DIR.mkdir(parents=True, exist_ok=True)
        (HTML_DIR / f"{_safe_id(analysis_id)}.html").write_bytes(html_bytes)
    return record


def load_html(analysis_id: str) -> bytes | None:
    path = HTML_DIR / f"{_safe_id(analysis_id)}.html"
    if not path.is_file():
        return None
    return path.read_bytes()


def load_analysis(analysis_id: str) -> dict | None:
    path = _path(analysis_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
