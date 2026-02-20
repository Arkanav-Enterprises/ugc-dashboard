#!/usr/bin/env python3
"""
generate_variants.py — Generate persona video variants for asset pool.

Takes a reference image of a persona and generates new video clips with
different backgrounds/outfits using Replicate image-to-video models.

Usage:
    python3 generate_variants.py --persona sanya                    # Random background variant
    python3 generate_variants.py --persona sophie --scene cafe       # Specific scene
    python3 generate_variants.py --persona sanya --scene bedroom --outfit "navy blue hoodie"
    python3 generate_variants.py --persona sophie --list-scenes      # Show available scenes
    python3 generate_variants.py --persona sanya --model hailuo      # Use specific model

Output goes to output/variants/{persona}/ for review.
Move approved clips into assets/{persona}/hook/ or assets/{persona}/reaction/
"""

import os
import sys
import json
import time
import random
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
REF_IMAGES_DIR = ASSETS_DIR / "reference-images"
OUTPUT_DIR = PROJECT_ROOT / "output" / "variants"

# Supported Replicate models for image-to-video
MODELS = {
    "kling": "kwaivgi/kling-v2.1",
    "hailuo": "minimax/hailuo-2.3",
    "veo": "google/veo-3.1-fast",
}
DEFAULT_MODEL = "veo"

# Scene presets — only the SCENE paragraph changes, SUBJECT stays locked
SCENE_PRESETS = {
    # Indoor scenes (best for Sanya's cozy vibe)
    "cozy-room": "Cozy living room with warm ambient lighting from a bedside lamp, soft beige couch visible in background, wooden bookshelf with books, warm yellow-orange tones throughout the space; evening atmosphere.",
    "bedroom": "Minimalist bedroom with soft morning light streaming through sheer curtains, white bedding visible in background, small potted plant on nightstand; calm and peaceful morning atmosphere.",
    "cafe": "Cozy corner of a quiet coffee shop, warm overhead pendant light, exposed brick wall in background, steaming cup on a small wooden table just out of frame; soft indoor afternoon light.",
    "library": "Quiet library nook with tall wooden bookshelves filled with books, soft warm reading light, leather armchair arm visible at edge of frame; peaceful studious atmosphere.",

    # Outdoor scenes (best for Sophie's grounded vibe)
    "park": "Outdoor park setting with lush green grass and leafy trees in bright daylight; late morning or early afternoon with soft, natural sunlight casting gentle shadows.",
    "beach": "Sandy beach at golden hour, gentle waves in the far background, warm sunset light casting a golden glow; relaxed coastal atmosphere with soft ocean breeze.",
    "rooftop": "Urban rooftop terrace at golden hour, city skyline softly blurred in background, string lights overhead, concrete railing; warm evening urban atmosphere.",
    "garden": "Lush home garden with flowering bushes and a stone pathway, dappled sunlight through tree canopy, birds audible; peaceful suburban afternoon.",
    "campus": "University campus quad with green lawns and old brick buildings in background, students blurred in far distance, bright midday sun; youthful energetic atmosphere.",
}

# Base prompt templates per persona
# SUBJECT section stays fixed to preserve identity. SCENE gets swapped.
PROMPT_TEMPLATES = {
    "sanya": {
        "subject": "Woman with long wavy brown hair, wearing {outfit}, natural makeup highlighting her freckles; nude colored nails with two rings on her right hand (one thick, one thin and delicate).",
        "default_outfit": "a red crewneck sweatshirt",
        "action_hook": "The woman immediately has her hand covering her mouth with wide surprised eyes and a gentle smile, eyes crinkling with amusement; she holds this pose, barely moving; camera holds perfectly steady with very subtle zoom in. The key expression happens in the first 2 seconds.",
        "action_reaction": "The woman is already smiling warmly looking directly into the camera, slight head tilt, relaxed and happy; she holds this natural smile pose; camera holds steady. The key expression is visible from the very first frame.",
        "cinematography": "Soft natural lighting balanced to avoid harsh contrasts; warm and inviting emotional tone conveying shyness and genuine amusement; natural color palette.",
        "audio": "No dialogue. No music. Ambient room tone only.",
    },
    "sophie": {
        "subject": "Young woman with wavy brown hair, wearing {outfit}, natural makeup highlighting her freckles; nude colored nails with two rings on her right hand (one thick, one thin and delicate).",
        "default_outfit": "a sleeveless floral dress with a pattern of small red, blue, and orange flowers and green leaves",
        "action_hook": "The woman already has her hand covering her mouth with wide eyes showing amused surprise; she holds this pose barely moving; camera holds perfectly steady with very subtle zoom in. The key expression happens in the first 2 seconds.",
        "action_reaction": "The woman is already looking directly into the camera with a playful tongue-out expression, tongue pointing downward toward her chin, eyes bright and mischievous; she holds this pose; camera holds steady. The key expression is visible from the very first frame.",
        "cinematography": "Soft natural lighting balanced to avoid harsh contrasts; warm and inviting emotional tone conveying playfulness; natural color palette emphasizing greens and earth tones.",
        "audio": "No dialogue. No music. Ambient natural outdoor sounds only.",
    },
}


