# OpenClaw Dashboard

Last updated: 2026-02-26

---

## What This Is

The OpenClaw Dashboard is an internal web app for the team to monitor and control the content generation pipeline. It shows pipeline runs, costs, generated reels, PostHog analytics (funnel/conversion data for both apps), and provides an AI chat agent for content strategy.

**Live URL:** https://frontend-arkanaventerprises-7462s-projects.vercel.app

---

## Architecture

```
Browser (your team)
   │
   │  HTTPS
   ▼
Vercel (Next.js frontend)
   │
   │  /api/* proxied server-to-server (HTTP)
   ▼
VPS 72.60.204.30:8000 (FastAPI backend)
   │
   │  reads local files + runs pipeline scripts
   ▼
Pipeline data at /root/openclaw/
   (logs, assets, videos, skills, memory, scripts)
```

The frontend runs on Vercel (free tier). The backend runs on the Hostinger VPS as a systemd service. The browser only talks to Vercel over HTTPS — Vercel proxies API requests to the VPS behind the scenes, avoiding mixed-content issues without needing a domain or SSL certificate on the VPS.

---

## Repository

**GitHub:** https://github.com/Arkanav-Enterprises/ugc-dashboard

The repo contains only the dashboard code (not the pipeline scripts, skills, or assets):

```
ugc-dashboard/
├── .gitignore
├── DASHBOARD.md              ← This file
└── dashboard/
    ├── backend/                ← FastAPI (runs on VPS)
    │   ├── main.py             ← App entrypoint
    │   ├── config.py           ← Paths and env config (PIPELINE_ROOT)
    │   ├── requirements.txt    ← Python dependencies
    │   ├── models.py           ← Pydantic models
    │   ├── routers/
    │   │   ├── revenue.py      ← /api/revenue/* (RevenueCat metrics)
    │   │   ├── analytics.py    ← /api/analytics/* (PostHog funnel, trends, AI ask)
    │   │   ├── assets.py       ← /api/assets/* endpoints
    │   │   ├── chat.py         ← /api/chat/* (SSE streaming + WebSocket)
    │   │   ├── content.py      ← /api/content/* endpoints
    │   │   ├── knowledge.py    ← /api/knowledge/* endpoints
    │   │   ├── logs.py         ← /api/logs/* endpoints
    │   │   ├── outreach.py     ← /api/outreach/* (email campaigns)
    │   │   ├── pipeline.py     ← /api/pipeline/* (UGC + lifestyle run triggers)
    │   │   ├── schedule.py     ← /api/schedule/* endpoints
    │   │   ├── scout.py        ← /api/scout/* (opportunity scouting)
    │   │   ├── youtube_research.py ← /api/research/* (YT scan + analyze)
    │   │   └── reddit_research.py  ← /api/research/reddit/* (search + analyze)
    │   └── services/
    │       ├── claude_chat.py  ← Anthropic streaming chat (supports analytics context)
    │       ├── log_reader.py   ← Reads pipeline log files
    │       ├── pipeline_runner.py ← Runs UGC + lifestyle pipeline scripts as subprocesses
    │       ├── posthog_client.py ← PostHog Query API client (funnel, trends, AI summary)
    │       ├── skill_loader.py ← Loads skill/memory files for context
    │       ├── youtube_research.py ← YT channel scanning, transcript fetch, Claude analysis
    │       └── reddit_research.py  ← Reddit search, comment fetch, Claude analysis
    └── frontend/               ← Next.js (deployed to Vercel)
        ├── next.config.ts      ← API proxy rewrites (BACKEND_URL)
        ├── package.json
        └── src/
            ├── app/
            │   ├── page.tsx        ← Overview dashboard
            │   ├── revenue/        ← Revenue (RevenueCat MRR, trials, subs)
            │   ├── analytics/      ← PostHog Analytics (funnel charts + AI chat)
            │   ├── content/        ← Content Gallery
            │   ├── pipeline/       ← Pipeline Monitor (read-only)
            │   ├── generate/       ← Generate Videos (UGC + Lifestyle Reel)
            │   ├── chat/           ← Agent Chat + Action buttons + Analytics toggle
            │   ├── knowledge/      ← Knowledge Base editor
            │   ├── research/       ← Trend Research (YouTube + Reddit)
            │   ├── scout/          ← Opportunity Scout
            │   ├── outreach/       ← Outreach (email campaigns)
            │   ├── schedule/       ← Schedule manager
            │   ├── assets/         ← Asset Manager
            │   └── logs/           ← Logs viewer
            ├── components/
            │   ├── sidebar.tsx
            │   ├── theme-toggle.tsx
            │   └── ui/             ← shadcn/ui components
            └── lib/
                ├── api.ts          ← API client + types
                └── utils.ts
```

