#!/usr/bin/env python3
"""
autojournal_reel.py — Generate promotional reels for AutoJournal.

2-scene format: styled text background (hook) → screen recording (payoff).
No AI video generation — just text overlays and ffmpeg. ~$0.01 per reel.

Usage:
    python3 scripts/autojournal_reel.py                    # Full run
    python3 scripts/autojournal_reel.py --dry-run          # Text only, no video
    python3 scripts/autojournal_reel.py --no-upload        # Skip Google Drive upload
    python3 scripts/autojournal_reel.py --style dark       # Force a specific style
    python3 scripts/autojournal_reel.py --category A       # Force a specific category
"""

import argparse
import json
import os
import random
import re
import smtplib
import subprocess
import sys
import tempfile
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ─── Config ──────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

SKILLS_DIR = PROJECT_ROOT / "skills"
MEMORY_DIR = PROJECT_ROOT / "memory"
ASSETS_DIR = PROJECT_ROOT / "assets" / "autojournal"
FONTS_DIR = PROJECT_ROOT / "fonts"
LOGS_DIR = PROJECT_ROOT / "logs"
VIDEO_OUTPUT_DIR = PROJECT_ROOT / "video_output"

WIDTH, HEIGHT, FPS = 1080, 1920, 30
BITRATE = "8000k"
SCENE1_DURATION = 2.5
GDRIVE_FOLDER = "autojournal-social-videos"
JSONL_PATH = LOGS_DIR / "autojournal_reel.jsonl"

SCREEN_RECORDINGS_DIR = ASSETS_DIR / "screen-recordings"

# ─── Style definitions ───────────────────────────────

SCENE1_STYLES = {
    "dark": {
        "bg": "1A1A1A",
        "color": "F5F5F5",
        "font_size": 58,
        "grid": False,
    },
    "cream": {
        "bg": "FAF8F5",
        "color": "2C2C2C",
        "font_size": 58,
        "grid": False,
    },
    "terracotta": {
        "bg": "C4775A",
        "color": "FFFFFF",
        "font_size": 58,
        "grid": False,
    },
    "journal": {
        "bg": "FAF8F5",
        "color": "2C2C2C",
        "font_size": 56,
        "grid": True,
    },
    "dark_accent": {
        "bg": "1E293B",
        "color": "F8FAFC",
        "font_size": 58,
        "grid": False,
    },
}

STYLE_ORDER = ["dark", "cream", "terracotta", "journal", "dark_accent"]

# ─── Screen recording descriptions ───────────────────

SCREEN_RECORDING_DESCRIPTIONS = {
    "autojournal-food.mov": "AutoJournal showing a journal entry about food — photos of meals, restaurants, cooking moments woven into a personal narrative",
    "autojournal-food-v2.mov": "AutoJournal displaying a second food-focused journal entry — different meals and dining experiences with friends",
    "autojournal-friends.mov": "AutoJournal showing a journal entry about hanging out with friends — group photos, outings, candid moments turned into a story",
    "autojournal-travel.mov": "AutoJournal showing a travel journal entry — scenic photos, new places, and adventure moments written up beautifully",
}

# ─── Content categories ──────────────────────────────

CATEGORIES = {
    "A": {"weight": 40, "desc": "Curiosity / 'Wait what' — hook creates intrigue about the concept"},
    "B": {"weight": 30, "desc": "Relatable / 'That's so me' — viewer sees themselves in the scenario"},
    "C": {"weight": 15, "desc": "Discovery / 'I found something' — sharing a find with enthusiasm"},
    "D": {"weight": 15, "desc": "Transformation / Before-after — showing the change"},
}

# ─── Font resolution ─────────────────────────────────

