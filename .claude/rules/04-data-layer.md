# Слой данных

SQLite + SQLAlchemy 2.0 (async, `aiosqlite`). В базе живут **только темы и слова**.
Партии в БД не пишутся — см. [03-architecture.md](03-architecture.md).

## Модели

[models.py](../../src/bond_bot/infrastructure/database/models.py)

| Модель | Поля | Связи | Ограничения |
|---|---|---|---|
| `Theme` | `id`, `name` (64), `owner_id` (BigInteger, **nullable**), `is_builtin`, `created_at` | `words` → `Word` | `UNIQUE(owner_id, name)` |
| `Word` | `id`, `theme_id`, `text` (64) | `theme`, `similar` → `SimilarWord` | `UNIQUE(theme_id, text)` |
| `SimilarWord` | `id`, `word_id`, `text` (64) | `word` | `UNIQUE(word_id, text)` |

- `owner_id IS NULL` **только** у встроенных тем (`is_builtin=True`)
- `UNIQUE(owner_id, name)` — у одного пользователя не может быть двух тем с одинаковым
  именем, но у разных пользователей — сколько угодно
- Каскады: `cascade="all, delete-orphan"` + `ondelete="CASCADE"`. Удаление темы уносит
  слова и похожие
- `PRAGMA foreign_keys=ON` включается на каждом коннекте
  ([session.py:22](../../src/bond_bot/infrastructure/database/session.py#L22)) — без этого
  SQLite молча игнорирует внешние ключи

## Ловушка async lazy loading — читать перед любой правкой репозитория

Все relationship объявлены `lazy="selectin"`. Жадная загрузка отрабатывает, **только когда
объект реально загружается запросом**. У объекта, который в этой же сессии создали через
`session.add()`, связи не загружены, и обращение к ним пытается сходить в БД синхронно:

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called
```

Уже дважды ломало проект. Правило: **после `add()`/`flush()` не читать связи у этого же
объекта и не полагаться на `session.get()`** — он вернёт тот же незагруженный экземпляр
из identity map, запрос не выполнится.

```python
# WRONG — только что созданный объект, связи не загружены
theme = Theme(name="X")
session.add(theme)
await session.flush()
existing = {w.text for w in theme.words}          # MissingGreenlet

# RIGHT — явный запрос
existing = {
    w.text for w in await session.scalars(select(Word).where(Word.theme_id == theme.id))
}
```

```python
# WRONG — get() отдаст незагруженный объект из кеша, если его добавили в этой же сессии
theme = await session.get(Theme, theme_id)
for word in theme.words: ...

# RIGHT — select() всегда выполняет запрос, selectin отрабатывает
theme = await session.scalar(select(Theme).where(Theme.id == theme_id))
for word in theme.words: ...
```

Поэтому `ThemeRepository.get()` намеренно использует `select`, а не `session.get`
([repository.py:16](../../src/bond_bot/infrastructure/database/repository.py#L16)) —
**не «оптимизировать» обратно**. По той же причине `copy_to()` и `_sync_theme()` тянут
слова явными запросами.

`get_word()` при этом использует `session.get(Word, ...)` и это безопасно: `Word` в
идентичностной карте появляется только после загрузки запросом, вместе со своими
`similar`. Проверено эмпирически 2026-08-12 в обоих сценариях хендлера `show_word`.

## ThemeRepository — весь SQL проекта

[repository.py](../../src/bond_bot/infrastructure/database/repository.py). Хендлеры
**никогда** не пишут запросы сами.

| Метод | Назначение |
|---|---|
| `get(theme_id)` | Тема по id (через `select`) |
| `builtin()` | Встроенные темы |
| `owned_by(owner_id)` | Темы пользователя |
| `catalog(limit, offset)` / `catalog_size()` | Открытый каталог: всё, что `is_builtin=False` |
| `snapshot(theme_id)` | → `ThemeSnapshot` для движка |
| `create` / `rename` / `delete_theme` / `copy_to` | Темы |
| `add_word` / `delete_word` / `get_word` | Слова |
| `add_similar` / `delete_similar` | Похожие |

Нарушение `UNIQUE` перехватывается и превращается в `DuplicateError` с русским текстом
для пользователя — `IntegrityError` наружу не выходит. При перехвате обязателен
`await self.session.rollback()`, иначе сессия останется сломанной.

`copy_to()` разрешает коллизию имён сам: «Мемы» → «Мемы (2)» → «Мемы (3)»
(`_free_name`, до 99 копий).

## Встроенные темы

JSON в [resources/themes/](../../src/bond_bot/resources/themes/), 12 файлов, 317 слов.

```json
{ "name": "Кухня", "words": [ { "text": "Нож", "similar": ["Вилка", "Ложка"] } ] }
```

`seed_builtin_themes()` вызывается при каждом старте и **идемпотентна с дозаливкой**:
новые слова из JSON добавляются, существующие не трогаются, дубликаты не создаются.
Тема ищется по паре (`name`, `is_builtin=True`).

Добавить тему = положить новый JSON-файл. Код менять не нужно.
[tests/test_theme_files.py](../../tests/test_theme_files.py) проверит: ≥25 слов, нет
дублей, слово не попало в собственный список похожих, у каждого слова есть похожие.

## Миграции

Alembic в зависимостях, но **не инициализирован**: схема создаётся через
`Base.metadata.create_all()` в `init_db()`. При изменении моделей на существующей базе
нужно либо удалить `data/bond_bot.sqlite3`, либо завести Alembic по-настоящему.
