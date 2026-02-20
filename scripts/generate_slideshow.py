"""
Manifest Lock TikTok Slideshow Generator
Generates 6-slide carousel mixing AI images + real app screenshots.
Posts as draft to TikTok via Postiz API.
"""

import os
import base64
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
POSTIZ_API_KEY = os.environ.get("POSTIZ_API_KEY", "")
WORK_DIR = Path(os.environ.get("WORK_DIR", "/root/openclaw/output"))
ASSETS_DIR = Path(os.environ.get("ASSETS_DIR", "/root/openclaw/assets"))
WORK_DIR.mkdir(exist_ok=True)

SLIDE_WIDTH = 1024
SLIDE_HEIGHT = 1536
FONT_SIZE = int(SLIDE_WIDTH * 0.065)  # 6.5% of width = 67px
MAX_TEXT_WIDTH = int(SLIDE_WIDTH * 0.80)


# --- Core building blocks ---

def generate_image(prompt: str, output_path: Path) -> Path:
    """Generate a single image via OpenAI gpt-image-1.5."""
    resp = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": "gpt-image-1.5",
            "prompt": prompt,
            "n": 1,
            "size": f"{SLIDE_WIDTH}x{SLIDE_HEIGHT}",
        },
    )
    resp.raise_for_status()
    data = resp.json()["data"][0]

    # gpt-image-1.5 returns b64_json by default, not url
    if "url" in data:
        img_data = requests.get(data["url"]).content
    elif "b64_json" in data:
        img_data = base64.b64decode(data["b64_json"])
    else:
        raise ValueError(f"Unexpected response format: {list(data.keys())}")

    output_path.write_bytes(img_data)
    return output_path


def resize_asset(asset_path: Path, output_path: Path) -> Path:
    """Resize a local screenshot/asset to slide dimensions with padding."""
    img = Image.open(asset_path).convert("RGBA")

    # Fit within slide dimensions, preserving aspect ratio
    img.thumbnail((SLIDE_WIDTH, SLIDE_HEIGHT), Image.LANCZOS)

    # Create slide-sized canvas with dark purple background (matches brand)
    canvas = Image.new("RGBA", (SLIDE_WIDTH, SLIDE_HEIGHT), (45, 27, 105, 255))

    # Center the screenshot on canvas
    x = (SLIDE_WIDTH - img.width) // 2
    y = (SLIDE_HEIGHT - img.height) // 2
    canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)

    canvas.convert("RGB").save(output_path)
    return output_path


def add_text_overlay(image_path: Path, text: str, output_path: Path) -> Path:
    """Add hook text to slide with stroke for readability."""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", FONT_SIZE)
    except OSError:
        font = ImageFont.load_default()

    # Word wrap
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > MAX_TEXT_WIDTH and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    # Center vertically (not in top 15% or bottom 10%)
    line_height = FONT_SIZE * 1.3
    total_height = line_height * len(lines)
    min_y = int(SLIDE_HEIGHT * 0.20)
    max_y = int(SLIDE_HEIGHT * 0.65)
    start_y = max(min_y, min(max_y, (SLIDE_HEIGHT - total_height) / 2))

    # Draw text with dark stroke
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (SLIDE_WIDTH - text_width) / 2
        y = start_y + i * line_height

        for dx in range(-3, 4):
            for dy in range(-3, 4):
                draw.text((x + dx, y + dy), line, font=font, fill="black")
        draw.text((x, y), line, font=font, fill="white")

    img.save(output_path)
    return output_path


# --- Slideshow generators ---

def generate_slideshow(hook: str, slides_config: list[dict]) -> list[Path]:
    """
    Generate a mixed slideshow from AI images and local assets.

    Each slide in slides_config is one of:
      {"type": "generate", "prompt": "..."}
      {"type": "asset", "path": "app-screenshots/read-aloud.png"}
      {"type": "asset", "path": "...", "overlay_text": "Some text"}

    Hook text is always overlaid on slide 1 regardless of type.
    """
    slides = []
    for i, config in enumerate(slides_config):
        path = WORK_DIR / f"slide_{i+1}.png"
        slide_type = config.get("type", "generate")

        if slide_type == "asset":
            asset_path = ASSETS_DIR / config["path"]
            if not asset_path.exists():
                raise FileNotFoundError(f"Asset not found: {asset_path}")
            resize_asset(asset_path, path)
        else:
            generate_image(config["prompt"], path)

        # Text overlay: hook on slide 1, or explicit overlay_text on any slide
        overlay_text = hook if i == 0 else config.get("overlay_text")
        if overlay_text:
            overlay_path = WORK_DIR / f"slide_{i+1}_overlay.png"
            add_text_overlay(path, overlay_text, overlay_path)
            slides.append(overlay_path)
        else:
            slides.append(path)

    return slides


