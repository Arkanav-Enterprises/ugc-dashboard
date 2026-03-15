# OpenClaw Pipeline Documentation

Last updated: 2026-03-15

---

## What This Is

OpenClaw is an automated content generation pipeline that produces UGC-style TikTok/Instagram Reels for two iOS apps:

- **Manifest Lock** — makes you write a daily manifestation before unlocking your phone
- **Journal Lock** — makes you journal before unlocking your phone

The pipeline generates text overlays and captions via Claude, selects pre-made video clips from the asset pool, and stitches final reels with ffmpeg. **No video generation** — all video clips are pre-generated and reused.

Reels upload to Google Drive and an email notification is sent with the caption ready to post.

---

## Architecture

```
Daily Pipeline
  └─ autopilot.py --account [name]
       │
       ├─ For each account:
       │
       │   1. Load skill graph + memory files
       │      ├─ skills/content/hook-bank.md (46 ready-to-use hooks)
       │      ├─ skills/analytics/proven-hooks.md (what worked)
       │      ├─ memory/post-performance.md (performance data)
       │      ├─ memory/failure-log.md (rules not to break)
       │      └─ skills/personas/{persona}.md (voice/tone)
       │
       │   2. Claude API generates text overlays
       │      ├─ pov_text (max 50 chars, phone personification hook)
       │      ├─ reaction_text (max 40 chars, authentic reaction)
       │      ├─ caption (story-style, soft CTA, hashtags)
       │      └─ Enforces: no repeated hooks, phone personification,
       │         specific social context, emotional escalation
       │
       │   3. Select pre-made video clips (cycling logic)
       │      ├─ Hook clip from assets/{persona}/hook/
       │      ├─ Reaction clip from assets/{persona}/reaction/
       │      ├─ Screen recording from assets/screen-recordings/{app}/
       │      └─ No clip repeated within 7 days per account
       │
       │   4. assemble_video.py (ffmpeg)
       │      ├─ Normalize all clips to 1080x1920 @ 30fps
       │      ├─ Burn pov_text overlay on Part 1 (lower third)
       │      ├─ Burn reaction_text overlay on Part 3 (lower third)
       │      ├─ Concatenate: Hook → Screen Recording → Reaction
       │      ├─ Strip all audio (trending sound added when posting)
       │      └─ Output: video_output/reel_YYYYMMDD_HHMMSS.mp4
       │
       │   5. rclone uploads to Google Drive (manifest-social-videos/)
       │
       │   6. Email notification sent with caption
       │
       └─ Asset usage logged to memory/asset-usage.md
```

---

## Accounts (Priority Order — updated 2026-03-15 from 204-reel analysis)

| Account | Persona | App | Priority | Avg Views/Reel |
|---------|---------|-----|----------|---------------|
| @aliyah.journals | Aliyah | Journal Lock | HIGH | 1,522 |
| @aliyah.manifests | Aliyah | Manifest Lock | HIGH | 1,078 |
| @emillywilks | Emilly | Manifest Lock | MEDIUM | 906 |
| @riley.manifests | Riley | Manifest Lock | MEDIUM | 844 |
| @riley.journals | Riley | Journal Lock | MEDIUM | 763 |
| @sanyahealing | Sanya | Journal Lock | LOW | 746 |
| @sophie.unplugs | Sanya | Journal Lock | LOW | 491 |

**204 reels total, 190,189 views, 932 avg views/reel.**

Dedup logic ensures personas with two accounts (Aliyah, Riley, Sanya) never use the same hook on the same day.

---

## Performance Feedback Loop

The pipeline learns from its own output. Scraped reel metrics feed back into the generation rules.

```
LOCAL (Mac, Chrome CDP)                     VPS (content pipeline)
───────────────────────                     ──────────────────────
1. scrape_reel_metrics.mjs                  4. autopilot.py
   │ CDP → instagram.com/{account}/reels/      │ reads updated files at
   │ Grid: view counts                         │ content generation time
   │ Detail pages: captions, likes, dates      │
   ▼                                           ▼
   output/reel_metrics/                     load_context_for_account()
     ├── aliyah.manifests_2026-03-15.json     loads proven-hooks.md
     ├── riley.journals_2026-03-15.json       loads post-performance.md
     └── ...  (7 files)                       loads content_learnings.md
   │                                          │
   ▼                                          ▼
2. Claude Code (Opus) analyzes             DISCOVERY_RULES + FEAR_RULES
   │ Pattern analysis across 204 reels       hardcoded rules updated with
   │ Hook classification + ranking           data-backed insights
   │ Per-persona rules                       │
   ▼                                         ▼
3. Updates 3 files:                        5. Claude Sonnet generates hooks
   ├── memory/post-performance.md            following fresh data-driven rules
   ├── skills/analytics/proven-hooks.md      (question hooks #1, combine
   └── skills/analytics/content_learnings.md  patterns, unique captions, etc.)
   │
   ▼
   git push → VPS git pull → pipeline uses fresh data
```

