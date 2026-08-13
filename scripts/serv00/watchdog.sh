#!/usr/local/bin/bash
set -euo pipefail

SESSION="${SESSION:-bond_bot}"
LOG="${LOG:-$HOME/logs/watchdog.log}"

mkdir -p "$(dirname "$LOG")"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    exit 0
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') сессия $SESSION не найдена, запускаю" >> "$LOG"
"$HOME/bond_bot/scripts/serv00/run.sh" >> "$LOG" 2>&1
