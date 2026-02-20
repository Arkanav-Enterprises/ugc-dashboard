#!/bin/bash
# Video autopilot cron wrapper
# Runs daily at 12 PM IST (6:30 AM UTC)
# Generates 1 reel per persona: sanya (ManifestLock) + sophie (JournalLock) + aliyah (random app)
#
# Crontab entry (use `bash` prefix to avoid permission issues):
#   30 6 * * * bash /root/openclaw/scripts/autopilot_video_cron.sh >> /root/openclaw/logs/cron.log 2>&1

set -euo pipefail

# Cron has minimal PATH — ensure common tool locations are available
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

PROJECT_DIR="/root/openclaw"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/video_$(date +%Y%m%d_%H%M%S).log"

# Guard: ensure virtualenv exists
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "FATAL: virtualenv not found at $PROJECT_DIR/.venv" | tee -a "$LOGFILE"
    exit 1
fi

cd "$PROJECT_DIR"
source .venv/bin/activate

# Load .env safely (skip comments, blank lines, and lines with no =)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "=== Video autopilot started at $(date) ===" >> "$LOGFILE"

if python3 scripts/autopilot_video.py --persona all >> "$LOGFILE" 2>&1; then
    echo "=== Video autopilot finished OK at $(date) ===" >> "$LOGFILE"
else
    EXIT_CODE=$?
    echo "=== Video autopilot FAILED (exit $EXIT_CODE) at $(date) ===" >> "$LOGFILE"
    # Send failure alert if mail is available
    if command -v mail &>/dev/null; then
        tail -30 "$LOGFILE" | mail -s "[OpenClaw] Video cron FAILED $(date +%Y-%m-%d)" root
    fi
    exit $EXIT_CODE
fi

# Clean logs older than 30 days
find "$LOG_DIR" -name "video_*.log" -mtime +30 -delete