---

## Dashboard Pages

| Page | Path | What it does |
|------|------|-------------|
| **Overview** | `/` | Today's runs, cost vs cap, total reels, daily spend chart, persona stats |
| **Content Gallery** | `/content` | Browse generated reels with video playback, filter by persona |
| **Pipeline Monitor** | `/pipeline` | View run history with expandable details, cost trend chart, search runs |
| **Generate Videos** | `/generate` | Trigger UGC pipeline runs (per persona/app) or lifestyle reels. Mode toggle at top. |
| **Agent Chat** | `/chat` | Chat with Claude using skill/memory context + action buttons. "Analytics Data (PostHog)" checkbox injects live funnel/trend data into Claude's context. |
| **Knowledge Base** | `/knowledge` | View and edit skill files and memory files that feed into content generation |
| **Trend Research** | `/research` | Analyze YouTube channels or Reddit threads — fetch transcripts/comments, summarize with Claude, run cross-source theme analysis |
| **Opportunity Scout** | `/scout` | Discover content opportunities and trending topics |
| **Outreach** | `/outreach` | Manage and send email outreach campaigns |
| **Revenue** | `/revenue` | RevenueCat MRR, subscribers, trials for both apps with daily trends |
| **Analytics** | `/analytics` | PostHog funnel/conversion charts for ManifestLock and JournalLock, DAU trends, stat cards, AI chat for querying analytics data |
| **Schedule** | `/schedule` | View and toggle the daily cron schedule for video and text pipelines |
| **Asset Manager** | `/assets` | Browse reference images, clips, screen recordings, and asset usage history |
| **Logs** | `/logs` | View raw pipeline logs and run history |

---

## Action Buttons (Agent Chat page)

The Agent Chat page has four action buttons in the left panel:

| Button | Cost | Confirmation? | What it does |
|--------|------|---------------|-------------|
| **Generate Reel** | ~$0.61 | Yes | Generates a video clip via Replicate (Veo 3.1) for Sanya and assembles a full reel |
| **Dry Run** | Free | No | Runs the pipeline with `--dry-run` — generates text only, no video |
| **Caption Only** | Free | No | Runs with `--dry-run --skip-gen` — generates caption text only |
| **Run All Personas** | ~$1.83 | Yes | Generates video clips for all 3 personas (Sanya, Sophie, Aliyah) |

Costly actions (Generate Reel, Run All) show a confirmation dialog with the estimated cost before executing. All buttons show a spinner while running, disable during execution, and display the pipeline output directly in the chat when complete.

---

## Agent Chat — Skill & Memory Context

The Agent Chat page has a **Skill Context** and **Memory** panel on the left side with checkboxes. This controls what knowledge Claude has access to when you chat.

### Where the files come from

The file lists are read directly from the VPS filesystem:

- **Skill files** → `/root/openclaw/skills/*.md` (recursively scanned)
- **Memory files** → `/root/openclaw/memory/*.md` (recursively scanned)

