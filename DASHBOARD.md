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
   │  reads local files
   ▼
Pipeline data at /root/openclaw/
   (logs, assets, videos, skills, memory)
```

The frontend runs on Vercel (free tier). The backend runs on the Hostinger VPS as a systemd service. The browser only talks to Vercel over HTTPS — Vercel proxies API requests to the VPS behind the scenes, avoiding mixed-content issues without needing a domain or SSL certificate on the VPS.

---

## Repository

**GitHub:** https://github.com/Arkanav-Enterprises/ugc-dashboard

The repo contains only the dashboard code (not the pipeline scripts, skills, or assets):

```
ugc-dashboard/
├── .gitignore
└── dashboard/
    ├── backend/                ← FastAPI (runs on VPS)
    │   ├── main.py             ← App entrypoint
    │   ├── config.py           ← Paths and env config
    │   ├── requirements.txt    ← Python dependencies
    │   ├── models.py           ← Pydantic models
    │   ├── routers/
    │   │   ├── assets.py       ← /api/assets/* endpoints
    │   │   ├── chat.py         ← /api/chat/* (SSE + WebSocket)
    │   │   ├── content.py      ← /api/content/* endpoints
    │   │   ├── knowledge.py    ← /api/knowledge/* endpoints
    │   │   ├── logs.py         ← /api/logs/* endpoints
    │   │   └── pipeline.py     ← /api/pipeline/* endpoints
    │   └── services/
    │       ├── claude_chat.py  ← Anthropic streaming chat
    │       ├── log_reader.py   ← Reads pipeline log files
    │       ├── pipeline_runner.py ← Triggers pipeline runs
    │       └── skill_loader.py ← Loads skill/memory files
    └── frontend/               ← Next.js (deployed to Vercel)
        ├── next.config.ts      ← API proxy rewrites
        ├── package.json
        └── src/
            ├── app/
            │   ├── page.tsx        ← Overview dashboard
            │   ├── content/        ← Content Gallery
            │   ├── pipeline/       ← Pipeline Monitor
            │   ├── chat/           ← Agent Chat
            │   ├── knowledge/      ← Knowledge Base editor
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
| **Pipeline Monitor** | `/pipeline` | Trigger pipeline runs (generate, dry-run, caption-only), view active/recent runs |
| **Agent Chat** | `/chat` | Chat with Claude using skill/memory context, generate hooks and captions |
| **Knowledge Base** | `/knowledge` | View and edit skill files and memory files that feed into content generation |
| **Asset Manager** | `/assets` | Browse reference images, clips, screen recordings, and asset usage history |
| **Logs** | `/logs` | View raw pipeline logs and run history |

---

## What Lives Where

| Component | Location | Deployed via |
|-----------|----------|-------------|
| **Frontend** (Next.js) | Vercel | Auto-deploys on `git push` to GitHub |
| **Backend** (FastAPI) | VPS at `/root/ugc-dashboard/` | `git pull` + restart service |
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

## Development Workflow

### Making frontend changes

```bash
# 1. Edit files in dashboard/frontend/src/
# 2. Test locally
cd ~/openclaw/dashboard/frontend
npm run dev

# 3. Push to deploy (Vercel auto-builds)
cd ~/openclaw
git add dashboard/frontend/
git commit -m "description of change"
git push
```

Vercel picks up the push and deploys automatically. Takes ~30 seconds.

### Making backend changes

```bash
# 1. Edit files in dashboard/backend/
# 2. Test locally
cd ~/openclaw/dashboard/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# 3. Push and update VPS
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
| Frontend shows old version | Vercel cache | Push an empty commit: `git commit --allow-empty -m "redeploy" && git push` |
| Backend has old code | Forgot to pull on VPS | `cd /root/ugc-dashboard && git pull && systemctl restart openclaw-dashboard` |
| "No data" on Overview | Pipeline hasn't run yet or PIPELINE_ROOT wrong | Check `/root/openclaw/logs/video_autopilot.jsonl` exists |
| Port 8000 unreachable | Firewall blocking | `ufw allow 8000` on VPS |
| ANTHROPIC_API_KEY error in chat | Key not in .env | Check `/root/openclaw/.env` has the key set |

---

## Key URLs

| What | URL |
|------|-----|
| **Dashboard (live)** | https://frontend-arkanaventerprises-7462s-projects.vercel.app |
| **GitHub repo** | https://github.com/Arkanav-Enterprises/ugc-dashboard |
| **Vercel project** | https://vercel.com/arkanaventerprises-7462s-projects/frontend |
| **VPS backend health** | http://72.60.204.30:8000/api/health |
| **VPS SSH** | `ssh root@72.60.204.30` |
