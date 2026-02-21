# OpenClaw Dashboard

Last updated: 2026-02-21

---

## What This Is

The OpenClaw Dashboard is an internal web app for the team to monitor and control the UGC video generation pipeline. It shows pipeline runs, costs, generated reels, and provides an AI chat agent for content strategy.

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
    │   │   ├── assets.py       ← /api/assets/* endpoints
    │   │   ├── chat.py         ← /api/chat/* (SSE streaming + WebSocket)
    │   │   ├── content.py      ← /api/content/* endpoints
    │   │   ├── knowledge.py    ← /api/knowledge/* endpoints
    │   │   ├── logs.py         ← /api/logs/* endpoints
    │   │   ├── pipeline.py     ← /api/pipeline/* endpoints
    │   │   ├── schedule.py     ← /api/schedule/* endpoints
    │   │   ├── youtube_research.py ← /api/research/* (YT scan + analyze)
    │   │   └── reddit_research.py  ← /api/research/reddit/* (search + analyze)
    │   └── services/
    │       ├── claude_chat.py  ← Anthropic streaming chat
    │       ├── log_reader.py   ← Reads pipeline log files
    │       ├── pipeline_runner.py ← Runs pipeline scripts as subprocesses
    │       ├── skill_loader.py ← Loads skill/memory files for context
    │       ├── youtube_research.py ← YT channel scanning, transcript fetch, Claude analysis
    │       └── reddit_research.py  ← Reddit search, comment fetch, Claude analysis
    └── frontend/               ← Next.js (deployed to Vercel)
        ├── next.config.ts      ← API proxy rewrites (BACKEND_URL)
        ├── package.json
        └── src/
            ├── app/
            │   ├── page.tsx        ← Overview dashboard
            │   ├── content/        ← Content Gallery
            │   ├── pipeline/       ← Pipeline Monitor (read-only)
            │   ├── chat/           ← Agent Chat + Action buttons
            │   ├── knowledge/      ← Knowledge Base editor
            │   ├── research/       ← Trend Research (YouTube + Reddit)
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
| **Agent Chat** | `/chat` | Chat with Claude using skill/memory context + action buttons to trigger pipeline runs (see below) |
| **Knowledge Base** | `/knowledge` | View and edit skill files and memory files that feed into content generation |
| **Trend Research** | `/research` | Analyze YouTube channels or Reddit threads — fetch transcripts/comments, summarize with Claude, run cross-source theme analysis |
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

1. You check the files you want Claude to reference (3 skills + 2 memory files are pre-selected by default)
2. When you send a message, the frontend sends the selected file names along with your chat history
3. The backend reads the full content of each selected file from disk
4. The file contents are injected into Claude's **system prompt** as structured context:
   ```
   === SKILL: content-strategy.md ===
   (full file content)

   === MEMORY: post-performance.md ===
   (full file content)
   ```
5. Claude responds with awareness of your content strategy, past performance data, etc.

### Default selections

| Type | Default files |
|------|--------------|
| Skills | `content-strategy.md`, `manifest-lock-knowledge.md`, `tiktok-slideshows.md` |
| Memory | `post-performance.md`, `failure-log.md` |

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

## What Lives Where

| Component | Location | Deployed via |
|-----------|----------|-------------|
| **Frontend** (Next.js) | Vercel | `vercel deploy --prod` or auto-deploy on push |
| **Backend** (FastAPI) | VPS at `/root/ugc-dashboard/` | `git pull` + `systemctl restart openclaw-dashboard` |
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

Set via the systemd service file at `/etc/systemd/system/openclaw-dashboard.service`:

| Variable | Value | Purpose |
|----------|-------|---------|
| `PIPELINE_ROOT` | `/root/openclaw` | Tells the backend where pipeline data lives |

The backend also reads from `/root/openclaw/.env` for:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API for Agent Chat |
| `DAILY_COST_CAP` | Spending cap shown on Overview |

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
cd /root/ugc-dashboard && git pull && systemctl restart openclaw-dashboard
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
nano /etc/systemd/system/openclaw-dashboard.service
# (paste the service config below, save with Ctrl+O, exit with Ctrl+X)

# 5. Enable and start
systemctl daemon-reload
systemctl enable openclaw-dashboard
systemctl start openclaw-dashboard

# 6. Verify
systemctl status openclaw-dashboard
curl -s http://localhost:8000/api/health
```

---

## VPS Backend Service

The backend runs as a systemd service called `openclaw-dashboard`.

### Service file location
```
/etc/systemd/system/openclaw-dashboard.service
```

### Common commands (run on VPS)

```bash
# Check if it's running
systemctl status openclaw-dashboard

# View live logs
journalctl -u openclaw-dashboard -f

# Restart after code changes
systemctl restart openclaw-dashboard

# Stop the service
systemctl stop openclaw-dashboard

# Start the service
systemctl start openclaw-dashboard

# Pull latest code and restart (most common operation)
cd /root/ugc-dashboard && git pull && systemctl restart openclaw-dashboard
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
ExecStart=/root/ugc-dashboard/dashboard/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
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
| Dashboard shows "Loading..." forever | Backend not running on VPS | SSH to VPS, run `systemctl status openclaw-dashboard` |
| API errors in browser console | Backend crashed | `ssh root@72.60.204.30` then `systemctl restart openclaw-dashboard` |
| Chat not streaming | SSE endpoint issue | Check `journalctl -u openclaw-dashboard -f` for errors |
| Frontend shows old version | Vercel cache | Redeploy: `vercel deploy --prod --yes` from `dashboard/frontend/` |
| Backend has old code | Forgot to pull on VPS | `cd /root/ugc-dashboard && git pull && systemctl restart openclaw-dashboard` |
| "No data" on Overview | Pipeline hasn't run yet or PIPELINE_ROOT wrong | Check `/root/openclaw/logs/video_autopilot.jsonl` exists |
| Port 8000 unreachable | Firewall blocking | `ufw allow 8000` on VPS |
| ANTHROPIC_API_KEY error in chat | Key not in .env | Check `/root/openclaw/.env` has the key set |
| Action buttons show "No such file: .venv/bin/python3" | Pipeline venv missing | Backend falls back to system `python3` — run `git pull && systemctl restart openclaw-dashboard` on VPS |
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
