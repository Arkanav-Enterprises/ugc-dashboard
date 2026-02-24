#!/usr/bin/env python3
"""
Assemble a UGC-style reel from 3 clips with text overlays.

Structure: Hook (2s, with POV text) → Screen Recording (sped up) → Reaction (1s, with text)
All clips normalized to 1080×1920 @ 30fps, audio stripped, uploaded to Google Drive.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ─── Config ──────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent  # /root/openclaw
FONT_DIR = BASE_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "video_output"
GDRIVE_FOLDER = "manifest-social-videos"

WIDTH, HEIGHT, FPS = 1080, 1920, 30
BITRATE = "8000k"
FONT_SIZE = 56
TEXT_Y_RATIO = 0.75  # lower third
HORIZONTAL_PAD = 60  # pixels of padding on each side
STROKE_WIDTH = 3

# Chars per line at 56px on 1080w with ~60px padding each side
CHARS_PER_LINE = 32


# ─── Font resolution ─────────────────────────────────

def find_font(override=None):
    """Find the best available font: override > Geist > Playfair > DejaVu."""
    candidates = [
        override,
        FONT_DIR / "Geist-Regular.otf",
        FONT_DIR / "Geist-Regular.ttf",
        FONT_DIR / "Geist-Bold.otf",
        FONT_DIR / "Geist-Bold.ttf",
        FONT_DIR / "PlayfairDisplay-Regular.ttf",
        FONT_DIR / "PlayfairDisplay-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        if path and Path(path).exists():
            return str(Path(path).resolve())
    print("ERROR: No font found. Install Geist-Bold.ttf to /root/openclaw/fonts/")
    sys.exit(1)


# ─── Text wrapping ───────────────────────────────────

def wrap_text(text, max_chars=CHARS_PER_LINE):
    """Word-wrap text into lines that fit the lower third."""
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


def escape_drawtext(text):
    """Escape special chars for ffmpeg drawtext filter."""
    # ffmpeg drawtext needs : ; \ escaped
    # Replace ASCII apostrophe with Unicode right single quote (visually identical)
    # to avoid breaking ffmpeg's single-quote-delimited filter parser
    text = text.replace("'", "\u2019")
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace(";", "\\;")
    return text


# ─── ffmpeg helpers ──────────────────────────────────

def run_ffmpeg(args, dry_run=False):
    """Run an ffmpeg command. Returns True on success."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"] + args
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd)}")
        return True
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error: {result.stderr}")
        return False
    return True


def build_scale_pad_filter():
    """Scale to fit 1080x1920 and pad with black bars if needed."""
    return (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={FPS},"
        f"format=yuv420p"
    )


def build_drawtext_filter(text, font_path):
    """Build ffmpeg drawtext filter for multi-line centered text in lower third."""
    lines = wrap_text(text)
    line_height = int(FONT_SIZE * 1.4)
    total_height = line_height * len(lines)
    base_y = int(HEIGHT * TEXT_Y_RATIO) - total_height // 2

    filters = []
    for i, line in enumerate(lines):
        escaped = escape_drawtext(line)
        y = base_y + i * line_height
        f = (
            f"drawtext=fontfile='{font_path}'"
            f":text='{escaped}'"
            f":fontsize={FONT_SIZE}"
            f":fontcolor=white"
            f":borderw={STROKE_WIDTH}"
            f":bordercolor=black"
            f":x=max({HORIZONTAL_PAD}\\,(w-text_w)/2)"
            f":y={y}"
        )
        filters.append(f)
    return ",".join(filters)


# ─── Clip processing ─────────────────────────────────

def process_hook(input_path, output_path, text, font_path, dry_run=False):
    """Normalize hook clip + burn text overlay."""
    print(f"  Processing hook clip: {input_path}")
    scale = build_scale_pad_filter()
    drawtext = build_drawtext_filter(text, font_path)
    vf = f"{scale},{drawtext}"
    return run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output_path),
    ], dry_run)


def process_screen_recording(input_path, output_path, speed, dry_run=False):
    """Normalize screen recording + speed up."""
    print(f"  Processing screen recording: {input_path} (speed: {speed}x)")
    scale = build_scale_pad_filter()
    # setpts=PTS/speed speeds up the video
    vf = f"setpts=PTS/{speed},{scale}"
    return run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output_path),
    ], dry_run)


def process_reaction(input_path, output_path, text, font_path, dry_run=False):
    """Normalize reaction clip + burn text overlay."""
    print(f"  Processing reaction clip: {input_path}")
    scale = build_scale_pad_filter()
    drawtext = build_drawtext_filter(text, font_path)
    vf = f"{scale},{drawtext}"
    return run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output_path),
    ], dry_run)


