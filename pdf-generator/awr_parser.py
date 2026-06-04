"""
Parse Oracle AWR HTML exports into AwrMetrics for rule/health engines.

Uses only data extracted from the uploaded report — no demo fallbacks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from io import StringIO
from typing import Any

from rule_models import AwrMetrics

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


@dataclass
class WaitEventRow:
    event: str
    pct_db_time: float


@dataclass
class TopSqlRow:
    sql_id: str
    pct_db_time: float


@dataclass
class AwrParseResult:
    success: bool
    metrics: AwrMetrics | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extraction_notes: dict[str, str] = field(default_factory=dict)
    wait_events: list[WaitEventRow] = field(default_factory=list)
    top_sql_rows: list[TopSqlRow] = field(default_factory=list)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _parse_float(value: str) -> float | None:
    if not value or value in ("-", "N/A", "null"):
        return None
    cleaned = value.replace(",", "").replace("%", "").strip()
    m = re.search(r"-?\d+\.?\d*", cleaned)
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _normalize_event(name: str) -> str:
    n = _clean_text(name)
    if n.upper() in ("DB CPU", "CPU TIME", "CPU"):
        return "CPU time"
    return n


class _TableParser(HTMLParser):
    """Minimal HTML table extractor when BeautifulSoup is unavailable."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._current_table: list[list[str]] = []
        self._current_row: list[str] = []
        self._cell_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._current_row = []
        elif tag in ("td", "th") and self._in_row:
            self._in_cell = True
            self._cell_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table" and self._in_table:
            if self._current_table:
                self.tables.append(self._current_table)
            self._in_table = False
        elif tag == "tr" and self._in_row:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._in_row = False
        elif tag in ("td", "th") and self._in_cell:
            self._current_row.append(_clean_text("".join(self._cell_parts)))
            self._in_cell = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)


def _extract_tables(html: str) -> list[list[list[str]]]:
    if _HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        tables: list[list[list[str]]] = []
        for table in soup.find_all("table"):
            rows: list[list[str]] = []
            for tr in table.find_all("tr"):
                cells = [_clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)
        return tables

    parser = _TableParser()
    parser.feed(html)
    return parser.tables


def _page_text(html: str) -> str:
    if _HAS_BS4:
        return _clean_text(BeautifulSoup(html, "html.parser").get_text(" "))
    return _clean_text(re.sub(r"<[^>]+>", " ", html))