def find_font(bold=True):
    """Find the best available font."""
    candidates = [
        FONTS_DIR / ("Geist-Bold.otf" if bold else "Geist-Regular.otf"),
        FONTS_DIR / "Geist-Bold.otf",
        FONTS_DIR / "Geist-Regular.otf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return str(p.resolve())
    print("ERROR: No font found. Install Geist-Bold.otf to fonts/")
    sys.exit(1)


# ─── Text helpers ────────────────────────────────────

def strip_emojis(text):
    """Remove any non-ASCII characters that ffmpeg drawtext can't render."""
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


def escape_drawtext(text):
    """Escape special chars for ffmpeg drawtext filter."""
    text = strip_emojis(text)
    text = text.replace("'", "\u2019")
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace(";", "\\;")
    text = text.replace('"', '\\"')
    return text


def wrap_text(text, max_chars=25):
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


# ─── Asset / style selection ─────────────────────────

def pick_style(run_count, override=None):
    """Pick a style by rotating through the list, or use CLI override."""
    if override and override in SCENE1_STYLES:
        return override
    return STYLE_ORDER[run_count % len(STYLE_ORDER)]


def pick_screen_recording(recent_runs):
    """Pick a screen recording, avoiding the last 4 used."""
    available = sorted([
        f for f in SCREEN_RECORDINGS_DIR.iterdir()
        if f.suffix in (".mp4", ".mov")
    ])
    if not available:
        print(f"ERROR: No screen recordings in {SCREEN_RECORDINGS_DIR}")
        sys.exit(1)

    recent_used = {e.get("screen_recording", "") for e in recent_runs[-4:]}
    unused = [r for r in available if r.name not in recent_used]
    return random.choice(unused) if unused else random.choice(available)


def pick_category(override=None):
    """Pick a content category using weighted random, or use CLI override."""
    if override and override in CATEGORIES:
        return override
    population = []
    for cat, info in CATEGORIES.items():
        population.extend([cat] * info["weight"])
    return random.choice(population)


# ─── Context loading ─────────────────────────────────

def load_context():
    """Load skill/memory files for Claude system prompt."""
    files = [
        ("skills", "autojournal.md"),
        ("skills", "content/autojournal-hooks.md"),
    ]
    memory_files = [
        ("memory", "autojournal-performance.md"),
        ("memory", "failure-log.md"),
    ]

    parts = []
    for section, f in files:
        base = SKILLS_DIR if section == "skills" else MEMORY_DIR
        path = base / f
        if path.exists():
            parts.append(f"--- {section}/{f} ---\n{path.read_text()}")
    for section, f in memory_files:
        path = MEMORY_DIR / f
        if path.exists():
            parts.append(f"--- {section}/{f} ---\n{path.read_text()}")
    return "\n\n".join(parts)


# ─── Load recent runs ───────────────────────────────

def load_recent_runs():
    """Load recent runs from JSONL log."""
    if not JSONL_PATH.exists():
        return []
    entries = []
    for line in JSONL_PATH.read_text().splitlines():
        if line.strip():
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return entries


# ─── Text generation ─────────────────────────────────

USER_PROMPT = """You are writing text overlays for a 2-scene TikTok/Reels video promoting AutoJournal — an iOS app that reads your camera roll and writes a weekly journal entry automatically. The reel structure:
- Scene 1: A HOOK — first-person statement on a styled text background that creates curiosity
- Scene 2: A PAYOFF — the reveal, showing the app via screen recording with lower-third text

The screen recording for this reel shows: {screen_desc}

Content category for this reel: {category} — {category_desc}

Rules:
- Gen Z woman voice, casual, authentic, lowercase okay
- NEVER mention the app name in any overlay text
- Hook text (Scene 1): max 55 chars. First person, creates intrigue. This appears on a styled background with NO images.
- Payoff text (Scene 2): max 50 chars. The "aha" reveal that connects to the screen recording. NO emojis — plain ASCII only.
- Caption: Story-style with soft CTA. Include 3-5 relevant hashtags. Max 150 chars.
- The hook should make people stop scrolling. The payoff should make them want the app.

Return ONLY valid JSON:
{{
  "hook_text": "...",
  "payoff_text": "...",
  "caption": "...",
  "hashtags": "#autojournal #journaling ..."
}}"""


def generate_text(context, category, screen_desc, recent_hooks):
    """Call Claude to generate text overlays."""
    import anthropic

    cat_desc = CATEGORIES[category]["desc"]

    avoid_block = ""
    if recent_hooks:
        lines = [f'- "{h}"' for h in recent_hooks[-8:]]
        avoid_block = (
            "\n\nIMPORTANT — These hooks were used in recent reels. "
            "Do NOT repeat or closely paraphrase any of them. "
            "Pick a DIFFERENT angle and scenario:\n"
            + "\n".join(lines)
        )

    prompt = USER_PROMPT.format(
        screen_desc=screen_desc,
        category=category,
        category_desc=cat_desc,
    ) + avoid_block

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=f"You are the content engine for an AutoJournal reel pipeline. Follow the rules in these skill files:\n\n{context}",
        messages=[{"role": "user", "content": prompt}],
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


def build_scene1(hook_text, style_name, tmp_dir):
    """Build Scene 1: styled text background with centered text (no pill)."""
    style = SCENE1_STYLES[style_name]
    font_path = find_font(bold=True)

    lines = wrap_text(hook_text, max_chars=25)
    escaped = escape_drawtext("\n".join(lines))

    drawtext = (
        f"drawtext=fontfile='{font_path}'"
        f":text='{escaped}'"
        f":fontsize={style['font_size']}"
        f":fontcolor=0x{style['color']}"
        f":x=(w-text_w)/2"
        f":y=(h-text_h)/2"
        f":line_spacing=8"
    )

    if style["grid"]:
        vf = f"drawgrid=w=72:h=72:t=1:c=0xC4775A@0.08,{drawtext},format=yuv420p"
    else:
        vf = f"{drawtext},format=yuv420p"

    output = tmp_dir / "01_scene1.mp4"
    ok = run_ffmpeg([
        "-f", "lavfi", "-i", f"color=c=0x{style['bg']}:s={WIDTH}x{HEIGHT}:d={SCENE1_DURATION}:r={FPS}",
        "-vf", vf,
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output),
    ], "scene1")
    return output if ok else None


