#!/bin/bash
if ! command -v jq >/dev/null 2>&1; then exit 0; fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

[ -z "$FILE_PATH" ] && exit 0
[[ ! "$FILE_PATH" =~ \.py$ ]] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0
grep -qI '' "$FILE_PATH" 2>/dev/null || exit 0

IS_DOMAIN=0
[[ "$FILE_PATH" =~ /bond_bot/domain/ ]] && IS_DOMAIN=1

AWK_RESULT=$(awk -v is_domain="$IS_DOMAIN" '
{
    stripped = $0
    gsub(/^[[:space:]]+/, "", stripped)
    gsub(/[[:space:]]+$/, "", stripped)
}

/"""/ {
    if (ds_n < 5) { ds_s = ds_s (ds_n ? "; " : "") NR": "stripped }
    ds_n++
}

/^[[:space:]]*#/ {
    if (stripped !~ /^#!/ && stripped !~ /^#[[:space:]]*type:/ && stripped !~ /^#[[:space:]]*noqa/) {
        if (cm_n < 5) { cm_s = cm_s (cm_n ? "; " : "") NR": "stripped }
        cm_n++
    }
}

/[^_a-zA-Z]print[[:space:]]*\(/ || /^print[[:space:]]*\(/ {
    if (pr_n < 3) { pr_s = pr_s (pr_n ? "; " : "") NR": "stripped }
    pr_n++
}

/^from \.|^import \./ {
    if (ri_n < 3) { ri_s = ri_s (ri_n ? "; " : "") NR": "stripped }
    ri_n++
}

/session\.get[[:space:]]*\([[:space:]]*Theme/ {
    if (sg_n < 3) { sg_s = sg_s (sg_n ? "; " : "") NR": "stripped }
    sg_n++
}

is_domain && /^(from|import) (aiogram|sqlalchemy)/ {
    if (dl_n < 3) { dl_s = dl_s (dl_n ? "; " : "") NR": "stripped }
    dl_n++
}

END {
    if (ds_n) printf "DOCSTRING|%d|%s\n", ds_n, ds_s
    if (cm_n) printf "COMMENT|%d|%s\n", cm_n, cm_s
    if (pr_n) printf "PRINT|%d|%s\n", pr_n, pr_s
    if (ri_n) printf "REL_IMPORT|%d|%s\n", ri_n, ri_s
    if (sg_n) printf "SESSION_GET|%d|%s\n", sg_n, sg_s
    if (dl_n) printf "DOMAIN_LEAK|%d|%s\n", dl_n, dl_s
}
' "$FILE_PATH" 2>/dev/null)

[ -z "$AWK_RESULT" ] && exit 0

VIOLATIONS=""
while IFS='|' read -r name count sample; do
    [ -z "$name" ] && continue
    case "$name" in
        DOCSTRING)   VIOLATIONS="${VIOLATIONS}ДОКСТРИНГИ запрещены в проекте: убрать. ${sample}\n" ;;
        COMMENT)     VIOLATIONS="${VIOLATIONS}КОММЕНТАРИИ запрещены в проекте: убрать, пояснять в ответе. ${sample}\n" ;;
        PRINT)       VIOLATIONS="${VIOLATIONS}PRINT(): использовать logger или убрать. ${sample}\n" ;;
        REL_IMPORT)  VIOLATIONS="${VIOLATIONS}ОТНОСИТЕЛЬНЫЙ ИМПОРТ: только абсолютные from bond_bot... ${sample}\n" ;;
        SESSION_GET) VIOLATIONS="${VIOLATIONS}session.get(Theme) может вернуть объект из кеша сессии без загруженных words: использовать select(). ${sample}\n" ;;
        DOMAIN_LEAK) VIOLATIONS="${VIOLATIONS}domain/ не должен импортировать aiogram/sqlalchemy. ${sample}\n" ;;
    esac
done <<< "$AWK_RESULT"

if [ -n "$VIOLATIONS" ]; then
    V_ESC=$(printf '%s' "$VIOLATIONS" | jq -Rs .)
    FP_ESC=$(printf '%s' "$FILE_PATH" | jq -Rs .)
    jq -n --argjson msg "$V_ESC" --argjson fp "$FP_ESC" \
        '{decision:"block",reason:("Нарушение стиля в " + $fp),additionalContext:$msg}'
    exit 0
fi
exit 0
