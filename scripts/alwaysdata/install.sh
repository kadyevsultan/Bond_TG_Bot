#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/bond_bot}"
VENV="${VENV:-$HOME/venv}"
DATA_DIR="${DATA_DIR:-$HOME/bond_data}"
PYTHON="${PYTHON:-python3.12}"

command -v "$PYTHON" >/dev/null || PYTHON=python3.11

mkdir -p "$DATA_DIR"

if [ ! -d "$VENV" ]; then
    "$PYTHON" -m venv "$VENV"
fi

source "$VENV/bin/activate"
pip install --quiet --no-cache-dir --upgrade pip
cd "$APP_DIR"
pip install --no-cache-dir --no-compile -e .

find "$VENV" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "создан .env — заполните BOT_TOKEN, ADMIN_IDS, DB_PATH=$DATA_DIR/bond_bot.sqlite3"
fi

echo
echo "занято под venv: $(du -sh "$VENV" | cut -f1)"
echo "занято всего:    $(du -sh "$HOME" | cut -f1) из 100M"
echo
echo "команда для службы (Advanced -> Services):"
echo "$APP_DIR/scripts/alwaysdata/serve.sh"
