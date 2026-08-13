# Карта данных

> Снято 2026-08-12. Дистиллят — `.claude/rules/04-data-layer.md`.

## ORM-модели (`infrastructure/database/models.py`)

### Theme

| Поле | Тип | Null | Заметка |
|---|---|---|---|
| `id` | int PK | нет | |
| `name` | String(64) | нет | |
| `owner_id` | BigInteger, index | **да** | NULL только у встроенных |
| `is_builtin` | bool | нет | default False |
| `created_at` | DateTime(tz) | нет | `server_default=func.now()` |

- `words` → `list[Word]`, `cascade="all, delete-orphan"`, `lazy="selectin"`, `order_by=Word.id`
- `UniqueConstraint("owner_id", "name")` → `uq_theme_owner_name`
- `word_count` — property, `len(self.words)`; требует загруженной связи

### Word

| Поле | Тип | Null |
|---|---|---|
| `id` | int PK | нет |
| `theme_id` | FK themes.id, ondelete CASCADE, index | нет |
| `text` | String(64) | нет |

- `similar` → `list[SimilarWord]`, cascade + selectin
- `UniqueConstraint("theme_id", "text")` → `uq_word_theme_text`

### SimilarWord

| Поле | Тип | Null |
|---|---|---|
| `id` | int PK | нет |
| `word_id` | FK words.id, ondelete CASCADE, index | нет |
| `text` | String(64) | нет |

- `UniqueConstraint("word_id", "text")` → `uq_similar_word_text`

## Доменные структуры (`domain/entities.py`) — в БД НЕ хранятся

| Тип | Поля |
|---|---|
| `WordCard` (frozen) | `text`, `similar: tuple[str, ...]` |
| `ThemeSnapshot` (frozen) | `name`, `cards: tuple[WordCard, ...]`, property `words` |
| `Player` | `number`, `is_spy`, `word: str \| None`, `eliminated`, property `label` |
| `Game` | `theme_name`, `civilian_word`, `spy_mode`, `players`, `theme_words`, `phase`, `dealt_count`, `votes: dict[int,int]`, `round_number`, `outcome`, `last_eliminated` |

`Game` properties: `alive`, `spies`, `alive_spies`, `is_finished`, метод `player(number)`
(нумерация с 1, индекс = `number - 1`).

## Мост БД → домен

`ThemeRepository.snapshot(theme_id)` → `ThemeSnapshot`. Единственный способ, которым данные
попадают в движок. Движок ORM-объекты не видит.

## Встроенные темы (14 файлов, 372 слова, 951 похожее)

| Файл | Тема | Слов |
|---|---|---|
| animals.json | Животные | 27 |
| anime.json | Аниме | 26 |
| brands.json | Бренды | 26 |
| food.json | Еда | 27 |
| games.json | Игры | 26 |
| locations.json | Локации | 27 |
| memes.json | Мемы | 26 |
| movies.json | Фильмы | 27 |
| professions.json | Профессии | 27 |
| sport.json | Спорт | 26 |
| tech.json | Техника | 26 |
| transport.json | Транспорт | 26 |

У каждого слова ровно 3 похожих во всех встроенных темах.

## Что НЕ хранится в БД

Партии, голоса, результаты, статистика, имена игроков. Владелец отменил статистику явно.
