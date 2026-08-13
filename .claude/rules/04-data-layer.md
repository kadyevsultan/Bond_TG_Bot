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
- `PRAGMA foreign_keys=ON` включается на **каждом** SQLite-коннекте процесса: слушатель
  висит на классе `Engine` в [models.py](../../src/bond_bot/infrastructure/database/models.py),
  а не на одном экземпляре. Раньше он был привязан к engine из `session.py`, и тестовые
  engine работали без внешних ключей — каскады в тестах молча не срабатывали, а в бою
  срабатывали. Не переносить обратно

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

JSON в [resources/themes/](../../src/bond_bot/resources/themes/), 14 файлов, 372 слова.

```json
{ "name": "Кухня", "words": [ { "text": "Нож", "similar": ["Вилка", "Ложка"] } ] }
```

`seed_builtin_themes()` вызывается при каждом старте и **синхронизирует БД с JSON**:
новое добавляется, пропавшее из файла удаляется, существующее не дублируется. Тема ищется
по паре (`name`, `is_builtin=True`).

Синхронизация обходит темы, которые правил админ. Три поля решают всё:

| Что | Где | Зачем |
|---|---|---|
| `Theme.source_name` | `themes` | Имя из JSON, по нему сид находит тему. Не меняется при переименовании — иначе правка имени плодила бы дубликат |
| `Theme.is_customized` | `themes` | Ставится при любой правке встроенной темы. Сид такую тему пропускает целиком |
| `Theme.is_deleted` | `themes` | Мягкое удаление встроенной темы: слова целы, игроки темы не видят, сид её не восстанавливает |

`is_customized` ставится в одном месте — `ThemeRepository._mark_customized()`, который
вызывают `rename`, `add_word`, `delete_word`, `add_similar`, `delete_similar`. Поэтому
`delete_word` / `delete_similar` / `add_similar` **принимают тему первым аргументом**: без
неё пометить нечего.

Флаг темовой, а не словный: правка одного слова замораживает всю тему. Осознанно —
частичное слияние правок админа с JSON давало бы неочевидные результаты.

Удаление встроенной темы **мягкое**: `delete_theme()` ставит `is_deleted=True` и оставляет
слова на месте. Восстановление — `restore_theme()`, в UI это «🗑 Корзина» в хабе тем
(видна только админу) → карточка темы → «♻️ Восстановить тему». Пользовательские темы
удаляются физически, как раньше.

Всё, что показывает темы игрокам, фильтрует `is_deleted`: `builtin()`, `owned_by()`,
`catalog()`, `catalog_size()`. `get()` **не** фильтрует — иначе нечего было бы
восстанавливать; поэтому хендлеры `open_theme` и `play_theme` проверяют флаг сами.

Восстановленная тема снова синхронизируется с JSON, если её содержимое не правили:
удаление не считается правкой и `is_customized` не ставит.

Для пользовательских тем сид не вызывается никогда, `source_name` у них `NULL`.

Чего сид **не** умеет: заметить переименование. Правка `"name"` темы создаст вторую тему,
правка `"text"` слова — второе слово (старое удалится, так как его больше нет в JSON).
Переименование темы придётся доводить руками.

Добавить тему = положить новый JSON-файл. Код менять не нужно.
[tests/test_theme_files.py](../../tests/test_theme_files.py) проверит: ≥25 слов, нет
дублей, слово не попало в собственный список похожих, у каждого слова есть похожие.

## Миграции

Alembic настроен. Скрипты лежат **внутри пакета** —
[src/bond_bot/migrations/](../../src/bond_bot/migrations/), а не в корне проекта:
`session.py` находит их как `parents[2] / "migrations"` относительно себя, поэтому путь
верен при любой раскладке установки. В образе Docker пакет живёт в `site-packages`, и
привязка к корню проекта (`BASE_DIR`) там бы не сработала — миграции просто не нашлись бы.
`Config` собирается в коде, `alembic.ini` нужен только для CLI.
`init_db()` больше не вызывает `create_all()` — он выполняет `alembic upgrade head`
в отдельном потоке (`asyncio.to_thread`, потому что `env.py` внутри делает `asyncio.run`).

```bash
poetry run alembic revision --autogenerate -m "что изменилось"
poetry run alembic upgrade head
poetry run alembic downgrade -1
```

`env.py` берёт URL из `settings.db_url`, метаданные — из `Base.metadata`,
`render_as_batch=True` обязателен: SQLite не умеет `ALTER COLUMN` без пересоздания таблицы.

### Ловушка: batch-миграция + `foreign_keys=ON` = потеря дочерних строк

**Сработала 2026-08-13 на живой базе: 372 слова и 1116 похожих исчезли.**

`batch_alter_table` пересоздаёт таблицу: создаёт новую, копирует данные, **дропает старую**,
переименовывает. При включённых внешних ключах этот `DROP TABLE themes` каскадно уносит
`words`, а за ними `similar_words`. Схема при этом корректна, миграция «успешна», ошибок в
логе нет — данных просто нет.

Поэтому `env.py` вешает на миграционный engine слушатель, который ставит
`PRAGMA foreign_keys=OFF`. Он регистрируется **после** глобального `ON` из `models.py`,
поэтому выигрывает. **Не убирать и не менять порядок.**

Регресс закреплён тестом `test_migrations_keep_child_rows`: заполняет базу на предыдущей
ревизии, гонит `upgrade head`, проверяет, что дочерние строки целы.

`alembic.ini` в корне указывает `script_location = %(here)s/src/bond_bot/migrations` —
локальный CLI и рантайм смотрят в одно место.

**Мост для баз, созданных до Alembic:** `migrate()` проверяет, есть ли таблица `themes` при
отсутствии записанной ревизии, и в этом случае делает `stamp head` вместо `upgrade`
([session.py](../../src/bond_bot/infrastructure/database/session.py)). Проверять именно
ревизию, а не наличие таблицы `alembic_version`: пустая таблица версий создаётся самим
`alembic revision --autogenerate`, и проверка «таблица есть» ломала старт на живой базе.

`create_all()` остался только в тестовых фикстурах — они поднимают схему из метаданных
напрямую. [tests/test_migrations.py](../../tests/test_migrations.py) сверяет, что миграции
дают ту же схему, что и модели: забыть миграцию после правки модели не получится.

Таблицы больше не создаются при импорте — правка модели без миграции упадёт на тесте,
а не в бою.
