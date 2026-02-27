# TOOLS.md — OpenClaw Tool Reference

## Reddit Public JSON API

Used by the Trend Research page to search Reddit threads and fetch comments. No API key needed — append `.json` to any Reddit URL.

- **Search:** `https://www.reddit.com/search.json?q=...&sort=relevance&t=week`
- **Subreddit search:** `https://www.reddit.com/r/{sub}/search.json?q=...&restrict_sr=on`
- **Thread comments:** `https://www.reddit.com{permalink}.json`
- Requires `User-Agent: OpenClaw/1.0` header (Reddit blocks requests without one)
- Rate limit: ~60 requests/minute; returns 429 if exceeded

## Replicate API

AI video generation via Google Veo 3.1 Fast. Used by `autopilot_video.py` to generate reaction clips from reference images.

- ~$0.60 per 4-second clip
- Token in `.env` as `REPLICATE_API_TOKEN`
- Daily spending cap: `DAILY_COST_CAP` (default $5/day)

## Anthropic API

Claude generates hook text, reaction text, and captions. Used by both `autopilot.py` and `autopilot_video.py`.

- Model: `claude-sonnet-4-5-20250929`
- ~$0.01 per text generation call
- Key in `.env` as `ANTHROPIC_API_KEY`

## rclone

Uploads assembled reels to Google Drive (`manifest-social-videos` remote). Configured on the VPS.

## ffmpeg

Video processing — splitting raw Veo clips into hook/reaction segments, trimming, re-encoding. Used by `autopilot_video.py` and `assemble_video.py`.

## PostHog Query API

Live analytics for both apps (funnel conversion, DAU trends). Used by the dashboard's Analytics page and Agent Chat (when "Analytics Data" is checked).

- **Endpoint**: `POST https://us.i.posthog.com/api/projects/{project_id}/query/`
- **Query types**: `FunnelsQuery` (onboarding funnel steps) and `TrendsQuery` (DAU, feature usage)
- **Auth**: `Authorization: Bearer {personal_api_key}` header
- Two separate PostHog accounts — one per app:
  - ManifestLock: project 306371, key in `.env` as `POSTHOG_API_KEY_MANIFEST`
  - JournalLock: project 313945, key in `.env` as `POSTHOG_API_KEY_JOURNAL`
- Backend client: `dashboard/backend/services/posthog_client.py`

## RevenueCat v2 API

Daily MRR, revenue, subscribers, and trial metrics for both apps. Fetched by `scripts/fetch_revenue_metrics.py`, written to `memory/revenue-metrics.md` for pipeline context.

- **Endpoint**: `GET https://api.revenuecat.com/v2/projects/{project_id}/metrics/overview`
- **Auth**: `Authorization: Bearer {v2_secret_key}` — one key per project, scoped to `project_configuration:metrics:read`
- **Metrics**: mrr, revenue (28d), new_customers (28d), active_users, active_subscriptions, active_trials
- Two separate keys — one per project:
  - ManifestLock: key in `.env` as `RC_MANIFEST_LOCK_KEY`, project ID as `RC_MANIFEST_LOCK_PROJECT_ID`
  - JournalLock: key in `.env` as `RC_JOURNAL_LOCK_KEY`, project ID as `RC_JOURNAL_LOCK_PROJECT_ID`
- Runs daily at 7 AM IST via cron

## Gmail SMTP

Email notifications for completed reels and text briefs. Credentials in `.env` as `SMTP_USER` and `SMTP_PASS`.
