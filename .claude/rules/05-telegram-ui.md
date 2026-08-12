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

## HTML parse_mode — экранирование не сделано

`parse_mode=ParseMode.HTML` включён глобально
([__main__.py:29](../../src/bond_bot/__main__.py#L29)), а пользовательские названия тем и
слова подставляются в разметку **без экранирования**. Это известная незакрытая проблема,
подробности и воспроизведение — [07-known-issues.md](07-known-issues.md#1).

При любой правке `texts.py`, где в HTML попадает пользовательский текст, пропускать его
через `html.escape()`.

## Клавиатуры

`InlineKeyboardBuilder` + `.adjust()`. Кнопки строятся от **состояния**, а не
«все на все случаи»:

- `kb.discussion(game)` скрывает «Шпион называет слово» в режиме `DOUBLE_AGENT`
- `kb.vote_targets(game, voter)` исключает голосующего и выбывших
- `kb.theme_card(theme, can_edit, can_delete, page)` показывает «Слова»/«Скопировать себе»
  в зависимости от прав

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
def can_edit(theme, user_id):   # автор, и тема не встроенная
def can_delete(theme, user_id): # автор ИЛИ админ, и тема не встроенная
```

- Встроенные темы не редактирует и не удаляет **никто**, включая админа
- `settings.admin_id is None` → `can_delete` для чужих тем всегда `False` (fail-secure)
- Проверять права **до** любой мутации, даже если кнопка не показывалась
