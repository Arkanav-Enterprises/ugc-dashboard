"""Parse JSONL pipeline logs and daily_spend.json."""

import json
from datetime import datetime, date
from typing import Optional

from config import (
    JSONL_PATH, DAILY_SPEND_PATH, DAILY_COST_CAP, VIDEO_OUTPUT_DIR,
    ASSETS_DIR, PERSONA_COLORS, PERSONAS, PROJECT_ROOT,
)
from models import PipelineRun, OverviewStats, DailySpend, PersonaStats


def _normalize_reel_path(reel_path: Optional[str]) -> Optional[str]:
    """Normalize reel paths — handle both VPS /root/openclaw/ and local paths."""
    if not reel_path:
        return None
    # Replace VPS prefix with local project root
    if reel_path.startswith("/root/openclaw/"):
        reel_path = str(PROJECT_ROOT / reel_path[len("/root/openclaw/"):])
    return reel_path


def read_all_runs() -> list[PipelineRun]:
    """Read all pipeline runs from JSONL."""
    if not JSONL_PATH.exists():
        return []
    runs = []
    for line in JSONL_PATH.read_text().strip().split("\n"):
        if not line.strip():
            continue
        data = json.loads(line)
        data["reel_path"] = _normalize_reel_path(data.get("reel_path"))
        runs.append(PipelineRun(**data))
    return runs


def read_daily_spend() -> dict[str, float]:
    """Read daily spend ledger."""
    if not DAILY_SPEND_PATH.exists():
        return {}
    return json.loads(DAILY_SPEND_PATH.read_text())


def get_daily_spend_list() -> list[DailySpend]:
    """Get spend as a sorted list."""
    spend = read_daily_spend()
    return sorted(
        [DailySpend(date=d, amount=a) for d, a in spend.items()],
        key=lambda x: x.date,
    )


def get_overview_stats() -> OverviewStats:
    """Compute overview statistics."""
    runs = read_all_runs()
    spend = read_daily_spend()
    today = date.today().isoformat()

    today_runs = sum(1 for r in runs if r.timestamp.startswith(today))
    today_cost = spend.get(today, 0.0)
    total_reels = sum(1 for r in runs if r.reel_path)
    total_spend = sum(spend.values())

    return OverviewStats(
        today_runs=today_runs,
        today_cost=round(today_cost, 2),
        daily_cap=DAILY_COST_CAP,
        total_reels=total_reels,
        total_spend=round(total_spend, 2),
    )


def get_persona_stats() -> list[PersonaStats]:
    """Get per-persona statistics."""
    runs = read_all_runs()
    stats = []
    for persona in PERSONAS:
        persona_runs = [r for r in runs if r.persona == persona]
        last_run = persona_runs[-1].timestamp if persona_runs else None

        # Count clips
        hook_dir = ASSETS_DIR / persona / "hook"
        reaction_dir = ASSETS_DIR / persona / "reaction"
        hook_clips = len(list(hook_dir.glob("*.mp4"))) if hook_dir.exists() else 0
        reaction_clips = len(list(reaction_dir.glob("*.mp4"))) if reaction_dir.exists() else 0

        stats.append(PersonaStats(
            persona=persona,
            color=PERSONA_COLORS.get(persona, "#6b7280"),
            last_run=last_run,
            total_runs=len(persona_runs),
            hook_clips=hook_clips,
            reaction_clips=reaction_clips,
        ))
    return stats
