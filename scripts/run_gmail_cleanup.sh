#!/bin/bash
# Gmail auto-cleanup cron wrapper
# Loads environment variables and runs auto_cleanup.py

PROJECT_DIR="/home/natsuki/multi-agent-phantom"
LOG_FILE="/tmp/gmail_cleanup.log"

# Load environment variables from .gemini/.env
if [ -f "$PROJECT_DIR/.gemini/.env" ]; then
    set -a
    source "$PROJECT_DIR/.gemini/.env"
    set +a
fi

cd "$PROJECT_DIR"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
python3 "$PROJECT_DIR/scripts/auto_cleanup.py" >> "$LOG_FILE" 2>&1
echo "" >> "$LOG_FILE"
