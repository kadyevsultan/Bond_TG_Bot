from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bond_bot.config import settings
from bond_bot.infrastructure.database.models import Theme
from bond_bot.infrastructure.database.repository import DuplicateError, ThemeRepository
from bond_bot.infrastructure.database.session import get_session
from bond_bot.presentation import texts
from bond_bot.presentation.callbacks import MenuCB, ThemeCB
from bond_bot.presentation.keyboards import game as game_kb
from bond_bot.presentation.keyboards import themes as kb
from bond_bot.presentation.states import Setup, ThemeEditor

router = Router(name="themes")

MAX_LEN = 64


def can_edit(theme: Theme, user_id: int) -> bool:
    return not theme.is_builtin and theme.owner_id == user_id


def can_delete(theme: Theme, user_id: int) -> bool:
    if theme.is_builtin:
        return False
    return theme.owner_id == user_id or user_id == settings.admin_id


def author_of(theme: Theme, user_id: int) -> str:
    if theme.is_builtin:
        return "встроенная тема"
    return "вы" if theme.owner_id == user_id else "другой игрок"


@router.callback_query(MenuCB.filter(F.action == "themes"))
@router.callback_query(ThemeCB.filter(F.action == "hub"))
async def hub(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.THEMES_HUB, reply_markup=kb.hub())
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "noop"))
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "mine"))
async def my_themes(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    await state.update_data(list_action="mine")
    async with get_session() as session:
        themes = await ThemeRepository(session).owned_by(callback.from_user.id)

    if not themes:
        await callback.message.edit_text(texts.MY_THEMES_EMPTY, reply_markup=kb.hub())
        await callback.answer()
        return

    page = callback_data.page
    chunk = themes[page * kb.PAGE_SIZE : (page + 1) * kb.PAGE_SIZE]
    await callback.message.edit_text(
        texts.my_themes(len(themes)),
        reply_markup=kb.theme_list(chunk, "mine", page, len(themes)),
    )
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "catalog"))
async def catalog(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    await state.update_data(list_action="catalog")
    page = callback_data.page
    async with get_session() as session:
        repo = ThemeRepository(session)
        total = await repo.catalog_size()
        chunk = await repo.catalog(limit=kb.PAGE_SIZE, offset=page * kb.PAGE_SIZE)

    if not total:
        await callback.message.edit_text(texts.CATALOG_EMPTY, reply_markup=kb.hub())
        await callback.answer()
        return

    await callback.message.edit_text(
        texts.catalog(total),
        reply_markup=kb.theme_list(chunk, "catalog", page, total),
    )
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "back_list"))
async def back_to_list(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("list_action") == "catalog":
        await catalog(callback, callback_data, state)
    else:
        await my_themes(callback, callback_data, state)


@router.callback_query(ThemeCB.filter(F.action == "open"))
async def open_theme(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    await state.set_state(None)
    user_id = callback.from_user.id
    async with get_session() as session:
        theme = await ThemeRepository(session).get(callback_data.theme_id)
        if theme is None:
            await callback.answer("Тема не найдена", show_alert=True)
            return
        markup = kb.theme_card(
            theme,
            can_edit=can_edit(theme, user_id),
            can_delete=can_delete(theme, user_id),
            page=callback_data.page,
        )
        body = texts.theme_card(theme.name, theme.word_count, author_of(theme, user_id))

    await callback.message.edit_text(body, reply_markup=markup)
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "words"))
async def show_words(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    page = callback_data.page
    async with get_session() as session:
        theme = await ThemeRepository(session).get(callback_data.theme_id)
        if theme is None:
            await callback.answer("Тема не найдена", show_alert=True)
            return
        words = theme.words
        chunk = words[page * kb.WORDS_PAGE_SIZE : (page + 1) * kb.WORDS_PAGE_SIZE]
        markup = kb.word_list(
            theme,
            chunk,
            page,
            len(words),
            can_edit=can_edit(theme, callback.from_user.id),
        )
        body = texts.word_list(theme.name, len(words))

    await callback.message.edit_text(body, reply_markup=markup)
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "word"))
async def show_word(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(callback_data.theme_id)
        word = await repo.get_word(callback_data.word_id)
        if theme is None or word is None:
            await callback.answer("Слово не найдено", show_alert=True)
            return
        markup = kb.word_card(
            theme,
            word,
            can_edit=can_edit(theme, callback.from_user.id),
            page=callback_data.page,
        )
        body = texts.editor_word_card(word.text, [s.text for s in word.similar])

    await callback.message.edit_text(body, reply_markup=markup)
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "create"))
async def create_theme(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ThemeEditor.name)
    await callback.message.edit_text(texts.ASK_THEME_NAME, reply_markup=kb.cancel_to_hub())
    await callback.answer()