def build_prompt(persona: str, scene_key: str, outfit: str | None = None, clip_type: str = "hook") -> str:
    """Build a full video generation prompt from components."""
    template = PROMPT_TEMPLATES[persona]
    scene_desc = SCENE_PRESETS[scene_key]
    outfit_str = outfit or template["default_outfit"]

    action = template["action_hook"] if clip_type == "hook" else template["action_reaction"]

    prompt = f"""No subtitles. No music.

SHOT — Medium close-up, centered on the woman's face and upper body.

SUBJECT — {template['subject'].format(outfit=outfit_str)}

SCENE — {scene_desc}

ACTION AND CAMERA MOTION — {action}

CINEMATOGRAPHY — {template['cinematography']}

AUDIO — {template['audio']}

STYLE — Naturalistic aesthetic with sharp 4K clarity, vibrant colors; no text overlays, subtitles, or captioning."""

    return prompt


def upload_reference_image(persona: str) -> str:
    """Upload reference image to Replicate storage, return URL."""
    import replicate

    ref_path = REF_IMAGES_DIR / f"{persona}.png"
    if not ref_path.exists():
        ref_path = REF_IMAGES_DIR / f"{persona}.jpg"
    if not ref_path.exists():
        print(f"ERROR: No reference image found at {REF_IMAGES_DIR}/{persona}.png or .jpg")
        print(f"Place your reference image there and retry.")
        sys.exit(1)

    print(f"Uploading reference image: {ref_path}")
    file_obj = replicate.files.create(ref_path)
    url = file_obj.urls["get"]
    print(f"Uploaded: {url}")
    return url


def generate_video(prompt: str, image_url: str, model_key: str, duration: str = "5") -> str:
    """Call Replicate to generate video from image + prompt. Returns video URL."""
    import replicate

    model_id = MODELS[model_key]
    print(f"\nGenerating video with {model_key} ({model_id})...")
    print(f"Duration: {duration}s")
    print(f"Prompt preview: {prompt[:150]}...")

    input_params = {
        "prompt": prompt,
    }

    # Model-specific parameters
    if model_key == "kling":
        input_params["start_image"] = image_url
        input_params["duration"] = int(duration)
        input_params["mode"] = "standard"
    elif model_key == "hailuo":
        input_params["first_frame_image"] = image_url
        input_params["duration"] = int(duration)
    elif model_key == "veo":
        input_params["image"] = image_url
        input_params["duration"] = int(duration)
        input_params["aspect_ratio"] = "9:16"
        input_params["generate_audio"] = False

    output = replicate.run(model_id, input=input_params)
    video_url = output.url if hasattr(output, "url") else str(output)

    return video_url


def download_video(video_url: str, output_path: Path) -> Path:
    """Download generated video from Replicate URL."""
    import requests

    if not video_url:
        print(f"ERROR: No video URL returned from Replicate")
        sys.exit(1)

    print(f"Downloading video from: {video_url[:80]}...")
    resp = requests.get(video_url, timeout=120)
    resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)
    print(f"Saved: {output_path} ({len(resp.content) / 1024 / 1024:.1f}MB)")
    return output_path


def trim_video(input_path: Path, duration_seconds: float) -> Path:
    """Trim video to first N seconds using ffmpeg. Returns trimmed path."""
    trimmed_path = input_path.with_stem(input_path.stem + "_trimmed")
    cmd = (
        f'ffmpeg -y -i "{input_path}" -t {duration_seconds} '
        f'-c:v libx264 -preset fast -crf 18 -an "{trimmed_path}" 2>/dev/null'
    )
    os.system(cmd)
    if trimmed_path.exists():
        print(f"Trimmed to {duration_seconds}s: {trimmed_path.name}")
        return trimmed_path
    else:
        print(f"  WARN: ffmpeg trim failed, keeping original")
        return input_path


