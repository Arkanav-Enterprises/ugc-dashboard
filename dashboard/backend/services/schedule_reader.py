"""Schedule config reader and writer."""

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import SCHEDULE_CONFIG, JSONL_PATH, LOGS_DIR, ACCOUNTS


# IST is UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)

VALID_FREQUENCIES = {"daily", "weekdays", "every_2_days", "custom"}
ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]
HH_MM_RE = re.compile(r"^\d{2}:\d{2}$")


def _utc_to_ist(time_str: str) -> str:
    """Convert 'HH:MM' UTC to IST display string like '12:00 PM'."""
    h, m = map(int, time_str.split(":"))
    utc_dt = datetime.now(timezone.utc).replace(hour=h, minute=m, second=0, microsecond=0)
    ist_dt = utc_dt + IST_OFFSET
    return ist_dt.strftime("%-I:%M %p") + " IST"


def _validate_time(t: str) -> bool:
    """Check HH:MM format with valid ranges."""
    if not HH_MM_RE.match(t):
        return False
    h, m = map(int, t.split(":"))
    return 0 <= h <= 23 and 0 <= m <= 59


def _migrate_old_format(config: dict) -> dict:
    """Convert old video_pipeline/text_pipeline format to flat accounts dict."""
    vp = config.get("video_pipeline", {})
    tp = config.get("text_pipeline", {})

    # Use video pipeline's frequency/days as the global defaults
    frequency = vp.get("frequency", tp.get("frequency", "daily"))
    days_of_week = vp.get("days_of_week", tp.get("days_of_week", ALL_DAYS[:]))

    vp_time = vp.get("time_utc", "06:30")
    vp_enabled = vp.get("enabled", True)
    tp_enabled = tp.get("enabled", True)

    accounts: dict[str, dict] = {}

    # Merge video pipeline accounts
    for acct, acfg in vp.get("accounts", {}).items():
        accounts[acct] = {
            "enabled": acfg.get("enabled", True) and vp_enabled,
            "time_utc": vp_time,
        }

    # Merge text pipeline accounts (override time if they had per-account times)
    for acct, acfg in tp.get("accounts", {}).items():
        if acct in accounts:
            # Account existed in video pipeline — keep video time unless text had its own
            if "time_utc" in acfg:
                accounts[acct]["time_utc"] = acfg["time_utc"]
        else:
            accounts[acct] = {
                "enabled": acfg.get("enabled", True) and tp_enabled,
                "time_utc": acfg.get("time_utc", "06:30"),
            }

    return {
        "frequency": frequency,
        "days_of_week": days_of_week,
        "accounts": accounts,
    }


def _read_config() -> dict:
    """Read schedule config. Migrate from old format if detected."""
    if SCHEDULE_CONFIG.exists():
        config = json.loads(SCHEDULE_CONFIG.read_text())
    else:
        config = {}

    # Detect old format by presence of video_pipeline or text_pipeline keys
    if "video_pipeline" in config or "text_pipeline" in config:
        config = _migrate_old_format(config)
        _write_config(config)  # persist migration

    # Backfill defaults
    config.setdefault("frequency", "daily")
    config.setdefault("days_of_week", ALL_DAYS[:])
    accts = config.setdefault("accounts", {})

    # Ensure all known accounts exist
    for acct in ACCOUNTS:
        if acct not in accts:
            accts[acct] = {"enabled": True, "time_utc": "06:30"}
        else:
            accts[acct].setdefault("enabled", True)
            accts[acct].setdefault("time_utc", "06:30")

    return config


def _write_config(config: dict) -> None:
    """Write schedule config to disk."""
    SCHEDULE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_CONFIG.write_text(json.dumps(config, indent=2) + "\n")


def _get_last_runs() -> dict[str, tuple[str, str]]:
    """Parse video_autopilot.jsonl to find the last run per account.

    Returns {account: (timestamp, status)}.
    """
    last: dict[str, tuple[str, str]] = {}
    if not JSONL_PATH.exists():
        return last
    for line in JSONL_PATH.read_text().strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Try account field first, fall back to persona
        account = entry.get("account", "")
        if not account:
            persona = entry.get("persona", "")
            account = persona  # best effort
        ts = entry.get("timestamp", "")
        status = "ok" if entry.get("reel_path") else "text_only"
        if account:
            last[account] = (ts, status)
    return last


def _get_cron_history(limit: int = 20) -> list[dict]:
    """Parse logs/cron.log for recent run entries."""
    cron_log = LOGS_DIR / "cron.log"
    entries: list[dict] = []
    if not cron_log.exists():
        return entries
    lines = cron_log.read_text().strip().splitlines()
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

    slots = []
    for account, acfg in config.get("accounts", {}).items():
        time_utc = acfg.get("time_utc", "06:30")
        # Look up last run by account name, then by persona prefix
        persona = account.split(".")[0] if "." in account else account
        lr = last_runs.get(account) or last_runs.get(persona)
        slots.append({
            "account": account,
            "time_utc": time_utc,
            "time_ist": _utc_to_ist(time_utc),
            "enabled": acfg.get("enabled", True),
            "last_run": lr[0] if lr else None,
            "last_status": lr[1] if lr else None,
        })

    return {
        "frequency": config.get("frequency", "daily"),
        "days_of_week": config.get("days_of_week", ALL_DAYS[:]),
        "slots": slots,
        "cron_history": cron_history,
    }


def update_schedule(data: dict) -> dict:
    """Update schedule config from API request and return new state."""
    config = _read_config()

    # Global frequency
    if data.get("frequency") is not None:
        f = data["frequency"]
        if f in VALID_FREQUENCIES:
            config["frequency"] = f

    # Global days
    if data.get("days_of_week") is not None:
        days = [d for d in data["days_of_week"] if d in ALL_DAYS]
        config["days_of_week"] = days

    # Per-account updates
    if data.get("accounts"):
        for account, updates in data["accounts"].items():
            if account in config.get("accounts", {}):
                if "time_utc" in updates:
                    if not _validate_time(updates["time_utc"]):
                        del updates["time_utc"]
                config["accounts"][account].update(updates)

    _write_config(config)
    return get_schedule()
