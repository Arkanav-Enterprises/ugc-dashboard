# Failure Log

> **INSTRUCTIONS FOR CLAUDE**: Read this before every content generation run.
> Each entry here is a mistake that must not be repeated.
> If you're about to generate something that matches a pattern below, stop and pick a different approach.

## Content Failures

| Date | What We Did | Why It Failed | Rule Going Forward |
|------|-------------|---------------|-------------------|
| 2026-02-27 | Generated videos with UGC lighting type (studio golden hour look) | 100-130 views consistently vs 500-1,700 for default. Studio lighting reads as "produced content" not "authentic reaction." | **RULE: Only generate default clothing/setting videos. UGC lighting type is retired.** |
| 2026-02-27 | Generated videos with outdoor type (park/street backgrounds) | Same underperformance as UGC lighting. Outdoor setting doesn't match the intimate, confessional tone that works for these hooks. | **RULE: Only generate default clothing/setting videos. Outdoor type is retired.** |
| 2026-02-27 | Posted 15 reels on @emillywilks (Sanya) with similar "won't let me spiral" hooks | 2.9K views across 15 reels = ~193/reel. Repetitive hooks cause audience fatigue. Algorithm sees low engagement and suppresses further. | **RULE: Never repeat the same hook structure more than 2x on the same account. Vary angles: social context, emotion, specific situation.** |
| 2026-02-27 | Ran Sanya persona across two accounts (@sanyahealing, @sophie.unplugs) | Combined 3.2K views across 19 reels = ~168/reel. Sanya underperforms Aliyah by 4x on per-reel average regardless of account. | **RULE: Sanya and Emilly are lower priority. Allocate primary generation budget to Aliyah and Riley.** |

## Pipeline Failures

| Date | What We Did | Why It Changed | Rule Going Forward |
|------|-------------|----------------|-------------------|
| 2026-02-27 | Generated new videos via Veo/Replicate for each content run | Unnecessary cost and latency. Existing video pool (34 clips across personas) is sufficient. New video generation adds no performance lift — the hook text and stitching are what matter. | **RULE: Never generate new videos via Veo, Replicate, or any image-to-video API. Reuse existing clips from assets/{persona}/hook/ and assets/{persona}/reaction/. Only generate hook text, reaction text, and stitch the final video.** |

## Technical Failures

| Date | What Broke | Root Cause | Fix Applied |
|------|-----------|------------|-------------|
| — | No technical failures logged yet | — | — |

## Process Failures

| Date | What Happened | Impact | Prevention |
|------|--------------|--------|-----------|
| 2026-02-27 | Memory files (post-performance.md, failure-log.md) were empty templates for entire first month of posting | OpenClaw had zero performance signal to inform content decisions. Generated blind — same hooks, same video types, no learning loop. | **RULE: Update memory files within 48 hours of reviewing account metrics. Minimum weekly update.** |
| 2026-02-27 | No per-post save/share tracking in post-performance.md | Can only analyze views, not intent signals. Views alone don't tell us which content drives downloads. | **RULE: Log saves, shares, and comments for every reel that gets >300 views within 48 hours of posting.** |
