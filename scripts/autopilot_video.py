#!/usr/bin/env python3
"""
Video Autopilot (Full Pipeline) — ManifestLock + JournalLock

End-to-end automated reel generation:
1. Pick random reference image variant (pre-made backgrounds)
2. Generate video clip via Replicate (Google Veo 3.1 Fast)
3. Claude API generates hook + reaction text overlays
4. assemble_video.py stitches final reel
5. rclone uploads to Google Drive
6. Email notification with caption

Usage:
  python3 autopilot_video.py --persona sanya          # ManifestLock reel
  python3 autopilot_video.py --persona sophie          # JournalLock reel
  python3 autopilot_video.py --persona riley          # Both apps (like aliyah)
  python3 autopilot_video.py --persona both            # One reel for each (sanya+sophie)
  python3 autopilot_video.py --persona all             # All personas
  python3 autopilot_video.py --persona sanya --dry-run # Plan only
  python3 autopilot_video.py --persona sanya --no-upload
  python3 autopilot_video.py --persona sanya --skip-gen
  python3 autopilot_video.py --persona sanya --video-type ugc_lighting  # Override rotation
"""

import argparse
import json
import logging
import os
import random
import re
import requests
import smtplib
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

# ─── Config ──────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent  # /root/openclaw
SCRIPTS_DIR = BASE_DIR / "scripts"
SKILLS_DIR = BASE_DIR / "skills"
MEMORY_DIR = BASE_DIR / "memory"
LOGS_DIR = BASE_DIR / "logs"
CLIPS_DIR = BASE_DIR / "assets"
REF_IMAGES_DIR = BASE_DIR / "assets" / "reference-images"
SCREEN_REC_BASE = BASE_DIR / "assets" / "screen-recordings"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "")

GMAIL_USER = os.environ.get("GMAIL_USER") or os.environ.get("SMTP_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD") or os.environ.get("SMTP_PASS", "")
NOTIFY_EMAILS = (os.environ.get("NOTIFY_EMAILS") or os.environ.get("DELIVERY_EMAIL", "")).split(",")

MEMORY_FILES = ["post-performance.md", "failure-log.md", "asset-usage.md", "x-trends.md"]


def get_skill_files_for_persona(persona: str, app: str) -> list[str]:
    """Return graph-based skill files for a persona + app combination."""
    return [
        "INDEX.md",
        f"{app}.md",
        f"personas/{persona}.md",
        "content/content-mix.md",
        "content/hook-architecture.md",
        "content/text-overlays.md",
        "content/caption-formulas.md",
        "content/what-never-works.md",
        "analytics/proven-hooks.md",
    ]

# ─── Daily spending cap ──────────────────────────────
DAILY_COST_CAP = float(os.environ.get("DAILY_COST_CAP", "5.00"))  # $5/day default
COST_LEDGER = LOGS_DIR / "daily_spend.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("video-autopilot")


def check_daily_spend(estimated_cost):
    """Check if this run would exceed the daily spending cap. Returns (ok, spent_today)."""
    today = datetime.now().strftime("%Y-%m-%d")
    ledger = {}
    if COST_LEDGER.exists():
        ledger = json.loads(COST_LEDGER.read_text())
    spent = ledger.get(today, 0.0)
    if spent + estimated_cost > DAILY_COST_CAP:
        return False, spent
    return True, spent


