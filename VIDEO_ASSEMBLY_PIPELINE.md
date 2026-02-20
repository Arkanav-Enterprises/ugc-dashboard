# Video Assembly Pipeline

Last updated: 2026-02-20

---

## Overview

Automated UGC-style reaction reel generation for two iOS apps: **Manifest Lock** and **Journal Lock**. The pipeline rotates between 3 video types daily (original, UGC lighting, outdoor), picks the appropriate reference image, generates an AI video clip via Veo 3.1 Fast, generates text overlays via Claude, assembles the final reel with ffmpeg, uploads to Google Drive, and sends an email notification.

Runs daily at 12 PM IST via cron on the Hostinger VPS (72.60.204.30), producing 3 reels per day (one per persona). All personas use the same video type on a given day.

---

## Architecture

```
Daily Cron (12 PM IST / 6:30 AM UTC)
  └─ autopilot_video_cron.sh
       └─ autopilot_video.py --persona all
            │
            ├─ pick_video_type() → rotate daily: original → ugc_lighting → outdoor
            │
            ├─ For each persona (sanya, sophie, aliyah):
            │
            │   1. pick_app() → resolve which app this persona runs for
            │   2. pick_reference_image(persona, video_type) → select image for type
            │   3. Claude API → generates hook_text + reaction_text + caption
            │   4. Replicate (Veo 3.1 Fast) → 4s video from reference image + type-specific prompt
            │   5. ffmpeg split → hook clip + reaction clip (durations vary by type)
            │   6. assemble_video.py → normalize + text overlays + concatenate
            │   7. rclone → upload to Google Drive
            │   8. Email notification with caption
            │
            └─ Daily spend recorded in logs/daily_spend.json
```

### Reel Structure

```
Part 1: Hook clip (varies by type)     ← AI-generated, with hook_text overlay
Part 2: Screen recording (var)         ← Pre-recorded app demo, no overlay
Part 3: Reaction clip (varies by type) ← AI-generated, with reaction_text overlay
```

---

## Video Types

The pipeline rotates between 3 video types daily using `day_of_year % 3`. All personas use the same type on a given day. The `--video-type` CLI flag can override the rotation.

| Video Type | Reference Image | Prompt | Hook Clip | Reaction Clip |
|------------|-----------------|--------|-----------|---------------|
| **original** | Random from `{persona}-v{1-4}.*` | Randomized action from 5 variations | First 3s | First 2s |
| **ugc_lighting** | `{persona}-ugc.*` | Indoor golden hour, hand-reveal smile | First 2.5s | Last 2s (from 2s) |
| **outdoor** | `{persona}-outdoor.*` | Outdoor celebration, arm raise | First 2.2s | Last 1.8s (from 2.2s) |

### Reference Image Naming

```
assets/reference-images/
├── sanya-v1.png … sanya-v4.png       # Original: 4 variants, random selection
├── sophie-v1.png … sophie-v4.png
├── aliyah-v1.png … aliyah-v4.jpeg
├── sanya-ugc.jpeg                     # UGC lighting: 1 per persona
├── sophie-ugc.jpeg
├── aliyah-ugc.jpeg
├── sanya-outdoor.png                  # Outdoor: 1 per persona
├── sophie-outdoor.png
└── aliyah-outdoor.jpeg
```

### Prompt Strategy

All prompts share a core principle: preserve the reference image exactly and only animate facial expressions/body motion. The prompt never describes the character's appearance or background.

- **Original**: 5 randomized action variations (surprised, warm smile, curious-to-shocked, calm-to-disbelief, neutral-to-excited)
- **UGC lighting**: Indoor golden hour scene with hand-covering-mouth to smile reveal progression
- **Outdoor**: Relaxed smile building to celebratory arm raise

Prompts are defined in `VIDEO_PROMPTS` dict at module level in `autopilot_video.py`.

---

## Directory Structure

