# Стиль кода

Замеры по `src/` и `tests/` на 2026-08-12. Проценты — основание для правил.

| Практика | Замер | Вывод |
|---|---|---|
| Докстринги `"""` | **0** вхождений | ЗАПРЕЩЕНО |
| Комментарии `#` | **0** вхождений | ЗАПРЕЩЕНО |
| `print()` | **0** в `src/` | ЗАПРЕЩЕНО |
| Аннотации возврата `-> T` | 147 из 150 функций (98%) | ОБЯЗАТЕЛЬНО |
| Относительные импорты | 0 | ЗАПРЕЩЕНО |
| Абсолютные `from bond_bot...` | 39 | ОБЯЗАТЕЛЬНО |
| Импорты внутри функций | 1 (осознанный, см. ниже) | ИЗБЕГАТЬ |
| `from __future__ import annotations` | 15 файлов | принято по умолчанию |
| `logger` | 3 вызова, только `__main__.py` и `seed.py` | логировать скупо |

## Без докстрингов и комментариев

Прямое требование владельца проекта (2026-08-12): все существующие были удалены,
новые не добавлять. Смысл несут имена и структура.

```python
# WRONG
def max_spies(player_count: int) -> int:
    """Максимум шпионов: хотя бы один мирный должен знать слово."""
    # шпионов может быть большинство
    return player_count - 1

# RIGHT
def max_spies(player_count: int) -> int:
    return player_count - 1
```

Если поведение неочевидно — объяснять пользователю в ответе или в `.claude/rules/`,
а не в коде. Единственное исключение — `# type: ignore`, если он реально нужен.

## Именование

| Что | Как | Пример |
|---|---|---|
| Приватные функции движка | `_` в начале | `_eliminate`, `_spy_word`, `_finish` |
| Функции текстов | по экрану, который рисуют | `pass_phone`, `word_card`, `finished` |
| Функции клавиатур | по экрану | `kb.discussion`, `kb.vote_targets` |
| Значения enum | `SCREAMING_SNAKE` = строка-слаг | `DOUBLE_AGENT = "double_agent"` |
| Хендлеры | глагол или экран | `open_voting`, `show_words`, `receive_word` |

Имена функций в `texts.py` и `keyboards/` **не обязаны совпадать** между собой: в
`texts.py` есть и `word_card` (карточка игрока), и `editor_word_card` (карточка слова в
редакторе). Переименование одной сломает другую — раньше уже был конфликт имён, пойманный
ruff (F811).

## Импорты

```python
# RIGHT
from bond_bot.domain import engine
from bond_bot.presentation.keyboards import game as kb
from bond_bot.presentation.keyboards import themes as kb   # в themes.py

# WRONG
from ..domain import engine
from .keyboards.game import discussion, main_menu, tie
```

Модули клавиатур импортируются целиком под алиасом `kb`, чтобы на месте вызова было
видно `kb.discussion(game)`.

Единственный импорт внутри функции — `get_routers()` в
[handlers/__init__.py](../../src/bond_bot/presentation/handlers/__init__.py): без него
циклический импорт. Не копировать этот приём в другие места.

## Ошибки

- Домен бросает `GameError` с **русским текстом**, готовым к показу пользователю
- Репозиторий бросает `DuplicateError`, тоже с готовым текстом
- Хендлер ловит и отдаёт через `callback.answer(str(error), show_alert=True)`
- Голых `except:` и `except Exception:` в проекте нет — не добавлять

## Инструменты

```bash
poetry run ruff check src/ tests/     # line-length 100, select = E,F,I,UP,B,SIM
poetry run pytest                      # 86 тестов, asyncio_mode = auto
```

Обе команды должны проходить перед тем, как объявлять работу законченной.
Зависимости — **только** через Poetry: `poetry add <pkg>`, не `pip install`.
