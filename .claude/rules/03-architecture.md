# Архитектура

`src`-layout, слоистая структура. Пакет ставится в venv в editable-режиме через Poetry,
поэтому импорты одинаковы локально и на сервере.

## Слои и направление зависимостей

```
presentation/  (aiogram: handlers, keyboards, texts, states, callbacks)
      │ зависит от
      ▼
   domain/     (правила игры — НИ ОДНОГО импорта aiogram или sqlalchemy)
      ▲
      │ конвертирует данные в ThemeSnapshot
infrastructure/database/  (SQLAlchemy: models, repository, session, seed)

core/registry.py — активные партии в памяти, chat_id → Game
```

**Железное правило: `domain/` не импортирует ничего из `presentation/` и
`infrastructure/`.** Благодаря этому 30+ тестов правил бегут за 0.02с без Telegram и БД.
Если правило игры требует данных из БД — данные передаются внутрь как `ThemeSnapshot`,
а не запрашиваются из движка.

## Карта файлов

| Файл | Строк | Ответственность |
|---|---|---|
| [domain/entities.py](../../src/bond_bot/domain/entities.py) | 120 | `Game`, `Player`, `Phase`, `Outcome`, `SpyMode`, `ThemeSnapshot`, `WordCard` |
| [domain/engine.py](../../src/bond_bot/domain/engine.py) | 189 | Все переходы состояния, `GameError` |
| [core/registry.py](../../src/bond_bot/core/registry.py) | 21 | `dict[int, Game]` — партии по `chat_id` |
| [infrastructure/database/models.py](../../src/bond_bot/infrastructure/database/models.py) | 75 | `Theme`, `Word`, `SimilarWord` |
| [infrastructure/database/repository.py](../../src/bond_bot/infrastructure/database/repository.py) | 153 | `ThemeRepository` — весь SQL проекта |
| [infrastructure/database/session.py](../../src/bond_bot/infrastructure/database/session.py) | 36 | engine, `session_factory`, `init_db`, PRAGMA foreign_keys |
| [infrastructure/database/seed.py](../../src/bond_bot/infrastructure/database/seed.py) | 55 | Загрузка встроенных тем из JSON, идемпотентная |
| [presentation/handlers/game.py](../../src/bond_bot/presentation/handlers/game.py) | 315 | Сценарий партии от создания до финала |
| [presentation/handlers/themes.py](../../src/bond_bot/presentation/handlers/themes.py) | 401 | Редактор тем, каталог, права |
| [presentation/handlers/menu.py](../../src/bond_bot/presentation/handlers/menu.py) | 45 | `/start`, `/rules`, `/cancel`, главное меню |
| [presentation/texts.py](../../src/bond_bot/presentation/texts.py) | 224 | **Все** тексты бота |
| [presentation/keyboards/game.py](../../src/bond_bot/presentation/keyboards/game.py) | 144 | Клавиатуры партии |
| [presentation/keyboards/themes.py](../../src/bond_bot/presentation/keyboards/themes.py) | 177 | Клавиатуры редактора, пагинация |
| [presentation/callbacks.py](../../src/bond_bot/presentation/callbacks.py) | 28 | 5 `CallbackData`-фабрик |
| [presentation/states.py](../../src/bond_bot/presentation/states.py) | 16 | `Setup`, `ThemeEditor` |
| [config.py](../../src/bond_bot/config.py) | 37 | pydantic-settings из `.env` |
| [__main__.py](../../src/bond_bot/__main__.py) | 47 | Точка входа, polling |

`presentation/middlewares/` и `presentation/filters/` существуют, но **пусты** — созданы
на вырост. Не выдумывать, что там что-то есть.

## Роутеры

[handlers/__init__.py](../../src/bond_bot/presentation/handlers/__init__.py) — реестр.
**Порядок важен**, апдейт проверяется сверху вниз:

```python
return [menu.router, themes.router, game.router]
```

`themes.router` обрабатывает `MenuCB(action="themes")`, а `game.router` —
`MenuCB(action="new_game")`. Если добавить хендлер на тот же callback в более раннем
роутере — поздний перестанет срабатывать молча.

## Callback-фабрики

| Фабрика | Префикс | Поля | Где используется |
|---|---|---|---|
| `MenuCB` | `menu` | `action` | Главное меню, «В меню» |
| `SetupCB` | `setup` | `step`, `value` | Мастер создания игры |
| `GameCB` | `game` | `action`, `value` | Действия в партии, голосование |
| `GuessCB` | `guess` | `index` | Выбор слова шпионом (индекс в `game.theme_words`) |
| `ThemeCB` | `theme` | `action`, `theme_id`, `word_id`, `page` | Редактор и каталог |

Telegram ограничивает callback_data 64 байтами. Не добавлять в фабрики строковые поля
с пользовательским текстом — только идентификаторы и индексы.

## FSM

`MemoryStorage` — состояние теряется при рестарте, это принято осознанно.

| Группа | Состояния | Данные в `state.update_data` |
|---|---|---|
| `Setup` | `theme`, `players`, `spies`, `mode` | `theme_id`, `players`, `spies` |
| `ThemeEditor` | `name`, `word`, `similar` | `theme_id`, `word_id`, `list_action` |

`list_action` (`"mine"`/`"catalog"`) запоминает, откуда пришли, чтобы кнопка «Назад»
вернула в правильный список.

## Запуск

`__main__.py` при старте: `init_db()` → `seed_builtin_themes()` → `delete_webhook(drop_pending_updates=True)`
→ `start_polling`. Точка входа зарегистрирована как консольный скрипт `bond-bot`
в [pyproject.toml](../../pyproject.toml).
