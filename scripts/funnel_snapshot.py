#!/usr/bin/env python3
"""Pull onboarding funnel snapshots from PostHog and track over time.

Usage (run on VPS):
    python3 scripts/funnel_snapshot.py              # both apps, 30d
    python3 scripts/funnel_snapshot.py --app manifest-lock
    python3 scripts/funnel_snapshot.py --app journal-lock
    python3 scripts/funnel_snapshot.py --range 7d   # last 7 days

Appends to output/funnel_snapshots.jsonl and prints a visual comparison
against the most recent previous snapshot for the same app.
"""

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOTS_PATH = PROJECT_ROOT / "output" / "funnel_snapshots.jsonl"
API_BASE = "http://localhost:8000"

# Full funnel steps per app — these match the ANALYTICS.md definitions
FUNNEL_STEPS = {
    "manifest-lock": [
        "onboarding_started",
        "onboarding_intro1_continued",
        "onboarding_name_entered",
        "onboarding_age_selected",
        "onboarding_phone_usage_selected",
        "onboarding_stats_continued",
        "onboarding_motivation_continued",
        "onboarding_goal_selected",
        "onboarding_how_it_works_continued",
        "onboarding_mood_selected",
        "onboarding_manifestation_created",
        "onboarding_apps_selected",
        "onboarding_read_aloud_completed",
        "onboarding_commitment_selected",
        "onboarding_alarm_set",
        "onboarding_notification_permission_granted",
        "onboarding_completed",
    ],
    "journal-lock": [
        "onboarding_started",
        "onboarding_mascot_story_problem_continued",
        "onboarding_mascot_story_scrolling_continued",
        "onboarding_mascot_story_science_continued",
        "onboarding_mascot_story_solution_continued",
        "onboarding_journaling_reasons_selected",
        "onboarding_mind_topics_selected",
        "onboarding_mood_selected",
        "onboarding_experience_selected",
        "onboarding_journaling_style_selected",
        "onboarding_lock_time_set",
        "onboarding_guided_reflection_completed",
        "onboarding_manifestation_created",
        "onboarding_apps_selected",
        "onboarding_trial_started",
        "onboarding_completed",
    ],
}

BAR_WIDTH = 20  # max bar chars


def fetch_funnel(app: str, date_range: str) -> dict | None:
    """Fetch funnel data from the backend API."""
    steps_csv = ",".join(FUNNEL_STEPS[app])
    url = f"{API_BASE}/api/analytics/funnel?app={app}&date_from=-{date_range}&steps={steps_csv}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
            if "error" in data:
                print(f"  API error for {app}: {data['error']}")
                return None
            return data
    except Exception as e:
        print(f"  Failed to fetch {app}: {e}")
        return None


def get_previous_snapshot(app: str) -> dict | None:
    """Find the most recent snapshot for an app from the JSONL."""
    if not SNAPSHOTS_PATH.exists():
        return None
    prev = None
    for line in SNAPSHOTS_PATH.read_text().strip().splitlines():
        try:
            entry = json.loads(line)
            if entry.get("app") == app:
                prev = entry
        except json.JSONDecodeError:
            continue
    return prev


def save_snapshot(snapshot: dict) -> None:
    """Append a snapshot to the JSONL file."""
    SNAPSHOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOTS_PATH, "a") as f:
        f.write(json.dumps(snapshot) + "\n")


def shorten(name: str, max_len: int = 44) -> str:
    """Shorten a step name for display."""
    name = name.replace("onboarding_", "")
    if len(name) > max_len:
        return name[: max_len - 1] + "\u2026"
    return name


def bar(count: int, max_count: int) -> str:
    """Render a horizontal bar."""
    if max_count == 0:
        return ""
    width = round((count / max_count) * BAR_WIDTH)
    return "\u2588" * width + "\u2591" * (BAR_WIDTH - width)


def delta_str(current: float, previous: float | None) -> str:
    """Format a delta like +5.2% or -3.1%."""
    if previous is None:
        return ""
    diff = current - previous
    if abs(diff) < 0.1:
        return "  ="
    arrow = "\u2191" if diff > 0 else "\u2193"
    return f"{arrow}{diff:+.1f}%"


