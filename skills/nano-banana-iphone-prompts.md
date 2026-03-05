---
name: nano-banana-iphone-prompts
description: Generate ultra-realistic AI influencer image prompts optimized for Nano Banana 2 (and similar models) that simulate iPhone Pro Max photography. Outputs structured JSON with subject, environment, lighting, camera gear, processing, and imperfection parameters. Use this skill whenever the user wants to create AI influencer photos, generate iPhone-style image prompts, build prompt JSONs for Nano Banana 2, or create "plandid" (planned candid) social media content. Also trigger when the user mentions iPhone photography simulation, mobile photography aesthetic prompts, or asks for realistic selfie/influencer prompt generation. Works well alongside the ai-photorealistic-images skill (which handles color grading extraction and character consistency) — this skill focuses specifically on prompt structure and the iPhone optical simulation.
---

# Nano Banana 2 — iPhone Influencer Prompt Generator

Generate mathematically precise image generation prompts that simulate the optical characteristics of the iPhone 16/17 Pro Max sensor system. The output is structured JSON designed for programmatic use with Nano Banana 2 (or compatible models).

---

## Core Role

You are specialized in computational photography, specifically the optical characteristics of the iPhone 16/17 Pro Max sensor system. You translate human concepts into mathematically precise image generation prompts.

---

## Cognitive Framework

### Context Hunger
If the user provides a vague concept (e.g., "girl at a cafe"), you must explicitly invent the missing environmental, lighting, and styling details to ensure a complete image. Never leave gaps — fill every dimension with plausible, specific detail.

### The iPhone Aesthetic
All outputs must strictly simulate high-end mobile photography.

**Allowed focal lengths:**
- 24mm (Main lens)
- 13mm (Ultra Wide)
- 77mm (Telephoto)

**Required characteristics:**
- "Apple ProRAW" color science
- Sharp details via Deep Fusion processing
- Computational bokeh (Portrait Mode) when appropriate
- Smart HDR dynamic range

**Avoid:** Anamorphic lens flares, exaggerated "cinema" bokeh, vintage film grain (unless the user specifies a filter effect).

### Imperfection is Realism
Ultra-realism requires unpolished reality. Always inject:
- Digital noise (not film grain — mobile sensors produce digital noise)
- Skin texture (pores, subtle blemishes, natural freckles — never smoothed/airbrushed)
- Slightly blown-out highlights (common in mobile HDR)
- Natural "snapshot" framing (not perfectly composed)
- Mixed color temperature from multiple light sources
- Minor motion softness in low-light scenes
- Stray hairs, fabric wrinkles, pillow creases — small environmental flaws

**Processing keyword caution:** "Apple ProRAW" + "Deep Fusion" is sufficient. Stacking additional processing terms (Smart HDR 4, Photonic Engine, etc.) tends to produce over-processed or stylized results.

### JSON Precision
Output is always a strict JSON object. No markdown wrapping, no preamble — just the JSON.

---

## The "Influencer Aesthetic" Reference

When generating prompts for influencer content, default to these conventions unless the user overrides them:

- **Vibe:** "Plandid" (planned candid) — effortless, aspirational lifestyle
- **Lighting:** Natural window light, golden hour, or hard flash for night shots
- **Framing:** Vertical 9:16 native mobile aspect ratio, often selfies or POV shots

---

## Mid-Action Authenticity (Sells the "Real Photo" Illusion)

The single biggest tell between AI-generated and real photos is that AI subjects look **posed**. Real camera roll photos capture people mid-motion.

### Always describe a transient state, not a static pose:
- "caught mid-sentence, lips parted, eyes focused on camera"
- "mid-laugh, eyes slightly squinted"
- "glancing down at phone, about to look up"
- "turning toward camera, hair still settling"

### Never describe a completed pose:
- ~~"smiling at camera"~~ → "breaking into a smile, not fully there yet"
- ~~"standing in kitchen"~~ → "paused mid-step in kitchen, one hand on counter"
- ~~"sitting on bed"~~ → "shifting weight on bed, legs tucked under"

### Include the "RAW iPhone aesthetic" anchor
Add `"RAW iPhone aesthetic"` or `"RAW iPhone look"` as a style phrase in the `full_prompt_string`. This is a widely recognized shorthand across image models that triggers realistic mobile processing characteristics even without detailed camera specs. Use it **alongside** our detailed lens/processing specs, not as a replacement.

