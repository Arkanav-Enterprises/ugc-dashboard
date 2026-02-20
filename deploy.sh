#!/bin/bash
# Deploy OpenClaw project to Hostinger VPS
# Usage: ./deploy.sh <vps-ip> [--with-assets]

set -euo pipefail

VPS_IP="${1:?Usage: ./deploy.sh <vps-ip> [--with-assets]}"
VPS_USER="root"
VPS_DEST="/root/openclaw"
WITH_ASSETS="${2:-}"

echo "Deploying to ${VPS_USER}@${VPS_IP}:${VPS_DEST}..."

# Sync project files (exclude assets by default for speed)
EXCLUDE_ARGS="--exclude='output/' --exclude='logs/' --exclude='__pycache__/' --exclude='.DS_Store'"

if [ "$WITH_ASSETS" != "--with-assets" ]; then
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude='assets/app-screenshots/' --exclude='assets/demo-recordings/' --exclude='assets/splash.mp4' --exclude='assets/cta-images/'"
    echo "Skipping large assets (use --with-assets to include)"
fi

eval rsync -avz $EXCLUDE_ARGS \
    ~/openclaw/ "${VPS_USER}@${VPS_IP}:${VPS_DEST}/"

# Ensure all scripts are executable after rsync (prevents "Permission denied" in cron)
echo "Setting execute permissions on scripts..."
ssh "${VPS_USER}@${VPS_IP}" "chmod +x ${VPS_DEST}/scripts/*.sh ${VPS_DEST}/deploy.sh 2>/dev/null; true"

# Update crontab to use bash prefix (idempotent)
echo "Ensuring crontab uses 'bash' prefix..."
ssh "${VPS_USER}@${VPS_IP}" "crontab -l 2>/dev/null | sed 's|^\([0-9].*\) /root/openclaw/scripts/autopilot_video_cron.sh|\\1 bash /root/openclaw/scripts/autopilot_video_cron.sh|' | crontab -"

echo ""
echo "Deploy complete. Next steps on VPS:"
echo "  ssh ${VPS_USER}@${VPS_IP}"
echo "  cd ${VPS_DEST}"
echo "  cat .env  # verify API keys are set"
echo "  python3 -c \"from PIL import Image; print('Pillow OK')\""
