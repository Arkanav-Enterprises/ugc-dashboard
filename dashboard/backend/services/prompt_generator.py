"""Prompt generator — generates image and video prompts via Claude."""

import json
import os

import httpx
from pathlib import Path

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PIPELINE_ROOT = Path(os.environ.get("PIPELINE_ROOT", "/root/openclaw"))
MODEL = "claude-sonnet-4-5-20250929"

PERSONAS = {
    "aliyah": {
        "app_primary": "both",
        "base_appearance": (
            "American-Indian woman, early 20s, dark wavy shoulder-length hair, "
            "warm brown eyes, natural skin with visible pores and subtle freckles. "
            "Black oversized t-shirt. In bed, warm bedside lamp, hotel/bedroom setting."
        ),
        "expression_style": "dramatic",
    },
    "riley": {
        "app_primary": "both",
        "base_appearance": (
            "White woman, early 20s, brown wavy hair past shoulders with freckles, "
            "warm hazel eyes, natural skin texture. Cozy warm-toned bedroom, "
            "golden ambient lighting."
        ),
        "expression_style": "intimate",
    },
    "sanya": {
        "app_primary": "journal-lock",
        "base_appearance": (
            "Dark-haired woman, early 20s, band tee, outdoor park setting. "
            "Natural daylight, grounded casual energy."
        ),
        "expression_style": "subtle",
    },
    "emilly": {
        "app_primary": "manifest-lock",
        "base_appearance": (
            "Brunette woman, early 20s, red sweatshirt, cozy living room. "
            "Warm lamp lighting, intimate confessional energy."
        ),
        "expression_style": "vulnerable",
    },
}

NANO_BANANA_INLINE = """
Generate mathematically precise image generation prompts simulating iPhone 16/17 Pro Max photography.

Allowed focal lengths: 24mm (Main), 13mm (Ultra Wide), 77mm (Telephoto).
Required: Apple ProRAW color science, Deep Fusion, computational bokeh, Smart HDR.
Always inject: digital noise, skin texture (pores, blemishes), slightly blown highlights, natural snapshot framing.

JSON Schema:
{
  "meta_data": { "style": "iPhone Pro Max Photography", "aspect_ratio": "9:16", "mode": "..." },
  "prompt_components": {
    "subject": "...", "environment": "...", "lighting": "...",
    "camera_gear": "...", "processing": "...", "imperfections": "..."
  },
  "full_prompt_string": "Combined comma-separated string",
  "negative_prompt": "professional camera, DSLR, bokeh balls, anamorphic, cinema lighting, studio lighting"
}

Mode 2 (Existing Character): subject field must NEVER describe fixed appearance. Only pose, expression, clothing changes.
full_prompt_string must begin with "Using the attached reference image as the character, "
negative_prompt must additionally include "different person, different face, changed ethnicity, altered facial features"
"""


def _load_skill_file(filename: str) -> str:
    path = PIPELINE_ROOT / "skills" / filename
    if path.exists():
        return path.read_text()
    return ""


def _build_system_prompt(prompt_type: str, mode: str, persona: str) -> str:
    nano_banana_skill = _load_skill_file("nano-banana-iphone-prompts.md") or NANO_BANANA_INLINE
    persona_data = PERSONAS.get(persona, {})

    system = f"""You are a prompt generator for AI image and video models.

## Your Skill: Nano Banana iPhone Prompt Generator

{nano_banana_skill}

## Current Persona: {persona}

Base appearance (LOCKED — do not include in Mode 2 subject field):
{persona_data.get('base_appearance', 'Not defined')}

Expression style: {persona_data.get('expression_style', 'dramatic')}
Primary app: {persona_data.get('app_primary', 'both')}

## Current Mode: {mode}

## Output Type: {prompt_type}
"""

    if prompt_type == "video":
        system += """
## Video Prompt Rules (Veo 3.1 Fast)

In addition to the image JSON, also generate a `video_prompt` field. Structure:

```
"video_prompt": "Camera held at arm's length, selfie POV (thats where the camera is). [Setting].
[00:00-00:02] [Initial state — expression, body language. Subtle handheld drift.]
[00:02-00:04] [Reaction — specific physical expression change.]
Photorealistic, UGC selfie quality, natural skin texture, subtle handheld camera drift throughout."
```

Rules:
- Always include "Subtle handheld drift" for authentic selfie movement
- Always state "(thats where the camera is)"
- Describe expressions with physical specifics, not emotions
- Output aspect_ratio must be "9:16"
- Duration: 4 seconds
- generate_audio: false
"""

    system += """
## Response Format

Respond with ONLY the JSON object. No markdown backticks, no preamble, no explanation. Just valid JSON.
"""
    return system


async def generate_prompt(
    persona: str,
    scene_description: str,
    prompt_type: str = "image",
    mode: str = "existing_character",
    reference_image_base64: str | None = None,
    reference_image_media_type: str = "image/png",
) -> dict:
    """Generate an image or video prompt via Claude."""

    system = _build_system_prompt(prompt_type, mode, persona)

    user_content = []

    if reference_image_base64 and mode in ("existing_character", "mood_reference"):
        user_content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": reference_image_media_type,
                "data": reference_image_base64,
            },
        })

    mode_instruction = {
        "new_character": "Generate a Mode 1 (New Character) prompt.",
        "existing_character": "Generate a Mode 2 (Existing Character) prompt. Do NOT describe the character's fixed appearance in the subject field — only pose, expression, clothing changes, and scene.",
        "mood_reference": "Generate a Mode 3 (Mood Reference) prompt. Use the attached image for lighting/color/vibe only, create a new character.",
    }

    user_text = f"""{mode_instruction.get(mode, '')}

Persona: {persona}
Scene: {scene_description}
Prompt type: {prompt_type}

Generate the JSON prompt now."""

    user_content.append({"type": "text", "text": user_text})

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MODEL,
                "max_tokens": 2000,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
            },
        )
        if resp.status_code != 200:
            error_body = resp.text
            raise RuntimeError(f"Claude API error {resp.status_code}: {error_body}")
        data = resp.json()

    raw_text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            raw_text += block["text"]

    # Strip markdown fences if present
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"raw_text": raw_text, "error": "Failed to parse JSON"}