def list_scenes():
    """Print available scene presets."""
    print("\nAvailable scene presets:\n")
    print("  INDOOR (best for Sanya):")
    for key in ["cozy-room", "bedroom", "cafe", "library"]:
        print(f"    --scene {key:12s}  {SCENE_PRESETS[key][:70]}...")
    print("\n  OUTDOOR (best for Sophie):")
    for key in ["park", "beach", "rooftop", "garden", "campus"]:
        print(f"    --scene {key:12s}  {SCENE_PRESETS[key][:70]}...")


def main():
    parser = argparse.ArgumentParser(description="Generate persona video variants")
    parser.add_argument("--persona", required=True, choices=["sanya", "sophie"])
    parser.add_argument("--scene", default=None, help="Scene preset name (use --list-scenes to see options)")
    parser.add_argument("--outfit", default=None, help="Override outfit description (e.g., 'navy blue hoodie')")
    parser.add_argument("--clip-type", default="both", choices=["hook", "reaction", "both"],
                        help="Generate hook clip, reaction clip, or both (default: both)")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=list(MODELS.keys()),
                        help=f"Replicate model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--duration", default="5", help="Video duration in seconds (default: 5, most APIs minimum)")
    parser.add_argument("--list-scenes", action="store_true", help="List available scene presets")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without generating")
    parser.add_argument("--prompt-only", action="store_true", help="Print full prompt and exit")
    parser.add_argument("--no-trim", action="store_true", help="Skip auto-trim (keep full 5s clips)")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Auto-move trimmed clips into asset folders (skip review)")
    args = parser.parse_args()

    if args.list_scenes:
        list_scenes()
        return

    # Pick scene: use specified, or random
    if args.scene:
        if args.scene not in SCENE_PRESETS:
            print(f"ERROR: Unknown scene '{args.scene}'. Use --list-scenes to see options.")
            sys.exit(1)
        scene = args.scene
    else:
        indoor = ["cozy-room", "bedroom", "cafe", "library"]
        outdoor = ["park", "beach", "rooftop", "garden", "campus"]
        if args.persona == "sanya":
            scene = random.choice(indoor + ["park"])
        else:
            scene = random.choice(outdoor + ["cafe"])
        print(f"Random scene selected: {scene}")

    # Trim durations: hook = 2s, reaction = 1s
    TRIM_DURATIONS = {"hook": 2.0, "reaction": 1.0}

    clip_types = ["hook", "reaction"] if args.clip_type == "both" else [args.clip_type]
    generated_files = []

    for clip_type in clip_types:
        prompt = build_prompt(args.persona, scene, args.outfit, clip_type)

        if args.prompt_only or args.dry_run:
            print(f"\n{'='*60}")
            print(f"PERSONA: {args.persona} | SCENE: {scene} | TYPE: {clip_type}")
            print(f"{'='*60}")
            print(prompt)
            if args.dry_run:
                continue
            return

        # Upload reference image
        image_url = upload_reference_image(args.persona)

        # Generate
        video_url = generate_video(prompt, image_url, args.model, args.duration)

        # Download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        outfit_tag = args.outfit.replace(" ", "-")[:20] if args.outfit else "default"
        filename = f"{args.persona}_{clip_type}_{scene}_{outfit_tag}_{timestamp}.mp4"
        output_path = OUTPUT_DIR / args.persona / filename

        raw_path = download_video(video_url, output_path)

        # Auto-trim to usable duration
        if not args.no_trim:
            trimmed_path = trim_video(raw_path, TRIM_DURATIONS[clip_type])
            generated_files.append((clip_type, trimmed_path))
        else:
            generated_files.append((clip_type, raw_path))

    # Auto-approve: move trimmed clips into asset folders
    if args.auto_approve and generated_files:
        import shutil
        for clip_type, filepath in generated_files:
            dest_dir = ASSETS_DIR / args.persona / clip_type
            dest_dir.mkdir(parents=True, exist_ok=True)

            existing = sorted(dest_dir.glob("*.mp4"))
            next_num = len(existing) + 1
            dest = dest_dir / f"{next_num:03d}.mp4"

            shutil.copy2(filepath, dest)
            print(f"  → Added to pool: {dest}")

        print(f"\nAssets added. Autopilot will pick them up automatically.")
    elif generated_files:
        print(f"\n{'='*60}")
        print(f"Review output in: {OUTPUT_DIR / args.persona}/")
        if not args.no_trim:
            print(f"Clips already trimmed (hook=2s, reaction=1s).")
        print(f"To add to asset pool, move to:")
        print(f"  assets/{args.persona}/hook/")
        print(f"  assets/{args.persona}/reaction/")
        print(f"Or re-run with --auto-approve to skip review.")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
