#!/usr/bin/env python3
"""
analyze_reel_performance.py — Read scraped reel metrics, call Claude for pattern
analysis, and update the skill files that feed the content pipeline.

Usage:
    python3 scripts/analyze_reel_performance.py              # Full analysis
    python3 scripts/analyze_reel_performance.py --dry-run    # Print analysis, don't write files

Reads: output/reel_metrics/*.json (latest snapshot per account)
Writes:
  1. memory/post-performance.md
  2. skills/analytics/proven-hooks.md
  3. skills/analytics/content_learnings.md
"""

import os
import sys
import json
import glob
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METRICS_DIR = PROJECT_ROOT / "output" / "reel_metrics"
MEMORY_DIR = PROJECT_ROOT / "memory"
SKILLS_DIR = PROJECT_ROOT / "skills" / "analytics"

# Account metadata — mirrors autopilot.py
ACCOUNTS = {
    "aliyah.manifests": {"persona": "Aliyah", "app": "ManifestLock", "handle": "@aliyah.manifests"},
    "aliyah.journals":  {"persona": "Aliyah", "app": "JournalLock",  "handle": "@aliyah.journals"},
    "riley.manifests":  {"persona": "Riley",  "app": "ManifestLock", "handle": "@riley.manifests"},
    "riley.journals":   {"persona": "Riley",  "app": "JournalLock",  "handle": "@riley.journals"},
    "sanyahealing":     {"persona": "Sanya",  "app": "JournalLock",  "handle": "@sanyahealing"},
    "sophie.unplugs":   {"persona": "Sanya",  "app": "JournalLock",  "handle": "@sophie.unplugs"},
    "emillywilks":      {"persona": "Emilly", "app": "ManifestLock", "handle": "@emillywilks"},
}


# ---------------------------------------------------------------------------
# Load latest metric snapshots
# ---------------------------------------------------------------------------

def load_latest_metrics() -> dict[str, list[dict]]:
    """Load the most recent snapshot file per account. Returns {account: [reels]}."""
    if not METRICS_DIR.exists():
        print(f"❌ No metrics directory at {METRICS_DIR}")
        sys.exit(1)

    account_reels = {}
    for account in ACCOUNTS:
        pattern = str(METRICS_DIR / f"{account}_*.json")
        files = sorted(glob.glob(pattern))
        if not files:
            print(f"  WARN: No metrics found for {account}")
            continue
        latest = files[-1]  # Sorted by date suffix
        with open(latest) as f:
            reels = json.load(f)
        account_reels[account] = reels
        print(f"  Loaded {len(reels)} reels from {Path(latest).name}")

    if not account_reels:
        print("❌ No metric files found. Run scrape_reel_metrics.mjs first.")
        sys.exit(1)

    return account_reels


# ---------------------------------------------------------------------------
# Build analysis summary (no LLM needed for raw stats)
# ---------------------------------------------------------------------------

def build_stats_summary(account_reels: dict) -> dict:
    """Compute per-account and cross-account stats."""
    summary = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "accounts": {},
        "all_reels": [],
        "top_10": [],
        "bottom_10": [],
    }

    for account, reels in account_reels.items():
        meta = ACCOUNTS[account]
        total_views = sum(r.get("views", 0) for r in reels)
        avg_views = total_views // max(len(reels), 1)

        summary["accounts"][account] = {
            "handle": meta["handle"],
            "persona": meta["persona"],
            "app": meta["app"],
            "reels_posted": len(reels),
            "total_views": total_views,
            "avg_views": avg_views,
        }

        for r in reels:
            summary["all_reels"].append({
                **r,
                "account": account,
                "handle": meta["handle"],
                "persona": meta["persona"],
                "app": meta["app"],
            })

    # Sort all reels by views
    summary["all_reels"].sort(key=lambda r: r.get("views", 0), reverse=True)
    summary["top_10"] = summary["all_reels"][:10]
    summary["bottom_10"] = summary["all_reels"][-10:] if len(summary["all_reels"]) >= 10 else []

    return summary


# ---------------------------------------------------------------------------
# Call Claude for pattern analysis
# ---------------------------------------------------------------------------

