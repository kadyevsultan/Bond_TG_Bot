FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock README.md ./
COPY src ./src

RUN poetry install --only main --no-root \
    && poetry run pip install --no-cache-dir --no-deps . \
    && find /app/.venv -name "__pycache__" -type d -prune -exec rm -rf {} +


FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DB_PATH=/data/bond_bot.sqlite3

WORKDIR /app

RUN useradd --create-home --uid 1000 bond \
    && mkdir -p /data \
    && chown bond:bond /data

COPY --from=builder --chown=bond:bond /app/.venv /app/.venv

USER bond

CMD ["bond-bot"]