def build_scene2(screen_path, payoff_text, tmp_dir):
    """Build Scene 2: normalized screen recording with lower-third text pill."""
    font_path = find_font(bold=True)
    escaped = escape_drawtext(payoff_text)
    lines = wrap_text(payoff_text, max_chars=25)

    if len(lines) > 1:
        escaped = escape_drawtext("\n".join(lines))

    drawtext = (
        f"drawtext=fontfile='{font_path}'"
        f":text='{escaped}'"
        f":fontsize=48"
        f":fontcolor=white"
        f":box=1"
        f":boxcolor=black@0.85"
        f":boxborderw=20"
        f":line_spacing=8"
        f":x=(w-text_w)/2"
        f":y=h*0.75-text_h/2"
    )

    scale_pad = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={FPS},"
        f"format=yuv420p"
    )
    vf = f"{scale_pad},{drawtext}"

    output = tmp_dir / "02_scene2.mp4"
    ok = run_ffmpeg([
        "-i", str(screen_path),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output),
    ], "scene2")
    return output if ok else None


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


# ─── Email notification ──────────────────────────────

def send_email(hook, payoff, caption, hashtags, category, style, screen_rec, run_date):
    """Send a plain text email with reel details."""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    recipient = os.environ.get("DELIVERY_EMAIL", "")

    if not all([smtp_user, smtp_pass, recipient]):
        print("  Skipping email (SMTP_USER/SMTP_PASS/DELIVERY_EMAIL not set)")
        return

    body = f"""AutoJournal Reel — {run_date}

HOOK (Scene 1):
{hook}

PAYOFF (Scene 2):
{payoff}

CAPTION:
{caption}

HASHTAGS:
{hashtags}

Category: {category} | Style: {style} | Screen: {screen_rec}
"""

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = f"AutoJournal Reel: {hook[:50]}"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipient, msg.as_string())
        print(f"  Email sent to {recipient}")
    except Exception as e:
        print(f"  Email failed: {e}")


# ─── Logging ─────────────────────────────────────────

