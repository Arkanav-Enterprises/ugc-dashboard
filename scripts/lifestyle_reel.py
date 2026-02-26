#!/usr/bin/env python3
"""
lifestyle_reel.py — Generate lifestyle image reels for Journal Lock.

3-scene format: lifestyle image + hook → lifestyle image + response → screen recording + payoff.
No AI video generation — just images, text overlays, and ffmpeg. ~$0.01 per reel.

Usage:
    python3 scripts/lifestyle_reel.py                    # Full run
    python3 scripts/lifestyle_reel.py --dry-run          # Text only, no video
    python3 scripts/lifestyle_reel.py --no-upload        # Skip Google Drive upload
    python3 scripts/lifestyle_reel.py --scene-1-text "..." --scene-2-text "..." --scene-3-text "..."
"""

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, date
from pathlib import Path

# ─── Config ──────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)
SKILLS_DIR = PROJECT_ROOT / "skills"
MEMORY_DIR = PROJECT_ROOT / "memory"
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "video_output"
LOGS_DIR = PROJECT_ROOT / "logs"
FONT_DIR = PROJECT_ROOT / "fonts"
GDRIVE_FOLDER = "manifest-social-videos"

LIFESTYLE_IMAGES_DIR = ASSETS_DIR / "lifestyle-images" / "journal-lock"
SCREEN_RECORDINGS_DIR = ASSETS_DIR / "screen-recordings" / "journal-lock"

WIDTH, HEIGHT, FPS = 1080, 1920, 30
BITRATE = "8000k"
SCENE_1_DURATION = 4.0
SCENE_2_DURATION = 2.5
SCENE_3_MAX_DURATION = 12

# ─── Font resolution ─────────────────────────────────

def find_font(bold=True):
    """Find the best available font."""
    candidates = [
        FONT_DIR / ("Geist-Bold.otf" if bold else "Geist-Regular.otf"),
        FONT_DIR / "Geist-Bold.otf",
        FONT_DIR / "Geist-Regular.otf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return str(p.resolve())
    print("ERROR: No font found. Install Geist-Bold.otf to fonts/")
    sys.exit(1)


# ─── Text helpers ────────────────────────────────────

import re

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "\U00002600-\U000026FF"  # misc symbols
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "]+", flags=re.UNICODE
)


def strip_emojis(text):
    """Remove emoji characters that ffmpeg drawtext can't render."""
    return _EMOJI_RE.sub("", text).strip()


def escape_drawtext(text):
    """Escape special chars for ffmpeg drawtext filter."""
    text = strip_emojis(text)
    text = text.replace("'", "\u2019")
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace(";", "\\;")
    text = text.replace('"', '\\"')
    return text


