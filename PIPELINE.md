# OpenClaw Pipeline Documentation

Last updated: 2026-02-18

---

## What This Is

OpenClaw is an automated content generation pipeline that produces UGC-style TikTok/Instagram Reels for two iOS apps:

- **Manifest Lock** (persona: Sanya) — makes you write a daily manifestation before unlocking your phone
- **Journal Lock** (persona: Sophie) — makes you journal before unlocking your phone

The pipeline runs on a Hostinger VPS (72.60.204.30), generates 2 reels daily (one per app) at 12 PM IST, uploads them to Google Drive, and sends an email notification with the caption ready to post.

---

## Architecture

```
Daily Cron (12 PM IST)
  └─ autopilot_video.py --persona all
       │
       ├─ For each persona (sanya, sophie):
       │
       │   1. Pick random reference image variant
       │      └─ assets/reference-images/{persona}-v{1-4}.png
       │
       │   2. Claude API generates text overlays
       │      ├─ hook_text (max 50 chars, POV/shock hook)
       │      ├─ reaction_text (max 40 chars, authentic reaction)
       │      └─ caption (story-style, soft CTA, hashtags)
       │
       │   3. Replicate API (Google Veo 3.1 Fast)
       │      ├─ Upload reference image → get URL
       │      ├─ Generate 4s video clip (9:16 portrait, no audio)
       │      ├─ Split → hook clip (first 3s) + reaction clip (first 2s)
       │      └─ Cost: ~$0.60 per clip
       │
       │   4. assemble_video.py (ffmpeg)
       │      ├─ Normalize all clips to 1080x1920 @ 30fps
       │      ├─ Burn hook_text overlay on Part 1 (lower third)
       │      ├─ Burn reaction_text overlay on Part 3 (lower third)
       │      ├─ Concatenate: Hook → Screen Recording → Reaction
       │      ├─ Strip all audio (trending sound added manually when posting)
       │      └─ Output: video_output/reel_YYYYMMDD_HHMMSS.mp4
       │
       │   5. rclone uploads to Google Drive (manifest-social-videos/)
       │
       │   6. Email notification sent with caption
       │
       └─ Daily spend recorded in logs/daily_spend.json
```

---

## Directory Structure

