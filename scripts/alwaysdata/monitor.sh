#!/bin/bash
set -uo pipefail

MARKER="${MARKER:-$HOME/.bond_restart_requested}"

if [ -f "$MARKER" ]; then
    rm -f "$MARKER"
    echo "запрошен перезапуск после деплоя"
    exit 1
fi

exit 0