def record_spend(amount):
    """Record a cost entry for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    LOGS_DIR.mkdir(exist_ok=True)
    ledger = {}
    if COST_LEDGER.exists():
        ledger = json.loads(COST_LEDGER.read_text())
    ledger[today] = ledger.get(today, 0.0) + amount
    COST_LEDGER.write_text(json.dumps(ledger, indent=2))
    log.info(f"  Daily spend: ${ledger[today]:.2f} / ${DAILY_COST_CAP:.2f} cap")


# ─── Persona Definitions ──────────────────────────────

# Each persona maps to one or more apps. Multi-app personas pick randomly each run.
PERSONAS = {
    "sanya": {
        "apps": [("Manifest Lock", "manifest-lock")],
    },
    "sophie": {
        "apps": [("Journal Lock", "journal-lock")],
    },
    "aliyah": {
        "apps": [("Manifest Lock", "manifest-lock"), ("Journal Lock", "journal-lock")],
    },
    "olivia": {
        "apps": [("Manifest Lock", "manifest-lock")],
        "video_type": "olivia_default",
    },
    "riley": {
        "apps": [("Manifest Lock", "manifest-lock"), ("Journal Lock", "journal-lock")],
        "video_type": "riley_default",
    },
}


ACTIONS = [
    "The woman immediately has her hand covering her mouth with wide surprised eyes and a gentle smile, eyes crinkling with amusement; she holds this pose, barely moving; camera holds perfectly steady with very subtle zoom in. The key expression happens in the first 2 seconds.",
    "The woman is already smiling warmly looking directly into the camera, slight head tilt, relaxed and happy; she holds this natural smile pose; camera holds steady. The key expression is visible from the very first frame.",
    "The woman starts looking into camera with wide-eyed curiosity; eyebrows raise, mouth opens slightly as expression shifts to genuine happy shock; one hand comes up to cover her mouth; eyes widen further in wonder; smile gradually breaks through behind hand.",
    "The woman looks at the camera with a calm expression, then her eyes light up. Her lips part into a slow, genuine smile. She lets out a small, silent laugh and shakes her head in disbelief.",
    "The woman starts with a neutral expression looking at the camera. Slowly her eyebrows rise, eyes widen with surprise, then she breaks into an excited grin and does a small fist pump or excited hand gesture. The reaction feels spontaneous and unscripted.",
]


# ─── Video Type Rotation ─────────────────────────────

VIDEO_TYPES = ["original", "ugc_lighting", "outdoor"]

VIDEO_PROMPTS = {
    "original": None,  # Built dynamically via build_video_prompt() with randomized ACTIONS
    "ugc_lighting": """No subtitles. No captions. No music.

The woman in the image must look EXACTLY as she appears — same face, same hair, same clothing, same background, same everything. Do not change anything.

SHOT — Vertical 9:16, medium close-up from mid-chest up. Static camera with very subtle movement synced to natural light shifts.

SCENE — Indoor room with warm golden afternoon sunlight through window blinds. Shadow stripes across the scene. Warm tones with subtle light angle shift.

ACTION AND CAMERA MOTION:
- 0–0.8s: Playful stare at camera, hand near face.
- 0.8–1.5s: Eyes widen slightly, hint of a smirk.
- 1.5–2.5s: Hand lowers to reveal a genuine smile.
- 2.5–4s: Soft laugh with gentle head movement. Hair sways lightly.
Camera stays steady with very slight zoom-in.

STYLE — Cinematic quality 4K vertical video. Warm golden color palette with natural lighting. No text overlays, subtitles, or captions.""",
    "outdoor": """No subtitles. No music.

The woman in the image must look EXACTLY as she appears — same face, same hair, same clothing, same background, same everything. Do not change anything.

SHOT — Vertical 9:16, medium close-up. Outdoor natural lighting.

ACTION AND CAMERA MOTION:
- 0–1.0s: Relaxed smile, minimal motion, natural micro movements.
- 1.0–2.2s: Energy builds, smile widens, shoulders lift slightly, leans forward subtly.
- 2.2–3.2s: Right arm lifts upward in celebration, joyful expression, head tilts slightly.
- 3.2–4.0s: Holds celebratory pose, wide smile, arm extended upward.

Keep the same outdoor background throughout. Keep lighting consistent. Keep motion natural and realistic.

STYLE — Naturalistic aesthetic with sharp 4K clarity, vibrant colors. No text overlays or subtitles.""",
    "olivia_default": """No subtitles. No captions. No music.

The woman in the image must look EXACTLY as she appears — same face, same hair, same clothing, same everything. Do not change anything.

SHOT — Vertical 9:16, medium close-up from waist up. Slow tracking shot following her from the side or slightly behind.

SCENE — Outdoor golden hour, walking along a quiet tree-lined path or park trail. Warm sunlight filtering through leaves. Soft bokeh background.

ACTION AND CAMERA MOTION:
- 0–1.5s: Walking naturally, calm expression, looking slightly ahead. Hair moves softly with the breeze.
- 1.5–3.0s: Slight turn toward camera, subtle confident smile, keeps walking.
- 3.0–4.0s: Looks forward again, peaceful and grounded. Camera holds steady tracking shot.

No talking. No exaggerated expressions. Calm confidence, quiet purpose.

STYLE — Cinematic 4K vertical video. Golden hour color palette, warm amber tones, natural lighting. No text overlays, subtitles, or captions.""",
    "riley_default": """No subtitles. No captions. No music.