def generate_reaction_slideshow(hook: str, slides_config: list[dict]) -> list[Path]:
    """Backward-compatible wrapper — converts old format to new."""
    normalized = []
    for config in slides_config:
        if "type" not in config:
            normalized.append({"type": "generate", "prompt": config["prompt"]})
        else:
            normalized.append(config)
    return generate_slideshow(hook, normalized)


def generate_stat_slideshow(scenario: dict) -> list[Path]:
    """Generate a screen-time-shock slideshow (all AI-generated data cards)."""
    daily = scenario["daily_hours"]
    yearly_hours = daily * 365
    yearly_days = round(yearly_hours / 24)
    remaining_years = scenario["life_expectancy"] - scenario["age"]
    lifetime_hours = yearly_hours * remaining_years
    lifetime_years = round(lifetime_hours / 8760, 1)

    base_prompt = (
        "Clean modern infographic card, dark purple gradient background, "
        "large centered white bold sans-serif text, minimalist, no clutter, "
        "subtle sparkle particles, elegant. Portrait 1024x1536. "
    )

    slide_texts = [
        scenario["hook"],
        f"The average {scenario['persona']} spends\n{daily} hours a day on their phone",
        f"That's {yearly_hours:,} hours per year\nor {yearly_days} full days",
        f"Over your lifetime?\nThat's {lifetime_years} years\njust on your phone",
        "What if you spent just\n3 minutes of that\nmanifesting your goals?",
        "Manifest Lock\nEarn your screen time.\nLink in bio",
    ]

    slides_config = []
    for text in slide_texts:
        slides_config.append({
            "type": "generate",
            "prompt": f"{base_prompt}Text reads: '{text}'",
        })

    return generate_slideshow(scenario["hook"], slides_config)


def post_to_tiktok_draft(image_paths: list[Path], caption: str = "") -> dict:
    """Upload slideshow as TikTok draft via Postiz API."""
    media_ids = []
    for img_path in image_paths:
        with open(img_path, "rb") as f:
            resp = requests.post(
                "https://app.postiz.com/api/v1/media",
                headers={"Authorization": f"Bearer {POSTIZ_API_KEY}"},
                files={"file": f},
            )
            resp.raise_for_status()
            media_ids.append(resp.json()["id"])

    resp = requests.post(
        "https://app.postiz.com/api/v1/posts",
        headers={
            "Authorization": f"Bearer {POSTIZ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "platform": "tiktok",
            "type": "slideshow",
            "media_ids": media_ids,
            "privacy_level": "SELF_ONLY",
            "status": "draft",
        },
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    # Example: mixed slideshow — AI images + real app screenshot
    result = generate_slideshow(
        hook="I showed my mom my lifetime screen time. She went completely silent.",
        slides_config=[
            {"type": "generate", "prompt": "Candid photo, daughter showing phone to mother at kitchen table. Portrait 1024x1536."},
            {"type": "generate", "prompt": "Close-up of smartphone showing screen time dashboard. Portrait 1024x1536."},
            {"type": "generate", "prompt": "Close-up portrait of mother, shocked expression, natural light. Portrait 1024x1536."},
            {"type": "generate", "prompt": "Infographic: dark purple, white text: 7hrs x 365 x 60yrs = 11 YEARS. Portrait 1024x1536."},
            {"type": "asset", "path": "app-screenshots/read-aloud.png"},
            {"type": "generate", "prompt": "Wide shot, mother and daughter looking at phone together, warm light. Portrait 1024x1536."},
        ],
    )
    print(f"Generated {len(result)} slides:")
    for s in result:
        print(f"  {s}")