def wrap_text(text, max_chars=28):
    """Word-wrap text into lines."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if len(test) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines


# ─── Asset selection ─────────────────────────────────

def list_images(scene: str) -> list[Path]:
    """List available lifestyle images for a scene (scene-1 or scene-2)."""
    prefix = f"{scene}-v"
    return sorted([
        f for f in LIFESTYLE_IMAGES_DIR.iterdir()
        if f.name.startswith(prefix) and f.suffix in (".png", ".jpg", ".jpeg")
    ])


def list_screen_recordings() -> list[Path]:
    """List available screen recordings."""
    return sorted([
        f for f in SCREEN_RECORDINGS_DIR.iterdir()
        if f.suffix in (".mp4", ".mov")
    ])


def load_lifestyle_usage() -> list[dict]:
    """Load recent lifestyle reel usage from log."""
    log_path = LOGS_DIR / "lifestyle_reel.jsonl"
    if not log_path.exists():
        return []
    entries = []
    for line in log_path.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


def pick_image(scene: str, recent_entries: list[dict]) -> Path:
    """Pick an image not recently used."""
    available = list_images(scene)
    if not available:
        print(f"ERROR: No {scene} images in {LIFESTYLE_IMAGES_DIR}")
        sys.exit(1)

    key = f"{scene.replace('-', '_')}_image"
    recent_used = {e.get(key, "") for e in recent_entries[-7:]}
    unused = [img for img in available if img.name not in recent_used]
    return random.choice(unused) if unused else random.choice(available)


def pick_screen_recording(recent_entries: list[dict]) -> Path:
    """Pick a screen recording."""
    available = list_screen_recordings()
    if not available:
        print(f"ERROR: No screen recordings in {SCREEN_RECORDINGS_DIR}")
        sys.exit(1)

    recent_used = {e.get("screen_recording", "") for e in recent_entries[-7:]}
    unused = [r for r in available if r.name not in recent_used]
    return random.choice(unused) if unused else random.choice(available)


# ─── Skill context ───────────────────────────────────

def load_skill_context() -> str:
    """Load skill files for Claude system prompt."""
    files = [
        "content/content-mix.md",
        "content/hook-architecture.md",
        "content/what-never-works.md",
        "journal-lock.md",
    ]
    parts = []
    for f in files:
        path = SKILLS_DIR / f
        if path.exists():
            parts.append(f"--- {f} ---\n{path.read_text()}")
    # Memory files
    for f in ["post-performance.md", "failure-log.md"]:
        path = MEMORY_DIR / f
        if path.exists():
            parts.append(f"--- memory/{f} ---\n{path.read_text()}")
    return "\n\n".join(parts)


# ─── Text generation ─────────────────────────────────

USER_PROMPT = """You are writing text overlays for a 3-scene TikTok/Reels video promoting Journal Lock — an iOS app that blocks distracting apps (Instagram, TikTok, X, Snapchat etc.) until you write a journal entry of at least 3 sentences. The reel is a mini-story told across 3 scenes:
- Scene 1: A HOOK — first-person statement that creates curiosity or relatability
- Scene 2: A RESPONSE — someone else's reaction or a follow-up that builds tension
- Scene 3: A PAYOFF — the reveal, showing what the app actually does

Rules:
- Gen Z woman voice, casual, authentic, lowercase okay
- NEVER mention the app name in any overlay text
- Scene 1 text: max 60 chars. First person, creates intrigue.
- Scene 2 text: max 40 chars. Dialogue or reaction in quotes, OR a short follow-up.
- Scene 3 text: max 50 chars. The "aha" reveal. Can include one emoji.
- The story should feel like a real conversation or situation, not an ad.
- Vary the angles: boyfriend/friend/roommate/mom reactions, personal discovery, challenge results, before/after moments

Return ONLY valid JSON:
{
  "scene_1_text": "...",
  "scene_2_text": "...",
  "scene_3_text": "...",
  "caption": "Story-style caption with soft CTA. Include 3-5 relevant hashtags. Max 150 chars.",
  "content_angle": "relatable|discovery|challenge|transformation|dialogue"
}"""


def generate_text(context: str) -> dict:
    """Call Claude to generate text overlays."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=f"You are the content engine for a lifestyle reel pipeline. Follow the rules in these skill files:\n\n{context}",
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


# ─── ffmpeg helpers ──────────────────────────────────

