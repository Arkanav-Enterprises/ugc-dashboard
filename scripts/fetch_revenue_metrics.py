#!/usr/bin/env python3
"""
fetch_revenue_metrics.py — Pull daily overview metrics from RevenueCat v2 API.

Fetches MRR, revenue, subscribers, trials for Manifest Lock and Journal Lock.
Appends to logs/revenue_metrics.json, writes memory/revenue-metrics.md.

Usage:
    python3 scripts/fetch_revenue_metrics.py
    python3 scripts/fetch_revenue_metrics.py --dry-run
    python3 scripts/fetch_revenue_metrics.py --project manifest_lock
"""

import argparse
import json
import os
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_ROOT / "logs" / "revenue_metrics.json"
MEMORY_PATH = PROJECT_ROOT / "memory" / "revenue-metrics.md"

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

PROJECTS = {
    "manifest_lock": {
        "label": "Manifest Lock",
        "key": os.environ.get("RC_MANIFEST_LOCK_KEY", ""),
        "project_id": os.environ.get("RC_MANIFEST_LOCK_PROJECT_ID", ""),
    },
    "journal_lock": {
        "label": "Journal Lock",
        "key": os.environ.get("RC_JOURNAL_LOCK_KEY", ""),
        "project_id": os.environ.get("RC_JOURNAL_LOCK_PROJECT_ID", ""),
    },
}

METRIC_LABELS = {
    "mrr": "MRR",
    "revenue": "Revenue (28d)",
    "new_customers": "New Customers (28d)",
    "active_users": "Active Users",
    "active_subscriptions": "Active Subscriptions",
    "active_trials": "Active Trials",
}

MONEY_METRICS = {"mrr", "revenue"}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def fetch_overview(project_id: str, api_key: str) -> dict:
    """GET RevenueCat v2 overview metrics. Returns {metric_id: value}."""
    url = f"https://api.revenuecat.com/v2/projects/{project_id}/metrics/overview"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    })
    ctx = ssl.create_default_context()
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    data = json.loads(resp.read())
    all_metrics = {m["id"]: m["value"] for m in data["metrics"]}
    # Only keep metrics we track (skip currency breakdowns like mrr_eur, etc.)
    return {k: v for k, v in all_metrics.items() if k in METRIC_LABELS}


# ---------------------------------------------------------------------------
# Trend calculation
# ---------------------------------------------------------------------------

def load_previous_snapshot() -> dict | None:
    """Read last entry from revenue_metrics.json."""
    if not LOG_PATH.exists():
        return None
    try:
        entries = json.loads(LOG_PATH.read_text())
        if entries:
            return entries[-1]
    except (json.JSONDecodeError, IndexError):
        pass
    return None