### How to Run the Feedback Loop

```bash
# Step 1: Launch Chrome with CDP (quit Chrome first, then relaunch)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/Library/Application Support/Google/Chrome" &

# Step 2: Scrape all accounts (~20 min)
node scripts/scrape_reel_metrics.mjs

# Step 3: Analyze with Claude Code (ask Opus to read the JSONs and update the 3 files)
# Or use the stats-only fallback:
python3 scripts/analyze_reel_performance.py --no-llm

# Step 4: Commit and push
git add memory/post-performance.md skills/analytics/proven-hooks.md skills/analytics/content_learnings.md
git commit -m "Update performance data from latest scrape"
git push

# Step 5: Sync VPS
# On VPS: cd /root/openclaw && git pull && systemctl restart openclaw-api
```

### Dashboard Visualization

The Reel Metrics page at `/reel-metrics` in the dashboard shows:
- Account performance table (views, avg views, reels posted)
- Hook pattern analysis (which patterns perform best)
- Top reels leaderboard with expandable captions

---

## Directory Structure

```
/root/openclaw/
├── scripts/
│   ├── autopilot.py              # Main pipeline: text gen + asset selection + email
│   ├── lifestyle_reel.py         # Lifestyle reel pipeline: images + ffmpeg assembly
│   ├── assemble_video.py         # ffmpeg video stitching + text overlays + upload
│   ├── deliver_email.py          # Email delivery helper
│   ├── wrapper.sh                # Cron wrapper for routing commands
│   ├── fetch_revenue_metrics.py   # Daily RevenueCat metrics → memory/revenue-metrics.md
│   ├── scrape_reel_metrics.mjs    # CDP-based Instagram reel scraper (local only)
│   ├── analyze_reel_performance.py # Reads metrics, generates performance files
│   ├── generate_variants.py      # DEPRECATED — was Veo video generation
│   └── generate_ugc_video.py     # DEPRECATED — was Replicate avatar generation
├── assets/
│   ├── sanya/                    # Sanya avatar clips (@sanyahealing, @sophie.unplugs)
│   │   ├── hook/                 #   3 hook clips
│   │   └── reaction/             #   3 reaction clips
│   ├── emilly/                   # Emilly avatar clips (@emillywilks)
│   │   ├── hook/                 #   12 hook clips
│   │   └── reaction/             #   10 reaction clips
│   ├── aliyah/                   # Pre-generated clips
│   │   ├── hook/                 #   1 hook clip
│   │   └── reaction/             #   1 reaction clip
│   ├── screen-recordings/
│   │   ├── manifest-lock/        #   full-flow.mp4
│   │   └── journal-lock/         #   full-flow.mp4
│   ├── lifestyle-images/
│   │   └── journal-lock/         # Static lifestyle images for lifestyle reels
│   └── reference-images/         # Character reference images (not used in pipeline)
├── skills/                       # Context files fed to Claude for text generation
│   ├── INDEX.md                  # Skill graph entry point
│   ├── manifest-lock.md          # Manifest Lock product knowledge
│   ├── journal-lock.md           # Journal Lock product knowledge
│   ├── personas/
│   │   ├── aliyah.md             # Aliyah voice (top performer)
│   │   ├── riley.md              # Riley voice (breakout potential)
│   │   ├── sanya.md              # Sanya voice (@sanyahealing + @sophie.unplugs, JournalLock)
│   │   └── emilly.md             # Emilly voice (@emillywilks, ManifestLock)
│   ├── content/
│   │   ├── hook-bank.md          # 46 ready-to-use hooks by pattern type
│   │   ├── hook-architecture.md  # Hook formulas and quality rules
│   │   ├── content-mix.md        # Category ratios (A/B/C/D)
│   │   ├── text-overlays.md      # POV opener + reaction text patterns
│   │   ├── caption-formulas.md   # Caption structures and CTA rules
│   │   └── what-never-works.md   # Anti-patterns and banned phrases
│   ├── analytics/
│   │   ├── proven-hooks.md       # Hooks that performed (auto-updated by analysis)
│   │   ├── content_learnings.md  # Per-persona rules from reel analysis (auto-updated)
│   │   └── performance-loop.md   # Feedback loop process
│   ├── visual/
│   │   └── asset-cycling.md      # Asset rotation logic
│   └── platform/
│       ├── tiktok.md             # TikTok algorithm signals
│       └── instagram.md          # IG Reels differences
├── memory/                       # Performance tracking fed to Claude
│   ├── post-performance.md       # Account-level and per-reel performance data
│   ├── failure-log.md            # Dead patterns and rules not to break
│   ├── asset-usage.md            # Asset usage tracking and video pool inventory
│   └── revenue-metrics.md        # RevenueCat MRR/trials/subs (auto-updated daily)
├── fonts/
│   ├── Geist-Regular.otf         # Primary font for text overlays
│   └── Geist-Bold.otf           # Bold variant
├── video_output/                 # Finished assembled reels
├── output/                       # Pipeline output (JSON briefs, variants)
├── logs/
│   ├── lifestyle_reel.jsonl      # Lifestyle reel run history
│   ├── revenue_metrics.json      # RevenueCat daily snapshots (append-only)
│   └── *.log                     # Per-run logs
├── .env                          # API keys (never committed)
├── .venv/                        # Python virtual environment
└── deploy.sh                     # Rsync deployment helper
```

