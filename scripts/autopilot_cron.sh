#!/bin/bash
# autopilot_cron.sh — Cron wrapper for autopilot.py
# Loads environment, sets working directory, passes all args through.
#
# Cron entries:
#   30 1 * * * /root/openclaw/scripts/autopilot_cron.sh --account sophie.unplugs
#   45 1 * * * /root/openclaw/scripts/autopilot_cron.sh --account emillywilks
#   0  2 * * * /root/openclaw/scripts/autopilot_cron.sh --account sanyahealing

set -e

# Project root
cd /root/openclaw

# Load env vars (API keys, SMTP creds)
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Run autopilot, pass all args through
python3 scripts/autopilot.py "$@"