def print_funnel(app: str, funnel: dict, prev: dict | None) -> None:
    """Print a visual funnel comparison."""
    steps = funnel.get("steps", [])
    if not steps:
        print(f"  No data for {app}")
        return

    prev_steps = {}
    if prev:
        for s in prev.get("steps", []):
            if isinstance(s, dict):
                prev_steps[s["name"]] = s
        # Also handle the dict format from manual snapshots
        if not prev_steps and "steps" in prev:
            raw = prev["steps"]
            if isinstance(raw, dict):
                prev_steps = {k: {"name": k, "count": v, "conversion_rate": 0} for k, v in raw.items()}

    max_count = steps[0]["count"] if steps else 1
    overall = funnel.get("overall_conversion", 0)
    prev_overall = prev.get("overall_conversion") if prev else None

    app_label = "ManifestLock" if "manifest" in app else "JournalLock"
    prev_date = prev.get("date", "?") if prev else None

    print()
    print(f"  {app_label} Onboarding Funnel")
    print(f"  {'=' * 60}")
    if prev_date:
        print(f"  Comparing: today vs {prev_date}")
    print()
    print(f"  {'Step':<44} {'Count':>5}  {'Bar':<{BAR_WIDTH}}  {'Conv':>5}  {'Drop':>7}  {'vs prev':>8}")
    print(f"  {'─' * 44} {'─' * 5}  {'─' * BAR_WIDTH}  {'─' * 5}  {'─' * 7}  {'─' * 8}")

    prev_count = None
    for step in steps:
        name = step["name"]
        count = step["count"]
        conv = step["conversion_rate"]
        drop = step["drop_off_rate"]

        # Get previous conversion for delta
        ps = prev_steps.get(name)
        prev_conv = None
        if ps:
            if "conversion_rate" in ps:
                prev_conv = ps["conversion_rate"]
            elif max_count > 0 and isinstance(ps.get("count"), (int, float)):
                # Calculate from raw counts
                prev_max = max(s.get("count", 0) for s in prev_steps.values()) if prev_steps else 1
                prev_conv = (ps["count"] / prev_max * 100) if prev_max > 0 else 0

        short = shorten(name)
        b = bar(count, max_count)
        drop_str = f"-{drop:.1f}%" if drop > 0 else ""
        d = delta_str(conv, prev_conv)

        # Flag significant drops
        flag = ""
        if drop >= 25:
            flag = " << CLIFF"
        elif name == "onboarding_completed" and count == 0:
            flag = " << BUG"

        print(f"  {short:<44} {count:>5}  {b}  {conv:>4.0f}%  {drop_str:>7}  {d:>8}{flag}")

        prev_count = count

    print()
    d_overall = delta_str(overall, prev_overall)
    print(f"  Overall: {overall:.1f}% {d_overall}")
    print(f"  Started: {steps[0]['count']}  |  Completed: {steps[-1]['count']}")
    print()


def run(app: str, date_range: str) -> None:
    """Fetch, save, and display funnel for one app."""
    print(f"\n  Pulling {app} funnel ({date_range})...")
    funnel = fetch_funnel(app, date_range)
    if not funnel:
        return

    prev = get_previous_snapshot(app)

    # Build snapshot
    steps_dict = {s["name"]: s["count"] for s in funnel.get("steps", [])}
    started = funnel["steps"][0]["count"] if funnel.get("steps") else 0
    completed = funnel["steps"][-1]["count"] if funnel.get("steps") else 0
    snapshot = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "app": app,
        "range": date_range,
        "overall_conversion": funnel.get("overall_conversion", 0),
        "started": started,
        "completed": completed,
        "steps": funnel.get("steps", []),
    }

    save_snapshot(snapshot)
    print_funnel(app, funnel, prev)


def main():
    parser = argparse.ArgumentParser(description="Pull onboarding funnel snapshots")
    parser.add_argument("--app", choices=["manifest-lock", "journal-lock"], help="Single app (default: both)")
    parser.add_argument("--range", default="30d", help="Date range (default: 30d)")
    args = parser.parse_args()

    apps = [args.app] if args.app else ["manifest-lock", "journal-lock"]
    for app in apps:
        run(app, args.range)

    print(f"  Snapshots saved to {SNAPSHOTS_PATH}")
    print()


if __name__ == "__main__":
    main()