```
/root/openclaw/
├── scripts/
│   ├── autopilot_video.py        # Main pipeline: clip gen + text gen + assembly
│   ├── autopilot_video_cron.sh   # Cron wrapper (activates venv, loads .env)
│   ├── assemble_video.py         # ffmpeg video stitching + text overlays + upload
│   ├── generate_variants.py      # Manual tool: generate new reference image variants
│   ├── autopilot.py              # Slideshow generation (separate pipeline, nightly)
│   ├── autopilot_cron.sh         # Cron wrapper for slideshow autopilot
│   ├── generate_slideshow.py     # Image generation for slideshows
│   ├── deliver_email.py          # Email delivery helper
│   └── generate_ugc_video.py     # Legacy AI video generation script
├── assets/
│   ├── reference-images/         # Pre-made character images with varied backgrounds
│   │   ├── sanya-v1.png          #   Sanya: park background
│   │   ├── sanya-v2.png          #   Sanya: indoor/window background
│   │   ├── sanya-v3.png          #   Sanya: beach background
│   │   ├── sanya-v4.png          #   Sanya: city skyline background
│   │   ├── sophie-v1.png         #   Sophie: cozy living room
│   │   ├── sophie-v2.png         #   Sophie: apartment at night
│   │   ├── sophie-v3.png         #   Sophie: high-rise sunset
│   │   ├── sophie-v4.jpeg        #   Sophie: Central Park NYC
│   │   ├── aliyah-v1.png         #   Aliyah: variant 1
│   │   ├── aliyah-v2.jpeg        #   Aliyah: variant 2
│   │   ├── aliyah-v3.jpeg        #   Aliyah: variant 3
│   │   └── aliyah-v4.jpeg        #   Aliyah: variant 4
│   ├── screen-recordings/
│   │   ├── manifest-lock/        # App demo recordings for Manifest Lock
│   │   │   └── full-flow.mp4
│   │   └── journal-lock/         # App demo recordings for Journal Lock
│   │       └── full-flow.mp4
│   ├── sanya/                    # Generated clips (auto-created)
│   │   ├── hook/                 #   Hook clips (3s each)
│   │   └── reaction/             #   Reaction clips (2s each)
│   ├── sophie/                   # Generated clips (auto-created)
│   │   ├── hook/
│   │   └── reaction/
│   └── aliyah/                   # Generated clips (auto-created)
│       ├── hook/
│       └── reaction/
├── fonts/
│   ├── Geist-Regular.otf         # Primary font for text overlays
│   ├── Geist-Bold.otf            # Fallback font
│   └── PlayfairDisplay-Bold.ttf  # Fallback font
├── skills/                       # Context files fed to Claude for text generation
│   ├── content-strategy.md
│   ├── manifest-lock-knowledge.md
│   ├── tiktok-slideshows.md
│   └── ...
├── memory/                       # Performance tracking fed to Claude
│   ├── hook-results.md
│   ├── post-performance.md
│   └── failure-log.md
├── video_output/                 # Finished assembled reels
├── logs/
│   ├── daily_spend.json          # Replicate cost tracking per day
│   ├── video_autopilot.jsonl     # Run history (persona, text, cost, path)
│   ├── video_*.log               # Per-run cron logs
│   └── cron.log                  # Cron stderr/stdout
├── .env                          # API keys (never committed)
├── .venv/                        # Python virtual environment
└── deploy.sh                     # Rsync deployment helper
```

---

## Personas

| Persona | App(s) | Reference Images | Screen Recordings |
|---------|--------|------------------|-------------------|
| **sanya** | Manifest Lock | `sanya-v1.png` through `sanya-v4.png` | `screen-recordings/manifest-lock/` |
| **sophie** | Journal Lock | `sophie-v1.png` through `sophie-v4.jpeg` | `screen-recordings/journal-lock/` |
| **aliyah** | Both (random each run) | `aliyah-v1.png` through `aliyah-v4.jpeg` | Random: manifest-lock/ or journal-lock/ |

Each persona has 4 pre-made reference images with different backgrounds (park, indoor, beach, city, etc.). The pipeline randomly picks one per run so each reel has a unique setting without needing to describe the background in the video generation prompt. Aliyah is a multi-app persona who randomly generates for either Manifest Lock or Journal Lock each run.

---

## How Video Generation Works

### Why Pre-Made Reference Images?

Veo 3.1 Fast uses the reference image as the **first frame** of the video. If the prompt describes a different background than what's in the image, the model produces unrealistic results (it tries to morph one background into another). By pre-making reference images with varied backgrounds, each video starts from a realistic first frame and the model only needs to animate the character's expression.

### Prompt Strategy

The video prompt deliberately avoids describing the character's appearance or background. It only specifies:

1. **Preservation** — "The woman must look EXACTLY as she appears"
2. **Action** — One of 5 randomized reaction expressions (surprised, smiling, curious, disbelief, excited)
3. **Style** — Naturalistic 4K, no text overlays, no audio

This gives 4 backgrounds x 5 actions = **20 unique combinations per persona** (60 total across all three).

### Single-Clip Cost Optimization

Instead of generating separate hook and reaction clips (2 Veo calls), the pipeline generates a single 4-second clip and splits it:
- **Hook clip**: First 3 seconds (girl reacting, with POV text overlay)
- **Reaction clip**: First 2 seconds of the same clip (girl reacting, with reaction text overlay)

This halves the Replicate cost per reel.

---

## Text Generation (Claude API)

Text overlays and captions are generated by Claude (claude-sonnet-4-5-20250929) with app-specific system prompts. The Claude call receives:

