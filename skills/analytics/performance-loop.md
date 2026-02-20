---
name: performance-loop
description: "How to track content performance, the weekly review process, and how data feeds back into content decisions. The learning loop."
related: [proven-hooks, content-mix, hook-architecture, pipeline]
---

# Performance Loop — Analytics & Iteration

## Daily Tracking

After each post goes live, log in `memory/post-performance.md`:

```markdown
## [Date]
- Persona: [Sanya/Sophie]
- Category: [A/B/C/D]
- Hook: "[the POV text overlay]"
- Reaction: "[the reaction text]"
- Screen Recording: [which one]
- Platform: [TikTok/IG/Both]
- Views (24h): [count]
- Likes: [count]
- Comments: [count]
- Shares: [count]
- Saves: [count] (IG only)
- "What app?" comments: [count]
```

## Weekly Review (Every Sunday)

1. **Rank posts by engagement rate** (likes + comments + shares / views)
2. **Identify top 3 and bottom 3 performers**
3. **Pattern match**: What do the top 3 share? (hook type, category, persona, time, topic)
4. **Update [[proven-hooks]]** with winners
5. **Update [[what-never-works]]** with losers
6. **Adjust next week's [[content-mix]]** — shift 10% toward winning categories

## RevenueCat Correlation

After each week, check if content activity correlates with:
- New trial starts
- MRR changes
- Download spikes in App Store Connect

Log in `memory/daily-metrics.md`:

```markdown
## Week of [Date]
Posts published: [count]
Total views: [sum]
Best performer: "[hook]" — [views] views, [engagement]% engagement
RevenueCat: MRR $[X], New trials [Y], Conversions [Z]
Attribution: [which hooks likely drove downloads based on timing]
```

## Content → Conversion Signals

**High views, low trials:**
- Hook is working but CTA is weak — test stronger comment-reply strategy
- Wrong audience — adjust hashtags and persona targeting
- App Store listing may need work

**Low views, high trial rate per view:**
- Content resonates with the right people but isn't reaching enough
- Double down on that hook formula, test variations
- Consider cross-posting to maximize reach

## Metrics Targets (Starting Benchmarks)

- Views per post: >1K baseline, >10K for winners
- Engagement rate: >5% (likes + comments + shares / views)
- "What app?" comments: >3 per viral post
- Weekly new trials: track baseline, then aim for 10% improvement/week
