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

# ─── Read schedule config ────────────────────────────
CONFIG_FILE="$PROJECT_DIR/config/schedule.json"
PERSONA_ARG="all"  # default fallback

if [ -f "$CONFIG_FILE" ]; then
    # Check if video pipeline is enabled
    VP_ENABLED=$(python3 -c "import json; c=json.load(open('$CONFIG_FILE')); print(c['video_pipeline']['enabled'])" 2>/dev/null || echo "True")
    if [ "$VP_ENABLED" = "False" ]; then
        echo "=== Video pipeline DISABLED in config — skipping at $(date) ===" >> "$LOGFILE"
        exit 0
    fi

    # Build comma-separated list of enabled personas + collect video type overrides
    PERSONA_ARG=$(python3 -c "
import json, sys
c = json.load(open('$CONFIG_FILE'))
personas = c['video_pipeline'].get('personas', {})
enabled = [p for p, cfg in personas.items() if cfg.get('enabled', True)]
if not enabled:
    print('NONE', end='')
else:
    print(','.join(enabled), end='')
" 2>/dev/null || echo "all")

    if [ "$PERSONA_ARG" = "NONE" ]; then
        echo "=== All personas DISABLED in config — skipping at $(date) ===" >> "$LOGFILE"
        exit 0
    fi

    # Check for video type override (only if all enabled personas share the same override)
    VIDEO_TYPE_ARG=$(python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
personas = c['video_pipeline'].get('personas', {})
enabled = {p: cfg for p, cfg in personas.items() if cfg.get('enabled', True)}
types = set(cfg.get('video_type', 'auto') for cfg in enabled.values())
if len(types) == 1 and 'auto' not in types:
    print(types.pop(), end='')
else:
    print('', end='')
" 2>/dev/null || echo "")
fi

echo "=== Video autopilot started at $(date) ===" >> "$LOGFILE"
echo "  Personas: $PERSONA_ARG" >> "$LOGFILE"

CMD="python3 scripts/autopilot_video.py --persona $PERSONA_ARG"
if [ -n "$VIDEO_TYPE_ARG" ]; then
    CMD="$CMD --video-type $VIDEO_TYPE_ARG"
    echo "  Video type override: $VIDEO_TYPE_ARG" >> "$LOGFILE"
fi

if eval "$CMD" >> "$LOGFILE" 2>&1; then
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
