#!/bin/bash
set -uo pipefail

echo "=== окружение alwaysdata ==="
uname -a
echo "HOME: $HOME"
for v in python3.12 python3.11 python3; do
    echo "$v: $(command -v $v || echo НЕТ) $($v -V 2>/dev/null || true)"
done
echo "git:     $(command -v git || echo НЕТ)"
echo "sqlite3: $(command -v sqlite3 || echo НЕТ)"
echo "tmux:    $(command -v tmux || echo НЕТ)"

echo
echo "=== диск (лимит бесплатного плана — 100 МБ) ==="
du -sh "$HOME" 2>/dev/null
quota -s 2>/dev/null || echo "quota недоступна"

echo
echo "=== память ==="
free -m 2>/dev/null || echo "free недоступна"

echo
echo "=== проверка: ставятся ли зависимости из колёс, без компиляции ==="
TMP="$(mktemp -d)"
python3.12 -m venv "$TMP/venv" 2>/dev/null || python3.11 -m venv "$TMP/venv"
source "$TMP/venv/bin/activate"
python -V
pip install --quiet --no-cache-dir --upgrade pip
if pip install --no-cache-dir "aiogram>=3.15" "pydantic>=2"; then
    python -c "import aiogram, pydantic_core; print('OK, aiogram', aiogram.__version__)"
    echo "РЕЗУЛЬТАТ: колёса ставятся, компиляция не нужна"
else
    echo "РЕЗУЛЬТАТ: не установилось — присылать вывод целиком"
fi
du -sh "$TMP/venv"
deactivate
rm -rf "$TMP"
