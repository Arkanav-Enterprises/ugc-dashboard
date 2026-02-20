---
name: video-format
description: "The 3-part structure of every UGC reaction video post. Covers clip sequencing, text overlay placement, timing, and composition rules."
related: [text-overlays, asset-cycling, sanya, sophie]
---

# Video Format — UGC Reaction Structure

## The 3-Part Structure

Every post follows this sequence:

```
┌─────────────────────────────────────┐
│  PART 1: Persona + POV Text         │
│  (2-3 seconds)                      │
│                                     │
│  [Sanya/Sophie covering mouth]      │
│  Text overlay: "pov: you just..."   │
│                                     │
├─────────────────────────────────────┤
│  PART 2: Screen Recording           │
│  (3-8 seconds, sped up)             │
│                                     │
│  [App in action — the proof]        │
│  No persona, no text overlay        │
│                                     │
├─────────────────────────────────────┤
│  PART 3: Persona + Reaction Text    │
│  (2-3 seconds)                      │
│                                     │
│  [Sanya/Sophie smiling/reacting]    │
│  Text overlay: "i mean...WHAT"      │
│                                     │
└─────────────────────────────────────┘
```

Total video length: 7-14 seconds. Short enough to loop, long enough to tell a story.

## Part 1: The Hook Clip

- **Asset**: Pre-made Higgsfield video of persona with hand over mouth
- **Duration**: 2-3 seconds
- **Text overlay**: POV opener from [[text-overlays]]
- **Text position**: Center of frame, below the persona's face
- **Text style**: White, lowercase, bold sans-serif with black shadow
- **Purpose**: Create curiosity — "why is she reacting like this?"

## Part 2: The Screen Recording

- **Asset**: Pre-recorded screen capture of the app
- **Duration**: 3-8 seconds (speed up longer recordings to 1.3x-2.3x)
- **Content**: The "proof" — screen time stats, the practice flow, the unlock moment, streak screen
- **No text overlay** — the app UI speaks for itself
- **Speed**: Natural for short actions, sped up for longer flows
- **Purpose**: Deliver the substance that justifies the hook

### Screen Recording Selection by Category

| Category | Best Screen Recording |
|----------|----------------------|
| A (Screen Time Shock) | Stats screen, screen time numbers, daily usage |
| B (Reaction/Story) | Full practice flow: mood check → write → read aloud → unlock |
| C (Streak/Transformation) | Streak celebration screen, day counter, milestone |
| D (App Demo) | App blocking shield → practice → apps unlocked countdown |

## Part 3: The Reaction Clip

- **Asset**: Pre-made Higgsfield video of persona smiling or reacting positively
- **Duration**: 2-3 seconds
- **Text overlay**: Reaction text from [[text-overlays]]
- **Text position**: Same as Part 1 for visual consistency
- **Purpose**: Emotional payoff — "she's happy because it actually worked"

## Asset File Naming

Assets are stored in [[asset-cycling]] structure:

```
assets/
├── sanya/
│   ├── hook/         # Hand-over-mouth clips
│   │   ├── 001.mp4
│   │   └── 002.mp4
│   └── reaction/     # Smiling/positive reaction clips
│       ├── 001.mp4
│       └── 002.mp4
├── sophie/
│   ├── hook/
│   │   ├── 001.mp4
│   │   └── 002.mp4
│   └── reaction/
│       ├── 001.mp4
│       └── 002.mp4
└── screen-recordings/
    ├── stats-screen.mp4
    ├── full-practice.mp4
    ├── app-blocking.mp4
    ├── streak-celebration.mp4
    ├── mood-check.mp4
    └── unlock-countdown.mp4
```

## What the Pipeline Delivers

The automated pipeline (see [[pipeline]]) generates the TEXT, not the video. The email delivery contains:

1. Persona assignment (Sanya or Sophie)
2. POV text overlay (exact words for Part 1)
3. Suggested screen recording (which clip from the library)
4. Reaction text overlay (exact words for Part 3)
5. Caption for the post
6. Hashtags
7. Which hook/reaction asset files to use (from [[asset-cycling]] rotation)

The final video assembly is done manually in CapCut or similar.
