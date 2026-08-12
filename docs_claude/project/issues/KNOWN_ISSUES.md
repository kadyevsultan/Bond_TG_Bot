# Известные проблемы

> Снято 2026-08-12. Дистиллят — `.claude/rules/07-known-issues.md`.

| # | Severity | Проблема | Файл | Статус |
|---|---|---|---|---|
| 1 | HIGH | Пользовательский текст попадает в HTML без экранирования | `presentation/texts.py`, `keyboards/themes.py` | открыто |
| 2 | MEDIUM | Нет глобального обработчика ошибок (`Dispatcher.errors`) | `__main__.py` | открыто |
| 3 | LOW | `KeyError` при вводе слова после рестарта бота | `handlers/themes.py:receive_word` | открыто |
| 4 | LOW | Проверка «тема без слов» продублирована в двух местах | `handlers/game.py`, `handlers/themes.py` | открыто |
| 5 | LOW | Alembic в зависимостях, но не инициализирован | `pyproject.toml` | открыто |
| 6 | INFO | `KICK_ALL` может выгнать всех живых | `engine._eliminate` | принято |
| 7 | INFO | Партии и FSM теряются при рестарте | `core/registry.py`, `MemoryStorage` | принято владельцем |

## №1 подробно — воспроизведение

```python
>>> from bond_bot.presentation import texts
>>> texts.theme_card('Мемы <b>крутые', 5, 'вы')
'📗 <b>Мемы <b>крутые</b>\n\nСлов: 5\nАвтор: вы'
>>> texts.editor_word_card('Тим & Ко', ['a<b'])
'🔤 <b>Тим & Ко</b>\n\nПохожие слова:\n• a<b'
```

`parse_mode=ParseMode.HTML` глобальный (`__main__.py:29`). Telegram отвечает
`TelegramBadRequest: can't parse entities`. Из-за №2 исключение не перехватывается —
пользователь видит зависшую кнопку.

Достаточно назвать тему «Кошки & собаки», злого умысла не требуется.

## Безопасность — проверено, чисто

| Проверка | Результат |
|---|---|
| `.env` в индексе git | Нет, только `.env.example` |
| `.env` в истории git | Не найден |
| Секреты в трекаемых файлах | Нет |
| Fail-open дефолты (`getenv(..., "default")`) | Нет ни одного |
| Сырой SQL со склейкой строк | Нет; единственный `execute` — литерал `PRAGMA foreign_keys=ON` |
| Инъекции в ORM | Нет, всё через выражения SQLAlchemy |

`BOT_TOKEN` обязателен: без него `Settings()` падает при импорте — fail-secure.
`ADMIN_ID` отсутствует → `None` → админ-права никому, тоже fail-secure.

**Внимание:** боевой токен лежит в `.env` и был передан в переписке. Файл в `.gitignore`
и в историю не попадал, но при публикации репозитория токен стоит перевыпустить у BotFather.