- **Skill files** — content strategy, app knowledge, TikTok best practices
- **Memory files** — past hook performance, post metrics, failure logs
- **App context** — different descriptions for Manifest Lock vs Journal Lock

Output format:
```json
{
  "hook_text": "my screen time dropped 5 hours in 2 weeks",
  "reaction_text": "never going back to mindless scrolling",
  "caption": "story-style caption with soft CTA and hashtags...",
  "content_angle": "transformation"
}
```

Rules enforced:
- `hook_text` max 50 chars, must create curiosity/shock in <2 seconds
- `reaction_text` max 40 chars, authentic not salesy
- Gen Z woman voice, casual, lowercase okay
- Never mentions the app name in text overlays

---

## Video Assembly (ffmpeg)

`assemble_video.py` stitches the final reel:

1. **Normalize** all clips to 1080x1920 @ 30fps (H.264 High Profile, 8000k bitrate)
2. **Burn text overlays** on hook and reaction clips:
   - Font: Geist Regular 64px (fallback: Geist Bold, Playfair Bold, DejaVu Sans)
   - Color: White with 3px black stroke
   - Position: Lower third (Y = 75% of frame), centered horizontally
   - Auto word-wrapping at 85% frame width
3. **Speed up** screen recording if needed (default 1x for pre-edited recordings)
4. **Concatenate**: Hook → Screen Recording → Reaction
5. **Strip all audio** (trending sound added when posting)
6. **Upload** to Google Drive via rclone

---

## Cost Structure

| Component | Service | Cost |
|-----------|---------|------|
| Video clip (4s, Veo 3.1 Fast) | Replicate | ~$0.60 |
| Text generation | Anthropic Claude API | ~$0.01 |
| Assembly + upload | ffmpeg + rclone | Free |
| **Total per reel** | | **~$0.61** |
| **Daily total (3 reels)** | | **~$1.83** |

### Spending Cap

A daily spending cap (default $5.00) prevents runaway costs. Tracked in `logs/daily_spend.json`. The pipeline checks the cap before each Replicate call and skips the run if it would exceed the limit.

Override via environment variable:
```bash
export DAILY_COST_CAP=10.00
```

---

## Cron Schedule

```cron
# Video autopilot — daily at 12 PM IST (6:30 AM UTC)
# Generates 3 reels: sanya (ManifestLock) + sophie (JournalLock) + aliyah (random app)
30 6 * * * /root/openclaw/scripts/autopilot_video_cron.sh >> /root/openclaw/logs/cron.log 2>&1
```

The cron wrapper (`autopilot_video_cron.sh`):
1. Activates the Python venv
2. Loads environment variables from `.env`
3. Runs `autopilot_video.py --persona all`
4. Logs output to `logs/video_YYYYMMDD_HHMMSS.log`
5. Cleans up logs older than 30 days

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...     # Claude API for text generation
REPLICATE_API_TOKEN=r8_...       # Replicate for Veo 3.1 Fast video generation
OPENAI_API_KEY=sk-proj-...       # GPT Image (used by slideshow pipeline, not video)
SMTP_USER=email@gmail.com        # Gmail for email notifications
SMTP_PASS=xxxx xxxx xxxx xxxx    # Gmail app password
DELIVERY_EMAIL=email1,email2     # Comma-separated notification recipients
DAILY_COST_CAP=5.00              # Optional: override daily spending cap
```

---

## CLI Reference

### autopilot_video.py

```bash
# Generate 1 ManifestLock reel
python3 scripts/autopilot_video.py --persona sanya

# Generate 1 JournalLock reel
python3 scripts/autopilot_video.py --persona sophie

# Generate all 3 personas (daily cron does this)
python3 scripts/autopilot_video.py --persona all

# Generate sanya + sophie only
python3 scripts/autopilot_video.py --persona both

# Generate Aliyah only (random app)
python3 scripts/autopilot_video.py --persona aliyah

