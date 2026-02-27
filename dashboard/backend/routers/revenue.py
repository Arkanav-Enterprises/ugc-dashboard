"""Revenue metrics endpoints — reads RevenueCat data from logs/revenue_metrics.json."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import LOGS_DIR, MEMORY_DIR

router = APIRouter(prefix="/api/revenue", tags=["revenue"])

METRICS_LOG = LOGS_DIR / "revenue_metrics.json"
METRICS_MEMORY = MEMORY_DIR / "revenue-metrics.md"


def _load_log() -> list[dict]:
    """Load the full metrics log."""
    if not METRICS_LOG.exists():
        return []
    try:
        return json.loads(METRICS_LOG.read_text())
    except (json.JSONDecodeError, IOError):
        return []


@router.get("/current")
def get_current_metrics():
    """Return the latest snapshot + previous for trend display."""
    entries = _load_log()
    if not entries:
        raise HTTPException(status_code=404, detail="No revenue data yet. Run fetch_revenue_metrics.py first.")

    current = entries[-1]
    previous = entries[-2] if len(entries) >= 2 else None
    return {"current": current, "previous": previous}


@router.get("/history")
def get_metrics_history():
    """Return all historical snapshots for charting."""
    return _load_log()


@router.get("/summary")
def get_summary_markdown():
    """Return the memory file content (human-readable summary)."""
    if not METRICS_MEMORY.exists():
        raise HTTPException(status_code=404, detail="No revenue summary yet.")
    return {"content": METRICS_MEMORY.read_text()}