---

## Text Generation (Claude API)

Text overlays and captions are generated by Claude with skill graph context. The Claude call receives:

- **Skill files** — hook bank, content strategy, app knowledge, persona voice
- **Memory files** — post performance data, failure log rules
- **Hard rules** injected into the prompt (updated 2026-03-15 from 204-reel analysis):
  1. Combine two hook patterns — single-pattern avg 600 views, dual-pattern avg 1,200+
  2. Question hooks are #1 (avg 1,316 views) — "wait why does..." openers
  3. Plant/guilt metaphor #2 (avg 1,194) — exclusive to Aliyah
  4. Phone personification #3 (avg 1,177) — still strong
  5. Never use bare "i did the math" without a twist (71 reels, avg 150-250 views)
  6. Social context required (therapist, boss, roommate) — #1 reel (3,057 views) uses therapist
  7. Each caption unique across all 7 accounts
  8. Read content_learnings.md for per-persona rules

Output format:
```json
{
  "pov_text": "my phone won't unlock until i trauma dump",
  "reaction_text": "wait this actually works??",
  "caption": "story-style caption with soft CTA and hashtags...",
  "hashtags": "#screentime #phonetok #manifestation"
}
```

---

## Video Assembly (ffmpeg)

`assemble_video.py` stitches the final reel:

1. **Normalize** all clips to 1080x1920 @ 30fps (H.264 High Profile, 8000k bitrate)
2. **Burn text overlays** on hook and reaction clips:
   - Font: Geist Bold 55px (scenes 1-2), 48px (scene 3)
   - Color: White on black pill background (boxcolor=black@0.85)
   - Position: Lower third (Y = 75% of frame), centered horizontally
   - Auto word-wrapping at ~28 chars per line
3. **Concatenate**: Hook → Screen Recording → Reaction
4. **Strip all audio** (trending sound added when posting)
5. **Upload** to Google Drive via rclone

---

## Cost Structure

| Component | Service | Cost |
|-----------|---------|------|
| Text generation | Anthropic Claude API | ~$0.01 |
| Assembly + upload | ffmpeg + rclone | Free |
| **Total per reel** | | **~$0.01** |

Video generation via Veo/Replicate is retired. All clips are pre-generated and reused.

---

## Lifestyle Reel Pipeline

A separate pipeline that produces 3-scene reels using static lifestyle images and screen recordings. No AI video generation — just ffmpeg composition with Ken Burns effect and text overlays.

