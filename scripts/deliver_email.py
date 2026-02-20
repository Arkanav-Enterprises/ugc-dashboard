#!/usr/bin/env python3
"""Send slideshow slides + caption to your phone via email."""

import smtplib
import os
import sys
import glob
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path

# --- Config (set via environment variables) ---
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")  # your-email@gmail.com
SMTP_PASS = os.environ.get("SMTP_PASS", "")  # Gmail app password
RECIPIENT = os.environ.get("DELIVERY_EMAIL", "")  # where slides land

OUTPUT_DIR = Path("/root/openclaw/output")


def find_slides(output_dir: Path) -> list[Path]:
    """Find slide images in output directory, sorted by name."""
    patterns = ["slide_*.png", "slide_*.jpg"]
    slides = []
    for p in patterns:
        slides.extend(output_dir.glob(p))
    return sorted(slides, key=lambda f: f.name)


def send_slideshow(slides: list[Path], caption: str, hook: str) -> None:
    """Attach slides and send email with caption in body."""
    if not all([SMTP_USER, SMTP_PASS, RECIPIENT]):
        print("ERROR: Set SMTP_USER, SMTP_PASS, and DELIVERY_EMAIL env vars")
        sys.exit(1)

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = RECIPIENT
    msg["Subject"] = f"Manifest Lock Slideshow: {hook[:60]}"

    # Caption as email body
    body = f"HOOK:\n{hook}\n\n---\n\nCAPTION:\n{caption}\n\n---\n\n{len(slides)} slides attached."
    msg.attach(MIMEText(body, "plain"))

    # Attach each slide
    for slide in slides:
        with open(slide, "rb") as f:
            img = MIMEImage(f.read(), name=slide.name)
            img.add_header("Content-Disposition", "attachment", filename=slide.name)
            msg.attach(img)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, RECIPIENT, msg.as_string())

    print(f"Sent {len(slides)} slides to {RECIPIENT}")


if __name__ == "__main__":
    # Usage: python3 deliver_email.py "hook text" "caption text"
    # Or: python3 deliver_email.py "hook text" "caption text" /path/to/slides/
    if len(sys.argv) < 3:
        print("Usage: deliver_email.py <hook> <caption> [slides_dir]")
        sys.exit(1)

    hook = sys.argv[1]
    caption = sys.argv[2]
    slides_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else OUTPUT_DIR

    slides = find_slides(slides_dir)
    if not slides:
        print(f"No slides found in {slides_dir}")
        sys.exit(1)

    send_slideshow(slides, caption, hook)