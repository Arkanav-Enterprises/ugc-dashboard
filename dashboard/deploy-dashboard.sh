#!/bin/bash
# Deploy OpenClaw Dashboard to Hostinger VPS
# Usage: bash dashboard/deploy-dashboard.sh

set -euo pipefail

VPS_IP="72.60.204.30"
VPS_USER="root"
VPS_DEST="/root/openclaw/dashboard"

echo "=== Deploying OpenClaw Dashboard to ${VPS_USER}@${VPS_IP} ==="
echo ""

# 1. Build frontend locally
echo "[1/4] Building frontend..."
cd "$(dirname "$0")/frontend"
npm run build
cd ../..

# 2. Sync dashboard files to VPS
echo ""
echo "[2/4] Syncing files to VPS..."
rsync -avz --delete \
    --exclude='frontend/node_modules/' \
    --exclude='frontend/.next/' \
    --exclude='backend/.venv/' \
    --exclude='backend/__pycache__/' \
    --exclude='.DS_Store' \
    dashboard/ "${VPS_USER}@${VPS_IP}:${VPS_DEST}/"

# 3. Run setup on VPS
echo ""
echo "[3/4] Setting up on VPS..."
ssh "${VPS_USER}@${VPS_IP}" bash <<'REMOTE_SETUP'
set -euo pipefail

DASH_DIR="/root/openclaw/dashboard"

# Backend venv
echo "  Setting up backend venv..."
cd "$DASH_DIR/backend"
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
# Force-replace twscrape (PyPI 0.17 → GitHub main with x-client-transaction-id fix)
.venv/bin/pip uninstall -y twscrape 2>/dev/null || true
.venv/bin/pip install -q -r requirements.txt

# Frontend deps + build
echo "  Installing frontend deps..."
cd "$DASH_DIR/frontend"
npm install --production=false 2>/dev/null
echo "  Building frontend..."
npm run build

# Create systemd services
echo "  Creating systemd services..."

cat > /etc/systemd/system/openclaw-api.service <<EOF
[Unit]
Description=OpenClaw Dashboard API
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/openclaw/dashboard/backend
ExecStart=/root/openclaw/dashboard/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/root/openclaw/.env

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/openclaw-web.service <<EOF
[Unit]
Description=OpenClaw Dashboard Web
After=openclaw-api.service

[Service]
Type=simple
WorkingDirectory=/root/openclaw/dashboard/frontend
ExecStart=/usr/bin/npx next start -p 3000
Restart=always
RestartSec=5
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable openclaw-api openclaw-web
systemctl restart openclaw-api openclaw-web

echo "  Services started."
REMOTE_SETUP

# 4. Verify
echo ""
echo "[4/4] Verifying..."
sleep 3
ssh "${VPS_USER}@${VPS_IP}" "curl -sf http://localhost:8000/api/health && echo ' API OK' || echo ' API FAILED'"
ssh "${VPS_USER}@${VPS_IP}" "curl -sf -o /dev/null -w 'Web: HTTP %{http_code}\n' http://localhost:3000 || echo 'Web FAILED'"

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Dashboard is live at:"
echo "  http://${VPS_IP}:3000"
echo ""
echo "API docs at:"
echo "  http://${VPS_IP}:8000/docs"
echo ""
echo "To check status:"
echo "  ssh ${VPS_USER}@${VPS_IP} systemctl status openclaw-api openclaw-web"