def concatenate(clip_paths, output_path, dry_run=False):
    """Concatenate processed clips using ffmpeg concat demuxer."""
    print(f"  Concatenating {len(clip_paths)} clips...")
    # Write concat file list
    list_path = clip_paths[0].parent / "concat_list.txt"
    if not dry_run:
        with open(list_path, "w") as f:
            for p in clip_paths:
                f.write(f"file '{p}'\n")

    success = run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ], dry_run)

    # Cleanup concat list
    if not dry_run and list_path.exists():
        list_path.unlink()
    return success


# ─── Upload ──────────────────────────────────────────

def upload_to_drive(file_path, dry_run=False):
    """Upload finished reel to Google Drive via rclone."""
    cmd = f"rclone copy {file_path} gdrive:{GDRIVE_FOLDER}/"
    if dry_run:
        print(f"  [DRY RUN] {cmd}")
        return True
    print(f"  Uploading to Google Drive ({GDRIVE_FOLDER})...")
    result = os.system(cmd)
    if result == 0:
        print(f"  ✅ Uploaded: {file_path.name}")
        return True
    else:
        print(f"  ⚠️  Upload failed (exit code {result})")
        return False


# ─── Main ────────────────────────────────────────────

def assemble(args):
    """Full pipeline: normalize → overlay → concat → upload."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Resolve font
    font_path = find_font(args.font)
    print(f"Font: {Path(font_path).name}")

    # Output path
    if args.output:
        out_path = Path(args.output)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = OUTPUT_DIR / f"reel_{ts}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="reel_") as tmp:
        tmp = Path(tmp)

        # Step 1: Process each clip
        hook_out = tmp / "01_hook.mp4"
        screen_out = tmp / "02_screen.mp4"

        ok = process_hook(args.hook_clip, hook_out, args.hook_text, font_path, args.dry_run)
        if not ok:
            print("FAILED: Hook clip processing")
            return None

        ok = process_screen_recording(args.screen_recording, screen_out, args.speed, args.dry_run)
        if not ok:
            print("FAILED: Screen recording processing")
            return None

        clips_to_concat = [hook_out, screen_out]

        if args.reaction_clip is not None:
            react_out = tmp / "03_reaction.mp4"
            ok = process_reaction(args.reaction_clip, react_out, args.reaction_text, font_path, args.dry_run)
            if not ok:
                print("FAILED: Reaction clip processing")
                return None
            clips_to_concat.append(react_out)

        # Step 2: Concatenate
        ok = concatenate(clips_to_concat, out_path, args.dry_run)
        if not ok:
            print("FAILED: Concatenation")
            return None

    if not args.dry_run:
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"\n✅ Reel assembled: {out_path} ({size_mb:.1f} MB)")

    # Step 3: Upload
    if not args.no_upload:
        upload_to_drive(out_path, args.dry_run)

    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Assemble a UGC reel: hook + screen recording + reaction with text overlays"
    )
    parser.add_argument("--hook-clip", required=True, help="Path to hook/opening clip")
    parser.add_argument("--screen-recording", required=True, help="Path to screen recording clip")
    parser.add_argument("--reaction-clip", required=False, default=None, help="Path to closing reaction clip (optional)")
    parser.add_argument("--hook-text", required=True, help="Text overlay for hook clip (Part 1)")
    parser.add_argument("--reaction-text", required=False, default=None, help="Text overlay for reaction clip (Part 3, optional)")
    parser.add_argument("--speed", type=float, default=2.5, help="Speed multiplier for screen recording (default: 2.5)")
    parser.add_argument("--output", help="Output file path (default: auto-generated in video_output/)")
    parser.add_argument("--font", help="Path to .ttf font file (default: auto-detect)")
    parser.add_argument("--no-upload", action="store_true", help="Skip Google Drive upload")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")

    args = parser.parse_args()

    # Validate inputs exist
    inputs_to_check = [
        (args.hook_clip, "Hook clip"),
        (args.screen_recording, "Screen recording"),
    ]
    if args.reaction_clip is not None:
        inputs_to_check.append((args.reaction_clip, "Reaction clip"))
    for path, label in inputs_to_check:
        if not Path(path).exists():
            print(f"ERROR: {label} not found: {path}")
            sys.exit(1)

    print("=" * 50)
    print("Manifest Lock — Video Assembly")
    print("=" * 50)
    print(f"Hook text:     {args.hook_text}")
    print(f"Reaction text: {args.reaction_text or '(none)'}")
    print(f"Screen speed:  {args.speed}x")
    print()

    result = assemble(args)
    if result:
        print(f"\nDone. Post with trending audio on IG/TikTok.")
    else:
        print("\nAssembly failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