```
/root/openclaw/
├── scripts/
│   ├── autopilot_video.py        # Main pipeline: clip gen + text gen + assembly
│   ├── autopilot_video_cron.sh   # Cron wrapper (activates venv, loads .env)
│   ├── assemble_video.py         # ffmpeg stitching + text overlays + Drive upload
│   ├── generate_variants.py      # Manual tool: generate new reference images
│   ├── autopilot.py              # Slideshow pipeline (separate, nightly cron)
│   ├── autopilot_cron.sh         # Cron wrapper for slideshow autopilot
│   ├── deliver_email.py          # Email delivery helper
│   └── generate_slideshow.py     # Image generation for slideshows
├── assets/
│   ├── reference-images/         # Pre-made character images (flat directory)
│   │   ├── {persona}-v{1-4}.*    #   Original type: 4 variants per persona
│   │   ├── {persona}-ugc.*       #   UGC lighting type: 1 per persona
│   │   └── {persona}-outdoor.*   #   Outdoor type: 1 per persona
│   ├── screen-recordings/
│   │   ├── manifest-lock/        # App demo recordings for Manifest Lock
│   │   │   └── full-flow.mp4
│   │   └── journal-lock/         # App demo recordings for Journal Lock
│   │       └── full-flow.mp4
│   ├── sanya/                    # Auto-created generated clips
│   │   ├── hook/
│   │   └── reaction/
│   ├── sophie/
│   │   ├── hook/
│   │   └── reaction/
│   └── aliyah/
│       ├── hook/
│       └── reaction/
├── fonts/
│   ├── Geist-Regular.otf         # Primary font for text overlays
│   ├── Geist-Bold.otf            # Fallback
│   └── PlayfairDisplay-Bold.ttf  # Fallback
├── skills/                       # Context files fed to Claude for text generation
│   ├── content-strategy.md
│   ├── manifest-lock-knowledge.md
│   └── tiktok-slideshows.md
├── memory/                       # Performance tracking fed to Claude
│   ├── hook-results.md
│   ├── post-performance.md
│   ├── failure-log.md
│   └── asset-usage.md            # Tracks which images/types were used per day
├── video_output/                 # Finished assembled reels
├── logs/
│   ├── daily_spend.json          # Replicate cost tracking per day
│   ├── video_autopilot.jsonl     # Run history (JSONL, includes video_type field)
│   ├── video_*.log               # Per-run cron logs
│   └── cron.log                  # Cron stderr/stdout
├── .env                          # API keys (never committed)
├── .venv/                        # Python virtual environment
├── PIPELINE.md                   # Full pipeline documentation
└── VIDEO_ASSEMBLY_PIPELINE.md    # This file
```

---

## Personas

| Persona | Apps | Reference Images | Description |
|---------|------|------------------|-------------|
| **sanya** | Manifest Lock | `sanya-v{1-4}`, `sanya-ugc`, `sanya-outdoor` | Dark-haired woman, varied backgrounds |
| **sophie** | Journal Lock | `sophie-v{1-4}`, `sophie-ugc`, `sophie-outdoor` | Brown-haired woman, cozy/urban backgrounds |
| **aliyah** | Both (random) | `aliyah-v{1-4}`, `aliyah-ugc`, `aliyah-outdoor` | American-Indian woman, used for both apps |

Each persona has reference images for all 3 video types. Original type has 4 variants (random selection); UGC lighting and outdoor have 1 image each.

### Why Pre-Made Reference Images?

Veo 3.1 Fast uses the reference image as the **first frame** of the video. If the text prompt describes a different background than what's in the image, the model produces unrealistic results. By pre-making reference images with varied backgrounds, each video starts from a realistic first frame and the model only needs to animate the character's facial expression.

---

## Video Generation (Replicate)

### Model: Google Veo 3.1 Fast

