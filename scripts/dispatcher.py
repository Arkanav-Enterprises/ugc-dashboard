#!/usr/bin/env python3
"""Dispatcher — runs every minute via cron, fires autopilot per schedule.json.

Crontab entry:
  * * * * * /root/openclaw/.venv/bin/python3 /root/openclaw/scripts/dispatcher.py >> /root/openclaw/logs/dispatcher.log 2>&1
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "schedule.json"
LOCK_DIR = PROJECT_ROOT / "logs"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python3"
ENV_FILE = PROJECT_ROOT / ".env"


def _load_dotenv() -> dict[str, str]:
    """Load .env file into os.environ and return the full env dict."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            val = val.strip().strip("'\"")
            os.environ.setdefault(key.strip(), val)
    return dict(os.environ)

now = datetime.now(timezone.utc)
hhmm = now.strftime("%H:%M")
weekday = now.weekday()  # 0=Mon .. 6=Sun
date_str = now.strftime("%Y-%m-%d")


def log(msg: str) -> None:
    print(f"[{now.isoformat(timespec='seconds')}] {msg}", flush=True)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        log(f"WARN: config not found at {CONFIG_PATH}")
        return {}
    return json.loads(CONFIG_PATH.read_text())


def should_run_today(freq: str, days: list[int]) -> bool:
    if freq == "daily":
        return True
    if freq == "weekdays":
        return weekday < 5
    if freq == "every_2_days":
        return now.timetuple().tm_yday % 2 == 0
    if freq == "custom":
        return weekday in days
    return True


def lock_path(key: str) -> Path:
    return LOCK_DIR / f".dispatch_{key}_{date_str}.lock"


def is_locked(key: str) -> bool:
    return lock_path(key).exists()


def acquire_lock(key: str) -> None:
    lock_path(key).write_text(now.isoformat())


def fire(cmd: list[str], label: str, env: dict[str, str]) -> None:
    log(f"FIRE: {label} -> {' '.join(cmd)}")
    subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=open(LOCK_DIR / f"{label}_{date_str}.log", "a"),
        stderr=subprocess.STDOUT,
    )


def cleanup_old_locks(max_age_days: int = 7) -> None:
    cutoff = now - timedelta(days=max_age_days)
    for f in LOCK_DIR.glob(".dispatch_*.lock"):
        try:
            ts = datetime.fromisoformat(f.read_text().strip())
            if ts < cutoff:
                f.unlink()
        except (ValueError, OSError):
            pass


def main() -> None:
    env = _load_dotenv()

    config = load_config()
    if not config:
        return

    freq = config.get("frequency", "daily")
    days = config.get("days_of_week", [0, 1, 2, 3, 4, 5, 6])

    if not should_run_today(freq, days):
        log(f"SKIP: not scheduled today (freq={freq}, weekday={weekday})")
        cleanup_old_locks()
        return

    python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    autopilot = str(SCRIPTS_DIR / "autopilot.py")

    for account, acfg in config.get("accounts", {}).items():
        if not acfg.get("enabled", True):
            log(f"SKIP: {account} disabled")
            continue

        acct_time = acfg.get("time_utc", "06:30")
        key = account

        if hhmm != acct_time:
            log(f"SKIP: {account} not scheduled (now={hhmm}, want={acct_time})")
            continue

        if is_locked(key):
            log(f"SKIP: {account} already ran today")
            continue

        acquire_lock(key)
        fire([python, autopilot, "--account", account], account, env)

    cleanup_old_locks()


if __name__ == "__main__":
    main()
