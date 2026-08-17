#!/bin/bash
set -uo pipefail

if [ -f "$HOME/.bond_deploy" ]; then
    source "$HOME/.bond_deploy"
fi

AD_API_KEY="${AD_API_KEY:-}"
AD_SERVICE_ID="${AD_SERVICE_ID:-}"

if [ -n "$AD_API_KEY" ] && [ -n "$AD_SERVICE_ID" ]; then
    echo "перезапуск службы $AD_SERVICE_ID через API"
    code="$(curl -s -o /tmp/ad_restart.log -w '%{http_code}' -X POST \
        -u "$AD_API_KEY:" \
        "https://api.alwaysdata.com/v1/service/$AD_SERVICE_ID/restart/")"
    if [ "$code" = "200" ] || [ "$code" = "204" ]; then
        echo "служба перезапущена"
        exit 0
    fi
    echo "API ответил $code, пробую остановить процесс — платформа поднимет сама" >&2
    cat /tmp/ad_restart.log >&2
fi

if pkill -f "venv/bin/python -m bond_bot"; then
    echo "процесс остановлен, служба поднимет его автоматически"
else
    echo "процесс не найден — запустите службу в панели (Advanced -> Services)" >&2
fi