```python
client.run(
    "google/veo-3.1-fast",
    input={
        "prompt": video_prompt,
        "image": image_url,        # Reference image as first frame
        "duration": 4,             # 4 seconds (minimum allowed)
        "aspect_ratio": "9:16",    # Portrait for TikTok/Reels
        "generate_audio": False,   # Audio disabled (added when posting)
    },
)
```

### Single-Clip Cost Optimization

One 4-second Veo call is split into both clips via ffmpeg. Split points vary by video type:

| Video Type | Hook Clip | Reaction Clip |
|------------|-----------|---------------|
| original | 0s–3s (3s) | 0s–2s (2s) |
| ugc_lighting | 0s–2.5s (2.5s) | 2s–4s (2s) |
| outdoor | 0s–2.2s (2.2s) | 2.2s–4s (1.8s) |

Split points are defined in `CLIP_SPLIT_POINTS` dict at module level. For clips starting at a non-zero offset, ffmpeg uses `-ss` to seek.

This halves the Replicate cost per reel vs generating two separate clips.

---

## Text Generation (Claude API)

Model: `claude-sonnet-4-5-20250929`

The Claude call receives:
- **Skill files**: content-strategy.md, manifest-lock-knowledge.md, tiktok-slideshows.md
- **Memory files**: hook-results.md, post-performance.md, failure-log.md
- **App-specific system prompt**: Different descriptions for Manifest Lock vs Journal Lock

Response format:
```json
{
  "hook_text": "showed my screen time to my roommate. she went silent",
  "reaction_text": "now she uses it too lol",
  "caption": "Story-style caption with soft CTA and hashtags...",
  "content_angle": "relatable"
}
```

Rules:
- `hook_text`: Max 50 chars, first-person POV or shock statement
- `reaction_text`: Max 40 chars, authentic not salesy
- Gen Z woman voice, casual, lowercase okay
- Never mentions the app name in overlays
- Angles: discovery, challenge, transformation, relatable, stat

---

## Video Assembly (ffmpeg)

`assemble_video.py` stitches the final reel:

### Output Naming

Reels are named with persona and video type for easy identification:
```
reel_{persona}_{video_type}_{YYYYMMDD_HHMMSS}.mp4
```
Examples: `reel_sophie_ugc_lighting_20260220_174530.mp4`, `reel_sanya_outdoor_20260220_174812.mp4`

### Text Overlay Spec

- **Font**: Geist Regular (primary), Geist Bold (fallback), Playfair Bold (fallback), DejaVu Sans (system fallback)
- **Size**: 64px
- **Color**: White (`#FFFFFF`)
- **Stroke**: Black, 3px width
- **Position**: Lower third — centered horizontally, Y = 75% of frame height
- **Max width**: 85% of frame width with automatic word wrapping
- **Applied to**: Part 1 (hook text) and Part 3 (reaction text) only

### Video Normalization

All clips normalized before concatenation:

- **Resolution**: 1080x1920 (9:16 portrait)
- **FPS**: 30
- **Codec**: H.264 High Profile Level 4.0
- **Pixel format**: yuv420p
- **Bitrate**: 8000k
- **Audio**: Stripped from all clips
- **Scaling**: `scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2`

---

## Google Drive Upload

Uses **rclone** with pre-configured `gdrive` remote on VPS.

- **Target folder**: `gdrive:manifest-social-videos/`
- **Command**: `rclone copy <reel_path> gdrive:manifest-social-videos/`
- **Verification**: `rclone ls gdrive:manifest-social-videos/`

If rclone auth expires: `rclone config reconnect gdrive:`

---

## Logging

### JSONL Run Log

Each run appends to `logs/video_autopilot.jsonl` with fields:
```json
{
  "timestamp": "2026-02-20T17:30:00+00:00",
  "persona": "sophie",
  "video_type": "ugc_lighting",
  "hook_text": "...",
  "reaction_text": "...",
  "caption": "...",
  "content_angle": "relatable",
  "reel_path": "video_output/reel_sophie_ugc_lighting_20260220_173000.mp4",
  "cost_usd": 0.61
}
```

