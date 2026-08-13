#!/usr/local/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/bond_bot}"
VENV="${VENV:-$HOME/.virtualenvs/bond_bot}"
SESSION="${SESSION:-bond_bot}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups}"

cd "$APP_DIR"

mkdir -p "$BACKUP_DIR"
DB="$(grep -E '^DB_PATH=' .env | cut -d= -f2-)"
DB="${DB:-$APP_DIR/data/bond_bot.sqlite3}"
if [ -f "$DB" ]; then
    STAMP="$(date '+%Y%m%d-%H%M%S')"
    sqlite3 "$DB" ".backup '$BACKUP_DIR/bond_bot-$STAMP.sqlite3'"
    ls -1t "$BACKUP_DIR"/bond_bot-*.sqlite3 | tail -n +15 | xargs -r rm --
    echo "бэкап: $BACKUP_DIR/bond_bot-$STAMP.sqlite3"
fi

git pull --ff-only

source "$VENV/bin/activate"
export MAKEFLAGS="-j1" CPUCOUNT=1 MAX_CONCURRENCY=1
export CFLAGS="-I/usr/local/include" CXXFLAGS="-I/usr/local/include"
pip install --quiet --upgrade -e .

tmux kill-session -t "$SESSION" 2>/dev/null || true
"$APP_DIR/scripts/serv00/run.sh"
