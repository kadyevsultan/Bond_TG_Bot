#!/usr/local/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/bond_bot}"
VENV="${VENV:-$HOME/.virtualenvs/bond_bot}"
SESSION="${SESSION:-bond_bot}"
LOG="${LOG:-$HOME/logs/bond_bot.log}"

mkdir -p "$(dirname "$LOG")"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "already running in tmux session $SESSION"
    exit 0
fi

cd "$APP_DIR"
tmux new-session -d -s "$SESSION" \
    "source '$VENV/bin/activate' && exec python -m bond_bot >> '$LOG' 2>&1"

echo "started: tmux session $SESSION, log $LOG"