def call_claude_analysis(summary: dict) -> dict:
    """Send metrics to Claude sonnet for pattern analysis. Returns structured output."""
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)

    client = anthropic.Anthropic()

    # Read existing skill files for context
    existing_proven = ""
    proven_path = SKILLS_DIR / "proven-hooks.md"
    if proven_path.exists():
        existing_proven = proven_path.read_text()

    existing_perf = ""
    perf_path = MEMORY_DIR / "post-performance.md"
    if perf_path.exists():
        existing_perf = perf_path.read_text()

    # Build the prompt
    metrics_json = json.dumps({
        "date": summary["date"],
        "accounts": summary["accounts"],
        "top_10_reels": summary["top_10"],
        "bottom_10_reels": summary["bottom_10"],
        "total_reels_analyzed": len(summary["all_reels"]),
    }, indent=2)

    system_prompt = """You are a social media performance analyst for a UGC content pipeline.
You analyze Instagram reel metrics across 7 accounts promoting two apps (ManifestLock and JournalLock).

Your job is to identify what's working, what's not, and produce actionable rules for content generation.
Be specific and data-driven. Reference actual view counts and hook text."""

    user_prompt = f"""Here are the latest reel metrics scraped from Instagram:

{metrics_json}

And here are ALL reels with their captions (for hook pattern analysis):
{json.dumps([{{"caption": r.get("caption", ""), "views": r.get("views", 0), "account": r.get("account", ""), "persona": r.get("persona", "")}} for r in summary["all_reels"]], indent=2)}

---

Based on this data, produce THREE outputs as a single JSON object with these exact keys:

1. "post_performance_md" — A complete replacement for post-performance.md. Include:
   - Account performance summary table (as of today's date)
   - Per-reel standouts section with actual hook text and view counts
   - Winning hooks table with hook pattern, persona, views, and why it worked
   - Dead hooks table
   - Patterns section (what's working, what's not, audience signals)
   Keep the same format/structure as before but with fresh data.

2. "proven_hooks_md" — A complete replacement for proven-hooks.md. Include:
   - Hall of Fame table (top performers by views, include hook text, category, persona, account, views, date)
   - Patterns Emerging section
   - Dead Hooks table
   - Keep YAML frontmatter: name: proven-hooks, description, related fields

3. "content_learnings_md" — New file with per-persona content rules. Include:
   - Header noting it's auto-generated with today's date
   - Per-persona section (@handle format) with 3-5 bullet points each
   - Each bullet should be a specific, actionable rule derived from the data
   - Include specific numbers (view counts, averages) to back up each rule
   - End with a cross-persona patterns section

Return ONLY valid JSON with these three string keys. No markdown code fences."""

    print("\n🤖 Calling Claude for pattern analysis...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Parse response
    text = response.content[0].text.strip()

    # Handle potential markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3].strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"⚠ Claude returned invalid JSON: {e}")
        print(f"Raw response:\n{text[:500]}...")
        sys.exit(1)

    return result


# ---------------------------------------------------------------------------
# Write output files
# ---------------------------------------------------------------------------

def write_outputs(analysis: dict, dry_run: bool = False):
    """Write the three output files."""
    today = datetime.now().strftime("%Y-%m-%d")

    files = {
        MEMORY_DIR / "post-performance.md": analysis.get("post_performance_md", ""),
        SKILLS_DIR / "proven-hooks.md": analysis.get("proven_hooks_md", ""),
        SKILLS_DIR / "content_learnings.md": analysis.get("content_learnings_md", ""),
    }

    for path, content in files.items():
        if not content:
            print(f"  ⚠ No content for {path.name}, skipping")
            continue

        if dry_run:
            print(f"\n{'='*60}")
            print(f"DRY RUN — would write to {path}:")
            print(f"{'='*60}")
            print(content[:500] + ("..." if len(content) > 500 else ""))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"  ✅ Wrote {path.name} ({len(content)} chars)")


# ---------------------------------------------------------------------------
# Fallback: generate files without LLM (stats-only)
# ---------------------------------------------------------------------------