The woman in the image must look EXACTLY as she appears — same face, same hair, same clothing, same everything. Do not change anything.

SHOT — Vertical 9:16, medium side angle from waist up. Static camera, no zoom, no movement.

SCENE — Indoor study room. Sitting cross-legged on a cushioned armchair with a laptop on a small desk in front. Soft neutral indoor lighting, no golden-hour tint.

ACTION AND CAMERA MOTION:
- 0–1s: She types lightly on the laptop. Neutral focused expression.
- 1–2.5s: Subtle pause. Small eye movement toward screen. Slight shift in expression.
- 2.5–4s: Slight posture adjustment. Very small head tilt. Natural breathing visible.
Camera stays completely static throughout.

No talking. No lip movement. No exaggerated gestures.

STYLE — Naturalistic aesthetic with sharp 4K clarity, natural indoor tones. No text overlays, subtitles, or captions.""",
}

CLIP_SPLIT_POINTS = {
    "original": {
        "hook": {"start": 0, "duration": 3},
        "reaction": {"start": 0, "duration": 2},
    },
    "ugc_lighting": {
        "hook": {"start": 0, "duration": 2.5},
        "reaction": {"start": 2, "duration": 2},
    },
    "outdoor": {
        "hook": {"start": 0, "duration": 2.2},
        "reaction": {"start": 2.2, "duration": 1.8},
    },
    "olivia_default": {
        "hook": {"start": 0, "duration": 4},
        "reaction": None,
    },
    "riley_default": {
        "hook": {"start": 0, "duration": 2.5},
        "reaction": {"start": 2, "duration": 2},
    },
}


def pick_video_type():
    """Rotate video type daily: day 1 = original, day 2 = ugc_lighting, day 3 = outdoor, repeat."""
    day_of_year = datetime.now().timetuple().tm_yday
    return VIDEO_TYPES[day_of_year % 3]


def pick_reference_image(persona_name, video_type="original"):
    """Pick a reference image for this persona and video type.

    - original: Random selection from {persona}-v*.{png,jpeg,jpg}
    - ugc_lighting: Single file {persona}-ugc.{png,jpeg,jpg}
    - outdoor: Single file {persona}-outdoor.{png,jpeg,jpg}
    """
    if video_type in ("original", "olivia_default", "riley_default"):
        variants = sorted(
            f for f in REF_IMAGES_DIR.iterdir()
            if f.is_file() and f.name.startswith(f"{persona_name}-v") and f.suffix.lower() in (".png", ".jpg", ".jpeg")
        )
        if not variants:
            raise FileNotFoundError(f"No reference images found matching {REF_IMAGES_DIR}/{persona_name}-v*")
        choice = random.choice(variants)
    else:
        suffix_map = {"ugc_lighting": "ugc", "outdoor": "outdoor"}
        tag = suffix_map[video_type]
        matches = sorted(
            f for f in REF_IMAGES_DIR.iterdir()
            if f.is_file() and f.stem == f"{persona_name}-{tag}" and f.suffix.lower() in (".png", ".jpg", ".jpeg")
        )
        if not matches:
            raise FileNotFoundError(f"No reference image found matching {REF_IMAGES_DIR}/{persona_name}-{tag}.*")
        choice = matches[0]
    log.info(f"  Reference image: {choice.name}")
    return choice


def build_video_prompt(video_type="original"):
    """Build a video prompt for the given video type.

    - original: Randomized action + style (existing behavior)
    - ugc_lighting / outdoor: Fixed prompts from VIDEO_PROMPTS
    """
    if video_type != "original":
        return VIDEO_PROMPTS[video_type]

    action = random.choice(ACTIONS)

    prompt = f"""No subtitles. No music.

The woman in the image must look EXACTLY as she appears — same face, same hair, same clothing, same background, same everything. Do not change anything about the image.

SHOT — Medium close-up, centered on the woman's face and upper body.

ACTION AND CAMERA MOTION — {action}

AUDIO — No dialogue. No music. Ambient room tone only.

