# Структура проекта

> Снято 2026-08-12, коммит `fe875dc` (Session 001). Дистиллят — `.claude/rules/03-architecture.md`.

## Дерево

```
bond_bot/
├── CLAUDE.md, README.md
├── pyproject.toml, poetry.toml, poetry.lock
├── .env / .env.example / .gitignore
├── venv/                        # содержит Poetry, туда же ставятся зависимости
├── data/bond_bot.sqlite3        # gitignored, создаётся при первом запуске
├── src/bond_bot/
│   ├── __main__.py              # точка входа, polling
│   ├── config.py                # pydantic-settings
│   ├── domain/                  # правила игры, без внешних зависимостей
│   │   ├── entities.py
│   │   └── engine.py
│   ├── core/
│   │   └── registry.py          # dict[chat_id, Game]
│   ├── infrastructure/database/
│   │   ├── models.py, repository.py, session.py, seed.py
│   ├── presentation/
│   │   ├── callbacks.py, states.py, texts.py
│   │   ├── handlers/{__init__,menu,themes,game}.py
│   │   ├── keyboards/{game,themes}.py
│   │   ├── middlewares/         # ПУСТО
│   │   └── filters/             # ПУСТО
│   └── resources/themes/*.json  # 12 файлов встроенных тем
└── tests/                       # 5 файлов, 86 тестов
```

## Размеры (`wc -l`, 2026-08-12)

| Файл | Строк |
|---|---|
| presentation/handlers/themes.py | 401 |
| presentation/handlers/game.py | 315 |
| tests/test_engine.py | 256 |
| presentation/texts.py | 224 |
| domain/engine.py | 189 |
| presentation/keyboards/themes.py | 177 |
| infrastructure/database/repository.py | 153 |
| presentation/keyboards/game.py | 144 |
| tests/test_presentation.py | 121 |
| domain/entities.py | 120 |
| tests/test_themes_editor.py | 111 |
| tests/test_repository.py | 86 |
| infrastructure/database/models.py | 75 |
| infrastructure/database/seed.py | 55 |
| tests/test_theme_files.py | 51 |
| __main__.py | 47 |
| presentation/handlers/menu.py | 45 |
| config.py | 37 |
| infrastructure/database/session.py | 36 |
| presentation/callbacks.py | 28 |
| core/registry.py | 21 |
| presentation/states.py | 16 |
| **Итого с тестами** | **2725** |

## Тип проекта

Монолит, один процесс, один деплой-артефакт. Не монорепозиторий: единственный
`pyproject.toml`, ни `packages/`, ни `apps/`.

Найденные слои при сканировании директорий: `domain/`, `handlers/`, `infrastructure/`,
`presentation/`, `core/`. Стандартные для слоистой архитектуры, нестандартных нет.

## Точки входа

| Способ | Механика |
|---|---|
| `poetry run bond-bot` | `[project.scripts]` → `bond_bot.__main__:run`, скрипт в `venv/bin/bond-bot` |
| `python -m bond_bot` | Выполняет `__main__.py` пакета |

Пакет установлен в editable-режиме: `bond_bot.__file__` указывает на
`src/bond_bot/__init__.py`, правки применяются без переустановки.

## Последовательность старта

```
run() → asyncio.run(main())
  ├─ logging.basicConfig(INFO)
  ├─ await init_db()                    # create_all
  ├─ await seed_builtin_themes(session) # дозаливка 12 тем из JSON
  ├─ Bot(token, parse_mode=HTML)
  ├─ Dispatcher(storage=MemoryStorage())
  ├─ dp.include_routers(menu, themes, game)
  ├─ await bot.delete_webhook(drop_pending_updates=True)
  └─ await dp.start_polling(bot)
```
