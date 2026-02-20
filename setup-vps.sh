#!/bin/bash
# VPS Setup Script for OpenClaw
# Run this ON the Hostinger VPS after deploying files
# Usage: bash setup-vps.sh

set -euo pipefail

echo "=== OpenClaw VPS Setup ==="
echo ""

# 1. Check/upgrade Node.js
echo "[1/6] Checking Node.js version..."
if command -v node &> /dev/null; then
    NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
    echo "  Found Node.js v$(node --version)"
    if [ "$NODE_VER" -lt 22 ]; then
        echo "  Upgrading to Node.js 22..."
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        sudo apt-get install -y nodejs
    else
        echo "  Node.js is already v22+. OK."
    fi
else
    echo "  Installing Node.js 22..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# 2. Install OpenClaw
echo ""
echo "[2/6] Installing OpenClaw..."
npm install -g openclaw@latest
echo "  OpenClaw version: $(openclaw --version 2>/dev/null || echo 'installed')"

# 3. Install Python dependencies
echo ""
echo "[3/6] Installing Python dependencies..."
pip3 install Pillow python-dotenv requests
echo "  Pillow + deps installed."

# 4. Verify existing tools
echo ""
echo "[4/6] Verifying existing tools..."
python3 -c "from PIL import Image; print('  Pillow: OK')"
python3 -c "import requests; print('  Requests: OK')"
ffmpeg -version 2>/dev/null | head -1 && echo "  FFmpeg: OK" || echo "  WARNING: FFmpeg not found — needed for UGC videos"

# Check for existing Replicate/MoviePy from UGC pipeline
python3 -c "import replicate; print('  replicate: OK')" 2>/dev/null || echo "  NOTE: replicate not installed (needed for UGC videos only)"
python3 -c "import moviepy; print('  MoviePy: OK')" 2>/dev/null || echo "  NOTE: MoviePy not installed (needed for UGC videos only)"

# 5. Check .env
echo ""
echo "[5/6] Checking .env file..."
if [ -f /root/openclaw/.env ]; then
    # Check each key is set (not placeholder)
    for key in ANTHROPIC_API_KEY OPENAI_API_KEY REPLICATE_API_TOKEN POSTIZ_API_KEY; do
        val=$(grep "^${key}=" /root/openclaw/.env | cut -d= -f2)
        if [ -z "$val" ] || echo "$val" | grep -q "PASTE_YOUR"; then
            echo "  WARNING: $key is not set in .env"
        else
            echo "  $key: configured"
        fi
    done
else
    echo "  WARNING: .env file not found at /root/openclaw/.env"
fi

# 6. Make scripts executable
echo ""
echo "[6/6] Setting permissions..."
chmod +x /root/openclaw/scripts/wrapper.sh
echo "  Scripts are executable."

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Fill in API keys:  nano /root/openclaw/.env"
echo "  2. Run OpenClaw onboarding:  openclaw onboard --install-daemon"
echo "  3. Install ClawhHub skills:"
echo "     - RevenueCat: openclaw skill install @jeiting/revenuecat"
echo "     - Bird (X/Twitter): openclaw skill install @steipete/bird"
echo "  4. Test slideshow generation:"
echo "     cd /root/openclaw/scripts && python3 generate_slideshow.py"
echo "  5. Set up cron jobs (see below)"
echo ""
echo "Cron schedule (add with: crontab -e):"
echo "  0 2 * * * /root/openclaw/scripts/wrapper.sh batch_generate"
echo "  0 8 * * * /root/openclaw/scripts/wrapper.sh post_morning"
echo "  0 13 * * * /root/openclaw/scripts/wrapper.sh post_afternoon"
echo "  0 19 * * * /root/openclaw/scripts/wrapper.sh post_evening"
echo "  0 23 * * * /root/openclaw/scripts/wrapper.sh daily_metrics"
echo "  0 10 * * 0 /root/openclaw/scripts/wrapper.sh weekly_review"