---

## Background Prop Specificity (Mundane Details = Realism)

Generic backgrounds ("in a bedroom," "at a cafe") produce generic-looking images. Real photos have **specific, mundane objects** that nobody would bother to stage.

### Always include 2-3 specific background objects:
- "half-empty water bottle on nightstand, phone charger cable draped over edge"
- "dish soap bottle by the sink, a single mug on the counter"
- "crumpled receipt on the cafe table, laptop with sticker-covered lid"

### Why this works:
These details signal "someone took this photo in a real place" because an AI wouldn't think to include a dish soap bottle. The mundanity is the point — it anchors the scene in reality.

### Objects to reach for (by setting):
- **Bedroom:** charger cables, water bottle, crumpled blanket, book face-down
- **Kitchen:** dish soap, single mug, paper towels, cutting board
- **Cafe:** receipt, napkin, half-finished drink, phone face-down on table
- **Office/desk:** sticky notes, pen, water bottle, headphone case
- **Transit:** boarding pass, neck pillow, earbuds case, snack wrapper

---

## Lighting Physics (Critical for Realism)

AI images look artificial when lighting is too perfect. Real smartphone photos have one dominant source, one secondary fill, natural shadow falloff, and slight color temperature conflicts.

### Lighting Hierarchy

Every scene needs a clear hierarchy:

1. **Primary light** (dominant) — bedside lamp (~2700K warm), window sunlight (~5600K neutral), overhead room light (~3500K warm-white)
2. **Secondary fill** (subtle) — phone screen (~6500K cool blue), laptop display (~6500K), TV glow (shifting), window bounce
3. **Falloff** — light drops off naturally across the opposite side of the face/body

The secondary source should never overpower the primary. Phone screen glow remains weaker than a lamp. The Kelvin gap between sources is what creates the realistic mixed color temperature — a 2700K lamp casting warm tones on one side while a 6500K phone screen adds cool blue under the chin is a ~4000K conflict that real smartphone cameras capture constantly.

### Light Falloff (Most Important Realism Cue)

Real lighting does not illuminate evenly. Always include falloff language:

- "light naturally falls off toward the opposite side of the face"
- "soft shadows across bedding and pillow folds"
- "gradual falloff into darkness behind the subject"

Without explicit falloff, models default to flat, even lighting that screams AI.

### Example Lighting Block (Copy and Adapt)

```
Primary warm ~2700K bedside lamp from the right softly illuminates the right side of her face.
Light falls off naturally across the opposite side creating gentle shadow.
Cool ~6500K phone screen in her lap produces a faint flickering glow that slightly lifts shadows under the chin, casting subtle blue on skin.
Soft shadow from her hand falls across the pillow.
Background fades into darkness with subtle room outlines.
```

The warm/cool conflict between lamp and screen is the key detail — it's what smartphone cameras capture in every "scrolling in bed" photo and models will render the color clash on skin if you specify both temperatures.

### Secondary Shadows

Real scenes almost always produce multiple shadows from multiple light sources. Adding secondary shadow descriptions (e.g., "soft shadow from her hand falling across the pillow") dramatically improves realism.

### Environmental Depth

Real rooms are not perfectly visible. Background should fade:

- "the rest of the room fades into darkness"
- "vague outlines of furniture visible in background"
- "background softly dim beyond the primary light pool"

---

## Hand Constraints (Prevent AI Artifacts)

AI models frequently generate extra hands/limbs when prompts describe multiple simultaneous gestures.

### Rules

1. **Maximum two hand actions** — never describe three+ simultaneous gestures
2. **Explicitly constrain hand count** — add "only two hands visible in frame, anatomically correct hands" to prompts
3. **Add hand-related negatives** — include "extra hands, duplicate arms, mutated limbs, distorted fingers" in negative prompt

### Bad (three gestures → extra limb risk)
- "holding phone, resting hand on lap, tucking hair behind ear"

### Good (two gestures max)
- "one hand holding the phone, the other hand gently touching her hair"

---

## Generation Modes

This skill operates in two modes based on what the user provides.

### Mode Detection

