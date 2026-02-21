# Trend Research — Skill Guide

> **Status:** X/Twitter research was removed (Feb 2026) — twscrape and bird CLI are broken.
> Replaced by **YouTube + Reddit research** on the dashboard at `/research`.

## Current Research Sources

### YouTube Channel Analysis
1. Scan a channel for recent videos
2. Fetch transcripts, summarize each with Claude
3. Cross-video theme analysis to spot patterns and opportunities

### Reddit Thread Analysis
1. Search Reddit by topic (optionally filter by subreddit, time range)
2. Fetch top comments, summarize each thread with Claude
3. Cross-thread theme analysis to spot sentiment, pain points, and content angles

## Research Workflow

1. Open `/research` on the dashboard
2. Pick a source tab (YouTube or Reddit)
3. Search for topics in our niche: manifestation, screen time, habit tracking, self-improvement, journaling
4. Select relevant videos/threads and run analysis
5. Review cross-source analysis for content patterns and hooks
6. Apply insights to content generation — check past research in the "Past Research" panel

## What to Look For

- **Format patterns**: What content structures get engagement? (listicles, hot takes, personal stories)
- **Hook language**: What specific words or phrases drive engagement?
- **Community sentiment**: What do people complain about, love, or wish existed?
- **Content gaps**: Topics with lots of discussion but poor content — opportunities for us
- **Cross-platform potential**: Reddit threads with high engagement often translate to good TikTok/Reels hooks

## Integration with Content Pipeline

Research results are saved to `output/research/` as JSON files. Each result includes per-item summaries and a cross-source analysis. Use these to inform hook generation and content strategy.