def format_delta(metric_id: str, current: float, previous: float) -> str:
    """Format a trend string like '^ +$3.50' or 'v -2'."""
    delta = current - previous
    if delta == 0:
        return "-> 0"

    direction = "^ +" if delta > 0 else "v "
    if metric_id in MONEY_METRICS:
        return f"{direction}${delta:.2f}"
    return f"{direction}{delta:g}"


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_json_log(snapshot: dict):
    """Append snapshot to logs/revenue_metrics.json."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    if LOG_PATH.exists():
        try:
            entries = json.loads(LOG_PATH.read_text())
        except json.JSONDecodeError:
            entries = []
    entries.append(snapshot)
    LOG_PATH.write_text(json.dumps(entries, indent=2) + "\n")


def write_memory_file(snapshot: dict, previous: dict | None):
    """Write memory/revenue-metrics.md for pipeline consumption."""
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = snapshot["timestamp"]
    projects = snapshot["projects"]

    lines = [
        "# Revenue Metrics",
        f"\nLast updated: {ts}",
    ]

    # Combined summary
    total_mrr = sum(p.get("mrr", 0) for p in projects.values())
    total_subs = sum(p.get("active_subscriptions", 0) for p in projects.values())
    total_trials = sum(p.get("active_trials", 0) for p in projects.values())
    lines += [
        "\n## Combined",
        f"- **Total MRR**: ${total_mrr:.2f}",
        f"- **Total Active Subscriptions**: {total_subs:g}",
        f"- **Total Active Trials**: {total_trials:g}",
    ]

    # Per-project tables
    for name, metrics in projects.items():
        label = PROJECTS.get(name, {}).get("label", name)
        prev_metrics = previous["projects"].get(name, {}) if previous else {}

        lines += [f"\n## {label}", "| Metric | Value | Trend |", "|--------|-------|-------|"]
        for mid, mlabel in METRIC_LABELS.items():
            val = metrics.get(mid, 0)
            if mid in MONEY_METRICS:
                val_str = f"${val:.2f}"
            else:
                val_str = f"{val:g}"

            if prev_metrics and mid in prev_metrics:
                trend = format_delta(mid, val, prev_metrics[mid])
            else:
                trend = "--"
            lines.append(f"| {mlabel} | {val_str} | {trend} |")

    # Interpretation
    lines.append("\n## Interpretation for Content")
    if len(projects) == 2:
        names = list(projects.keys())
        mrr_0 = projects[names[0]].get("mrr", 0)
        mrr_1 = projects[names[1]].get("mrr", 0)
        total = mrr_0 + mrr_1
        if total > 0:
            leader = names[0] if mrr_0 >= mrr_1 else names[1]
            leader_label = PROJECTS[leader]["label"]
            pct = max(mrr_0, mrr_1) / total * 100
            lines.append(f"- {leader_label} is the stronger revenue driver ({pct:.0f}% of total MRR)")

        for name, metrics in projects.items():
            trials = metrics.get("active_trials", 0)
            subs = metrics.get("active_subscriptions", 0)
            if trials > subs and subs > 0:
                label = PROJECTS[name]["label"]
                lines.append(f"- {label}: {trials:g} active trials vs {subs:g} subscribers — conversion is the key lever")

    MEMORY_PATH.write_text("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fetch RevenueCat overview metrics")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch and print, but don't write files")
    parser.add_argument("--project", choices=list(PROJECTS.keys()),
                        help="Fetch one project only")
    args = parser.parse_args()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    snapshot = {"timestamp": timestamp, "projects": {}}
    errors = []

    targets = {args.project: PROJECTS[args.project]} if args.project else PROJECTS

    for name, config in targets.items():
        if not config["key"] or not config["project_id"]:
            print(f"  SKIP {config['label']}: missing RC_*_KEY or RC_*_PROJECT_ID env vars")
            errors.append(name)
            continue

        print(f"  Fetching {config['label']}...")
        try:
            metrics = fetch_overview(config["project_id"], config["key"])
            snapshot["projects"][name] = metrics
            print(f"    MRR=${metrics.get('mrr', 0):.2f}, "
                  f"subscriptions={metrics.get('active_subscriptions', 0):g}, "
                  f"trials={metrics.get('active_trials', 0):g}")
        except Exception as e:
            print(f"    ERROR: {e}")
            errors.append(name)

    if not snapshot["projects"]:
        print("All projects failed. No data to write.")
        raise SystemExit(1)

    if args.dry_run:
        print(f"\n[DRY RUN] Would write to {LOG_PATH} and {MEMORY_PATH}")
        print(json.dumps(snapshot, indent=2))
        return

    previous = load_previous_snapshot()
    write_json_log(snapshot)
    write_memory_file(snapshot, previous)
    print(f"\n  Logged to {LOG_PATH.relative_to(PROJECT_ROOT)}")
    print(f"  Updated {MEMORY_PATH.relative_to(PROJECT_ROOT)}")

    if errors:
        print(f"\n  WARNING: Failed projects: {', '.join(errors)}")


if __name__ == "__main__":
    main()