def run_ffmpeg(args, label=""):
    """Run ffmpeg. Returns True on success."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error ({label}): {result.stderr}")
        return False
    return True


def build_drawtext(text, font_path, font_size=48, y_ratio=0.45):
    """Build drawtext filter with black pill background."""
    escaped = escape_drawtext(text)
    lines = wrap_text(text)

    if len(lines) > 1:
        escaped = escape_drawtext("\n".join(lines))
        return (
            f"drawtext=fontfile='{font_path}'"
            f":text='{escaped}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":box=1"
            f":boxcolor=black@0.85"
            f":boxborderw=20"
            f":line_spacing=8"
            f":x=(w-text_w)/2"
            f":y=h*{y_ratio}-text_h/2"
        )
    else:
        return (
            f"drawtext=fontfile='{font_path}'"
            f":text='{escaped}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":box=1"
            f":boxcolor=black@0.85"
            f":boxborderw=20"
            f":x=(w-text_w)/2"
            f":y=h*{y_ratio}-text_h/2"
        )


def build_scene_image(image_path, text, output_path, duration, font_path,
                      font_size=48, y_ratio=0.45):
    """Build a scene from a static image with Ken Burns + text overlay."""
    total_frames = int(duration * FPS)
    drawtext = build_drawtext(text, font_path, font_size, y_ratio)

    # zoompan creates video from image, then text overlay, then normalize
    vf = (
        f"zoompan=z='1+0.05*on/{total_frames}'"
        f":x='iw/2-(iw/zoom/2)'"
        f":y='ih/2-(ih/zoom/2)'"
        f":d={total_frames}"
        f":s={WIDTH}x{HEIGHT}"
        f":fps={FPS}"
        f",{drawtext}"
        f",format=yuv420p"
    )

    return run_ffmpeg([
        "-loop", "1", "-i", str(image_path),
        "-vf", vf,
        "-t", str(duration),
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output_path),
    ], f"scene image {image_path.name}")


def build_scene_screen(recording_path, text, output_path, font_path,
                       max_duration=SCENE_3_MAX_DURATION, font_size=42, y_ratio=0.75):
    """Build scene 3 from screen recording with text overlay."""
    drawtext = build_drawtext(text, font_path, font_size, y_ratio)

    scale_pad = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={FPS},"
        f"format=yuv420p"
    )
    vf = f"{scale_pad},{drawtext}"

    return run_ffmpeg([
        "-i", str(recording_path),
        "-t", str(max_duration),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output_path),
    ], "scene screen recording")


def concatenate(clip_paths, output_path):
    """Concatenate clips using ffmpeg concat demuxer."""
    list_path = clip_paths[0].parent / "concat_list.txt"
    with open(list_path, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    ok = run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ], "concat")

    if list_path.exists():
        list_path.unlink()
    return ok


# ─── Upload ──────────────────────────────────────────

def upload_to_drive(file_path):
    """Upload to Google Drive via rclone."""
    print(f"  Uploading to Google Drive ({GDRIVE_FOLDER})...")
    result = os.system(f"rclone copy {file_path} gdrive:{GDRIVE_FOLDER}/")
    if result == 0:
        print(f"  Uploaded: {file_path.name}")
    else:
        print(f"  Upload failed (exit code {result})")


# ─── Logging ─────────────────────────────────────────

def log_run(entry: dict):
    """Append to lifestyle_reel.jsonl."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "lifestyle_reel.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def update_asset_usage(scene_1_img: str, scene_2_img: str, screen_rec: str):
    """Append to memory/asset-usage.md."""
    path = MEMORY_DIR / "asset-usage.md"
    line = f"| {date.today().isoformat()} | lifestyle | {scene_1_img} | {scene_2_img} | {screen_rec} |"
    if path.exists():
        content = path.read_text()
        path.write_text(content.rstrip() + "\n" + line + "\n")
    else:
        header = "## Recent Asset Usage\n\n| Date | Type | Scene 1 | Scene 2 | Screen Recording |\n|------|------|---------|---------|------------------|\n"
        path.write_text(header + line + "\n")