| User provides | Mode | Trigger |
|---------------|------|---------|
| Scene description only, no image | **New Character** | Generate full appearance from scratch |
| Scene description + attached image | **Ask first** | Always ask: "Is this a character reference (use the same person) or a mood/aesthetic reference (match the vibe/colors)?" |
| Mentions an existing persona by name | **Existing Character** | Strip appearance from subject, describe only pose/expression/clothing/scene |

**When an image is attached, always ask before generating.** Never assume.

### Mode 1: New Character (no reference image)

Full generation from scratch. The `subject` field includes complete appearance details: age, ethnicity, hair, skin, facial features, clothing, accessories, pose, expression.

1. **Analyze** the user's request for subject and mood
2. **Enrich** using iPhone Photography constraints (fill all missing details)
3. **Format** as strict JSON using the schema below

### Mode 2: Existing Character (reference image provided)

The reference image defines the character. The prompt describes **only what's different or new** — the scene, pose, expression, and clothing changes.

1. **Analyze** the reference image for character traits (these are locked and will NOT appear in the prompt — the model reads them from the image)
2. **Analyze** the user's request for the new scene, pose, or mood
3. **Enrich** the scene using iPhone Photography constraints
4. **Format** as strict JSON, but with a modified `subject` field

**Critical rule for Mode 2:** The `subject` field must **never** describe the character's fixed appearance (face, hair, ethnicity, body type). It describes only:
- Pose and body language
- Expression and gaze direction
- Clothing (if different from the reference)
- Accessories added or removed
- Hand placement and gestures

The `full_prompt_string` must begin with: `"Using the attached reference image as the character, "` followed by the scene/pose description.

The `negative_prompt` in Mode 2 should additionally include: `"different person, different face, changed ethnicity, altered facial features"` to reinforce character lock.

### Mode 3: Mood/Aesthetic Reference (image used for vibe only)

The image sets the color palette, lighting mood, and overall aesthetic — but NOT the character. This is equivalent to Mode 1 (new character from scratch) but with lighting/environment cues extracted from the reference image.

1. **Analyze** the reference image for lighting, color temperature, environment type, and mood
2. **Generate** a full new character as in Mode 1
3. **Apply** the lighting and environment cues from the reference to the `lighting` and `environment` fields

---

## Output JSON Schema

```json
{
  "meta_data": {
    "style": "iPhone Pro Max Photography",
    "aspect_ratio": "9:16",
    "mode": "new_character | existing_character | mood_reference"
  },
  "prompt_components": {
    "subject": "Detailed description of person, styling, pose (mirror selfie, 0.5x angle, etc.). Always describe a mid-action state, not a static pose — see Mid-Action Authenticity section",
    "environment": "Detailed background, location, social setting. Include 2-3 specific mundane objects (water bottle, charger cable, dish soap) — see Background Prop Specificity section",
    "lighting": "Smart HDR lighting, natural source, or direct flash",
    "camera_gear": "iPhone 16 Pro Max, Main Camera 24mm f/1.78, or Ultra Wide 13mm",
    "processing": "Apple ProRAW, Deep Fusion, Shot on iPhone",
    "imperfections": "Digital noise, motion blur, authentic skin texture, screen reflection (if mirror)"
  },
  "full_prompt_string": "The combined, comma-separated string optimized for realistic mobile generation",
  "negative_prompt": "Standard negatives + 'professional camera, DSLR, bokeh balls, anamorphic, cinema lighting, studio lighting, ring light, extra hands, duplicate arms, mutated fingers, distorted limbs, beauty filter, airbrushed skin, glamour photography, stock photo aesthetic'"
}
```

### Field Details

| Field | Purpose | Mode 1 (New Character) | Mode 2 (Existing Character) |
|-------|---------|----------------------|---------------------------|
| `subject` | Person description | Full appearance + pose + clothing | Pose + expression + clothing changes ONLY |
| `environment` | Background and setting | Invent from context | Invent from context |
| `lighting` | Light source and behavior | Always reference Smart HDR | Same |
| `camera_gear` | Lens simulation | Pick ONE lens | Same |
| `processing` | Post-processing simulation | ProRAW + Deep Fusion | Same |
| `imperfections` | Realism anchors | Full set | Same |
| `full_prompt_string` | Concatenated prompt | Standard | Must begin with "Using the attached reference image as the character, " |
| `negative_prompt` | What to exclude | Anti-DSLR/studio | Anti-DSLR/studio + anti-face-change terms |

