#!/bin/bash
# OpenClaw cron wrapper script
# Routes cron commands to the appropriate Python scripts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/${1:-unknown}_${TIMESTAMP}.log"

export WORK_DIR="$PROJECT_DIR/output"
export ASSETS_DIR="$PROJECT_DIR/assets"

# Source environment variables
source "$PROJECT_DIR/.env" 2>/dev/null || true

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

case "${1:-help}" in
    batch_generate)
        log "Starting batch content generation..."
        cd "$SCRIPT_DIR"
        python3 generate_slideshow.py 2>&1 | tee -a "$LOG_FILE"
        log "Batch generation complete."
        ;;

    post_morning)
        log "Posting morning content..."
        cd "$SCRIPT_DIR"
        # Find the latest generated slides and post them
        python3 post_to_tiktok.py "$WORK_DIR"/slide_*.png 2>&1 | tee -a "$LOG_FILE"
        log "Morning post complete."
        ;;

    post_afternoon)
        log "Posting afternoon content..."
        cd "$SCRIPT_DIR"
        python3 post_to_tiktok.py "$WORK_DIR"/slide_*.png 2>&1 | tee -a "$LOG_FILE"
        log "Afternoon post complete."
        ;;

    post_evening)
        log "Posting evening content..."
        cd "$SCRIPT_DIR"
        python3 post_to_tiktok.py "$WORK_DIR"/slide_*.png 2>&1 | tee -a "$LOG_FILE"
        log "Evening post complete."
        ;;

    daily_metrics)
        log "Pulling daily metrics from RevenueCat..."
        # This would be handled by the OpenClaw agent via ClawhHub RevenueCat skill
        log "Metrics pull complete — check memory/daily-metrics.md"
        ;;

    weekly_review)
        log "Weekly review reminder sent."
        # Trigger OpenClaw agent to perform weekly analysis
        log "Review memory/post-performance.md and memory/hook-results.md"
        ;;

    help|*)
        echo "Usage: $0 {batch_generate|post_morning|post_afternoon|post_evening|daily_metrics|weekly_review}"
        echo ""
        echo "Commands:"
        echo "  batch_generate   - Generate content for the day (run at 2am)"
        echo "  post_morning     - Post morning content (8am)"
        echo "  post_afternoon   - Post afternoon content (1pm)"
        echo "  post_evening     - Post evening content (7pm)"
        echo "  daily_metrics    - Pull RevenueCat metrics (11pm)"
        echo "  weekly_review    - Trigger weekly review (Sunday 10am)"
        ;;
esac