def generate_stats_only(summary: dict) -> dict:
    """Generate output files using raw stats only (no Claude API call)."""
    today = summary["date"]

    # Build account table
    rows = []
    for account, stats in sorted(summary["accounts"].items(), key=lambda x: x[1]["total_views"], reverse=True):
        rows.append(
            f"| {stats['handle']} | {stats['persona']} | {stats['app']} | "
            f"{stats['total_views']:,} | {stats['reels_posted']} | "
            f"{stats['avg_views']:,} |"
        )
    account_table = "\n".join(rows)

    # Build top reels
    top_reels = []
    for r in summary["top_10"]:
        caption = r.get("caption", "").split("\n")[0][:80]
        if caption:
            top_reels.append(f'- "{caption}" — {r.get("views", 0):,} views ({r.get("handle", "")})')

    # Build bottom reels
    bottom_reels = []
    for r in summary["bottom_10"]:
        caption = r.get("caption", "").split("\n")[0][:80]
        if caption:
            bottom_reels.append(f'- "{caption}" — {r.get("views", 0):,} views ({r.get("handle", "")})')

    post_perf = f"""# Post Performance Tracker

> **INSTRUCTIONS FOR CLAUDE**: This is your primary signal for content decisions.
> Before generating any content, read the Patterns and Dead Hooks sections.
> Prioritize variations of Winning Hooks. Avoid anything in Dead Hooks.
> Weight saves and shares over views — they signal real intent.

## Account Performance Summary (as of {today})

| Account | Persona | App | Total Views | Reels Posted | Avg Views/Reel |
|---------|---------|-----|-------------|-------------|----------------|
{account_table}

## Top Performing Reels

{chr(10).join(top_reels) if top_reels else "No data yet."}

## Lowest Performing Reels

{chr(10).join(bottom_reels) if bottom_reels else "No data yet."}
"""

    proven = f"""---
name: proven-hooks
description: "Living document of hooks that performed well. Updated after each analysis run. Reference for inspiration and anti-repetition checks."
related: [hook-architecture, performance-loop, what-never-works, hook-bank]
---

# Proven Hooks — What Actually Worked (Updated {today})

## Hall of Fame (Top Performers)

| Hook | Persona | Account | Views | Date |
|------|---------|---------|-------|------|
"""
    for r in summary["top_10"]:
        caption = r.get("caption", "").split("\n")[0][:80]
        if caption:
            proven += f'| "{caption}" | {r.get("persona", "")} | {r.get("handle", "")} | {r.get("views", 0):,} | {r.get("timestamp", today)} |\n'

    # Content learnings — per persona
    persona_reels = defaultdict(list)
    for r in summary["all_reels"]:
        persona_reels[r.get("persona", "Unknown")].append(r)

    learnings = f"# Content Learnings (auto-generated {today})\n\n"
    for persona, reels in sorted(persona_reels.items()):
        reels.sort(key=lambda r: r.get("views", 0), reverse=True)
        total = sum(r.get("views", 0) for r in reels)
        avg = total // max(len(reels), 1)
        top = reels[0] if reels else {}
        learnings += f"## {persona}\n"
        learnings += f"- {len(reels)} reels analyzed, {total:,} total views, {avg:,} avg views/reel\n"
        if top.get("caption"):
            learnings += f'- Top reel: "{top["caption"][:60]}" ({top.get("views", 0):,} views)\n'
        learnings += "\n"

    return {
        "post_performance_md": post_perf,
        "proven_hooks_md": proven,
        "content_learnings_md": learnings,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze reel performance metrics")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing files")
    parser.add_argument("--no-llm", action="store_true", help="Stats-only mode (no Claude API call)")
    args = parser.parse_args()

    print("📊 Loading latest reel metrics...")
    account_reels = load_latest_metrics()

    print(f"\n📈 Building stats summary...")
    summary = build_stats_summary(account_reels)
    print(f"  Total reels: {len(summary['all_reels'])}")
    print(f"  Top reel: {summary['top_10'][0].get('views', 0):,} views" if summary["top_10"] else "")

    if args.no_llm:
        print("\n📝 Generating stats-only output (no LLM)...")
        analysis = generate_stats_only(summary)
    else:
        analysis = call_claude_analysis(summary)

    print("\n📝 Writing output files...")
    write_outputs(analysis, dry_run=args.dry_run)

    print("\n✅ Analysis complete.")
    if not args.dry_run:
        print("Next steps:")
        print("  1. Review the updated files in memory/ and skills/analytics/")
        print("  2. git add + commit + push")
        print("  3. Sync VPS: cd /root/openclaw && git pull && systemctl restart openclaw-api")


if __name__ == "__main__":
    main()
