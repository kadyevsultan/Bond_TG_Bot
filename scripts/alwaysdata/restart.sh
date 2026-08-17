#!/bin/bash
set -uo pipefail

if [ -f "$HOME/.bond_deploy" ]; then
    source "$HOME/.bond_deploy"
fi

AD_API_KEY="${AD_API_KEY:-}"
AD_SERVICE_ID="${AD_SERVICE_ID:-}"
AD_ACCOUNT="${AD_ACCOUNT:-$(basename "$HOME")}"
MARKER="${MARKER:-$HOME/.bond_restart_requested}"

if [ -n "$AD_API_KEY" ] && [ -n "$AD_SERVICE_ID" ]; then
    echo "перезапуск службы $AD_SERVICE_ID через API (account=$AD_ACCOUNT)"
    code="$(curl -s -o /tmp/ad_restart.log -w '%{http_code}' -X POST \
        --basic --user "$AD_API_KEY account=$AD_ACCOUNT:" \
        "https://api.alwaysdata.com/v1/service/$AD_SERVICE_ID/restart/")"

    case "$code" in
        200 | 204)
            echo "служба перезапущена"
            exit 0
            ;;
        *)
            echo "ОШИБКА: API ответил $code" >&2
            cat /tmp/ad_restart.log >&2
            exit 1
            ;;
    esac
fi

touch "$MARKER"
echo "API-ключа нет: поставлен маркер $MARKER"
echo "служба перезапустится при следующей проверке Monitoring command (в течение минуты)"
