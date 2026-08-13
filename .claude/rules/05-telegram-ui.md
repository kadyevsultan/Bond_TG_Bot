# UI: правила работы с Telegram

## Одно сообщение на весь сценарий

Партия и редактор живут в **одном** сообщении, которое перерисовывается через
`callback.message.edit_text(...)`. 35 из 36 вызовов в хендлерах — именно `edit_text`.

```python
# WRONG — слово останется в истории чата, следующий игрок его пролистает
await callback.message.answer(texts.word_card(game, player))

# RIGHT
await callback.message.edit_text(texts.word_card(game, player), reply_markup=kb.hide(is_last))
```

Исключение: ответы на текстовый ввод в редакторе тем (`message.answer`) — там пользователь
уже прислал сообщение, и редактировать нечего.

## Каждый callback обязан получить `answer()`

Иначе у пользователя крутится «часики» до таймаута.

```python
# RIGHT — успешный путь
await callback.message.edit_text(...)
await callback.answer()

# RIGHT — отказ
await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
return
```

## Тексты только в texts.py

В хендлерах и клавиатурах **нет** строк, показываемых пользователю, — всё в
[texts.py](../../src/bond_bot/presentation/texts.py). Исключение — короткие тосты в
`callback.answer("Удалено")`.

## HTML parse_mode — экранирование обязательно

`parse_mode=ParseMode.HTML` включён глобально
([__main__.py](../../src/bond_bot/__main__.py)). Весь пользовательский текст в
[texts.py](../../src/bond_bot/presentation/texts.py) проходит через `html.escape()` —
названия тем, слова, похожие слова, списки добавленного и пропущенного.

Тексты `DuplicateError` из репозитория тоже экранируются: они уходят в `message.answer()`
и парсятся как HTML.

При добавлении любой новой подстановки пользовательского текста в разметку —
`escape()` обязателен, иначе тема с символом `&` в названии перестанет открываться.

## Ошибки: единая точка

`Dispatcher.errors` подключён через
[presentation/errors.py](../../src/bond_bot/presentation/errors.py):

- «безобидные» ответы Telegram (`message is not modified`, `query is too old`,
  `message to edit not found`) гасятся в `info`-лог
- остальное логируется с трейсбеком, пользователю показывается `UNEXPECTED_ERROR`
  и главное меню — вместо зависшего экрана
- `InaccessibleMessage` (сообщение старше 48 часов) обрабатывается через `bot.send_message`,
  потому что `edit_text` у него нет

Хендлер зарегистрирован на самом `Dispatcher`, а не на роутере: ошибки поднимаются вверх по
цепочке роутеров, и обработчик на соседнем роутере не сработал бы.

## Клавиатуры

`InlineKeyboardBuilder` + `.adjust()`. Кнопки строятся от **состояния**, а не
«все на все случаи»:

- `kb.discussion(game)` скрывает «Шпион называет слово» в режиме `DOUBLE_AGENT`
- `kb.vote_targets(game, voter)` исключает голосующего и выбывших
- `kb.theme_card(theme, can_edit, can_delete, page)` собирается от прав: игрок видит
  «Скопировать себе» и «Посмотреть слова», админ — кнопки правки. На **встроенной** теме
  «Скопировать себе» есть у обоих: админу она нужна, чтобы сделать личный форк, не меняя
  общую тему. На своей теме копии нет — копировать себя незачем

Скрытие кнопки — **не** замена проверке в движке или хендлере: пользователь может нажать
старую кнопку из истории. Проверять всегда в обоих местах.

## Пагинация

`PAGE_SIZE = 8` для тем, `WORDS_PAGE_SIZE = 10` для слов
([keyboards/themes.py](../../src/bond_bot/presentation/keyboards/themes.py)).
Номер страницы ездит в `ThemeCB.page`. Кнопка-счётчик «2/5» ведёт на `action="noop"`,
у которого есть хендлер, отвечающий пустым `answer()`.

Клавиатура Telegram ограничена ~100 кнопками; без пагинации тема на 200 слов упадёт.

## Права в редакторе тем

[handlers/themes.py](../../src/bond_bot/presentation/handlers/themes.py):

```python
def can_edit(theme, user_id):    # встроенная → только админ; своя → автор
def can_delete(theme, user_id):  # встроенная → только админ; своя → автор ИЛИ админ
```

- Админ определяется `settings.is_admin(user_id)` — единственный источник, `ADMIN_IDS`
- Список админов пуст → встроенные темы не правит и не удаляет никто (fail-secure)
- Правка встроенной темы админом необратимо отвязывает её от JSON — см.
  [04-data-layer.md](04-data-layer.md)
- Проверять права **до** любой мутации, даже если кнопка не показывалась
- `kb.hub(is_admin=...)` добавляет «🗑 Корзина». Хендлер `trash` всё равно проверяет права
  сам: кнопки нет, но старый callback из истории есть
- У темы в корзине карточка другая: `kb.theme_card()` при `theme.is_deleted` отдаёт
  `deleted_theme_card()` — только «Восстановить» и «Назад», без «Играть» и «Удалить»
