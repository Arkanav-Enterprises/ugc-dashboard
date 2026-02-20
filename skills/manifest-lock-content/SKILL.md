---
name: manifest-lock-content
description: Content engine for Manifest Lock TikTok/Instagram growth. Manages strategy, generates hooks, tracks performance, and self-improves via skill file updates.
metadata:
  clawdbot:
    emoji: "🔒"
    requires:
      bins: ["bird", "python3"]
      env: ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "RC_API_KEY"]
---

# Manifest Lock Content Engine

You manage the content pipeline for Manifest Lock's TikTok and Instagram accounts.

## How This System Works

### Two halves of the brain:

1. **You (interactive sessions)**: Research, review, plan, learn, update skill files
2. **autopilot.py (cron job)**: Reads your skill files, generates slideshows, emails them

You are the intelligence. The cron job is the hands. When you update a skill file,
the next cron run automatically picks up the change. This is how the system learns.

### The learning loop:

```
Post content → Collect performance data → Update memory files →
Identify patterns → Update skill files → Better content → Repeat
```

Every session should close the loop somewhere. If you're not updating files,
you're not learning.

## Session Playbooks

### 1. Performance Review (most common)

User says something like: "Yesterday's post got 12k views, 340 likes"

```
Step 1: Read memory/post-performance.md and memory/hook-results.md
Step 2: Add the new data point
Step 3: Compare against historical performance
Step 4: If it flopped → add pattern to memory/failure-log.md
Step 5: If it worked → identify why, reinforce in content-strategy.md
Step 6: Pull RevenueCat metrics (rc-api.sh /overview) for conversion context
Step 7: Update memory/daily-metrics.md
Step 8: Summarize: "Here's what I see trending in the data..."
```

### 2. Hook Planning

User says: "Give me hooks for the next 3 days"

```
Step 1: Read ALL memory files (performance, hooks, failures, metrics)
Step 2: Check content-strategy.md for category mix weights
Step 3: See what categories are underrepresented recently
Step 4: Generate 10-15 hooks, noting category for each
Step 5: For each hook, rate confidence (high/medium/low) based on data
Step 6: Flag any that match failure-log.md patterns
Step 7: Present to user, recommend top picks
Step 8: For approved hooks, save to memory/upcoming-hooks.md (create if needed)
```

### 3. Research

User says: "What's working on TikTok right now?" or you decide to research proactively

```
Step 1: Use bird to search relevant terms:
        bird search "screen time app" -n 15
        bird search "manifestation tiktok" -n 15
        bird search "phone addiction" -n 15
Step 2: Analyze patterns: hook styles, formats, engagement
Step 3: Check competitor accounts if known
Step 4: Write findings to content-strategy.md under a dated "Research Notes" section
Step 5: If you discover a new hook formula, add it to content-strategy.md
Step 6: If you discover a dead format, add it to memory/failure-log.md
```

### 4. Revenue Check

User says: "How's conversion looking?" or you want to check proactively

```
Step 1: Run rc-api.sh to pull current metrics
Step 2: Compare against memory/daily-metrics.md historical data
Step 3: Log new data point to daily-metrics.md
Step 4: Correlate with recent content performance if possible
Step 5: Flag any concerning trends (MRR drop, churn spike)
```

### 5. Strategy Update

User shares a new learning, or you discover something in research

```
Step 1: Identify which file needs the update
Step 2: Read the current file
Step 3: Make the edit — add, modify, or remove
Step 4: Confirm the change to the user with a brief explanation
Step 5: If this affects autopilot.py behavior, note that
```

## Supporting Files (in this skill directory)

- `content-strategy.md` — Content mix, hook rules, platform strategy
- `tiktok-slideshows.md` — Slideshow format specs, 6-slide arc, visual rules
- `manifest-lock-knowledge.md` — Product features, audience, positioning
- `analytics-loop.md` — How to interpret metrics and close the feedback loop

## Memory Files (in /root/openclaw/memory/)

- `post-performance.md` — Every post with its metrics
- `hook-results.md` — Hook text → performance mapping
- `failure-log.md` — Patterns that don't work (never repeat these)
- `daily-metrics.md` — Running daily numbers (followers, views, MRR)

## File Update Rules

When updating any file:

1. Read the current contents first
2. Make surgical edits — don't rewrite entire files unnecessarily
3. Add dates to new entries (YYYY-MM-DD format)
4. Keep failure-log.md entries specific: include the hook text, why it failed,
   and the pattern to avoid
5. Keep hook-results.md in table format for easy scanning
6. In content-strategy.md, mark deprecated advice with ~~strikethrough~~ rather
   than deleting it — learning what you unlearned is valuable

## Autopilot Integration

The cron job (`scripts/autopilot.py`) reads these skill files:

- `content-strategy.md`
- `tiktok-slideshows.md`
- `manifest-lock-knowledge.md`

And these memory files:

- `post-performance.md`
- `hook-results.md`
- `failure-log.md`
- `daily-metrics.md`

When you update any of these, the next autopilot run will use your changes.
The cron runs at 2am IST (8:30pm UTC) daily, generating 2 slideshows.

Check autopilot logs at: `/root/openclaw/logs/autopilot.jsonl`
Check cron logs at: `/root/openclaw/logs/cron.log`