```
lifestyle_reel.py
  │
  1. Claude API → generates scene text (hook, response, payoff)
  │   └─ Plain ASCII only (no emojis)
  │
  2. Pick lifestyle images (assets/lifestyle-images/journal-lock/)
  │   └─ Cycles through images, avoids repeats within 7 runs
  │
  3. Pick screen recording (assets/screen-recordings/journal-lock/)
  │
  4. ffmpeg assembly:
  │   ├─ Scene 1: Lifestyle image + Ken Burns zoom + hook text (3s)
  │   ├─ Scene 2: Lifestyle image + Ken Burns zoom + response text (3s)
  │   ├─ Scene 3: Screen recording + payoff text (up to 12s)
  │   └─ Concatenate scenes → final reel
  │
  5. rclone → upload to Google Drive
  │
  └─ Run logged to logs/lifestyle_reel.jsonl
```

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...           # Claude API for text generation
SMTP_USER=email@gmail.com              # Gmail for email notifications
SMTP_PASS=xxxx xxxx xxxx xxxx          # Gmail app password
DELIVERY_EMAIL=email1,email2           # Comma-separated notification recipients
RC_MANIFEST_LOCK_KEY=sk_...            # RevenueCat v2 key for Manifest Lock
RC_MANIFEST_LOCK_PROJECT_ID=...        # RevenueCat project ID
RC_JOURNAL_LOCK_KEY=sk_...             # RevenueCat v2 key for Journal Lock
RC_JOURNAL_LOCK_PROJECT_ID=...         # RevenueCat project ID
```

Note: `REPLICATE_API_TOKEN` and `OPENAI_API_KEY` are no longer needed for the active pipeline. They may still be in .env for legacy scripts.

---

## CLI Reference

### autopilot.py

```bash
# Generate for one account
python3 scripts/autopilot.py --account aliyah.manifests

# Generate for all 7 accounts
python3 scripts/autopilot.py

# Force a content category
python3 scripts/autopilot.py --account aliyah.journals --category A

# Dry run — generate text only, no email
python3 scripts/autopilot.py --account riley.manifests --dry-run

# Text only — skip asset selection and email
python3 scripts/autopilot.py --idea-only
```

### lifestyle_reel.py

```bash
# Generate a lifestyle reel (Journal Lock)
python3 scripts/lifestyle_reel.py

# Dry run — generate text only, no ffmpeg assembly
python3 scripts/lifestyle_reel.py --dry-run

# Skip Google Drive upload
python3 scripts/lifestyle_reel.py --no-upload

# Override generated text
python3 scripts/lifestyle_reel.py --scene-1-text "Hook text" --scene-2-text "Response" --scene-3-text "Payoff"
```

### scrape_reel_metrics.mjs

```bash
# Scrape all 7 accounts (requires Chrome with CDP on port 9222)
node scripts/scrape_reel_metrics.mjs

# Single account
node scripts/scrape_reel_metrics.mjs --account aliyah.manifests

# Limit reels per account
node scripts/scrape_reel_metrics.mjs --account riley.journals --max-reels 5
```

### analyze_reel_performance.py

```bash
# Full analysis (calls Claude API for pattern insights)
python3 scripts/analyze_reel_performance.py

# Stats-only mode (no Claude API call)
python3 scripts/analyze_reel_performance.py --no-llm

# Dry run — print output without writing files
python3 scripts/analyze_reel_performance.py --dry-run
```

### fetch_revenue_metrics.py

```bash
# Fetch metrics for both apps and write to logs + memory
python3 scripts/fetch_revenue_metrics.py

# Dry run — fetch + print, no file writes
python3 scripts/fetch_revenue_metrics.py --dry-run

# Single project only
python3 scripts/fetch_revenue_metrics.py --project manifest_lock
```

---

## Cron Schedule

```cron
# Video autopilot — daily at 12:00 PM IST (6:30 AM UTC)
30 6 * * * cd /root/openclaw && bash scripts/autopilot_video_cron.sh

# RevenueCat metrics — daily at 7:00 AM IST (1:30 AM UTC)
30 1 * * * cd /root/openclaw && source .venv/bin/activate && python3 scripts/fetch_revenue_metrics.py >> logs/cron.log 2>&1
```

---

## VPS Setup

**Server**: Hostinger VPS at 72.60.204.30 (Ubuntu 24.04)

### Dependencies
```bash
apt install ffmpeg
pip install anthropic requests python-dotenv httpx
```

### rclone (Google Drive)
Pre-configured with `gdrive` remote pointing to `manifest-social-videos/` folder.
```bash
rclone ls gdrive:manifest-social-videos/    # List uploaded reels
rclone config reconnect gdrive:             # Re-auth if expired
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No reference images found` | Missing variant images | Check `assets/reference-images/{persona}-v*.png` exists |
| `No screen recordings` | Missing app demos | Add `.mp4` files to `assets/screen-recordings/{app}/` |
| `NO HOOK CLIPS` | Missing pre-generated clips | Check `assets/{persona}/hook/` has .mp4 files |
| rclone upload failed | Auth token expired | `rclone config reconnect gdrive:` on VPS |
| Text overlay not visible | Font missing | Install Geist-Bold.otf to `fonts/` directory |
| Email not sent | Gmail credentials wrong | Check `SMTP_USER` and `SMTP_PASS` in `.env` |
| Same hook repeated | Dedup logic not catching | Check output/ for today's JSON files |
