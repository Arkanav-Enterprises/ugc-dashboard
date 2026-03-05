"""Video stitcher — FFmpeg scene processing + concatenation with async job queue."""

import json
import os
import queue
import shutil
import smtplib
import subprocess
import sys
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import httpx

from config import VIDEO_OUTPUT_DIR

GDRIVE_FOLDER = "manifest-social-videos"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
RECIPIENT = os.environ.get("DELIVERY_EMAIL", "")

# ─── Config ──────────────────────────────────────────

WIDTH, HEIGHT, FPS = 1080, 1920, 30
BITRATE = "8000k"
FONT_SIZE = 56
TEXT_Y_RATIO = 0.75
HORIZONTAL_PAD = 60
STROKE_WIDTH = 3
CHARS_PER_LINE = 32

FONT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "fonts"


# ─── Helpers (copied from assemble_video.py) ─────────

def find_font():
    candidates = [
        FONT_DIR / "Geist-Regular.otf",
        FONT_DIR / "Geist-Regular.ttf",
        FONT_DIR / "Geist-Bold.otf",
        FONT_DIR / "Geist-Bold.ttf",
        FONT_DIR / "PlayfairDisplay-Regular.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return str(path.resolve())
    return None


def wrap_text(text, max_chars=CHARS_PER_LINE):
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
    text = text.replace("'", "\u2019")
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace(";", "\\;")
    return text


def build_scale_pad_filter():
    return (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={FPS},"
        f"format=yuv420p"
    )


def build_drawtext_filter(text, font_path):
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


# ─── Scene processing ────────────────────────────────

def _process_scene(input_path, output_path, text, speed, font_path, log_lines):
    """Normalize a single scene: scale/pad + optional speed + optional text overlay."""
    vf_parts = []

    # Speed adjustment comes first (before scale) so we work with original res
    if speed and speed != 1.0:
        vf_parts.append(f"setpts=PTS/{speed}")

    vf_parts.append(build_scale_pad_filter())

    if text and text.strip() and font_path:
        vf_parts.append(build_drawtext_filter(text.strip(), font_path))

    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(input_path),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-b:v", BITRATE,
        "-profile:v", "high", "-level", "4.0",
        str(output_path),
    ]

    log_lines.append(f"  Processing: {Path(input_path).name}")
    if text and text.strip():
        log_lines.append(f"    Text: {text.strip()}")
    if speed and speed != 1.0:
        log_lines.append(f"    Speed: {speed}x")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log_lines.append(f"  ERROR: {result.stderr}")
        return False
    return True


