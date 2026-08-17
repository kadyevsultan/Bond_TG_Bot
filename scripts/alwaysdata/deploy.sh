#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/bond_bot}"
VENV="${VENV:-$HOME/venv}"
DATA_DIR="${DATA_DIR:-$HOME/bond_data}"
PYTHON="${PYTHON:-python3.12}"

command -v "$PYTHON" >/dev/null || PYTHON=python3.11

mkdir -p "$DATA_DIR"

DB="$DATA_DIR/bond_bot.sqlite3"
if [ -f "$DB" ]; then
    sqlite3 "$DB" ".backup '$DATA_DIR/backup.sqlite3'"
    echo "бэкап: $(du -h "$DATA_DIR/backup.sqlite3" | cut -f1)"
fi

if [ ! -d "$VENV" ]; then
    echo "создаю venv на $PYTHON"
    "$PYTHON" -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install --quiet --no-cache-dir --upgrade pip
cd "$APP_DIR"
pip install --quiet --no-cache-dir --no-compile -e .
find "$VENV" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

if [ ! -f "$APP_DIR/.env" ]; then
    echo "ОШИБКА: нет $APP_DIR/.env — его пишет CI из секретов, либо создайте вручную" >&2
    exit 1
fi

bash "$APP_DIR/scripts/alwaysdata/restart.sh"

echo "занято: $(du -sh "$HOME" | cut -f1) из 100M"
