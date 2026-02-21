# X/Twitter Research — Skill Guide

> **INSTRUCTIONS FOR CLAUDE**: Use this skill when researching content trends on X/Twitter.
> The dashboard has an X Research page at `/research` that wraps the `bird` CLI.
> Insights saved there go to `memory/x-trends.md` — always check that file before generating content.

## Research Workflow

1. **Browse trending topics** — Use the Trending tab to see what's currently viral
2. **Search by keyword** — Search for terms in our niche: manifestation, screen time, habit tracking, self-improvement, daily affirmations
3. **Study top accounts** — Look up accounts in our space to see what formats and hooks they're using
4. **Save what's useful** — Use "Save to Trends" on any post worth referencing later
5. **Apply to content** — Before generating hooks, check `memory/x-trends.md` for current trends

## What to Look For

- **Format patterns**: How are viral posts structured? (e.g., "Day X of..." threads, hot take + proof, before/after)
- **Hook language**: What specific words or phrases are driving engagement right now?
- **Engagement ratios**: High reply-to-like ratio = controversial. High RT-to-like ratio = shareable. High like-to-RT ratio = relatable.
- **Cross-platform potential**: Posts with high saves/bookmarks often translate well to TikTok/Reels

## Key Accounts to Monitor

<!-- Add handles you want to check regularly -->
<!-- Format: @handle — why they matter -->

## Integration with Content Pipeline

The content generation pipeline reads `memory/x-trends.md` during hook generation.
When you save a trend or post from the dashboard, it gets appended to that file.
The bot then uses those entries as inspiration for its next content batch.

Loop: Browse X → Save insights → Bot reads trends → Generate content → Post → Measure → Repeat