@router.message(ThemeEditor.name)
async def receive_theme_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer(texts.ASK_THEME_NAME, reply_markup=kb.cancel_to_hub())
        return
    if len(name) > MAX_LEN:
        await message.answer(texts.THEME_NAME_TOO_LONG, reply_markup=kb.cancel_to_hub())
        return

    async with get_session() as session:
        repo = ThemeRepository(session)
        try:
            theme = await repo.create(name, owner_id=message.from_user.id)
        except DuplicateError as error:
            await message.answer(str(error), reply_markup=kb.cancel_to_hub())
            return
        body = texts.theme_card(theme.name, 0, "вы")
        markup = kb.theme_card(theme, can_edit=True, can_delete=True, page=0)

    await state.set_state(None)
    await message.answer(body, reply_markup=markup)


@router.callback_query(ThemeCB.filter(F.action == "add_word"))
async def ask_word(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    async with get_session() as session:
        theme = await ThemeRepository(session).get(callback_data.theme_id)
        if theme is None or not can_edit(theme, callback.from_user.id):
            await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
            return
        name = theme.name

    await state.set_state(ThemeEditor.word)
    await state.update_data(theme_id=callback_data.theme_id)
    await callback.message.edit_text(
        texts.ask_word(name),
        reply_markup=kb.cancel_input(callback_data.theme_id),
    )
    await callback.answer()


@router.message(ThemeEditor.word)
async def receive_word(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    theme_id = data["theme_id"]
    lines = _clean_lines(message.text)
    if not lines:
        return

    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(theme_id)
        if theme is None or not can_edit(theme, message.from_user.id):
            await message.answer(texts.NOT_YOUR_THEME, reply_markup=kb.hub())
            return

        added, skipped = [], []
        for line in lines:
            if len(line) > MAX_LEN:
                skipped.append(line[:20] + "…")
                continue
            try:
                await repo.add_word(theme, line)
                added.append(line)
            except DuplicateError:
                skipped.append(line)

        theme = await repo.get(theme_id)
        body = texts.added_words(added, skipped)
        markup = kb.theme_card(theme, can_edit=True, can_delete=True, page=0)
        card = texts.theme_card(theme.name, theme.word_count, "вы")

    await message.answer(f"{body}\n\n{card}", reply_markup=markup)


@router.callback_query(ThemeCB.filter(F.action == "add_similar"))
async def ask_similar(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(callback_data.theme_id)
        word = await repo.get_word(callback_data.word_id)
        if theme is None or word is None or not can_edit(theme, callback.from_user.id):
            await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
            return
        word_text = word.text

    await state.set_state(ThemeEditor.similar)
    await state.update_data(theme_id=callback_data.theme_id, word_id=callback_data.word_id)
    await callback.message.edit_text(
        texts.ask_similar(word_text),
        reply_markup=kb.cancel_input(callback_data.theme_id),
    )
    await callback.answer()


@router.message(ThemeEditor.similar)
async def receive_similar(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lines = _clean_lines(message.text)
    if not lines:
        return

    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(data["theme_id"])
        word = await repo.get_word(data["word_id"])
        if theme is None or word is None or not can_edit(theme, message.from_user.id):
            await message.answer(texts.NOT_YOUR_THEME, reply_markup=kb.hub())
            return

        added, skipped = [], []
        for line in lines:
            if len(line) > MAX_LEN or line == word.text:
                skipped.append(line)
                continue
            try:
                await repo.add_similar(word, line)
                added.append(line)
            except DuplicateError:
                skipped.append(line)

        word = await repo.get_word(data["word_id"])
        body = texts.added_words(added, skipped)
        card = texts.editor_word_card(word.text, [s.text for s in word.similar])
        markup = kb.word_card(theme, word, can_edit=True, page=0)

    await message.answer(f"{body}\n\n{card}", reply_markup=markup)


@router.callback_query(ThemeCB.filter(F.action == "del_similar"))
async def delete_similar(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(callback_data.theme_id)
        if theme is None or not can_edit(theme, callback.from_user.id):
            await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
            return
        await repo.delete_similar(callback_data.word_id)

    await callback.answer("Удалено")
    await show_words(callback, ThemeCB(action="words", theme_id=callback_data.theme_id, page=0))


@router.callback_query(ThemeCB.filter(F.action == "del_word"))
async def delete_word(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(callback_data.theme_id)
        if theme is None or not can_edit(theme, callback.from_user.id):
            await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
            return
        await repo.delete_word(callback_data.word_id)

    await callback.answer("Слово удалено")
    await show_words(
        callback,
        ThemeCB(action="words", theme_id=callback_data.theme_id, page=callback_data.page),
    )


@router.callback_query(ThemeCB.filter(F.action == "confirm_delete"))
async def confirm_delete(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    async with get_session() as session:
        theme = await ThemeRepository(session).get(callback_data.theme_id)
        if theme is None or not can_delete(theme, callback.from_user.id):
            await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
            return
        body = texts.confirm_delete(theme.name)
        markup = kb.confirm_delete(theme)

    await callback.message.edit_text(body, reply_markup=markup)
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "delete"))
async def delete_theme(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(callback_data.theme_id)
        if theme is None or not can_delete(theme, callback.from_user.id):
            await callback.answer(texts.NOT_YOUR_THEME, show_alert=True)
            return
        await repo.delete_theme(theme)

    await callback.message.edit_text(texts.THEME_DELETED, reply_markup=kb.hub())
    await callback.answer()


@router.callback_query(ThemeCB.filter(F.action == "copy"))
async def copy_theme(callback: CallbackQuery, callback_data: ThemeCB) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        theme = await repo.get(callback_data.theme_id)
        if theme is None:
            await callback.answer("Тема не найдена", show_alert=True)
            return
        copy = await repo.copy_to(theme, callback.from_user.id)
        body = texts.theme_card(copy.name, copy.word_count, "вы")
        markup = kb.theme_card(copy, can_edit=True, can_delete=True, page=0)

    await callback.message.edit_text(body, reply_markup=markup)
    await callback.answer("Тема скопирована — теперь её можно править")


@router.callback_query(ThemeCB.filter(F.action == "play"))
async def play_theme(callback: CallbackQuery, callback_data: ThemeCB, state: FSMContext) -> None:
    async with get_session() as session:
        theme = await ThemeRepository(session).get(callback_data.theme_id)
        if theme is None or not theme.word_count:
            await callback.answer("В теме нет слов", show_alert=True)
            return

    await state.set_state(Setup.players)
    await state.update_data(theme_id=callback_data.theme_id)
    await callback.message.edit_text(texts.CHOOSE_PLAYERS, reply_markup=game_kb.player_count())
    await callback.answer()


def _clean_lines(text: str | None) -> list[str]:
    if not text:
        return []
    seen, result = set(), []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result
