---
name: asset-cycling
description: "How to select and rotate pre-made video assets without repeating. Tracks recent usage to maintain variety."
related: [video-format, pipeline, sanya, emilly]
---

# Asset Cycling — Rotation Logic

## Problem

With a small pool of pre-made video clips (2-5 per persona per type), viewers will notice repetition if we use the same clip every day. The cycling system ensures maximum variety.

## Rotation Rules

1. **Never use the same hook clip two days in a row** for the same persona
2. **Never use the same reaction clip two days in a row** for the same persona
3. **Never pair the same hook + reaction combo within a 7-day window**
4. **Screen recordings can repeat more often** — the text overlay and context change their meaning

## Tracking Usage

The pipeline maintains a simple log at `memory/asset-usage.md`:

```markdown
## Recent Asset Usage

| Date | Persona | Hook Clip | Reaction Clip | Screen Recording |
|------|---------|-----------|---------------|-----------------|
| 2026-02-18 | sanya | hook/001.mp4 | reaction/002.mp4 | stats-screen.mp4 |
| 2026-02-18 | emilly | hook/002.mp4 | reaction/001.mp4 | app-blocking.mp4 |
| 2026-02-17 | sanya | hook/002.mp4 | reaction/001.mp4 | full-practice.mp4 |
```

When selecting assets, the pipeline:
1. Reads the last 7 days from this log
2. Excludes any hook clip used for this persona yesterday
3. Excludes any reaction clip used for this persona yesterday
4. Excludes any hook+reaction combo used in the last 7 days
5. Selects randomly from remaining options

## When the Pool Is Too Small

If there are only 2 clips per type (the minimum), the rotation is forced:
- Day 1: hook/001 + reaction/001
- Day 2: hook/002 + reaction/002
- Day 3: hook/001 + reaction/002
- Day 4: hook/002 + reaction/001
- Then repeat

This gives 4 unique combinations before any repetition — enough for a work week.

## Adding New Assets

When new Higgsfield videos are generated:
1. Drop them into the correct folder (`assets/{persona}/{hook|reaction}/`)
2. Name sequentially: `003.mp4`, `004.mp4`, etc.
3. The pipeline auto-discovers new files on next run
4. More assets = longer rotation = less repetition = better

## Screen Recording Cycling

Screen recordings are less sensitive to repetition because the text overlay changes their meaning. Still, prefer variety:

- Match screen recording to content category (see [[video-format]] table)
- Don't use the same screen recording for both personas on the same day
- Prioritize the most visually dynamic recordings (app blocking, unlock countdown) for Category A and B content
