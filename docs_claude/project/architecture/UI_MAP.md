# Карта экранов и хендлеров

> Снято 2026-08-12. Дистиллят — `.claude/rules/05-telegram-ui.md`.

## Команды

| Команда | Хендлер | Действие |
|---|---|---|
| `/start` | `menu.cmd_start` | Сброс FSM + партии, приветствие, главное меню |
| `/rules` | `menu.cmd_rules` | Правила игры |
| `/cancel` | `menu.cmd_cancel` | Сброс FSM + партии |

## Сценарий партии (`handlers/game.py`)

| Callback | Хендлер | Экран |
|---|---|---|
| `MenuCB(new_game)` | `new_game` | Выбор темы (встроенные + свои, только со словами) |
| `SetupCB(theme)` | `pick_theme` | Число игроков 3–20 |
| `SetupCB(players)` | `pick_players` | Число шпионов 1..N-1 |
| `SetupCB(spies)` | `pick_spies` | Выбор режима |
| `SetupCB(mode)` | `pick_mode` | Старт партии → «Передайте телефон» |
| `SetupCB(back_theme / back_players / back_spies)` | 3 хендлера | Шаг назад |
| `GameCB(reveal)` | `reveal_word` | Карточка со словом |
| `GameCB(hide)` | `hide_word` | Следующий игрок или обсуждение |
| `GameCB(open_voting)` | `open_voting` | Вопрос «за кого голосует Игрок N» |
| `GameCB(vote)` | `cast_vote` | Следующий голосующий или итог |
| `GameCB(tie_revote / tie_kick_all / tie_extra_round)` | `resolve_tie` | Разрешение ничьей |
| `GameCB(spy_guess)` | `spy_guess_warning` | Предупреждение о необратимости |
| `GameCB(guess_open)` | `spy_guess_open` | Список слов темы |
| `GuessCB(index)` | `spy_guess_submit` | Финал |
| `GameCB(guess_cancel)` | `spy_guess_cancel` | Назад в обсуждение |
| `GameCB(cancel)` | `cancel_game` | Отмена партии |

Служебные функции: `show_theme_choice`, `show_pass_phone`, `show_discussion`,
`ask_next_voter`, `finish_voting`, `show_after_elimination`, `show_result`.

`ask_next_voter` всегда берёт `pending_voters(game)[0]` — порядок опроса совпадает с
порядком игроков.

## Редактор тем (`handlers/themes.py`)

| Callback | Хендлер | Экран / действие |
|---|---|---|
| `MenuCB(themes)` / `ThemeCB(hub)` | `hub` | Хаб: мои темы, каталог, создать |
| `ThemeCB(mine)` | `my_themes` | Список своих тем (пагинация 8) |
| `ThemeCB(catalog)` | `catalog` | Открытый каталог (пагинация 8) |
| `ThemeCB(open)` | `open_theme` | Карточка темы, кнопки по правам |
| `ThemeCB(back_list)` | `back_to_list` | Назад в тот список, откуда пришли (`list_action`) |
| `ThemeCB(words)` | `show_words` | Слова темы (пагинация 10) |
| `ThemeCB(word)` | `show_word` | Слово и его похожие |
| `ThemeCB(create)` | `create_theme` | Ввод названия (FSM `ThemeEditor.name`) |
| `ThemeCB(add_word)` | `ask_word` | Ввод слов (FSM `ThemeEditor.word`) |
| `ThemeCB(add_similar)` | `ask_similar` | Ввод похожих (FSM `ThemeEditor.similar`) |
| `ThemeCB(del_word)` | `delete_word` | Удаление слова |
| `ThemeCB(del_similar)` | `delete_similar` | Удаление похожего |
| `ThemeCB(confirm_delete)` / `ThemeCB(delete)` | 2 хендлера | Удаление темы с подтверждением |
| `ThemeCB(copy)` | `copy_theme` | Копия чужой темы себе |
| `ThemeCB(play)` | `play_theme` | Игра с этой темой напрямую |
| `ThemeCB(noop)` | `noop` | Кнопка-счётчик страниц |

Текстовый ввод (`message`-хендлеры): `receive_theme_name`, `receive_word`,
`receive_similar`. Слова и похожие принимаются **пачкой** — каждое с новой строки,
`_clean_lines()` убирает пустые и дубли внутри одного сообщения, ответ показывает
добавленные и пропущенные.

## Клавиатуры

`keyboards/game.py`: `main_menu`, `theme_choice`, `player_count`, `spy_count`, `spy_mode`,
`reveal`, `hide`, `discussion`, `vote_targets`, `tie`, `spy_guess_confirm`, `guess_words`,
`finished`, `back_home`.

`keyboards/themes.py`: `hub`, `theme_list`, `theme_card`, `confirm_delete`, `word_list`,
`word_card`, `cancel_input`, `cancel_to_hub`, приватный `_pager`.
