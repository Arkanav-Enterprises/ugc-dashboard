# Analytics Loop — RevenueCat + PostHog Integration

## RevenueCat Metrics (via ClawhHub skill)
Access via the RevenueCat ClawhHub skill (installed separately).

Key metrics to check daily:
- MRR (Monthly Recurring Revenue) — the north star
- New trials started today
- Trial conversions today
- Churn rate
- Active subscribers count

## Correlation Tracking

After each batch of posts, log in memory/daily-metrics.md:

```
## [Date]
Posts published: [count]
Total views: [sum]
Best performer: [hook] — [views]
RevenueCat: MRR $[X], New trials [Y], Conversions [Z]
App Store: Downloads [N] (check App Store Connect)
Attribution: [which hooks likely drove downloads based on timing]
```

## Weekly Review Process
Every Sunday, analyze:
1. Which content category (A/B/C/D) drove the most views?
2. Which hooks got the highest engagement rate (likes+comments/views)?
3. Did high-view posts correlate with download/trial spikes in RevenueCat?
4. What's the estimated cost per acquisition? (API costs / new trials)
5. Update hook formulas based on findings
6. Plan next week's content mix

## Metrics Targets (Starting benchmarks, adjust after 2 weeks)
- Views per post: >10K average (>50K for winners)
- Posts per day: 3 (18 slides total)
- Weekly new trials: track baseline first, then 10% improvement/week
- Cost per trial: <$2 (at $0.50/post, need 1 trial per 4 posts minimum)
- MRR growth: track weekly trend

## Content → Conversion Signals
If views are high but trials are low:
- Hook is good but CTA is weak — strengthen the app mention
- Wrong audience — adjust hashtags and hook persona targeting
- App Store listing needs work — check screenshots, description, reviews

If views are low but trial rate per view is high:
- Content resonates with the right audience but isn't reaching enough people
- Double down on that content type, increase posting frequency
- Test that hook formula with broader appeal angles
