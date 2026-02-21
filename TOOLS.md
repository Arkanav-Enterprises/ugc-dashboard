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

## Gmail SMTP

Email notifications for completed reels and text briefs. Credentials in `.env` as `GMAIL_USER` and `GMAIL_APP_PASSWORD`.