def log_run(entry):
    """Append to autojournal_reel.jsonl."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(JSONL_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ─── Main pipeline ───────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate promotional reels for AutoJournal")
    parser.add_argument("--dry-run", action="store_true", help="Generate text only, no video")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")
    parser.add_argument("--style", choices=list(SCENE1_STYLES.keys()), help="Force a specific Scene 1 style")
    parser.add_argument("--category", choices=list(CATEGORIES.keys()), help="Force a specific content category")
    parser.add_argument("--hook-text", help="Override hook text (Scene 1)")
    parser.add_argument("--payoff-text", help="Override payoff text (Scene 2)")
    args = parser.parse_args()

    print("=" * 50)
    print("AutoJournal — Reel Pipeline")
    print("=" * 50)

    # 1. Load recent runs
    recent = load_recent_runs()
    run_count = len(recent)

    # 2. Pick style and category
    style_name = pick_style(run_count, override=args.style)
    category = pick_category(override=args.category)
    print(f"\n  Style: {style_name} | Category: {category}")

    # 3. Pick screen recording
    screen_path = pick_screen_recording(recent)
    screen_desc = SCREEN_RECORDING_DESCRIPTIONS.get(screen_path.name, "AutoJournal app screen recording")
    print(f"  Screen: {screen_path.name}")

    # 4. Generate or use override text
    if args.hook_text and args.payoff_text:
        content = {
            "hook_text": args.hook_text,
            "payoff_text": args.payoff_text,
            "caption": "",
            "hashtags": "",
        }
        print("\n  Using override text")
    else:
        print("\n  Generating text via Claude...")
        context = load_context()
        recent_hooks = [e.get("hook_text", "") for e in recent if e.get("hook_text")]
        content = generate_text(context, category, screen_desc, recent_hooks)

    print(f"  Hook:    {content['hook_text']}")
    print(f"  Payoff:  {content['payoff_text']}")
    if content.get("caption"):
        print(f"  Caption: {content['caption']}")

    if args.dry_run:
        print("\n  [DRY RUN] Skipping video assembly")
        log_run({
            "timestamp": datetime.now().isoformat(),
            "style": style_name,
            "category": category,
            "screen_recording": screen_path.name,
            "hook_text": content["hook_text"],
            "payoff_text": content["payoff_text"],
            "caption": content.get("caption", ""),
            "hashtags": content.get("hashtags", ""),
            "reel_path": None,
            "cost_usd": 0.01,
            "dry_run": True,
        })
        print("\n  Done (dry run).")
        return

    # 5. Assemble video
    print("\n  Assembling video...")
    VIDEO_OUTPUT_DIR.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = VIDEO_OUTPUT_DIR / f"autojournal_{ts}.mp4"

    with tempfile.TemporaryDirectory(prefix="autojournal_") as tmp:
        tmp = Path(tmp)

        # Scene 1: styled text background + hook
        print("  Building scene 1 (hook)...")
        scene1 = build_scene1(content["hook_text"], style_name, tmp)
        if not scene1:
            print("FAILED: Scene 1")
            sys.exit(1)

        # Scene 2: screen recording + payoff
        print("  Building scene 2 (payoff)...")
        scene2 = build_scene2(screen_path, content["payoff_text"], tmp)
        if not scene2:
            print("FAILED: Scene 2")
            sys.exit(1)

        # Concatenate
        print("  Concatenating...")
        ok = concatenate([scene1, scene2], out_path)
        if not ok:
            print("FAILED: Concatenation")
            sys.exit(1)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\n  Reel assembled: {out_path} ({size_mb:.1f} MB)")

    # 6. Upload
    if not args.no_upload:
        upload_to_drive(out_path)

    # 7. Email notification
    send_email(
        hook=content["hook_text"],
        payoff=content["payoff_text"],
        caption=content.get("caption", ""),
        hashtags=content.get("hashtags", ""),
        category=category,
        style=style_name,
        screen_rec=screen_path.name,
        run_date=date.today().isoformat(),
    )

    # 8. Log
    log_run({
        "timestamp": datetime.now().isoformat(),
        "style": style_name,
        "category": category,
        "screen_recording": screen_path.name,
        "hook_text": content["hook_text"],
        "payoff_text": content["payoff_text"],
        "caption": content.get("caption", ""),
        "hashtags": content.get("hashtags", ""),
        "reel_path": str(out_path),
        "cost_usd": 0.01,
    })

    print(f"\n  Done. Caption:\n  {content.get('caption', '(none)')}")


if __name__ == "__main__":
    main()
