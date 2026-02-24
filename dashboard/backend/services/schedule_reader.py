"""Schedule config reader and writer."""

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import SCHEDULE_CONFIG, JSONL_PATH, LOGS_DIR


VIDEO_TYPES = ["original", "ugc_lighting", "outdoor"]

# IST is UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)


def _utc_to_ist(time_str: str) -> str:
    """Convert 'HH:MM' UTC to IST display string like '12:00 PM'."""
    h, m = map(int, time_str.split(":"))
    utc_dt = datetime.now(timezone.utc).replace(hour=h, minute=m, second=0, microsecond=0)
    ist_dt = utc_dt + IST_OFFSET
    return ist_dt.strftime("%-I:%M %p") + " IST"


def _predict_video_type(day_offset: int = 0) -> str:
    """Replicate the VIDEO_TYPES[day_of_year % 3] rotation logic."""
    day_of_year = datetime.now().timetuple().tm_yday + day_offset
    return VIDEO_TYPES[day_of_year % 3]


def _read_config() -> dict:
    """Read schedule config, return defaults if file missing."""
    if SCHEDULE_CONFIG.exists():
        return json.loads(SCHEDULE_CONFIG.read_text())
    return {
        "video_pipeline": {
            "enabled": True,
            "time_utc": "06:30",
            "personas": {
                "sanya": {"enabled": True, "video_type": "auto"},
                "sophie": {"enabled": True, "video_type": "auto"},
                "aliyah": {"enabled": True, "video_type": "auto"},
                "olivia": {"enabled": True, "video_type": "auto"},
            },
        },
        "text_pipeline": {
            "enabled": True,
            "accounts": {
                "sophie.unplugs": {"enabled": True, "time_utc": "01:30"},
                "emillywilks": {"enabled": True, "time_utc": "01:45"},
                "sanyahealing": {"enabled": True, "time_utc": "02:00"},
            },
        },
    }


def _write_config(config: dict) -> None:
    """Write schedule config to disk."""
    SCHEDULE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_CONFIG.write_text(json.dumps(config, indent=2) + "\n")


def _get_last_runs() -> dict[str, tuple[str, str]]:
    """Parse video_autopilot.jsonl to find the last run per persona.

    Returns {persona: (timestamp, status)}.
    """
    last: dict[str, tuple[str, str]] = {}
    if not JSONL_PATH.exists():
        return last
    for line in JSONL_PATH.read_text().strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        persona = entry.get("persona", "")
        ts = entry.get("timestamp", "")
        status = "ok" if entry.get("reel_path") else "text_only"
        last[persona] = (ts, status)
    return last


def _get_cron_history(limit: int = 20) -> list[dict]:
    """Parse logs/cron.log for recent run entries."""
    cron_log = LOGS_DIR / "cron.log"
    entries: list[dict] = []
    if not cron_log.exists():
        return entries
    lines = cron_log.read_text().strip().splitlines()
    # Pattern: === Video autopilot started/finished/FAILED at <date> ===
    pattern = re.compile(
        r"=== Video autopilot (started|finished OK|FAILED.*?) at (.+?) ==="
    )
    for line in reversed(lines):
        m = pattern.search(line)
        if m:
            action = m.group(1)
            timestamp = m.group(2).strip()
            if "FAILED" in action:
                status = "failed"
                message = action
            elif "finished" in action:
                status = "ok"
                message = "Completed successfully"
            else:
                status = "running"
                message = "Started"
            entries.append({
                "timestamp": timestamp,
                "status": status,
                "message": message,
            })
            if len(entries) >= limit:
                break
    return entries


def get_schedule() -> dict:
    """Build the full schedule state for the API."""
    config = _read_config()
    last_runs = _get_last_runs()
    cron_history = _get_cron_history()

    vp = config["video_pipeline"]
    tp = config["text_pipeline"]

    slots = []

    # Video persona slots
    for persona, pcfg in vp.get("personas", {}).items():
        lr = last_runs.get(persona)
        effective_type = pcfg.get("video_type", "auto")
        if effective_type == "auto":
            effective_type = _predict_video_type()
        slots.append({
            "type": "video",
            "persona": persona,
            "account": None,
            "time_utc": vp.get("time_utc", "06:30"),
            "time_ist": _utc_to_ist(vp.get("time_utc", "06:30")),
            "video_type": pcfg.get("video_type", "auto"),
            "enabled": pcfg.get("enabled", True) and vp.get("enabled", True),
            "last_run": lr[0] if lr else None,
            "last_status": lr[1] if lr else None,
        })

    # Text account slots
    for account, acfg in tp.get("accounts", {}).items():
        slots.append({
            "type": "text",
            "persona": None,
            "account": account,
            "time_utc": acfg.get("time_utc", "00:00"),
            "time_ist": _utc_to_ist(acfg.get("time_utc", "00:00")),
            "video_type": None,
            "enabled": acfg.get("enabled", True) and tp.get("enabled", True),
            "last_run": None,
            "last_status": None,
        })

    return {
        "video_pipeline_enabled": vp.get("enabled", True),
        "text_pipeline_enabled": tp.get("enabled", True),
        "video_time_utc": vp.get("time_utc", "06:30"),
        "video_time_ist": _utc_to_ist(vp.get("time_utc", "06:30")),
        "today_video_type": _predict_video_type(),
        "slots": slots,
        "cron_history": cron_history,
    }


def update_schedule(data: dict) -> dict:
    """Update schedule config from API request and return new state."""
    config = _read_config()

    if data.get("video_pipeline_enabled") is not None:
        config["video_pipeline"]["enabled"] = data["video_pipeline_enabled"]

    if data.get("text_pipeline_enabled") is not None:
        config["text_pipeline"]["enabled"] = data["text_pipeline_enabled"]

    if data.get("video_personas"):
        for persona, updates in data["video_personas"].items():
            if persona in config["video_pipeline"]["personas"]:
                config["video_pipeline"]["personas"][persona].update(updates)

    if data.get("text_accounts"):
        for account, updates in data["text_accounts"].items():
            if account in config["text_pipeline"]["accounts"]:
                config["text_pipeline"]["accounts"][account].update(updates)

    _write_config(config)
    return get_schedule()
