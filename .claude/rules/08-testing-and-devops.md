# Тесты и окружение

## Тесты: 128 штук, ~2.4 секунды

| Файл | Тестов | Что проверяет |
|---|---|---|
| [test_engine.py](../../tests/test_engine.py) | 28 | Правила игры: раздача, голосование, ничьи, победа, догадка шпиона |
| [test_presentation.py](../../tests/test_presentation.py) | 10 | Тексты и клавиатуры на реальном `Game`, конфликты роутеров |
| [test_repository.py](../../tests/test_repository.py) | 20 | Репозиторий на базе в памяти, пометки правок, мягкое удаление |
| [test_themes_editor.py](../../tests/test_themes_editor.py) | 21 | Права админа и автора, корзина, состав карточки темы, пагинация |
| [test_theme_files.py](../../tests/test_theme_files.py) | 30 | Валидация JSON-файлов тем (параметризовано по файлам) |
| [test_seed.py](../../tests/test_seed.py) | 9 | Синхронизация с JSON, пропуск правок админа, корзина |
| [test_migrations.py](../../tests/test_migrations.py) | 3 | Схема из миграций = схема моделей, сохранность дочерних строк |
| [test_config.py](../../tests/test_config.py) | 9 | Разбор `ADMIN_IDS`, `is_admin` |

`asyncio_mode = "auto"` — async-тесты не требуют маркера.

### Как тестировать что

**Правила игры — только через движок, без моков Telegram:**

```python
game = engine.start_game(THEME, 5, 1, SpyMode.CLASSIC, rng=random.Random(42))
```

`rng` параметризован специально: с фиксированным сидом раздача детерминирована.
**Не заменять на глобальный `random.seed()`.**

**Тексты и клавиатуры — на настоящем `Game`, а не на заглушках.** Это ловит реальные
дефекты: `test_every_text_renders_for_both_modes` проверяет, что загаданное слово не
утекает в карточку шпиона, а `test_vote_keyboard_excludes_voter_and_eliminated` — что в
голосовании нет лишних игроков.

**База — SQLite в памяти через фикстуру `repo`** (`test_repository.py`,
`test_themes_editor.py`). Свой engine на тест, `Base.metadata.create_all`, `dispose` после.
Файловую базу в тестах не трогать.

**Файлы тем — отдельным тестом с параметризацией по `THEMES_DIR.glob("*.json")`.**
Новая тема автоматически попадает под проверку.

### Правило при добавлении фич

Изменение в `domain/engine.py` без теста в `test_engine.py` не принимается: это
единственный слой, где ошибка портит саму игру, и он тестируется мгновенно.

## Окружение

Poetry 2.4.1, Python 3.12.2. `virtualenvs.create = false` в
[poetry.toml](../../poetry.toml) — Poetry ставит зависимости прямо в `venv/` проекта,
второе окружение не плодится.

```bash
./venv/bin/poetry install
./venv/bin/poetry run bond-bot          # или python -m bond_bot
./venv/bin/poetry run pytest
./venv/bin/poetry run ruff check src/ tests/
```

Зависимости добавлять **только** через `poetry add`, не `pip install`.

## Переменные окружения

[.env.example](../../.env.example) → `.env` (в `.gitignore`, в историю git не попадал).

| Переменная | Обязательна | Поведение |
|---|---|---|
| `BOT_TOKEN` | да | Без неё `Settings()` падает при импорте — fail-secure |
| `ADMIN_IDS` | нет | Список ID через запятую. Админы правят встроенные темы и удаляют чужие. Пусто → прав ни у кого |
| `DB_PATH` | нет | По умолчанию `data/bond_bot.sqlite3`, каталог создаётся сам |

`ADMIN_IDS` разбирается `BeforeValidator` ([config.py:8](../../src/bond_bot/config.py#L8)):
пустая строка → пустой список, `111,222` → `[111, 222]`. Без него pydantic падал на разборе.
Единственная переменная для админских прав — `ADMIN_ID` убран 2026-08-13.

`Settings()` создаётся на уровне модуля, поэтому **любой** импорт `bond_bot.config`
требует валидного `.env`. В тестах это работает, потому что `.env` лежит в корне.

## Деплой

Docker, **multi-stage**. [Dockerfile](../../Dockerfile) +
[docker-compose.yml](../../docker-compose.yml).

- `builder`: Poetry ставит зависимости в `/app/.venv` (`POETRY_VIRTUALENVS_IN_PROJECT=true`),
  затем пакет ставится туда же обычным `pip install --no-deps .`
- `runtime`: копируется только готовый `.venv`, `PATH` указывает на него. Poetry, pip-кеш и
  сборочные зависимости в финальный образ не попадают

Измерено 2026-08-13: одностадийный образ 392 МБ, multi-stage 264 МБ (−33%).

```bash
docker compose up -d --build
docker compose logs -f
```

Режим доставки апдейтов — **polling** (`delete_webhook(drop_pending_updates=True)` при
старте): не нужен домен и HTTPS.

Что важно в конфигурации и почему:

- **`volumes: bond-data:/data` — обязательно.** Без volume база живёт в слое контейнера и
  умирает вместе с ним; все пользовательские темы пропадут при первом же `up --build`
- `DB_PATH=/data/bond_bot.sqlite3` задан в образе и в compose. Без него `BASE_DIR` увёл бы
  базу в `/app/data`, то есть внутрь контейнера
- `restart: unless-stopped` — падение процесса больше не означает лежачий бот
- `env_file: .env` — `BOT_TOKEN` в образ не попадает, `.env` в `.dockerignore`
- образ запускается под пользователем `bond` (uid 1000), не под root
- миграции применяются при старте (`init_db()` → `alembic upgrade head`), отдельный шаг в
  деплое не нужен; скрипты лежат внутри пакета, поэтому `alembic.ini` в образ не копируется
- **бот масштабируется только в один экземпляр**: два процесса на одном токене дают
  `TelegramConflictError`, а партии живут в памяти каждого процесса отдельно

Проверено 2026-08-13 на multi-stage образе: чистый volume (миграция + сид, 14 тем /
372 слова), повторный старт на существующем volume (данные целы), запуск `bond-bot` доходит
до валидации токена, `MIGRATIONS_DIR` разрешается в
`/app/.venv/lib/python3.12/site-packages/bond_bot/migrations`.

CI по-прежнему нет — `pytest` и `ruff` запускаются руками. Бэкап базы владелец настраивает
на сервере отдельно.

## Git

Ветка `main`, история короткая: `da434b0 first commit`, `9fe6409 feature done 1 stage`,
`fe875dc on board claude` (Session 001).
Коммитить только по просьбе владельца.
