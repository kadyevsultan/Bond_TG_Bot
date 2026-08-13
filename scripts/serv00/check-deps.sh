#!/usr/local/bin/bash
set -uo pipefail

echo "=== окружение serv00 ==="
uname -a
echo "python3.12: $(command -v python3.12 || echo НЕТ)"
echo "python3.11: $(command -v python3.11 || echo НЕТ)"
echo "cargo:      $(command -v cargo || echo НЕТ)"
echo "rustc:      $(command -v rustc || echo НЕТ)"
echo "mise:       $(command -v mise || echo НЕТ)"
echo "tmux:       $(command -v tmux || echo НЕТ)"
echo "git:        $(command -v git || echo НЕТ)"
echo "sqlite3:    $(command -v sqlite3 || echo НЕТ)"
echo "память:     $(sysctl -n hw.physmem 2>/dev/null || echo '?')"

echo
echo "=== главная проверка: собирается ли pydantic ==="
TMP="$(mktemp -d)"
python3.12 -m venv "$TMP/venv" 2>/dev/null || python3.11 -m venv "$TMP/venv"
source "$TMP/venv/bin/activate"

export MAKEFLAGS="-j1" CPUCOUNT=1 MAX_CONCURRENCY=1
export CARGO_BUILD_JOBS=1
export CFLAGS="-I/usr/local/include" CXXFLAGS="-I/usr/local/include"

python -V
pip install --quiet --upgrade pip wheel
if pip install "pydantic>=2"; then
    python -c "import pydantic, pydantic_core; print('pydantic OK:', pydantic.VERSION)"
    echo "РЕЗУЛЬТАТ: serv00 подходит, можно продолжать"
else
    echo "РЕЗУЛЬТАТ: pydantic не собрался — нужен путь Б (готовые пакеты FreeBSD)"
fi

deactivate
rm -rf "$TMP"
