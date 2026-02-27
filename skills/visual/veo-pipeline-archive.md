# Veo/Replicate Video Generation Pipeline — Archive

> **STATUS**: Retired 2026-02-27 for the OpenClaw content pipeline.
> Kept as reference for reuse with future apps or avatars.

## Why It Was Retired

- Cost: ~$0.61/reel (1 Veo clip ~$0.60 + Claude text ~$0.01) vs $0.01/reel with pre-made clips
- No performance lift from fresh video generation — hook text and stitching drive views, not novel video
- Existing clip pool (34 clips across personas) provides enough variety

## Architecture

```
Reference Image → Replicate (image-to-video) → Raw 4s clip
                                                    ↓
                                              Split into hook + reaction clips
                                                    ↓
Claude API → Hook text + Reaction text → FFmpeg overlay on clips
                                                    ↓
                                        Screen recording composited
                                                    ↓
                                          Final 1080x1920 reel
```

## Supported Engines (Replicate)

| Engine | Model ID | Typical Time | Notes |
|--------|----------|-------------|-------|
| **Veo** (default) | `google/veo-3.1-fast` | 1-3 min | Best quality, ~$0.60/clip |
| **Seedance** | `bytedance/seedance-1.5-pro` | 2-5 min | Alternative, comparable quality |
| **Kling** | `kwaivgi/kling-v2.1` | — | Used in generate_variants.py |
| **Hailuo** | `minimax/hailuo-2.3` | — | Used in generate_variants.py |

## Key Scripts (still in repo, marked DEPRECATED)

- `scripts/autopilot_video.py` — Full pipeline: pick ref image, generate video via Replicate, Claude text gen, FFmpeg stitch, upload
- `scripts/generate_ugc_video.py` — UGC reaction videos using Replicate SadTalker + OpenAI TTS + MoviePy compositing
- `scripts/generate_variants.py` — Batch variant generation: takes a reference image, generates clips across multiple scene presets

## CLI Interface (autopilot_video.py)

```bash
python3 scripts/autopilot_video.py \
  --persona sanya \
  --video-type original \
  --engine veo \
  --dry-run \
  --no-upload \
  --skip-gen \
  --app manifest-lock
```

Arguments:
- `--persona`: sanya, sophie, aliyah, olivia, riley, both, all, or comma-separated
- `--video-type`: original, ugc_lighting, outdoor, olivia_default, riley_default
- `--engine`: veo (default), seedance
- `--dry-run`: Plan only, skip generation
- `--no-upload`: Build reel but skip Google Drive upload
- `--skip-gen`: Use existing clips from assets/, skip Replicate call
- `--app`: manifest-lock or journal-lock (for multi-app personas)

## UGC Reaction Video Pipeline (generate_ugc_video.py)

A higher-production variant using AI talking heads:

1. Claude generates script (hook + talking points, 30-60s)
2. OpenAI TTS (`tts-1`, voice `nova`) generates speech audio
3. Replicate SadTalker (`cjwbw/sadtalker`) generates talking head from audio + reference image
4. MoviePy composites: avatar (top 60%) + app screen recording overlay + caption area
5. Brand splash appended

Cost: $2-5/video. Intended for 2-3x/week, demo-heavy or emotional content.

## Video Type Presets (generate_variants.py)

Scene presets controlled the video prompt while keeping the subject (persona) locked:

- **original** — Default indoor/bedroom setting
- **ugc_lighting** — Studio ring-light look (retired: 100-130 views)
- **outdoor** — Park/nature setting (retired: 100-130 views)
- **olivia_default** / **riley_default** — Persona-specific defaults

## Environment Variables Required

```
REPLICATE_API_TOKEN=...   # Replicate API key
OPENAI_API_KEY=...        # For TTS in UGC reaction pipeline
ANTHROPIC_API_KEY=...     # Claude for text generation
```

## Reuse Checklist for New App/Avatar

1. Generate 3-5 reference images for the new avatar (consistent face/style)
2. Run `generate_variants.py --persona <name> --model veo` to build initial clip pool
3. Copy the autopilot_video.py flow: pick ref image, generate clip, split hook/reaction, overlay text
4. Once you have 10+ clips per type, switch to clip reuse (current autopilot.py approach) to cut costs
5. Only re-generate clips when the pool feels stale or you need a new setting/outfit
