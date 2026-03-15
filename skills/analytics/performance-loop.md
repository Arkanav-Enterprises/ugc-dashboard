---
name: performance-loop
description: "Automated feedback loop: scrape reel metrics → analyze patterns → update skill files → pipeline uses fresh data. Replaces manual weekly reviews."
related: [proven-hooks, content_learnings, hook-architecture, pipeline]
---

# Performance Loop — Automated Feedback

## Overview

The pipeline learns from its own output through an automated feedback loop. Reel metrics are scraped from Instagram, analyzed for patterns, and the results are written back into the skill files that the generation pipeline reads.

## The Loop

```
SCRAPE → ANALYZE → UPDATE FILES → PUSH → PIPELINE READS FRESH DATA
```

### Step 1: Scrape (Local Mac, ~20 min)

```bash
# Launch Chrome with CDP (quit Chrome first)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome" &

# Scrape all 7 accounts
node scripts/scrape_reel_metrics.mjs
```

**What it does:** Connects to Chrome via CDP, navigates to each account's reels grid, extracts view counts from the grid overlay, then visits each reel detail page to extract captions, likes, timestamps, and audio from Instagram's embedded JSON (`xdt_api__v1__media__shortcode__web_info`).

**Output:** `output/reel_metrics/{account}_{date}.json` — one file per account.

### Step 2: Analyze (Local, with Claude Code)

Ask Claude Code (Opus) to read the JSON files and update the three skill files. Opus analyzes patterns, classifies hooks, and writes data-driven rules.

Or use the stats-only fallback:
```bash
python3 scripts/analyze_reel_performance.py --no-llm
```

### Step 3: Update Files

Three files get updated:

| File | Purpose | Loaded by |
|------|---------|-----------|
| `memory/post-performance.md` | Account rankings, top reels, winning/dead hooks, patterns | `load_memory_file()` |
| `skills/analytics/proven-hooks.md` | Hall of fame, pattern rankings, dead hooks list | `read_skill()` |
| `skills/analytics/content_learnings.md` | Per-persona rules with specific numbers | `read_skill()` |

### Step 4: Push + Sync VPS

```bash
git add memory/post-performance.md skills/analytics/proven-hooks.md skills/analytics/content_learnings.md
git commit -m "Update performance data from latest scrape"
git push
```

VPS: `cd /root/openclaw && git pull && systemctl restart openclaw-api`

### Step 5: Pipeline Uses Fresh Data

`autopilot.py` → `load_context_for_account()` loads all three files into the Claude system prompt. The hardcoded `DISCOVERY_RULES` and `FEAR_RULES` also reference data-backed insights (updated manually when patterns shift significantly).

## How Data Flows Into Generation

```python
# In autopilot.py, the system prompt includes:
skills = [
    ("analytics/proven-hooks.md",     "Proven winners"),
    ("analytics/content_learnings.md", "Content learnings from performance analysis"),
]
# Plus memory files:
memory = [
    ("post-performance.md", "Performance data"),
]
```

The `DISCOVERY_RULES` string (hardcoded in autopilot.py) encodes the highest-signal rules:
- Combine two hook patterns (dual-pattern avg 1,200+ views vs single-pattern 600)
- Question hooks are #1 (avg 1,316 views)
- Never use bare "i did the math" without a twist
- Each caption unique across all 7 accounts

These rules are updated when the analysis reveals significant shifts in what works.

## Hook Pattern Classification

The analysis classifies each reel's first caption line into patterns:

| Pattern | Avg Views | Signal |
|---------|-----------|--------|
| Question Hook ("wait why does...") | 1,316 | Use more |
| Plant Metaphor | 1,194 | Aliyah only |
| Phone Personification | 1,177 | Strong |
| Number Shock (with twist) | 1,057 | Need unique angle |
| Social Context (therapist, boss) | 728 | High variance, high ceiling |
| Math Shock (bare) | 535 | Saturated — needs twist |
| Confession | 461 | Needs surprising reveal |
| Generic | 432 | Avoid |

## Dashboard Visualization

The `/reel-metrics` page in the dashboard shows:
- Account performance summary (stat cards + table)
- Hook pattern analysis cards with performance tiers
- Top reels leaderboard with expandable captions

Data served by `dashboard/backend/routers/reel_metrics.py` from the scraped JSON files.

## When to Run

- **Weekly** at minimum — reel performance stabilizes after ~72 hours
- **After posting bursts** — when 10+ new reels are posted, scrape to capture fresh data
- **Before strategy changes** — scrape first to get a baseline before adjusting rules
