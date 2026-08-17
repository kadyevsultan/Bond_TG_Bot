#!/bin/bash
set -euo pipefail

VENV="${VENV:-$HOME/venv}"
APP_DIR="${APP_DIR:-$HOME/bond_bot}"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

cd "$APP_DIR"
exec "$VENV/bin/python" -m bond_bot