These are the same skill and memory files that the pipeline's `autopilot_video.py` uses for content generation. When you edit them via the Knowledge Base page or deploy new ones with `deploy.sh`, they appear here automatically.

### How context injection works

1. You check the files you want Claude to reference (5 skills + 3 memory files are pre-selected by default)
2. When you send a message, the frontend sends the selected file names along with your chat history
3. The backend reads the full content of each selected file from disk
4. The file contents are injected into Claude's **system prompt** as structured context:
   ```
   === SKILL: INDEX.md ===
   (full file content)

   === MEMORY: post-performance.md ===
   (full file content)
   ```
5. Claude responds with awareness of your content strategy, past performance data, etc.

More checkboxes = more context for Claude, but also more tokens per request. Toggle based on what you're asking about.

### Agent Chat defaults vs Pipeline context

The Agent Chat and the video pipeline (`autopilot_video.py`) load **different subsets** of the same skill/memory files:

| | Agent Chat (defaults) | Pipeline (`autopilot_video.py`) |
|---|---|---|
| **Skills loaded** | 5 | 9 (persona-specific) |
| **Memory loaded** | 3 | 4 |
| **Persona-aware** | No (manual checkbox) | Yes (auto-selects per persona) |

**Agent Chat defaults** (lighter — for general Q&A):

| Type | Files |
|------|-------|
| Skills | `INDEX.md`, `manifest-lock.md`, `content/content-mix.md`, `content/hook-architecture.md`, `content/what-never-works.md` |
| Memory | `post-performance.md`, `failure-log.md`, `x-trends.md` |

**Pipeline context** (heavier — for content generation, per persona):

| Type | Files |
|------|-------|
| Skills | `INDEX.md`, `{app}.md` (manifest-lock or journal-lock), `personas/{persona}.md`, `content/content-mix.md`, `content/hook-architecture.md`, `content/text-overlays.md`, `content/caption-formulas.md`, `content/what-never-works.md`, `analytics/proven-hooks.md` |
| Memory | `post-performance.md`, `failure-log.md`, `asset-usage.md`, `x-trends.md` |

**What the pipeline loads that chat doesn't (by default):**
- `personas/{persona}.md` — voice, tone, and look for the specific persona
- `content/text-overlays.md` — patterns for POV and reaction text on video clips
- `content/caption-formulas.md` — caption structures, CTA patterns, hashtag rules
- `analytics/proven-hooks.md` — hooks that actually performed well
- `asset-usage.md` — tracks which assets have been used to avoid repeats

The pipeline also dynamically picks the right app file (`manifest-lock.md` for Sophie, `journal-lock.md` for Sanya) and the right persona file. In Agent Chat, you'd need to manually check those boxes if you want that context.

**Tip:** When using Agent Chat to generate content for a specific persona, check that persona's file + `text-overlays.md` + `caption-formulas.md` + `proven-hooks.md` to match what the pipeline would see.

### Analytics Data Toggle

The Agent Chat page has a **Data Sources** card in the left sidebar with an "Analytics Data (PostHog)" checkbox. When checked, the backend calls `format_metrics_for_ai()` from the PostHog client and injects live funnel/conversion/trend data into Claude's system prompt. This lets you ask the agent questions about your analytics without switching to the Analytics page.

### Streaming

Chat responses stream in real-time via SSE (Server-Sent Events). The backend calls Claude's streaming API (`claude-sonnet-4-5-20250929`) and forwards each text chunk to the frontend as it arrives. For local development, a WebSocket endpoint is also available at `/api/chat/ws`.

---

## Trend Research Page

The `/research` page supports two research sources, selectable via tabs:

### YouTube

1. Paste a YouTube channel URL and choose how many videos to scan
2. `yt-dlp` fetches the channel's video metadata (title, views, duration, thumbnail)
3. Select which videos to analyze
4. For each selected video, `youtube-transcript-api` fetches the transcript (with optional proxy)
5. Claude summarizes each transcript (key points + summary)
6. Claude runs a cross-video theme analysis (streaming via SSE)
7. Result saved to `output/research/{id}.json` with `source: "youtube"`