# Dry run — generate text only, no video/cost
python3 scripts/autopilot_video.py --persona all --dry-run

# Skip Google Drive upload
python3 scripts/autopilot_video.py --persona sanya --no-upload

# Use existing clips instead of generating new ones
python3 scripts/autopilot_video.py --persona sanya --skip-gen
```

### assemble_video.py

```bash
# Manual assembly with custom clips and text
python3 scripts/assemble_video.py \
  --hook-clip assets/sanya/hook/clip.mp4 \
  --screen-recording assets/screen-recordings/manifest-lock/full-flow.mp4 \
  --reaction-clip assets/sanya/reaction/clip.mp4 \
  --hook-text "POV: your phone won't let you scroll" \
  --reaction-text "wait this actually works??" \
  --speed 1
```

### generate_variants.py

```bash
# Generate new reference image variants (for adding more backgrounds)
python3 scripts/generate_variants.py --persona sanya --scene beach --dry-run
python3 scripts/generate_variants.py --persona sophie --list-scenes
```

---

## VPS Setup

**Server**: Hostinger VPS at 72.60.204.30 (Ubuntu)

### Dependencies
```bash
apt install ffmpeg
pip install replicate requests python-dotenv httpx
```

### rclone (Google Drive)
Pre-configured with `gdrive` remote pointing to `manifest-social-videos/` folder.
```bash
rclone ls gdrive:manifest-social-videos/    # List uploaded reels
rclone config reconnect gdrive:             # Re-auth if expired
```

### Deploy from local
```bash
rsync -avz --exclude='.venv/' --exclude='video_output/' --exclude='output/' --exclude='__pycache__/' --exclude='.git/' --exclude='logs/' -e ssh . root@72.60.204.30:/root/openclaw/
```

---

## Adding New Content

### New Reference Images
1. Create/source new images of the persona in different settings
2. Name them `{persona}-v{N}.png` (e.g., `sanya-v5.png`)
3. Place in `assets/reference-images/`
4. The pipeline will automatically include them in the random rotation

### New Screen Recordings
1. Record the app demo on device
2. Edit/trim as needed (the pipeline passes `--speed 1` so recordings play at original speed)
3. Place in `assets/screen-recordings/{manifest-lock|journal-lock}/`
4. The pipeline randomly picks from all recordings in the directory

### New Action Variations
Edit the `ACTIONS` list in `autopilot_video.py` to add new facial expression/reaction descriptions.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `DAILY CAP HIT` in logs | Spending limit reached | Wait until tomorrow or increase `DAILY_COST_CAP` |
| Replicate timeout | Veo generation >10min | Usually transient; cron will retry next day |
| `No reference images found` | Missing variant images | Check `assets/reference-images/{persona}-v*.png` exists |
| `No screen recordings` | Missing app demos | Add `.mp4` files to `assets/screen-recordings/{app}/` |
| rclone upload failed | Auth token expired | `rclone config reconnect gdrive:` on VPS |
| Text overlay not visible | Font missing | Install Geist-Bold.otf to `fonts/` directory |
| Wrong aspect ratio | Veo defaults to 16:9 | Ensure `aspect_ratio: "9:16"` in generate_video() |
| Character looks different | Prompt overriding image | Prompt should NOT describe appearance, only action |
| Email not sent | Gmail credentials wrong | Check `SMTP_USER` and `SMTP_PASS` in `.env` |

---

## Logs and Monitoring

- **Run history**: `logs/video_autopilot.jsonl` — JSON lines with persona, text, cost, reel path per run
- **Daily spend**: `logs/daily_spend.json` — cumulative Replicate cost per day
- **Cron output**: `logs/cron.log` — stderr/stdout from cron wrapper
- **Per-run logs**: `logs/video_YYYYMMDD_HHMMSS.log` — detailed output per cron execution
- **Email notifications** — sent after each successful/failed run
