# Машина состояний партии

Единственная машина состояний в проекте: `Phase` в
[entities.py:14](../../src/bond_bot/domain/entities.py#L14).
Переходы происходят **только** в [domain/engine.py](../../src/bond_bot/domain/engine.py) —
хендлеры фазу напрямую не присваивают.

```
                      start_game()
                           │
                           ▼
                      ┌─────────┐  reveal_next() × N игроков
                      │ DEALING │──────────────────┐
                      └─────────┘                  │
                                                   ▼
   ┌──────────────── resolve_tie(EXTRA_ROUND) ┌────────────┐
   │                                          │ DISCUSSION │◄──── _eliminate() если игра идёт
   │      ┌─────── resolve_tie(REVOTE) ──┐    └────────────┘
   ▼      ▼                              │       │      │
┌────────────┐  close_voting() ничья  ┌─────┐    │      │ open_spy_guess()
│  VOTING    │───────────────────────►│ TIE │    │      │ (кроме DOUBLE_AGENT)
└────────────┘                        └─────┘    │      ▼
   ▲    │ close_voting() один лидер      │       │  ┌───────────┐
   │    │                                │       │  │ SPY_GUESS │
   └────┘ open_voting()                  │       │  └───────────┘
        │                                │       │      │ resolve_spy_guess()
        ▼                                ▼       ▼      ▼
     _eliminate() ──────────────────► ┌──────────────────┐
     (все шпионы выбыли ИЛИ ≤2 живых) │     FINISHED     │ терминальное
                                      └──────────────────┘
```

## Переходы: функция → откуда → куда

| Функция | Допустимая фаза на входе | Фаза на выходе |
|---|---|---|
| `start_game()` | — | `DEALING` |
| `reveal_next()` | `DEALING` | `DEALING`, на последнем игроке → `DISCUSSION` |
| `open_voting()` | `DISCUSSION`, `TIE` | `VOTING` |
| `cast_vote()` | `VOTING` | `VOTING` |
| `close_voting()` | `VOTING` | `TIE` при ничьей, иначе через `_eliminate()` |
| `resolve_tie(REVOTE)` | `TIE` | `VOTING` |
| `resolve_tie(EXTRA_ROUND)` | `TIE` | `DISCUSSION` |
| `resolve_tie(KICK_ALL)` | `TIE` | через `_eliminate()` |
| `open_spy_guess()` | любая кроме `FINISHED`, **кроме `DOUBLE_AGENT`** | `SPY_GUESS` |
| `resolve_spy_guess()` | `SPY_GUESS` | `FINISHED` |
| `_eliminate()` | — | `DISCUSSION` или `FINISHED` |

Любой вызов в неподходящей фазе бросает `GameError` — это защита от старых callback'ов,
которые пользователь может нажать в истории чата. **Не убирать эти проверки.**

## Ничья

`close_voting()` возвращает список лидеров. Длина > 1 → ничья, партия ждёт решения хоста
([engine.py:close_voting](../../src/bond_bot/domain/engine.py#L145)).

Три варианта (`TieResolution`), все три реализованы и покрыты тестами:

- `REVOTE` — тот же состав голосует заново
- `EXTRA_ROUND` — назад в обсуждение, `round_number += 1`, никого не выгоняем
- `KICK_ALL` — выгнать всех лидеров сразу

## Что происходит при выбывании

`_eliminate()` ([engine.py:189](../../src/bond_bot/domain/engine.py#L189)) — единственное
место, где игрок помечается выбывшим:

1. `game.last_eliminated` = выгнанные (бот покажет, были ли они шпионами)
2. `eliminated = True` каждому
3. `votes.clear()`, `round_number += 1`
4. Проверка конца игры в фиксированном порядке: нет живых шпионов → мирные победили;
   иначе живых ≤ 2 → шпионы победили; иначе `DISCUSSION`

Выбывший исключается из `game.alive`, а значит автоматически из голосования и из клавиатур.
`cast_vote()` отдельно запрещает голоса от/за выбывших.

## Подводный камень: `round_number` растёт и при `EXTRA_ROUND`, и при `_eliminate()`

Это счётчик кругов обсуждения, а не «раундов голосования». Не использовать его для
подсчёта голосований.