### Reddit

1. Enter a search query + optional subreddit filter, time range, and thread count
2. Backend hits Reddit's public JSON API (`reddit.com/search.json`) — no API key needed
3. Select which threads to analyze from the scored/ranked results
4. For each selected thread, backend fetches top comments via `reddit.com{permalink}.json`
5. Claude summarizes each thread's discussion (key points + summary + sentiment)
6. Claude runs a cross-thread theme analysis (streaming via SSE)
7. Result saved to `output/research/{id}.json` with `source: "reddit"`

### Shared

- Both sources use the same SSE streaming pattern and progress UI
- Past results list shows a "YouTube" or "Reddit" badge per entry
- Results are stored in the same directory and listed together
- Reddit requires a `User-Agent` header (`OpenClaw/1.0`) — no API keys

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/research/scan` | POST | Scan YouTube channel for videos |
| `/api/research/analyze` | POST | SSE stream YouTube video analysis |
| `/api/research/reddit/search` | POST | Search Reddit for threads |
| `/api/research/reddit/analyze` | POST | SSE stream Reddit thread analysis |
| `/api/research/results` | GET | List all saved research (both sources) |
| `/api/research/results/{id}` | GET | Get a specific saved result |

---

## Analytics Page

The `/analytics` page shows live PostHog data for both apps. Two separate PostHog accounts are queried (different personal API keys per project).

### Features

- **App selector tabs** — Manifest Lock / Journal Lock
- **Date range buttons** — 7d / 30d / 90d
- **4 stat cards** — Overall Conversion %, Avg DAU, Biggest Drop-off step, Funnel Entries count
- **Funnel BarChart** — Horizontal bars with green-to-red gradient showing conversion at each step, drop-off % between bars
- **DAU LineChart** — Daily active user trend over selected date range
- **AI Chat panel** — Ask questions about the analytics data. Uses `POST /api/analytics/ask` (SSE streaming) with PostHog data injected into Claude's system prompt.

### Default Funnel Steps

**ManifestLock**: `onboarding_started` → `onboarding_name_entered` → `onboarding_goal_selected` → `onboarding_manifestation_created` → `onboarding_read_aloud_completed` → `onboarding_completed`

**JournalLock**: `onboarding_started` → `onboarding_journaling_reasons_selected` → `onboarding_manifestation_created` → `onboarding_apps_selected` → `onboarding_trial_started` → `onboarding_completed`

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/analytics/funnel` | GET | Funnel data for an app (optional step overrides) |
| `/api/analytics/trends` | GET | Trend data for an app (events, interval, date range) |
| `/api/analytics/summary` | GET | Combined summary for both apps |
| `/api/analytics/ask` | POST | SSE streaming Claude chat with PostHog context |

---

## Generate Videos Page

The `/generate` page has a **UGC / Lifestyle Reel** mode toggle at the top.

### UGC Mode

- Persona selector buttons (sanya, sophie, aliyah, olivia, riley)
- App checkboxes (which apps to generate for)
- Video type dropdown (auto rotation or manual override)
- Option toggles: Dry Run, No Upload, Skip Gen
- Triggers `POST /api/pipeline/run` per selected app

### Lifestyle Reel Mode

- Description of the 3-scene format
- Option toggles: Dry Run, No Upload
- Triggers `POST /api/pipeline/lifestyle-run`

Both modes show active runs in an expandable list at the bottom with real-time status polling.

---

## What Lives Where

| Component | Location | Deployed via |
|-----------|----------|-------------|
| **Frontend** (Next.js) | Vercel | `vercel deploy --prod` or auto-deploy on push |
| **Backend** (FastAPI) | VPS at `/root/ugc-dashboard/` | `git pull` + `systemctl restart openclaw-api` |
| **Pipeline** (scripts, skills, assets) | VPS at `/root/openclaw/` | `deploy.sh` (rsync from local) |
| **Working copy** (everything) | Local at `~/openclaw/` | Edit here, push/deploy from here |

