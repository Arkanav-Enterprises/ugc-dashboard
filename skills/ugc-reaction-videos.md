# UGC Reaction Video Pipeline — Manifest Lock

## Overview

AI-generated UGC-style reaction videos using the existing Replicate + MoviePy pipeline
on the Hostinger VPS. Higher production value than slideshows, used sparingly (2-3/week).

## Pipeline Architecture

1. Script generation (Anthropic API) → hook + talking points
2. AI avatar generation (Replicate) → realistic talking head video
3. Screen recording overlay (MoviePy) → app demo composited with avatar
4. Brand splash + CTA (MoviePy) → splash.mp4 appended
5. Export → vertical 1080x1920 MP4
6. Deliver via email → user posts natively with trending sound

## Script Structure

- 0-3s: Hook (same formulas as slideshows)
- 3-15s: Setup (the problem or discovery)
- 15-30s: Demo (show the app in action)
- 30-45s: Result/reaction (what happened)
- 45-60s: CTA (soft, conversational)

Total length: 30-60 seconds (TikTok sweet spot)

## Avatar Configuration

- Style: casual, relatable, 20s-30s demographic
- Tone: excited but authentic, not salesy
- Background: bedroom/office/casual setting
- Framing: shoulders up, slightly off-center for text space

## Video Composition

```
┌──────────────────┐
│  Avatar (top 60%) │
│                    │
│ ┌──────────────┐  │
│ │  App Screen   │  │
│ │  (overlay)    │  │
│ └──────────────┘  │
│  Caption area      │
└──────────────────┘
```

## Generation Script

Located at: ~/openclaw/scripts/generate_ugc_video.py
Uses existing Replicate configuration from the UGC pipeline.

## When to Use UGC vs Slideshows

- Slideshows: daily bread-and-butter, cheap ($0.50), high volume
- UGC videos: 2-3x per week, higher cost ($2-5), for content that needs
  demonstration or emotional delivery
- Use UGC for: app demos, transformation stories, direct responses to comments
- Use slideshows for: stat content, curiosity hooks, streak updates

## Quality Checklist Before Posting

- [ ] Audio is clear and synced with lip movement
- [ ] App demo footage is crisp and readable
- [ ] Brand splash plays at end
- [ ] Total length is 30-60 seconds
- [ ] Hook is in first 3 seconds
- [ ] CTA feels natural, not forced
