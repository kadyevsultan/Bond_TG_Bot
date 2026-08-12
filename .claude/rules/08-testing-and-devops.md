# Тесты и окружение

## Тесты: 78 штук, ~1.8 секунды

| Файл | Тестов | Что проверяет |
|---|---|---|
| [test_engine.py](../../tests/test_engine.py) | 24 | Правила игры: раздача, голосование, ничьи, победа, догадка шпиона |
| [test_presentation.py](../../tests/test_presentation.py) | 8 | Тексты и клавиатуры на реальном `Game`, конфликты роутеров |
| [test_repository.py](../../tests/test_repository.py) | 8 | Репозиторий на базе в памяти |
| [test_themes_editor.py](../../tests/test_themes_editor.py) | 12 | Права, копирование тем, пагинация |
| [test_theme_files.py](../../tests/test_theme_files.py) | 26 | Валидация JSON-файлов тем (параметризовано по файлам) |

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
| `ADMIN_ID` | нет | Пустая строка → `None` → админ-удаление недоступно |
| `DB_PATH` | нет | По умолчанию `data/bond_bot.sqlite3`, каталог создаётся сам |

Пустая строка в `ADMIN_ID` превращается в `None` через `BeforeValidator`
([config.py:8](../../src/bond_bot/config.py#L8)) — иначе pydantic падал на разборе `int`.

`Settings()` создаётся на уровне модуля, поэтому **любой** импорт `bond_bot.config`
требует валидного `.env`. В тестах это работает, потому что `.env` лежит в корне.

## Деплой

Не настроен. Нет Dockerfile, нет CI, нет systemd-юнита. Владелец отложил осознанно.
Режим доставки апдейтов — **polling** (`delete_webhook(drop_pending_updates=True)` при
старте), для бесплатного хостинга или запуска с ноутбука это правильный выбор: не нужен
домен и HTTPS.

## Git

Ветка `main`, история короткая: `da434b0 first commit`, `9fe6409 feature done 1 stage`.
Коммитить только по просьбе владельца.