---

## Environment Variables

### Vercel (frontend)

Set via Vercel dashboard or CLI (`vercel env`):

| Variable | Value | Purpose |
|----------|-------|---------|
| `BACKEND_URL` | `http://72.60.204.30:8000` | Next.js rewrites proxy /api/* to this URL |

### VPS (backend)

Set via the systemd service file at `/etc/systemd/system/openclaw-api.service`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `PIPELINE_ROOT` | `/root/openclaw` | Tells the backend where pipeline data lives |

The backend also reads from `/root/openclaw/.env` for:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API for Agent Chat + lifestyle reel text gen |
| `DAILY_COST_CAP` | Spending cap shown on Overview |
| `POSTHOG_API_KEY_MANIFEST` | PostHog personal API key for ManifestLock (project 306371) |
| `POSTHOG_API_KEY_JOURNAL` | PostHog personal API key for JournalLock (project 313945) |
| `POSTHOG_HOST` | PostHog API host (default: `https://us.i.posthog.com`) |
| `RC_MANIFEST_LOCK_KEY` | RevenueCat v2 API key for Manifest Lock |
| `RC_MANIFEST_LOCK_PROJECT_ID` | RevenueCat project ID for Manifest Lock |
| `RC_JOURNAL_LOCK_KEY` | RevenueCat v2 API key for Journal Lock |
| `RC_JOURNAL_LOCK_PROJECT_ID` | RevenueCat project ID for Journal Lock |

---

## How the API Proxy Works

The frontend uses **Next.js rewrites** (configured in `next.config.ts`) to proxy all `/api/*` requests to the VPS backend:

```
Browser → GET https://frontend-....vercel.app/api/pipeline/overview
         → Vercel rewrites to → http://72.60.204.30:8000/api/pipeline/overview
         → Response returned to browser
```

This means:
- The browser only talks to Vercel (HTTPS) — no mixed-content warnings
- No domain name or SSL certificate needed on the VPS
- The VPS just needs port 8000 open

For the **Agent Chat**, the backend provides an SSE (Server-Sent Events) endpoint at `POST /api/chat/stream` instead of WebSocket, since Vercel's serverless infrastructure doesn't support WebSocket proxying. A WebSocket endpoint (`/api/chat/ws`) is kept for local development.

---

## How Pipeline Actions Work

When a user clicks an action button (e.g. "Caption Only"):

1. Frontend calls `POST /api/pipeline/run` with the action config
2. Backend starts `autopilot_video.py` as a subprocess (using system `python3` or the pipeline's `.venv` if it exists)
3. Backend returns a `run_id` immediately
4. Frontend polls `GET /api/pipeline/run/{run_id}` every 2 seconds
5. Backend streams stdout from the subprocess into the run's output
6. When the subprocess finishes, status changes to `completed` or `failed`
7. Frontend displays the full output in the chat

---

## Development Workflow

### Making frontend changes

```bash
# 1. Edit files in dashboard/frontend/src/
# 2. Test locally
cd ~/openclaw/dashboard/frontend
npm run dev

# 3. Push to GitHub
cd ~/openclaw
git add dashboard/frontend/
git commit -m "description of change"
git push

# 4. Deploy to Vercel
cd ~/openclaw/dashboard/frontend
vercel deploy --prod --yes --token <YOUR_TOKEN>
```

### Making backend changes

```bash
# 1. Edit files in dashboard/backend/
# 2. Test locally
cd ~/openclaw/dashboard/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# 3. Push to GitHub
cd ~/openclaw
git add dashboard/backend/
git commit -m "description of change"
git push

# 4. SSH to VPS and pull
ssh root@72.60.204.30
cd /root/ugc-dashboard && git pull && systemctl restart openclaw-api
```

### Making pipeline changes (scripts, skills, assets)

```bash
# These don't go through GitHub — use the existing rsync deploy
./deploy.sh 72.60.204.30
```

---

## VPS Initial Setup

These steps were already completed. Documented here for reference if the VPS needs to be rebuilt.

```bash
# 1. Open port 8000
ufw allow 8000

# 2. Clone the dashboard repo
cd /root
git clone https://github.com/Arkanav-Enterprises/ugc-dashboard.git

# 3. Set up the backend
cd /root/ugc-dashboard/dashboard/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Create the systemd service
nano /etc/systemd/system/openclaw-api.service
# (paste the service config below, save with Ctrl+O, exit with Ctrl+X)

# 5. Enable and start
systemctl daemon-reload
systemctl enable openclaw-api
systemctl start openclaw-api

# 6. Verify
systemctl status openclaw-api
curl -s http://localhost:8000/api/health
```

---

## VPS Backend Service

The backend runs as a systemd service called `openclaw-api`.

### Service file location
```
/etc/systemd/system/openclaw-api.service
```

### Common commands (run on VPS)

```bash
# Check if it's running
systemctl status openclaw-api

# View live logs
journalctl -u openclaw-api -f

# Restart after code changes
systemctl restart openclaw-api

# Stop the service
systemctl stop openclaw-api

# Start the service
systemctl start openclaw-api

# Pull latest code and restart (most common operation)
cd /root/ugc-dashboard && git pull && systemctl restart openclaw-api
```

### Service configuration

```ini
[Unit]
Description=OpenClaw Dashboard API
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/ugc-dashboard/dashboard/backend
Environment=PIPELINE_ROOT=/root/openclaw
ExecStart=/root/openclaw/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

The service:
- Starts automatically on VPS reboot
- Restarts automatically if it crashes (after 5 seconds)
- Runs uvicorn on `0.0.0.0:8000` (accessible from outside)

---

## VPS Firewall

Port 8000 is open via UFW:
```bash
ufw allow 8000
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Dashboard shows "Loading..." forever | Backend not running on VPS | SSH to VPS, run `systemctl status openclaw-api` |
| API errors in browser console | Backend crashed | `ssh root@72.60.204.30` then `systemctl restart openclaw-api` |
| Chat not streaming | SSE endpoint issue | Check `journalctl -u openclaw-api -f` for errors |
| Frontend shows old version | Vercel cache | Redeploy: `vercel deploy --prod --yes` from `dashboard/frontend/` |
| Backend has old code | Forgot to pull on VPS | `cd /root/ugc-dashboard && git pull && systemctl restart openclaw-api` |
| "No data" on Overview | Pipeline hasn't run yet or PIPELINE_ROOT wrong | Check `/root/openclaw/logs/video_autopilot.jsonl` exists |
| Port 8000 unreachable | Firewall blocking | `ufw allow 8000` on VPS |
| ANTHROPIC_API_KEY error in chat | Key not in .env | Check `/root/openclaw/.env` has the key set |
| Action buttons show "No such file: .venv/bin/python3" | Pipeline venv missing | Backend falls back to system `python3` — run `git pull && systemctl restart openclaw-api` on VPS |
| Action buttons fire with no confirmation | Old frontend version | Redeploy frontend — Generate Reel and Run All require confirmation now |

---

## Key URLs

| What | URL |
|------|-----|
| **Dashboard (live)** | https://frontend-arkanaventerprises-7462s-projects.vercel.app |
| **GitHub repo** | https://github.com/Arkanav-Enterprises/ugc-dashboard |
| **Vercel project** | https://vercel.com/arkanaventerprises-7462s-projects/frontend |
| **VPS backend health** | http://72.60.204.30:8000/api/health |
| **VPS SSH** | `ssh root@72.60.204.30` |
