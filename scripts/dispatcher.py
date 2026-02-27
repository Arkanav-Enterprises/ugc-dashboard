#!/usr/bin/env python3
"""Dispatcher — runs every minute via cron, fires pipelines per schedule.json.

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
        # Run on even day-of-year
        return now.timetuple().tm_yday % 2 == 0
    if freq == "custom":
        return weekday in days
    return True  # unknown frequency — default to run


def lock_path(key: str) -> Path:
    return LOCK_DIR / f".dispatch_{key}_{date_str}.lock"


def is_locked(key: str) -> bool:
    return lock_path(key).exists()


def acquire_lock(key: str) -> None:
    lock_path(key).write_text(now.isoformat())


def fire(cmd: list[str], label: str) -> None:
    log(f"FIRE: {label} -> {' '.join(cmd)}")
    subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
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
    config = load_config()
    if not config:
        return

    # ─── Video pipeline ─────────────────────────────
    vp = config.get("video_pipeline", {})
    if vp.get("enabled", True):
        vp_time = vp.get("time_utc", "06:30")
        vp_freq = vp.get("frequency", "daily")
        vp_days = vp.get("days_of_week", [0, 1, 2, 3, 4, 5, 6])
        key = "video_pipeline"

        if hhmm == vp_time and should_run_today(vp_freq, vp_days):
            if is_locked(key):
                log(f"SKIP: {key} already ran today")
            else:
                acquire_lock(key)
                fire(
                    ["bash", str(SCRIPTS_DIR / "autopilot_video_cron.sh")],
                    "video",
                )
        else:
            log(f"SKIP: {key} not scheduled (now={hhmm}, want={vp_time})")
    else:
        log("SKIP: video_pipeline disabled")

    # ─── Text pipeline ──────────────────────────────
    tp = config.get("text_pipeline", {})
    if tp.get("enabled", True):
        tp_freq = tp.get("frequency", "daily")
        tp_days = tp.get("days_of_week", [0, 1, 2, 3, 4, 5, 6])

        if not should_run_today(tp_freq, tp_days):
            log(f"SKIP: text_pipeline not scheduled today (freq={tp_freq})")
        else:
            for account, acfg in tp.get("accounts", {}).items():
                if not acfg.get("enabled", True):
                    continue
                acct_time = acfg.get("time_utc", "00:00")
                key = f"text_{account}"

                if hhmm == acct_time:
                    if is_locked(key):
                        log(f"SKIP: {key} already ran today")
                    else:
                        acquire_lock(key)
                        fire(
                            [
                                "bash",
                                str(SCRIPTS_DIR / "autopilot_cron.sh"),
                                "--account",
                                account,
                            ],
                            f"text_{account}",
                        )
                else:
                    log(f"SKIP: {key} not scheduled (now={hhmm}, want={acct_time})")
    else:
        log("SKIP: text_pipeline disabled")

    cleanup_old_locks()


if __name__ == "__main__":
    main()
