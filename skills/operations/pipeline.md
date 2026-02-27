---
name: pipeline
description: "End-to-end architecture of the content generation and delivery system. Cron schedule, email format, asset selection, and manual posting workflow."
related: [video-format, asset-cycling, content-mix, performance-loop]
---

# Pipeline — Content Generation System

## Architecture Overview

```
                    ┌──────────────────────┐
                    │   Cron (2x daily)    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   autopilot.py       │
                    │                      │
                    │  1. Read skill graph │
                    │     (INDEX.md →      │
                    │      relevant nodes) │
                    │                      │
                    │  2. Select persona   │
                    │     + category       │
                    │                      │
                    │  3. Generate text    │
                    │     (Anthropic API)  │
                    │     - POV overlay    │
                    │     - Reaction text  │
                    │     - Caption        │
                    │     - Hashtags       │
                    │                      │
                    │  4. Select assets    │
                    │     (cycling logic)  │
                    │                      │
                    │  5. Deliver email    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Email to Phone     │
                    │                      │
                    │  Subject: [persona]  │
                    │  Body:               │
                    │   - Text overlays    │
                    │   - Caption          │
                    │   - Asset filenames  │
                    │   - Screen rec pick  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Manual Assembly    │
                    │                      │
                    │  CapCut / editor:    │
                    │  1. Drop hook clip   │
                    │  2. Add POV text     │
                    │  3. Drop screen rec  │
                    │  4. Drop react clip  │
                    │  5. Add react text   │
                    │  6. Add trending     │
                    │     sound            │
                    │  7. Post natively    │
                    └──────────────────────┘
```

## Cron Schedule

```bash
# Content generation — 3x daily (one per account)
# @sanyahealing (Sanya, JournalLock) at 7:00 AM IST (1:30 AM UTC)
30 1 * * * /root/openclaw/scripts/autopilot_cron.sh --account sanyahealing >> /root/openclaw/logs/cron.log 2>&1

# @sophie.unplugs (Sanya, JournalLock) at 7:15 AM IST (1:45 AM UTC)
45 1 * * * /root/openclaw/scripts/autopilot_cron.sh --account sophie.unplugs >> /root/openclaw/logs/cron.log 2>&1

# @emillywilks (Emilly, ManifestLock) at 7:30 AM IST (2:00 AM UTC)
0 2 * * * /root/openclaw/scripts/autopilot_cron.sh --account emillywilks >> /root/openclaw/logs/cron.log 2>&1
```

All three run early morning IST so content is ready to review and post during the day.

## What the Pipeline Generates (Text Only)

No images or videos are generated. The Anthropic API call produces:

1. **Account**: @sanyahealing, @sophie.unplugs, or @emillywilks (based on --account flag)
2. **Persona**: Sanya or Emilly (derived from account)
3. **App**: JournalLock or ManifestLock (derived from account)
4. **Category**: A/B/C/D (weighted random per [[content-mix]])
5. **POV text overlay**: The hook text for Part 1 of [[video-format]]
6. **Suggested screen recording**: Which app recording to use
7. **Reaction text overlay**: The payoff text for Part 3 of [[video-format]]
8. **Caption**: The post caption per [[caption-formulas]]
9. **Hashtags**: 5 tags per [[tiktok]] and [[instagram]] rules
10. **Asset selections**: Which hook clip and reaction clip (from [[asset-cycling]] rotation)

**Deduplication:** When generating for Sanya's two accounts, the pipeline checks that @sophie.unplugs content is different from @sanyahealing content generated earlier the same day.

## Email Delivery Format

Subject line: `[@sanyahealing] Cat-A: "pov: your screen time is 7 hours"` or `[@emillywilks] Cat-B: "pov: your phone locked until you manifest"`

Body:
```
CONTENT — @sanyahealing (Sanya / JournalLock)
Category: A (Screen Time Shock)
Date: 2026-02-18

━━━ TEXT OVERLAYS ━━━

POV (Part 1): pov: you check your screen time and it says 7 hours 23 minutes

Reaction (Part 3): 47 minutes. that's all.

━━━ CAPTION ━━━

I didn't think 3 minutes in the morning would change anything.
Then I checked my screen time after 2 weeks.
Drop your screen time below 👇

#screentime #manifestation #digitaldetox #morningroutine #habits

━━━ ASSETS ━━━

Hook clip: sanya/hook/002.mp4
Reaction clip: sanya/reaction/001.mp4
Screen recording: stats-screen.mp4

━━━ POSTING NOTES ━━━

- Add trending sound before publishing
- Post to TikTok first, then IG Reels (adjust hashtags)
- Never mention "Manifest Lock" in caption
```

## Skill Graph Traversal

When autopilot.py runs for an account, it reads the skill graph in this order:

1. `INDEX.md` — understand the landscape, resolve account → persona → app
2. `{manifest-lock,journal-lock}.md` — load the correct app's product knowledge
3. `personas/{sanya,emilly}.md` — load persona voice
4. `content/content-mix.md` — select category (or use assigned)
5. `content/hook-architecture.md` — generate hook following rules
6. `content/text-overlays.md` — format as POV opener + reaction text
7. `content/caption-formulas.md` — generate caption
8. `content/what-never-works.md` — final quality check
9. `analytics/proven-hooks.md` — anti-repetition check (also checks other accounts generated today)
10. `visual/asset-cycling.md` + `memory/asset-usage.md` — select assets

## Manual Posting Workflow

After receiving the email:

1. Open CapCut (or preferred editor)
2. Import the specified hook clip, screen recording, and reaction clip
3. Add text overlays as specified in the email
4. Browse TikTok for a trending sound that fits the mood
5. Export as 1080x1920 vertical video
6. Post to TikTok (draft first if unsure)
7. Wait 1-2 hours, then post to IG Reels (remove TikTok watermark, adjust hashtags)
8. Reply to "what app?" comments individually throughout the day

## CLI Flags

```bash
python3 autopilot.py                                  # Generate for all 7 accounts
python3 autopilot.py --account sanyahealing            # @sanyahealing only
python3 autopilot.py --account sophie.unplugs          # @sophie.unplugs only
python3 autopilot.py --account emillywilks             # @emillywilks only
python3 autopilot.py --account sanyahealing --category A   # Force category
python3 autopilot.py --dry-run                         # Generate but don't email
python3 autopilot.py --idea-only                       # Print text only, no asset selection
```