STYLE — Naturalistic aesthetic with sharp 4K clarity, vibrant colors; no text overlays, subtitles, or captioning."""

    return prompt


# ─── AI Clip Generation (Replicate) ─────────────────


def generate_video(image_url, video_prompt, engine="veo"):
    """Generate video from image via Replicate (Veo or Seedance)."""
    import replicate
    import httpx

    if engine == "seedance":
        model_id = "bytedance/seedance-1.5-pro"
        log.info("Generating video (Seedance 1.5 Pro, ~2-5min)...")
        client = replicate.Client(
            api_token=REPLICATE_API_TOKEN,
            timeout=httpx.Timeout(900, connect=30),
        )
        output = client.run(
            model_id,
            input={
                "prompt": video_prompt,
                "input_urls": [image_url],
                "aspect_ratio": "9:16",
                "resolution": "720p",
                "duration": 4,
                "generate_audio": False,
                "fixed_lens": False,
            },
        )
    else:
        model_id = "google/veo-3.1-fast"
        log.info("Generating video (Google Veo 3.1 Fast, ~1-3min)...")
        client = replicate.Client(
            api_token=REPLICATE_API_TOKEN,
            timeout=httpx.Timeout(600, connect=30),
        )
        output = client.run(
            model_id,
            input={
                "prompt": video_prompt,
                "image": image_url,
                "duration": 4,
                "aspect_ratio": "9:16",
                "generate_audio": False,
            },
        )
    url = output.url
    log.info(f"  Video ready ({model_id})")
    return url


def download_file(url, output_path):
    """Download a file from URL."""
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    log.info(f"  Downloaded: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def trim_clip(input_path, duration_seconds):
    """Trim a clip to the first N seconds using ffmpeg."""
    trimmed_path = input_path.with_stem(input_path.stem + "_trimmed")
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(input_path),
            "-t", str(duration_seconds),
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an",
            str(trimmed_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode == 0 and trimmed_path.exists():
        log.info(f"  Trimmed to {duration_seconds}s: {trimmed_path.name}")
        input_path.unlink()
        trimmed_path.rename(input_path)
        return input_path
    log.warning(f"  Trim failed, keeping original")
    return input_path


def get_clip_split_points(video_type):
    """Return split points for a video type: {hook: {start, duration}, reaction: {start, duration}}."""
    return CLIP_SPLIT_POINTS[video_type]


def generate_clips(persona_name, video_type="original", ref_image=None, engine="veo"):
    """Generate fresh hook + reaction clips via Replicate.

    Flow: upload reference image → generate a single 4s clip (Veo or Seedance) →
    split into hook + reaction using type-specific split points.

    Returns (hook_clip_path, reaction_clip_path).
    """
    import replicate

    if not REPLICATE_API_TOKEN:
        raise RuntimeError("REPLICATE_API_TOKEN not set in .env — cannot generate AI clips")

    persona_dir = CLIPS_DIR / persona_name
    hook_dir = persona_dir / "hook"
    reaction_dir = persona_dir / "reaction"
    hook_dir.mkdir(parents=True, exist_ok=True)
    reaction_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Upload reference image
    if ref_image is None:
        ref_image = pick_reference_image(persona_name, video_type)
    log.info(f"Uploading reference image: {ref_image.name}")
    image_url = replicate.files.create(ref_image).urls["get"]
    log.info(f"  Uploaded to Replicate storage")

    # 2. Generate ONE video clip → split using type-specific split points
    log.info(f"--- Generating clip (engine={engine}, type={video_type}) ---")
    video_prompt = build_video_prompt(video_type)
    video_url = generate_video(image_url, video_prompt, engine=engine)
    raw_path = hook_dir / f"{ts}_raw.mp4"
    download_file(video_url, raw_path)

    splits = get_clip_split_points(video_type)

    # Hook clip
    hook_split = splits["hook"]
    hook_path = hook_dir / f"{ts}.mp4"
    hook_cmd = ["ffmpeg", "-y"]
    if hook_split["start"] > 0:
        hook_cmd += ["-ss", str(hook_split["start"])]
    hook_cmd += ["-i", str(raw_path), "-t", str(hook_split["duration"]),
                 "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an", str(hook_path)]
    subprocess.run(hook_cmd, capture_output=True)
    log.info(f"  Hook clip: {hook_path.name} ({hook_split['duration']}s)")

    # Reaction clip (optional — None for hook-only formats like olivia_default)
    react_split = splits["reaction"]
    reaction_path = None
    if react_split is not None:
        reaction_path = reaction_dir / f"{ts}.mp4"
        react_cmd = ["ffmpeg", "-y"]
        if react_split["start"] > 0:
            react_cmd += ["-ss", str(react_split["start"])]
        react_cmd += ["-i", str(raw_path), "-t", str(react_split["duration"]),
                      "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-an", str(reaction_path)]
        subprocess.run(react_cmd, capture_output=True)
        log.info(f"  Reaction clip: {reaction_path.name} ({react_split['duration']}s)")

    # Clean up raw
    raw_path.unlink(missing_ok=True)

    if reaction_path:
        log.info(f"Clips saved: {hook_path.name}, {reaction_path.name}")
    else:
        log.info(f"Clip saved: {hook_path.name} (hook only)")
    return hook_path, reaction_path


# ─── Asset helpers ───────────────────────────────────

def find_clips(directory, extensions=(".mp4", ".mov")):
    """Find all video clips in a directory."""
    if not directory.exists():
        return []
    return sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in extensions and not f.name.startswith(".")
    )


def pick_screen_recording(screen_rec_dir):
    """Randomly select a screen recording from the given directory."""
    rec_dir = SCREEN_REC_BASE / screen_rec_dir
    recs = find_clips(rec_dir)
    if not recs:
        raise FileNotFoundError(f"No screen recordings in {rec_dir}")
    choice = random.choice(recs)
    log.info(f"Screen rec: {choice.name}")
    return choice


# ─── Context loading ─────────────────────────────────

def load_context(persona: str = "sanya", app: str = "manifest-lock"):
    """Load skill + memory files as context for Claude."""
    parts = []
    for name in get_skill_files_for_persona(persona, app):
        path = SKILLS_DIR / name
        if path.exists():
            parts.append(f"=== SKILL: {name} ===\n{path.read_text()}")
    for name in MEMORY_FILES:
        path = MEMORY_DIR / name
        if path.exists():
            content = path.read_text().strip()
            if content:
                parts.append(f"=== MEMORY: {name} ===\n{content}")
    return "\n\n".join(parts)


# ─── Text generation via Claude ──────────────────────

def generate_text(context, persona_name, app_name):
    """Call Claude API to generate hook + reaction text."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    APP_DESCRIPTIONS = {
        "Manifest Lock": "an iOS app that makes you write a daily manifestation before unlocking your phone. It replaces doomscrolling with intentional goal-setting.",
        "Journal Lock": "an iOS app that makes you journal before unlocking your phone. It replaces doomscrolling with daily self-reflection and emotional check-ins.",
    }

    # Olivia uses a hook-only format (no reaction clip)
    if persona_name == "olivia":
        system = f"""You are the {app_name} content engine. You generate short text overlays for UGC-style TikTok/Instagram Reels.

The app: {app_name} is {APP_DESCRIPTIONS[app_name]}

The video format (hook + screen recording only, NO reaction clip):
- Part 1 (hook clip): Woman walking outdoors at golden hour, calm confidence. YOUR hook text appears below her.
- Part 2 (screen recording): App demo plays. No text overlay.

Olivia's voice: Anti-woo. Zero fluff. "Wrote it down, did the work, it happened." Low words, high proof. She doesn't convince — she states. Calm, grounded, matter-of-fact.

Rules:
- hook_text: First-person statement or quiet flex. Max 50 characters. Understated confidence, not hype.
- Voice: Millennial woman, direct, no filler, no emojis in overlays
- Never mention the app name in text overlays
- Every hook implies proof without explaining it
- Vary angles: quiet result, daily ritual, undeniable proof, calm flex

Also generate a caption (first-person, minimal, soft CTA, max 5 hashtags).

Respond ONLY with valid JSON, no markdown fences:
{{
  "hook_text": "...",
  "caption": "...",
  "content_angle": "quiet_result|daily_ritual|proof|calm_flex"
}}"""
    else:
        system = f"""You are the {app_name} content engine. You generate short text overlays for UGC-style TikTok/Instagram Reels.

The app: {app_name} is {APP_DESCRIPTIONS[app_name]}

The video format:
- Part 1 (hook clip): AI girl looking at camera. YOUR hook text appears below her face.
- Part 2 (screen recording): App demo plays. No text overlay.
- Part 3 (reaction clip): AI girl reacting. YOUR reaction text appears below her face.

Rules:
- hook_text: First-person POV or shocking statement. Max 50 characters. Must create curiosity or shock in under 2 seconds.
- reaction_text: Short reaction to the screen recording. Max 40 characters. Authentic, not salesy.
- Voice: Gen Z woman, casual, lowercase okay, authentic
- Never mention the app name in text overlays
- Every hook must create conflict, curiosity, or shock
- Vary angles: discovery, challenge, transformation, relatable struggle, shocking stat

Also generate a caption (first-person, story-style, soft CTA, max 5 hashtags).

Respond ONLY with valid JSON, no markdown fences:
{{
  "hook_text": "...",
  "reaction_text": "...",
  "caption": "...",
  "content_angle": "discovery|challenge|transformation|relatable|stat"
}}"""

    user_msg = f"""Generate hook_text and reaction_text for a {app_name} UGC reel.

Persona: {persona_name}
Today: {datetime.now().strftime('%A %B %d')}
Seed: {random.randint(1000, 9999)}

Context:
{context[:6000]}

Generate fresh, non-repetitive content. Avoid hooks from memory files."""

    log.info("Generating text via Claude API...")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user_msg}],
        },
        timeout=30,
    )
    resp.raise_for_status()

    raw = resp.json()["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]

    try:
        result = json.loads(raw.strip())
    except json.JSONDecodeError:
        # Claude sometimes produces unescaped quotes inside string values.
        # Extract fields with regex as a fallback.
        log.warning("JSON parse failed, attempting regex extraction...")
        def _extract(key: str) -> str:
            m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
            return m.group(1) if m else ""
        result = {
            "hook_text": _extract("hook_text"),
            "reaction_text": _extract("reaction_text"),
            "caption": _extract("caption"),
            "content_angle": _extract("content_angle") or "discovery",
        }
        if not result["hook_text"]:
            raise ValueError(f"Could not extract hook_text from Claude response: {raw[:200]}")

    # Normalize: ensure reaction_text exists for pipeline compat (empty for hook-only personas)
    if "reaction_text" not in result:
        result["reaction_text"] = ""
    if "content_angle" not in result:
        result["content_angle"] = "discovery"

    log.info(f"Hook:     {result['hook_text']}")
    if result["reaction_text"]:
        log.info(f"Reaction: {result['reaction_text']}")
    log.info(f"Angle:    {result.get('content_angle', 'unknown')}")
    return result


# ─── Video assembly ──────────────────────────────────

def assemble_video(hook_clip, screen_rec, reaction_clip, text, no_upload=False, persona_name=None, video_type=None):
    """Call assemble_video.py to stitch the final reel."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = ["reel"]
    if persona_name:
        parts.append(persona_name)
    if video_type:
        parts.append(video_type)
    parts.append(ts)
    output_name = "_".join(parts) + ".mp4"
    output_path = BASE_DIR / "video_output" / output_name

    cmd = [
        sys.executable, str(SCRIPTS_DIR / "assemble_video.py"),
        "--hook-clip", str(hook_clip),
        "--screen-recording", str(screen_rec),
        "--hook-text", text["hook_text"],
        "--speed", "1",
        "--output", str(output_path),
    ]
    if reaction_clip is not None:
        cmd += ["--reaction-clip", str(reaction_clip),
                "--reaction-text", text["reaction_text"]]
    if no_upload:
        cmd.append("--no-upload")

    log.info("Assembling video...")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))

    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            log.info(f"  {line}")
    if result.returncode != 0:
        raise RuntimeError(f"assemble_video.py failed: {result.stderr}")

    for line in result.stdout.split("\n"):
        if "Reel assembled:" in line:
            return Path(line.split("Reel assembled:")[1].strip().split(" ")[0])
    return None


# ─── Logging + Email ─────────────────────────────────

def save_log(persona, text, reel_path, cost, video_type="original"):
    """Append run to JSONL log."""
    LOGS_DIR.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "persona": persona,
        "video_type": video_type,
        "hook_text": text["hook_text"],
        "reaction_text": text["reaction_text"],
        "caption": text.get("caption", ""),
        "content_angle": text.get("content_angle", ""),
        "reel_path": str(reel_path) if reel_path else None,
        "cost_usd": cost,
    }
    with open(LOGS_DIR / "video_autopilot.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def update_asset_usage(persona, ref_image_name, screen_rec_name, app_name, video_type="original"):
    """Append an entry to memory/asset-usage.md for tracking."""
    path = MEMORY_DIR / "asset-usage.md"
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"| {today} | {persona} | {ref_image_name} | {screen_rec_name} | {app_name} | {video_type} |"

    if path.exists():
        content = path.read_text()
        # Append entry before the end of the file
        content = content.rstrip() + "\n" + entry + "\n"
        path.write_text(content)
    else:
        header = (
            "# Asset Usage Tracker\n\n"
            "## Recent Asset Usage\n\n"
            "| Date | Persona | Reference Image | Screen Recording | App | Video Type |\n"
            "|------|---------|-----------------|-----------------|-----|------------|\n"
            + entry + "\n"
        )
        path.write_text(header)


def send_notification(subject, body):
    """Send email notification."""
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, NOTIFY_EMAILS]):
        log.warning("Email not configured — skipping notification")
        return
    recipients = [e.strip() for e in NOTIFY_EMAILS if e.strip()]
    if not recipients:
        return
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        log.info("Email notification sent")
    except Exception as e:
        log.warning(f"Email failed: {e}")


# ─── Main ────────────────────────────────────────────

def run_persona(persona_name, dry_run=False, no_upload=False, skip_gen=False, video_type=None, app_filter=None, engine="veo"):
    """Run the full pipeline for a single persona. Multi-app personas generate one reel per app."""
    if video_type is None:
        # Check for persona-specific video_type override before daily rotation
        video_type = PERSONAS[persona_name].get("video_type") or pick_video_type()
    log.info(f"Video type: {video_type} (day {datetime.now().timetuple().tm_yday})")
    apps = PERSONAS[persona_name]["apps"]
    if app_filter:
        apps = [(name, d) for name, d in apps if d == app_filter]
        if not apps:
            available = [d for _, d in PERSONAS[persona_name]["apps"]]
            log.error(f"App '{app_filter}' not available for {persona_name}. Options: {available}")
            return
    for app_name, screen_rec_dir in apps:
        _run_persona_for_app(persona_name, app_name, screen_rec_dir, dry_run, no_upload, skip_gen, video_type, engine=engine)


def _run_persona_for_app(persona_name, app_name, screen_rec_dir, dry_run=False, no_upload=False, skip_gen=False, video_type="original", engine="veo"):
    """Run the full pipeline for a single persona + app combination."""
    start_time = datetime.now()
    log.info("=" * 50)
    log.info(f"{app_name} — Video Autopilot ({persona_name}, type={video_type})")
    log.info("=" * 50)

    cost = 0.0
    estimated_cost = 0.61  # 1 Veo clip (~$0.60) + Claude text (~$0.01)

    try:
        # 0. Check daily spending cap
        ok, spent = check_daily_spend(estimated_cost)
        if not ok and not dry_run:
            log.error(f"DAILY CAP HIT: ${spent:.2f} spent today, cap is ${DAILY_COST_CAP:.2f}. "
                      f"Skipping run. Set DAILY_COST_CAP env var to override.")
            return
        if not dry_run:
            log.info(f"Daily spend: ${spent:.2f} / ${DAILY_COST_CAP:.2f} cap")

        # 1. Pick screen recording for this app
        log.info(f"Persona: {persona_name} ({app_name})")
        screen_rec = pick_screen_recording(screen_rec_dir)

        # 1b. Preview reference image selection (for logging)
        ref_image = pick_reference_image(persona_name, video_type)

        # 2. Generate text (~$0.01)
        context = load_context(persona=persona_name, app=screen_rec_dir)
        text = generate_text(context, persona_name, app_name)
        cost += 0.01

        if dry_run:
            splits = get_clip_split_points(video_type)
            log.info(f"\n[DRY RUN] Would generate AI clip + assemble reel")
            log.info(f"  App:        {app_name}")
            log.info(f"  Video type: {video_type}")
            log.info(f"  Ref image:  {ref_image.name}")
            log.info(f"  Hook:       \"{text['hook_text']}\"")
            if text.get("reaction_text"):
                log.info(f"  Reaction:   \"{text['reaction_text']}\"")
            log.info(f"  Screen:     {screen_rec.name}")
            log.info(f"  Hook split: {splits['hook']['duration']}s from {splits['hook']['start']}s")
            if splits["reaction"] is not None:
                log.info(f"  React split: {splits['reaction']['duration']}s from {splits['reaction']['start']}s")
            else:
                log.info(f"  React split: (none — hook-only format)")
            log.info(f"  Caption:    {text.get('caption', 'N/A')[:100]}...")
            log.info(f"  Est cost:   ~$0.61 (skipped)")
            save_log(persona_name, text, None, cost, video_type)
            update_asset_usage(persona_name, ref_image.name, screen_rec.name, app_name, video_type)
            return

        # 3. Generate or pick clips
        splits = get_clip_split_points(video_type)
        needs_reaction = splits["reaction"] is not None

        if skip_gen:
            persona_dir = CLIPS_DIR / persona_name
            hooks = find_clips(persona_dir / "hook")
            if not hooks:
                raise FileNotFoundError(f"No existing hook clips for {persona_name}")
            hook_clip = random.choice(hooks)
            reaction_clip = None
            if needs_reaction:
                reactions = find_clips(persona_dir / "reaction")
                if not reactions:
                    raise FileNotFoundError(f"No existing reaction clips for {persona_name}")
                reaction_clip = random.choice(reactions)
                log.info(f"Using existing: {hook_clip.name}, {reaction_clip.name}")
            else:
                log.info(f"Using existing: {hook_clip.name} (hook only)")
        else:
            hook_clip, reaction_clip = generate_clips(persona_name, video_type, ref_image=ref_image, engine=engine)
            cost += 0.60  # 1 video clip (4s)
            record_spend(cost)

        # 4. Assemble
        reel_path = assemble_video(hook_clip, screen_rec, reaction_clip, text, no_upload=no_upload, persona_name=persona_name, video_type=video_type)

        # 5. Log + notify
        save_log(persona_name, text, reel_path, cost, video_type)
        update_asset_usage(persona_name, ref_image.name, screen_rec.name, app_name, video_type)
        elapsed = (datetime.now() - start_time).total_seconds()

        send_notification(
            subject=f"New {app_name} Reel — {persona_name.upper()} ({reel_path.name if reel_path else '?'})",
            body=(
                f"New reel ready!\n\n"
                f"App: {app_name}\n"
                f"Persona: {persona_name}\n"
                f"Video type: {video_type}\n"
                f"Hook: {text['hook_text']}\n"
                f"Reaction: {text['reaction_text']}\n"
                f"File: {reel_path.name if reel_path else 'N/A'}\n"
                f"Time: {elapsed:.0f}s\n"
                f"Cost: ~${cost:.2f}\n\n"
                f"Caption:\n{text.get('caption', 'N/A')}\n\n"
                f"Google Drive → manifest-social-videos\n"
            ),
        )
        log.info(f"\nDone in {elapsed:.0f}s. Cost: ~${cost:.2f}")

    except Exception as e:
        log.error(f"Pipeline failed for {persona_name}: {e}")
        elapsed = (datetime.now() - start_time).total_seconds()
        send_notification(
            subject=f"{app_name} Reel FAILED ({persona_name})",
            body=f"Failed after {elapsed:.0f}s\n\nError: {e}\n\n{traceback.format_exc()}",
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video autopilot for ManifestLock + JournalLock")
    parser.add_argument("--persona", required=True,
                        help="sanya, sophie, aliyah, both, all, or comma-separated list (e.g. sanya,aliyah)")
    parser.add_argument("--video-type", choices=["original", "ugc_lighting", "outdoor", "olivia_default", "riley_default"],
                        help="Override daily rotation with a specific video type")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, skip generation")
    parser.add_argument("--no-upload", action="store_true", help="Build but skip Drive upload")
    parser.add_argument("--skip-gen", action="store_true", help="Use existing clips, skip Replicate")
    parser.add_argument("--app", choices=["manifest-lock", "journal-lock"],
                        help="Run only this app (useful for multi-app personas like aliyah)")
    parser.add_argument("--engine", choices=["veo", "seedance"], default="veo",
                        help="Video generation engine (default: veo)")
    args = parser.parse_args()

    # Resolve video type: CLI override or daily rotation
    video_type = args.video_type  # None means pick_video_type() will be called in run_persona

    valid_personas = {"sanya", "sophie", "aliyah", "olivia", "riley"}
    if args.persona == "both":
        personas = ["sanya", "sophie"]
    elif args.persona == "all":
        personas = ["sanya", "sophie", "aliyah", "olivia", "riley"]
    elif "," in args.persona:
        personas = [p.strip() for p in args.persona.split(",") if p.strip()]
        bad = [p for p in personas if p not in valid_personas]
        if bad:
            parser.error(f"Unknown persona(s): {', '.join(bad)}")
    else:
        if args.persona not in valid_personas:
            parser.error(f"Unknown persona: {args.persona}")
        personas = [args.persona]
    for p in personas:
        run_persona(p, dry_run=args.dry_run, no_upload=args.no_upload, skip_gen=args.skip_gen, video_type=video_type, app_filter=args.app, engine=args.engine)
