"""Read/write funnel snapshots from output/funnel_snapshots.jsonl."""

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SNAPSHOTS_PATH = PROJECT_ROOT / "output" / "funnel_snapshots.jsonl"


def list_snapshots(app: str | None = None) -> list[dict]:
    """Read all snapshots, optionally filtered by app."""
    if not SNAPSHOTS_PATH.exists():
        return []
    entries = []
    for line in SNAPSHOTS_PATH.read_text().strip().splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if app is None or entry.get("app") == app:
                entries.append(entry)
        except json.JSONDecodeError:
            continue
    return entries


def save_snapshot(app: str, funnel_data: dict, notes: str | None = None) -> dict:
    """Append a new snapshot to the JSONL file. Returns the saved snapshot."""
    steps = funnel_data.get("steps", [])
    started = steps[0]["count"] if steps else 0
    completed = steps[-1]["count"] if steps else 0

    snapshot = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "app": app,
        "range": "30d",
        "overall_conversion": funnel_data.get("overall_conversion", 0),
        "started": started,
        "completed": completed,
        "steps": steps,
        "changes_pending": [notes] if notes else [],
    }

    SNAPSHOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOTS_PATH, "a") as f:
        f.write(json.dumps(snapshot) + "\n")

    return snapshot