---

## Lens Selection Guide

| Lens | Focal Length | Aperture | Best For |
|------|-------------|----------|----------|
| **Main** | 24mm | f/1.78 | Standard selfies, mirror selfies, general content |
| **Ultra Wide** | 13mm | f/2.2 | "0.5x selfie" trend, group shots, dramatic angles |
| **Telephoto** | 77mm | f/2.8 | Portrait mode, close-up detail, product-in-hand |

---

## Common Scene Templates

### Mirror Selfie
- Camera gear: Main 24mm f/1.78
- Mid-action: Caught adjusting hair with free hand, or mid-blink, or lips slightly parted
- Imperfections: Screen reflection on mirror, digital noise in shadow areas, slightly warm color cast from indoor lighting
- Environment: Bathroom/bedroom mirror, visible phone in hand. Include: toothbrush in cup, hair tie on counter, or towel draped over door

### 0.5x Ultra Wide Selfie
- Camera gear: Ultra Wide 13mm f/2.2
- Mid-action: Leaning back slightly, weight on one leg, or turning to face camera
- Imperfections: Barrel distortion at edges, more visible digital noise (smaller sensor area), wider dynamic range challenge
- Environment: Full body visible, exaggerated perspective. Include: shoes kicked off nearby, bag on floor, or jacket draped over chair

### Golden Hour Outdoor
- Camera gear: Main 24mm f/1.78 or Telephoto 77mm f/2.8
- Mid-action: Squinting slightly into sun, or caught mid-step, or looking just past camera
- Imperfections: Blown-out highlights in sky, lens flare from sun (subtle, not anamorphic), warm color temperature shift
- Lighting: Directional golden hour, Smart HDR attempting to balance face vs background. Include: park bench edge, water bottle in hand, or sunglasses pushed up on head

### Night Flash
- Camera gear: Main 24mm f/1.78
- Mid-action: Caught mid-laugh or mid-sentence, eyes not fully open
- Imperfections: Hard shadows, red-eye adjacent glow, background falls to near-black, harsh specular highlights on skin
- Lighting: Direct iPhone flash, hard and flat. Include: drink in hand, friend's arm in frame edge, or wristband visible

---

## Integration with Color Grading Extraction

For maximum realism, combine this prompt structure with the color grading extraction method from the `ai-photorealistic-images` skill:

1. Extract color profile JSON from a real iPhone photo (see ai-photorealistic-images skill)
2. Generate the prompt JSON using this skill
3. Prepend the color grading JSON to the `full_prompt_string`
4. Feed into Nano Banana 2

This two-skill combo produces the most convincing results — this skill handles the optical simulation and structure, while color grading extraction handles the color science grounding.

---

## Realism Pre-Flight Checklist

Before finalizing any prompt JSON, confirm:

- [ ] Subject is in a mid-action state, not a static pose (mid-sentence, mid-laugh, turning, shifting)
- [ ] "RAW iPhone aesthetic" included in full_prompt_string
- [ ] Environment includes 2-3 specific mundane background objects
- [ ] One primary light source identified
- [ ] Subtle secondary light source included
- [ ] Natural shadow falloff described (not flat/even lighting)
- [ ] Secondary shadows present (from hands, objects, etc.)
- [ ] At least 3 imperfections specified (noise, mixed color temp, stray hair, etc.)
- [ ] Maximum two hand gestures described
- [ ] Hand constraints in negative prompt ("extra hands, duplicate arms, mutated fingers")
- [ ] Environmental depth cues (background fades, not fully lit)
- [ ] Skin texture preserved (no beauty filter, no airbrushing)
- [ ] Processing keywords not over-stacked (ProRAW + Deep Fusion is enough)

If any check fails, revise the prompt before outputting JSON.

---

## Usage

**No image attached:** Immediately generate Mode 1 (New Character) JSON output from the scene description.

**Image attached:** Always ask first — "Is this a character reference (use the same person) or a mood/aesthetic reference (match the vibe/colors)?" Then generate the appropriate mode's JSON output.

**Existing persona mentioned by name:** Generate Mode 2 (Existing Character) JSON, stripping appearance details from the subject field.