### Asset Usage Tracking

`memory/asset-usage.md` tracks which reference images and video types were used per day to avoid repetition:

```
| Date | Persona | Reference Image | Screen Recording | App | Video Type |
```

---

## Cost Structure

| Component | Service | Cost |
|-----------|---------|------|
| Video clip (4s, Veo 3.1 Fast) | Replicate | ~$0.60 |
| Text generation | Anthropic Claude API | ~$0.01 |
| Assembly + upload | ffmpeg + rclone | Free |
| **Total per reel** | | **~$0.61** |
| **Daily total (3 reels)** | | **~$1.83** |

### Daily Spending Cap

Default: $5.00/day. Tracked in `logs/daily_spend.json`. Pipeline checks before each Replicate call and skips the run if it would exceed the limit.

Override: `export DAILY_COST_CAP=10.00` in `.env`

---

## Cron Schedule

```cron
# Video autopilot — daily at 12 PM IST (6:30 AM UTC)
# Generates 3 reels: sanya (ManifestLock) + sophie (JournalLock) + aliyah (random app)
# Video type rotates automatically: original → ugc_lighting → outdoor
30 6 * * * /root/openclaw/scripts/autopilot_video_cron.sh >> /root/openclaw/logs/cron.log 2>&1
```

### Manual Run

```bash
cd /root/openclaw
source .venv/bin/activate

# Full run — all 3 personas (auto-rotated video type)
python3 scripts/autopilot_video.py --persona all

# Single persona
python3 scripts/autopilot_video.py --persona aliyah

# Override video type (bypass daily rotation)
python3 scripts/autopilot_video.py --persona sanya --video-type ugc_lighting
python3 scripts/autopilot_video.py --persona all --video-type outdoor

# Dry run (text only, no video/cost)
python3 scripts/autopilot_video.py --persona all --dry-run

# Skip Drive upload
python3 scripts/autopilot_video.py --persona sanya --no-upload

# Use existing clips (skip Replicate)
python3 scripts/autopilot_video.py --persona sophie --skip-gen
```

---

## CLI Reference

### autopilot_video.py

| Argument | Required | Options | Description |
|----------|----------|---------|-------------|
| `--persona` | Yes | `sanya`, `sophie`, `aliyah`, `both`, `all` | Which persona(s) to generate for |
| `--video-type` | No | `original`, `ugc_lighting`, `outdoor` | Override daily rotation with a specific video type |
| `--dry-run` | No | — | Plan only, skip video generation |
| `--no-upload` | No | — | Build reel but skip Google Drive upload |
| `--skip-gen` | No | — | Use existing clips, skip Replicate |

### assemble_video.py

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--hook-clip` | Yes | — | Path to hook/opening clip |
| `--screen-recording` | Yes | — | Path to screen recording clip |
| `--reaction-clip` | Yes | — | Path to closing reaction clip |
| `--hook-text` | Yes | — | Text overlay for Part 1 |
| `--reaction-text` | Yes | — | Text overlay for Part 3 |
| `--speed` | No | `2.5` | Speed multiplier for screen recording (1 = no change) |
| `--output` | No | Auto | Output path (auto-generated with persona + video type) |
| `--font` | No | Auto | Path to font file |
| `--no-upload` | No | `False` | Skip Google Drive upload |
| `--dry-run` | No | `False` | Print commands without executing |

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...       # Claude API for text generation
REPLICATE_API_TOKEN=r8_...         # Replicate for Veo 3.1 Fast
OPENAI_API_KEY=sk-proj-...         # GPT Image (slideshow pipeline only)
SMTP_USER=email@gmail.com          # Gmail for notifications
SMTP_PASS=xxxx xxxx xxxx xxxx      # Gmail app password
DELIVERY_EMAIL=email1,email2       # Notification recipients
DAILY_COST_CAP=5.00                # Optional: daily spending cap override
```