def _concatenate(clip_paths, output_path, log_lines):
    """Concat processed clips using ffmpeg concat demuxer."""
    log_lines.append(f"  Concatenating {len(clip_paths)} clips...")

    list_path = clip_paths[0].parent / "concat_list.txt"
    with open(list_path, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    list_path.unlink(missing_ok=True)

    if result.returncode != 0:
        log_lines.append(f"  ERROR: {result.stderr}")
        return False
    return True


# ─── Caption + email ─────────────────────────────────

def _generate_caption(scene_texts, log_lines):
    """Generate an Instagram caption from scene text overlays via Claude."""
    if not ANTHROPIC_API_KEY:
        log_lines.append("  SKIP CAPTION: No ANTHROPIC_API_KEY set")
        return None

    overlays = "\n".join(f"Scene {i+1}: \"{t}\"" for i, t in enumerate(scene_texts) if t)
    if not overlays:
        return None

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 300,
                "system": (
                    "You write Instagram/TikTok captions for screen time wellness apps. "
                    "Never mention the app by name. Keep it authentic, first-person, casual."
                ),
                "messages": [{"role": "user", "content": (
                    f"Write a short Instagram caption (2-3 lines) and 5 hashtags for a reel "
                    f"with these text overlays:\n{overlays}\n\n"
                    f"Reply with ONLY this JSON (no markdown fencing):\n"
                    f'{{"caption": "the caption text", "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5"}}'
                )}],
            },
            timeout=20,
        )
        raw = resp.json()["content"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return json.loads(raw.strip())
    except Exception as e:
        log_lines.append(f"  Caption generation error: {e}")
        return None


def _send_email(subject, body, log_lines):
    """Send delivery email. Fails gracefully."""
    if not all([SMTP_USER, SMTP_PASS, RECIPIENT]):
        log_lines.append("  SKIP EMAIL: Set SMTP_USER, SMTP_PASS, DELIVERY_EMAIL env vars")
        return

    recipients = [r.strip() for r in RECIPIENT.split(",") if r.strip()]
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
        log_lines.append(f"  Email sent to {', '.join(recipients)}")
    except Exception as e:
        log_lines.append(f"  EMAIL ERROR: {e}")


# ─── Job queue (same pattern as pipeline_runner.py) ──

_jobs: dict[str, dict] = {}
_queue: queue.Queue[tuple[str, list[dict], Path]] = queue.Queue()
_worker_started = False
_worker_lock = threading.Lock()


def _ensure_worker():
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
        threading.Thread(target=_worker_loop, daemon=True).start()


def _worker_loop():
    while True:
        job_id, scenes, upload_dir = _queue.get()
        try:
            _jobs[job_id]["status"] = "running"
            _run_stitch(job_id, scenes, upload_dir)
        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["output"] += f"\nFatal error: {e}"
        finally:
            # Clean up uploaded files
            shutil.rmtree(upload_dir, ignore_errors=True)
            _queue.task_done()


def _run_stitch(job_id, scenes, upload_dir):
    log_lines = []
    job = _jobs[job_id]

    def sync_log(msg):
        log_lines.append(msg)
        job["output"] = "\n".join(log_lines)

    font_path = find_font()
    if not font_path:
        sync_log("WARNING: No font found — text overlays will be skipped")

    sync_log(f"Stitching {len(scenes)} scenes...")

    VIDEO_OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"stitch_{ts}_{job_id}.mp4"
    out_path = VIDEO_OUTPUT_DIR / out_filename

    with tempfile.TemporaryDirectory(prefix="stitch_") as tmp:
        tmp = Path(tmp)
        processed = []

        for i, scene in enumerate(scenes):
            input_file = upload_dir / scene["filename"]
            output_file = tmp / f"{i:02d}_scene.mp4"

            sync_log(f"\nScene {i + 1}/{len(scenes)}:")
            ok = _process_scene(
                input_file, output_file,
                scene.get("text"), scene.get("speed"),
                font_path, log_lines,
            )
            job["output"] = "\n".join(log_lines)

            if not ok:
                job["status"] = "failed"
                sync_log(f"\nFAILED at scene {i + 1}")
                return

            processed.append(output_file)

        sync_log("")
        ok = _concatenate(processed, out_path, log_lines)
        job["output"] = "\n".join(log_lines)

        if not ok:
            job["status"] = "failed"
            sync_log("\nFAILED at concatenation")
            return

    size_mb = out_path.stat().st_size / (1024 * 1024)
    sync_log(f"\nDone! Output: {out_filename} ({size_mb:.1f} MB)")

    # Upload to Google Drive via rclone
    sync_log(f"\nUploading to Google Drive ({GDRIVE_FOLDER})...")
    rc = os.system(f"rclone copy {out_path} gdrive:{GDRIVE_FOLDER}/")
    if rc == 0:
        sync_log(f"Uploaded to Google Drive.")
    else:
        sync_log(f"WARNING: Drive upload failed (exit code {rc}). Video saved locally.")

    # Generate caption from text overlays and email it
    scene_texts = [s.get("text", "") for s in scenes]
    if any(t.strip() for t in scene_texts):
        sync_log(f"\nGenerating caption...")
        caption_data = _generate_caption(scene_texts, log_lines)
        job["output"] = "\n".join(log_lines)

        if caption_data:
            caption = caption_data.get("caption", "")
            hashtags = caption_data.get("hashtags", "")
            sync_log(f"  Caption: {caption}")
            sync_log(f"  Hashtags: {hashtags}")

            email_body = (
                f"New stitched reel ready: {out_filename}\n"
                f"Google Drive: {GDRIVE_FOLDER}/\n\n"
                f"--- TEXT OVERLAYS ---\n"
                + "\n".join(f"Scene {i+1}: {t}" for i, t in enumerate(scene_texts) if t.strip())
                + f"\n\n--- CAPTION ---\n{caption}\n\n{hashtags}"
            )
            _send_email(f"Stitch Ready — {out_filename}", email_body, log_lines)
            job["output"] = "\n".join(log_lines)

    job["status"] = "completed"
    job["result_filename"] = out_filename


# ─── Public API ──────────────────────────────────────

def start_stitch_job(scenes: list[dict], upload_dir: Path) -> dict:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "output": "",
        "result_filename": None,
    }
    _ensure_worker()
    _queue.put((job_id, scenes, upload_dir))
    return {"job_id": job_id, "status": "queued"}


def get_stitch_job(job_id: str) -> dict | None:
    job = _jobs.get(job_id)
    if not job:
        return None
    return {
        "id": job["id"],
        "status": job["status"],
        "output": job["output"],
        "result_filename": job.get("result_filename"),
    }
