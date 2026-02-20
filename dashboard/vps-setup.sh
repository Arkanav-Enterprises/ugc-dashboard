#!/bin/bash
# OpenClaw Dashboard — VPS Setup Script
# Run this ON the VPS after transferring dashboard/ files
set -euo pipefail

DASH_DIR="/root/openclaw/dashboard"
echo "=== OpenClaw Dashboard VPS Setup ==="

# 1. Backend venv + deps
echo "[1/4] Setting up backend..."
cd "$DASH_DIR/backend"
python3 -m venv .venv
.venv/bin/pip install --quiet -r requirements.txt
echo "  Backend ready."

# 2. Frontend deps + build
echo "[2/4] Setting up frontend..."
cd "$DASH_DIR/frontend"
npm install 2>/dev/null
npm run build
echo "  Frontend ready."

# 3. Create systemd services
echo "[3/4] Creating systemd services..."

cat > /etc/systemd/system/openclaw-api.service <<'EOF'
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

cat > /etc/systemd/system/openclaw-web.service <<'EOF'
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

# 4. Open firewall ports
echo "[4/4] Opening ports 3000 and 8000..."
if command -v ufw &>/dev/null; then
    ufw allow 3000/tcp 2>/dev/null || true
    ufw allow 8000/tcp 2>/dev/null || true
fi
echo "  Ports open."

sleep 3
echo ""
echo "=== Verifying ==="
curl -sf http://localhost:8000/api/health && echo " API OK" || echo " API FAILED"
curl -sf -o /dev/null -w "Web: HTTP %{http_code}\n" http://localhost:3000 || echo "Web FAILED (may need a few more seconds)"

echo ""
echo "=== Dashboard is live! ==="
echo "  Web:  http://$(hostname -I | awk '{print $1}'):3000"
echo "  API:  http://$(hostname -I | awk '{print $1}'):8000/docs"
