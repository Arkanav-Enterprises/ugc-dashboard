#!/bin/bash
# autopilot_cron.sh — Cron wrapper for autopilot.py
# Loads environment, sets working directory, passes all args through.
#
# Cron entries:
#   30 1 * * * /root/openclaw/scripts/autopilot_cron.sh --account sophie.unplugs
#   45 1 * * * /root/openclaw/scripts/autopilot_cron.sh --account emillywilks
#   0  2 * * * /root/openclaw/scripts/autopilot_cron.sh --account sanyahealing

set -e

# Save original args before parsing
ORIG_ARGS=("$@")

# Project root
cd /root/openclaw

# Load env vars (API keys, SMTP creds)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# ─── Read schedule config ────────────────────────────
CONFIG_FILE="/root/openclaw/config/schedule.json"

# Extract --account value from args
ACCOUNT=""
ARGS=("$@")
for (( i=0; i<${#ARGS[@]}; i++ )); do
    if [ "${ARGS[$i]}" = "--account" ] && [ $((i+1)) -lt ${#ARGS[@]} ]; then
        ACCOUNT="${ARGS[$((i+1))]}"
        break
    fi
done

if [ -n "$ACCOUNT" ] && [ -f "$CONFIG_FILE" ]; then
    ENABLED=$(python3 -c "
import json
c = json.load(open('$CONFIG_FILE'))
tp = c.get('text_pipeline', {})
if not tp.get('enabled', True):
    print('False')
else:
    acct = tp.get('accounts', {}).get('$ACCOUNT', {})
    print(acct.get('enabled', True))
" 2>/dev/null || echo "True")

    if [ "$ENABLED" = "False" ]; then
        echo "[$(date)] Text pipeline: $ACCOUNT DISABLED in config — skipping"
        exit 0
    fi
fi

# Run autopilot, pass all args through
python3 scripts/autopilot.py "${ORIG_ARGS[@]}"
