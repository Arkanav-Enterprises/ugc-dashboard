# Prompt Generator — Video Stitcher Feature

The Prompt Generator is a collapsible panel on the `/stitcher` page that generates AI image and video prompts for Nano Banana 2 (image) and Veo 3.1 Fast (video).

## Settings Reference

### Persona

Select which character the prompt is generated for. Each persona has a **locked appearance** that Claude uses as context:

| Persona | Appearance | Expression Style | App |
|---------|-----------|-----------------|-----|
| **Aliyah** | American-Indian woman, early 20s, dark wavy shoulder-length hair, warm brown eyes, black oversized t-shirt, bedroom setting | Dramatic | Both |
| **Riley** | White woman, early 20s, brown wavy hair, freckles, warm hazel eyes, cozy bedroom, golden lighting | Intimate | Both |
| **Sanya** | Dark-haired woman, early 20s, band tee, outdoor park, natural daylight | Subtle | JournalLock |
| **Emilly** | Brunette woman, early 20s, red sweatshirt, cozy living room, warm lamp | Vulnerable | ManifestLock |

### Type

- **Image** — Generates a Nano Banana 2 prompt (iPhone Pro Max photography style). Output is a JSON with `full_prompt_string`, `negative_prompt`, and structured `prompt_components`.
- **Video** — Same as image, plus a `video_prompt` field formatted for Veo 3.1 Fast with timestamped action beats (`[00:00-00:02]`), selfie POV framing, and handheld drift instructions.

### Mode

Controls how the character is described in the prompt:

- **Existing Character** (default) — Uses a reference image for the character's face/body. The `subject` field in the prompt only describes pose, expression, and clothing changes — NOT the character's fixed appearance (hair color, ethnicity, etc.). The `full_prompt_string` starts with "Using the attached reference image as the character, ...". Best for generating consistent content with an established persona.

- **New Character** — Generates a complete character description from scratch. The prompt includes full appearance details. Use this when creating a new persona or one-off character.

- **Mood Reference** — Uses a reference image only for lighting, color palette, and vibe. A new character is generated — the image is not used for face/body matching. Use this to capture the aesthetic of an existing photo with a different character.

### Reference Image

Only visible in **Existing Character** and **Mood Reference** modes. Upload a photo that will be sent to Claude as context:

- **Existing Character mode**: Upload a clear photo of the persona. Claude generates a prompt that matches this person.
- **Mood Reference mode**: Upload any photo with the lighting/colors/vibe you want. Claude uses it for aesthetic reference only.

Supports JPEG, PNG, WebP. The image is base64-encoded and sent directly to the Claude API.

### Scene Description

Free-text description of what's happening in the scene. Be specific about:

- **Setting**: where (bed, desk, mirror, outdoor)
- **Action**: what they're doing (looking at phone, putting phone down, journaling)
- **Expression**: physical specifics, not emotions (furrowed brow, slight smile, eyes wide)
- **Lighting details**: blue phone glow, warm lamp, golden hour

**Image examples:**
- "In bed at night, looking at phone with worried expression, blue phone glow on face"
- "Mirror selfie, holding phone low, confident half-smile, bathroom with warm overhead light"

**Video examples:**
- "Worried expression looking at phone, then slowly smiles and puts phone down"
- "Reading journal with focused expression, then looks up at camera with surprised relief"

## Output

After generation, the panel shows:

1. **JSON output** — Full structured prompt with all components
2. **Copy Full Prompt** — Copies `full_prompt_string` (paste directly into Nano Banana / image gen)
3. **Copy JSON** — Copies the entire JSON object
4. **Copy Video Prompt** — Only visible for video type, copies the `video_prompt` field (paste into Veo 3.1)
5. **Use as Scene** — Adds a new scene to the stitcher below with the `full_prompt_string` pre-filled as the text overlay

## Technical Details

- Backend: `services/prompt_generator.py` → calls Claude API (Sonnet) with Nano Banana skill context
- Router: `routers/prompts.py` → `POST /api/prompts/generate`, `GET /api/prompts/personas`
- Cost: ~$0.01 per generation (single Claude API call)
- Persona appearances are defined in `prompt_generator.py` → `PERSONAS` dict. Update there as characters evolve.