# ─── Main pipeline ───────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate lifestyle image reels for Journal Lock")
    parser.add_argument("--dry-run", action="store_true", help="Generate text only, no video")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")
    parser.add_argument("--scene-1-text", help="Override scene 1 text")
    parser.add_argument("--scene-2-text", help="Override scene 2 text")
    parser.add_argument("--scene-3-text", help="Override scene 3 text")
    parser.add_argument("--scene-1-image", help="Force specific scene 1 image filename")
    parser.add_argument("--scene-2-image", help="Force specific scene 2 image filename")
    args = parser.parse_args()

    print("=" * 50)
    print("Journal Lock — Lifestyle Reel Pipeline")
    print("=" * 50)

    # 1. Select assets
    print("\n  Selecting assets...")
    recent = load_lifestyle_usage()

    if args.scene_1_image:
        scene_1_path = LIFESTYLE_IMAGES_DIR / args.scene_1_image
        if not scene_1_path.exists():
            print(f"ERROR: Scene 1 image not found: {scene_1_path}")
            sys.exit(1)
    else:
        scene_1_path = pick_image("scene-1", recent)

    if args.scene_2_image:
        scene_2_path = LIFESTYLE_IMAGES_DIR / args.scene_2_image
        if not scene_2_path.exists():
            print(f"ERROR: Scene 2 image not found: {scene_2_path}")
            sys.exit(1)
    else:
        scene_2_path = pick_image("scene-2", recent)

    screen_rec_path = pick_screen_recording(recent)

    print(f"  Scene 1: {scene_1_path.name}")
    print(f"  Scene 2: {scene_2_path.name}")
    print(f"  Screen:  {screen_rec_path.name}")

    # 2. Generate or use override text
    if args.scene_1_text and args.scene_2_text and args.scene_3_text:
        content = {
            "scene_1_text": args.scene_1_text,
            "scene_2_text": args.scene_2_text,
            "scene_3_text": args.scene_3_text,
            "caption": "",
            "content_angle": "manual",
        }
        print("\n  Using override text")
    else:
        print("\n  Generating text via Claude...")
        context = load_skill_context()
        content = generate_text(context)

    print(f"  Scene 1: {content['scene_1_text']}")
    print(f"  Scene 2: {content['scene_2_text']}")
    print(f"  Scene 3: {content['scene_3_text']}")
    if content.get("caption"):
        print(f"  Caption: {content['caption']}")

    if args.dry_run:
        print("\n  [DRY RUN] Skipping video assembly")
        log_run({
            "timestamp": datetime.now().isoformat(),
            "scene_1_image": scene_1_path.name,
            "scene_2_image": scene_2_path.name,
            "screen_recording": screen_rec_path.name,
            "scene_1_text": content["scene_1_text"],
            "scene_2_text": content["scene_2_text"],
            "scene_3_text": content["scene_3_text"],
            "caption": content.get("caption", ""),
            "content_angle": content.get("content_angle", ""),
            "reel_path": None,
            "cost_usd": 0.01,
            "dry_run": True,
        })
        print("\n  Done (dry run).")
        return

    # 3. Assemble video
    print("\n  Assembling video...")
    OUTPUT_DIR.mkdir(exist_ok=True)
    font_path = find_font(bold=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"lifestyle_journallock_{ts}.mp4"

    with tempfile.TemporaryDirectory(prefix="lifestyle_") as tmp:
        tmp = Path(tmp)
        scene_1_out = tmp / "01_scene1.mp4"
        scene_2_out = tmp / "02_scene2.mp4"
        scene_3_out = tmp / "03_scene3.mp4"

        # Scene 1: lifestyle image + hook (center, 48px)
        print("  Building scene 1 (hook)...")
        ok = build_scene_image(scene_1_path, content["scene_1_text"], scene_1_out,
                               SCENE_1_DURATION, font_path, font_size=48, y_ratio=0.45)
        if not ok:
            print("FAILED: Scene 1")
            sys.exit(1)

        # Scene 2: lifestyle image + response (center, 48px)
        print("  Building scene 2 (response)...")
        ok = build_scene_image(scene_2_path, content["scene_2_text"], scene_2_out,
                               SCENE_2_DURATION, font_path, font_size=48, y_ratio=0.45)
        if not ok:
            print("FAILED: Scene 2")
            sys.exit(1)

        # Scene 3: screen recording + payoff (lower third, 42px)
        print("  Building scene 3 (payoff)...")
        ok = build_scene_screen(screen_rec_path, content["scene_3_text"], scene_3_out,
                                font_path)
        if not ok:
            print("FAILED: Scene 3")
            sys.exit(1)

        # Concatenate
        print("  Concatenating...")
        ok = concatenate([scene_1_out, scene_2_out, scene_3_out], out_path)
        if not ok:
            print("FAILED: Concatenation")
            sys.exit(1)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\n  Reel assembled: {out_path} ({size_mb:.1f} MB)")

    # 4. Upload
    if not args.no_upload:
        upload_to_drive(out_path)

    # 5. Log
    log_run({
        "timestamp": datetime.now().isoformat(),
        "scene_1_image": scene_1_path.name,
        "scene_2_image": scene_2_path.name,
        "screen_recording": screen_rec_path.name,
        "scene_1_text": content["scene_1_text"],
        "scene_2_text": content["scene_2_text"],
        "scene_3_text": content["scene_3_text"],
        "caption": content.get("caption", ""),
        "content_angle": content.get("content_angle", ""),
        "reel_path": str(out_path),
        "cost_usd": 0.01,
    })
    update_asset_usage(scene_1_path.name, scene_2_path.name, screen_rec_path.name)

    print(f"\n  Done. Caption:\n  {content.get('caption', '(none)')}")


if __name__ == "__main__":
    main()
