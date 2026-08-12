#!/bin/bash
INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // "."' 2>/dev/null || echo ".")
TODAY=$(date +"%Y-%m-%d")
TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
SESSION_DIR="$CWD/docs_claude/sessions"

[ -d "$SESSION_DIR" ] || exit 0
mkdir -p "$SESSION_DIR/$TODAY"

BRANCH=$(cd "$CWD" && git branch --show-current 2>/dev/null || echo "unknown")
LAST_COMMIT=$(cd "$CWD" && git log --oneline -1 2>/dev/null || echo "unknown")
CHANGED=$(cd "$CWD" && git status --porcelain 2>/dev/null | head -10)
[ -z "$CHANGED" ] && CHANGED="(рабочее дерево чистое)"

cat >> "$SESSION_DIR/SESSION_LOG.md" <<INNER

---
**$TIMESTAMP** | ветка: $BRANCH | коммит: $LAST_COMMIT
Изменения:
$CHANGED
INNER

exit 0