---

## Adding New Content

### New Reference Images (Original Type)
1. Create images of the persona in different settings
2. Name as `{persona}-v{N}.png` or `.jpg`/`.jpeg` (e.g., `aliyah-v5.png`)
3. Place in `assets/reference-images/`
4. Pipeline automatically includes them in random rotation

### New Reference Images (UGC/Outdoor Types)
1. Create a single image per persona for the type
2. Name as `{persona}-ugc.*` or `{persona}-outdoor.*`
3. Place in `assets/reference-images/` (flat directory, no subdirectories)

### New Video Types
1. Add the type name to `VIDEO_TYPES` list
2. Add the prompt to `VIDEO_PROMPTS` dict
3. Add split points to `CLIP_SPLIT_POINTS` dict
4. Add reference images as `{persona}-{type_tag}.*`
5. Update `pick_reference_image()` suffix map
6. Update `--video-type` choices in argparse

### New Screen Recordings
1. Record app demo on device, edit/trim as needed
2. Place in `assets/screen-recordings/{manifest-lock|journal-lock}/`
3. Pipeline randomly picks from all recordings in the directory

### New Personas
1. Add entry to `PERSONAS` dict in `autopilot_video.py` with app mapping
2. Add reference images for all 3 video types to `assets/reference-images/`
3. Update `--persona` choices in argparse
4. Update cron persona list if needed

### New Action Variations (Original Type Only)
Edit the `ACTIONS` list in `autopilot_video.py` to add new facial expression descriptions.

---

## VPS Setup

**Server**: Hostinger VPS at 72.60.204.30 (Ubuntu)

### Dependencies
```bash
apt install ffmpeg
cd /root/openclaw
python3 -m venv .venv
source .venv/bin/activate
pip install replicate requests python-dotenv httpx
```

### Deploy from local Mac
```bash
rsync -avz -e ssh --exclude '.venv/' --exclude 'video_output/' --exclude 'output/' --exclude '__pycache__/' --exclude '.git/' --exclude 'logs/' --exclude '.DS_Store' ~/openclaw/ root@72.60.204.30:/root/openclaw/
```

### Font Installation
```bash
cd /root/openclaw/fonts
wget https://github.com/vercel/geist-font/releases/download/1.4.01/Geist-v1.4.01.zip
unzip Geist-v1.4.01.zip
cp Geist-v1.4.01/otf/Geist-Regular.otf Geist-v1.4.01/otf/Geist-Bold.otf .
rm -rf Geist-v1.4.01 __MACOSX Geist-v1.4.01.zip
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `DAILY CAP HIT` in logs | Spending limit reached | Wait until tomorrow or increase `DAILY_COST_CAP` |
| Replicate timeout | Veo generation >10min | Usually transient; cron retries next day |
| `No reference images found` | Missing images for video type | Check `assets/reference-images/` has images matching the type pattern |
| `No screen recordings` | Missing app demos | Add `.mp4` to `assets/screen-recordings/{app}/` |
| Veo E005 "flagged as sensitive" | Replicate content filter triggered | Soften prompt language; avoid "lock identity", "photorealistic", "no morphing" |
| rclone upload failed | Auth token expired | `rclone config reconnect gdrive:` on VPS |
| Text overlay not visible | Font missing | Install Geist-Regular.otf to `fonts/` |
| Wrong aspect ratio | Veo default is 16:9 | Ensure `aspect_ratio: "9:16"` in `generate_video()` |
| Character looks different | Prompt overriding image | Prompt should NOT describe appearance, only action |
| Only 2 reels generated | VPS has old `--persona both` | Re-sync scripts to VPS |
| Email not sent | Gmail credentials wrong | Check `SMTP_USER` and `SMTP_PASS` in `.env` |
