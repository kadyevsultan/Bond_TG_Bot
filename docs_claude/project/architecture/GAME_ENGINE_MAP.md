# Карта движка игры

> Снято 2026-08-12. `domain/engine.py`, 189 строк, 0 внешних зависимостей кроме stdlib.
> Дистиллят — `.claude/rules/02-state-machines.md`.

## Публичный API

| Функция | Сигнатура | Возвращает |
|---|---|---|
| `max_spies` | `(player_count: int) -> int` | `player_count - 1` |
| `start_game` | `(theme, player_count, spy_count=1, spy_mode=CLASSIC, rng=None) -> Game` | новая партия в `DEALING` |
| `reveal_next` | `(game) -> Player` | следующий игрок, инкремент `dealt_count` |
| `open_voting` | `(game) -> None` | чистит голоса, фаза `VOTING` |
| `cast_vote` | `(game, voter: int, target: int) -> None` | пишет `votes[voter] = target` |
| `pending_voters` | `(game) -> list[Player]` | живые, кто ещё не голосовал |
| `leaders` | `(game) -> list[int]` | номера с максимумом голосов |
| `close_voting` | `(game) -> list[int]` | лидеры; >1 → фаза `TIE` |
| `resolve_tie` | `(game, resolution) -> list[int]` | выбывшие (может быть пусто) |
| `open_spy_guess` | `(game) -> None` | фаза `SPY_GUESS`; **бросает в DOUBLE_AGENT** |
| `submit_spy_guess` | `(game, word: str) -> bool` | угадал ли; партия → `FINISHED` |

Приватные: `_spy_word`, `_eliminate`, `_finish`.

## Проверки, бросающие GameError

| Место | Условие |
|---|---|
| `start_game` | `player_count < 3` |
| `start_game` | `spy_count` вне `1..player_count-1` |
| `start_game` | пустая тема |
| `reveal_next` | фаза не `DEALING` |
| `open_voting` | фаза не `DISCUSSION`/`TIE` |
| `cast_vote` | фаза не `VOTING` |
| `cast_vote` | голосующий или цель выбыли |
| `cast_vote` | голос за себя |
| `close_voting` | фаза не `VOTING` |
| `close_voting` | не все проголосовали |
| `resolve_tie` | фаза не `TIE` |
| `open_spy_guess` | партия окончена |
| `open_spy_guess` | режим `DOUBLE_AGENT` |
| `submit_spy_guess` | фаза не `SPY_GUESS` |

Все 14 — защита от повторного нажатия старых кнопок из истории чата. Тексты русские,
показываются пользователю как есть.

## Раздача ролей (`start_game`)

```
card = rng.choice(theme.cards)
spy_numbers = set(rng.sample(range(1, player_count+1), spy_count))
для каждого номера:
    мирный            → word = card.text
    шпион + DOUBLE    → word = _spy_word(...)   случайное из card.similar,
                                                иначе случайное другое слово темы
    шпион + CLASSIC   → word = None
```

`rng` инжектируется параметром — тесты передают `random.Random(42)` и получают
детерминированную раздачу. Каждый шпион тянет слово независимо.

## Детерминизм и тестируемость

Движок не читает время, не ходит в сеть, не пишет глобальное состояние. Единственный
источник случайности — переданный `rng`. Поэтому 24 теста правил бегут за ~0.02 с.