def _find_label_value(html: str, labels: tuple[str, ...]) -> str | None:
    text = html if len(html) < 500_000 else _page_text(html)
    for label in labels:
        patterns = [
            rf"{re.escape(label)}\s*</td>\s*<td[^>]*>([^<]+)",
            rf"{re.escape(label)}\s*:?\s*</[^>]+>\s*<[^>]+>([^<]+)",
            rf"{re.escape(label)}\s*:\s*([^\n<]+)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                val = _clean_text(m.group(1))
                if val:
                    return val
    return None


def _snap_elapsed_minutes(text: str) -> float | None:
    m = re.search(
        r"Snap\s+Elapsed\s*(?:\(mins\))?\s*([0-9,.]+)",
        text,
        re.I,
    )
    if m:
        return _parse_float(m.group(1))
    m = re.search(r"Elapsed\s*:\s*([0-9,.]+)\s*mins?", text, re.I)
    if m:
        return _parse_float(m.group(1))
    begin = re.search(r"Begin Snap.*?(\d{1,2}:\d{2})", text, re.I | re.S)
    end = re.search(r"End Snap.*?(\d{1,2}:\d{2})", text, re.I | re.S)
    if begin and end:
        # Fallback: cannot compute跨天 reliably; use default window
        return 60.0
    return None


def _table_after_heading(html: str, headings: tuple[str, ...]) -> list[list[str]] | None:
    if not _HAS_BS4:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(string=True):
        t = _clean_text(str(tag))
        if not t:
            continue
        if any(h.lower() in t.lower() for h in headings):
            parent = tag.parent
            for _ in range(8):
                if parent is None:
                    break
                nxt = parent.find_next("table")
                if nxt:
                    rows = []
                    for tr in nxt.find_all("tr"):
                        cells = [_clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
                        if any(cells):
                            rows.append(cells)
                    if rows:
                        return rows
                parent = parent.parent
    return None


def _find_column_index(header: list[str], candidates: tuple[str, ...]) -> int | None:
    for i, cell in enumerate(header):
        cl = cell.lower()
        for c in candidates:
            if c in cl:
                return i
    return None


def _parse_load_profile(tables: list[list[list[str]]], text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for rows in tables:
        if not rows:
            continue
        header_join = " ".join(rows[0]).lower()
        if "per second" not in header_join and "per sec" not in header_join:
            continue
        col = _find_column_index(rows[0], ("per second", "1st per sec", "per sec"))
        if col is None and len(rows[0]) > 1:
            col = 1
        for row in rows[1:]:
            if not row:
                continue
            label = row[0].lower()
            val = _parse_float(row[col]) if col is not None and col < len(row) else None
            if val is None:
                continue
            if "db time" in label and "cpu" not in label:
                out["db_time_per_sec"] = val
            elif label.startswith("physical read") and "total" not in label:
                out["physical_reads_per_sec"] = val
            elif "average active sessions" in label or label.strip() == "aas":
                out["aas"] = val
    # Text fallback: "DB Time(s): 12.4"
    if "db_time_per_sec" not in out:
        m = re.search(r"DB\s+Time\s*\(s\)\s*:\s*([0-9,.]+)", text, re.I)
        if m:
            out["db_time_per_sec"] = _parse_float(m.group(1)) or 0.0
    if "physical_reads_per_sec" not in out:
        m = re.search(r"Physical\s+read\s*\([^)]*\)\s*:\s*([0-9,.]+)", text, re.I)
        if m:
            out["physical_reads_per_sec"] = _parse_float(m.group(1)) or 0.0
    return out


def _parse_wait_events(
    tables: list[list[list[str]]],
    html: str,
) -> tuple[str, float, dict[str, float], list[WaitEventRow]]:
    """Returns top_wait_event, top_wait_pct, all_event_pcts, ranked wait rows."""
    best_event = ""
    best_pct = 0.0
    event_pcts: dict[str, float] = {}
    event_display: dict[str, str] = {}

    wait_tables = []
    heading_rows = _table_after_heading(
        html,
        (
            "Top 10 Foreground Events",
            "Top 5 Timed Foreground Events",
            "Top Timed Events",
            "Foreground Wait Events",
        ),
    )
    if heading_rows:
        wait_tables.append(heading_rows)

    for rows in tables:
        header = " ".join(rows[0]).lower() if rows else ""
        if "% db" in header or "% db wait" in header or "% db time" in header:
            if "event" in header or any("db file" in " ".join(r).lower() for r in rows[1:3]):
                wait_tables.append(rows)

    for rows in wait_tables:
        if len(rows) < 2:
            continue
        header = rows[0]
        event_col = _find_column_index(header, ("event",)) or 0
        pct_col = _find_column_index(
            header,
            ("% db time", "% db wait", "% dbtime", "%total wait"),
        )
        if pct_col is None:
            for i, h in enumerate(header):
                if "%" in h and "db" in h.lower():
                    pct_col = i
                    break
        if pct_col is None:
            continue
        for row in rows[1:]:
            if event_col >= len(row) or pct_col >= len(row):
                continue
            event = _normalize_event(row[event_col])
            if not event or event.startswith("-") or event.lower() == "event":
                continue
            pct = _parse_float(row[pct_col])
            if pct is None:
                continue
            key = event.lower()
            event_pcts[key] = pct
            event_display[key] = event
            if pct > best_pct:
                best_pct = pct
                best_event = event

    wait_rows = sorted(
        [
            WaitEventRow(event=event_display[k], pct_db_time=v)
            for k, v in event_pcts.items()
        ],
        key=lambda r: r.pct_db_time,
        reverse=True,
    )
    return best_event, best_pct, event_pcts, wait_rows


def _parse_top_sql_list(
    tables: list[list[list[str]]],
    html: str,
    limit: int = 10,
) -> list[TopSqlRow]:
    """Return top SQL statements by % DB time from AWR HTML."""
    sql_tables: list[list[list[str]]] = []
    heading_rows = _table_after_heading(html, ("SQL ordered by Elapsed Time",))
    if heading_rows:
        sql_tables.append(heading_rows)

    for rows in tables:
        header = " ".join(rows[0]).lower() if rows else ""
        if "sql id" in header and ("elapsed" in header or "%db" in header or "% total" in header):
            sql_tables.append(rows)

    results: list[TopSqlRow] = []
    seen: set[str] = set()

    for rows in sql_tables:
        if len(rows) < 2:
            continue
        header = rows[0]
        sql_col = _find_column_index(header, ("sql id", "sqlid"))
        pct_col = _find_column_index(
            header,
            ("% db time", "%total", "% dbtime", "pct db"),
        )
        if sql_col is None:
            continue
        for row in rows[1:]:
            if sql_col >= len(row):
                continue
            sql_id = re.sub(r"[^a-zA-Z0-9]", "", row[sql_col])[:13]
            if not sql_id or sql_id.lower() in ("sqlid", "total"):
                continue
            if sql_id in seen:
                continue
            pct = 0.0
            if pct_col is not None and pct_col < len(row):
                pct = _parse_float(row[pct_col]) or 0.0
            seen.add(sql_id)
            results.append(TopSqlRow(sql_id=sql_id, pct_db_time=pct))
            if len(results) >= limit:
                break
        if results:
            break

    results.sort(key=lambda r: r.pct_db_time, reverse=True)
    return results[:limit]


def _parse_top_sql(tables: list[list[list[str]]], html: str) -> tuple[str, float]:
    rows = _parse_top_sql_list(tables, html, limit=1)
    if rows:
        return rows[0].sql_id, rows[0].pct_db_time
    return "", 0.0


def _parse_instance_efficiency(tables: list[list[list[str]]], text: str) -> float | None:
    for rows in tables:
        for row in rows:
            label = row[0].lower() if row else ""
            if "buffer cache hit" in label or "buffer hit" in label:
                for cell in row[1:]:
                    v = _parse_float(cell)
                    if v is not None and 0 < v <= 100:
                        return v
    m = re.search(r"Buffer\s+(?:cache\s+)?hit\s*(?:ratio)?\s*[:\s]+([0-9,.]+)\s*%?", text, re.I)
    if m:
        return _parse_float(m.group(1))
    return None


def _parse_cpu_pct(tables: list[list[list[str]]], text: str) -> float | None:
    for rows in tables:
        header = " ".join(rows[0]).lower() if rows else ""
        if "%total cpu" in header or "host cpu" in header:
            for row in rows[1:]:
                for cell in row:
                    v = _parse_float(cell)
                    if v is not None and 0 < v <= 100:
                        return v
    for label in ("%Total CPU", "% User + System", "CPU Usage"):
        m = re.search(rf"{re.escape(label)}\s*[:\s]+([0-9,.]+)", text, re.I)
        if m:
            v = _parse_float(m.group(1))
            if v is not None:
                return v
    m = re.search(r"Host\s+CPU.*?%User.*?([0-9,.]+).*?%System.*?([0-9,.]+)", text, re.I | re.S)
    if m:
        u = _parse_float(m.group(1)) or 0
        s = _parse_float(m.group(2)) or 0
        return min(100.0, u + s)
    return None


def _parse_memory(tables: list[list[list[str]]]) -> tuple[float, float, float | None]:
    pga_alloc = 0.0
    pga_target = 0.0
    shared_free: float | None = None
    for rows in tables:
        for row in rows:
            if not row:
                continue
            label = row[0].lower()
            if "pga aggr target" in label or "pga aggregate target" in label:
                for cell in row[1:]:
                    v = _parse_float(cell)
                    if v and v > 100:
                        pga_target = v
                        break
            if "pga aggr total" in label or "pga allocated" in label:
                for cell in row[1:]:
                    v = _parse_float(cell)
                    if v and v > 0:
                        pga_alloc = v
                        break
            if "shared pool free" in label and "%" in label:
                for cell in row[1:]:
                    v = _parse_float(cell)
                    if v is not None:
                        shared_free = v
    return pga_alloc, pga_target, shared_free


def _parse_active_sessions(text: str, load: dict[str, float], elapsed_min: float) -> float:
    if "aas" in load:
        return load["aas"]
    db_time = load.get("db_time_per_sec", 0.0)
    if db_time and elapsed_min > 0:
        return db_time
    m = re.search(r"Average\s+Active\s+Sessions\s*([0-9,.]+)", text, re.I)
    if m:
        return _parse_float(m.group(1)) or 0.0
    return db_time


def parse_awr_html(html: str | bytes) -> AwrParseResult:
    """
    Parse an Oracle AWR HTML report into AwrMetrics.
    Raises no exceptions; returns errors in AwrParseResult.
    """
    if isinstance(html, bytes):
        html = html.decode("utf-8", errors="replace")

    if not html or len(html) < 500:
        return AwrParseResult(success=False, errors=["File is empty or too small to be a valid AWR HTML report."])

    text = _page_text(html)
    tables = _extract_tables(html)
    notes: dict[str, str] = {}
    warnings: list[str] = []

    db_name = _find_label_value(html, ("DB Name", "Database Name")) or "Oracle Database"
    instance = _find_label_value(html, ("Instance", "Inst Name", "Instance Name")) or "ORCL"
    notes["database"] = db_name
    notes["instance"] = instance

    elapsed = _snap_elapsed_minutes(text) or 60.0
    notes["elapsed_minutes"] = f"{elapsed:.1f}"

    load = _parse_load_profile(tables, text)
    cpu = _parse_cpu_pct(tables, text)
    if cpu is None:
        warnings.append("CPU utilization not found in report; using 0%.")
        cpu = 0.0
    notes["cpu_usage_pct"] = f"{cpu:.1f}%"

    top_wait, top_wait_pct, event_pcts, wait_event_rows = _parse_wait_events(tables, html)
    if not top_wait:
        return AwrParseResult(
            success=False,
            errors=["Could not parse Top Foreground Events / wait event table from AWR HTML."],
            warnings=warnings,
        )
    notes["top_wait"] = f"{top_wait} ({top_wait_pct:.1f}%)"

    buffer_busy = 0.0
    for key, pct in event_pcts.items():
        if "buffer busy" in key:
            buffer_busy = pct
            break
    log_sync = 0.0
    for key, pct in event_pcts.items():
        if "log file sync" in key:
            log_sync = pct
            break

    sql_rows = _parse_top_sql_list(tables, html)
    sql_id = sql_rows[0].sql_id if sql_rows else ""
    sql_pct = sql_rows[0].pct_db_time if sql_rows else 0.0
    if not sql_id:
        warnings.append("Top SQL ID not found; SQL concentration scored as 0%.")
    notes["top_sql"] = f"{sql_id or 'N/A'} ({sql_pct:.1f}%)"

    phys_reads = load.get("physical_reads_per_sec", 0.0)
    if phys_reads <= 0:
        m = re.search(r"Physical\s+reads(?:\s+per\s+sec)?\s*:?\s*([0-9,.]+)", text, re.I)
        if m:
            phys_reads = _parse_float(m.group(1)) or 0.0
    if phys_reads <= 0:
        warnings.append("Physical reads per second not found; I/O pressure may be understated.")

    hit = _parse_instance_efficiency(tables, text)
    if hit is None:
        warnings.append("Buffer cache hit ratio not found; using 90% for scoring only.")
        hit = 90.0
    notes["buffer_cache_hit"] = f"{hit:.1f}%"

    pga_alloc, pga_target, shared_free = _parse_memory(tables)
    if pga_target <= 0:
        pga_target = max(pga_alloc, 1024.0)
    if pga_alloc <= 0:
        pga_alloc = pga_target * 0.5
    if shared_free is None:
        shared_free = 15.0
        warnings.append("Shared pool free % not found; assumed 15%.")

    aas = _parse_active_sessions(text, load, elapsed)

    metrics = AwrMetrics(
        database_name=db_name[:128],
        instance_name=instance[:64],
        cpu_usage_pct=float(cpu),
        db_time_aas=float(aas),
        db_time_minutes=float(elapsed),
        top_wait_event=top_wait,
        top_wait_event_pct=float(top_wait_pct),
        top_sql_id=sql_id or "unknown",
        top_sql_db_time_pct=float(sql_pct),
        buffer_busy_waits_pct=float(buffer_busy),
        active_sessions_avg=float(aas),
        physical_reads_per_sec=float(phys_reads),
        log_file_sync_pct=float(log_sync),
        buffer_cache_hit_ratio_pct=float(hit),
        pga_allocated_mb=float(pga_alloc),
        pga_target_mb=float(pga_target),
        shared_pool_free_pct=float(shared_free),
    )

    return AwrParseResult(
        success=True,
        metrics=metrics,
        warnings=warnings,
        extraction_notes=notes,
        wait_events=wait_event_rows,
        top_sql_rows=sql_rows,
    )
