from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bond_bot.infrastructure.database.models import Theme, Word
from bond_bot.presentation.callbacks import MenuCB, ThemeCB

PAGE_SIZE = 8
WORDS_PAGE_SIZE = 10


def hub(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Встроенные темы", callback_data=ThemeCB(action="builtin"))
    builder.button(text="📁 Мои темы", callback_data=ThemeCB(action="mine"))
    builder.button(text="🌍 Каталог", callback_data=ThemeCB(action="catalog"))
    builder.button(text="➕ Создать тему", callback_data=ThemeCB(action="create"))
    if is_admin:
        builder.button(text="🗑 Корзина", callback_data=ThemeCB(action="trash"))
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(1)
    return builder.as_markup()


def _pager(builder: InlineKeyboardBuilder, action: str, page: int, total: int, size: int) -> None:
    pages = max(1, (total + size - 1) // size)
    if pages == 1:
        return
    if page > 0:
        builder.button(text="◀️", callback_data=ThemeCB(action=action, page=page - 1))
    builder.button(text=f"{page + 1}/{pages}", callback_data=ThemeCB(action="noop"))
    if page < pages - 1:
        builder.button(text="▶️", callback_data=ThemeCB(action=action, page=page + 1))


def theme_list(themes: list[Theme], action: str, page: int, total: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for theme in themes:
        builder.button(
            text=f"{theme.name} · {theme.word_count}",
            callback_data=ThemeCB(action="open", theme_id=theme.id, page=page),
        )
    builder.adjust(1)

    pager = InlineKeyboardBuilder()
    _pager(pager, action, page, total, PAGE_SIZE)
    builder.attach(pager)

    tail = InlineKeyboardBuilder()
    tail.button(text="⬅️ Назад", callback_data=ThemeCB(action="hub"))
    builder.attach(tail)
    return builder.as_markup()


def theme_card(theme: Theme, can_edit: bool, can_delete: bool, page: int) -> InlineKeyboardMarkup:
    if theme.is_deleted:
        return deleted_theme_card(theme, can_restore=can_delete)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🎮 Играть с этой темой",
        callback_data=ThemeCB(action="play", theme_id=theme.id),
    )
    if can_edit:
        builder.button(
            text="✏️ Слова",
            callback_data=ThemeCB(action="words", theme_id=theme.id),
        )
        builder.button(
            text="➕ Добавить слово",
            callback_data=ThemeCB(action="add_word", theme_id=theme.id),
        )
    else:
        builder.button(
            text="📥 Скопировать себе",
            callback_data=ThemeCB(action="copy", theme_id=theme.id),
        )
        builder.button(
            text="👀 Посмотреть слова",
            callback_data=ThemeCB(action="words", theme_id=theme.id),
        )
    if can_edit and theme.is_builtin:
        builder.button(
            text="📥 Скопировать себе",
            callback_data=ThemeCB(action="copy", theme_id=theme.id),
        )
    if can_delete:
        builder.button(
            text="🗑 Удалить тему",
            callback_data=ThemeCB(action="confirm_delete", theme_id=theme.id),
        )
    builder.button(text="⬅️ Назад", callback_data=ThemeCB(action="back_list", page=page))
    builder.adjust(1)
    return builder.as_markup()


def deleted_theme_card(theme: Theme, can_restore: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_restore:
        builder.button(
            text="♻️ Восстановить тему",
            callback_data=ThemeCB(action="restore", theme_id=theme.id),
        )
    builder.button(text="⬅️ Назад", callback_data=ThemeCB(action="trash"))
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete(theme: Theme) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗑 Да, удалить",
        callback_data=ThemeCB(action="delete", theme_id=theme.id),
    )
    builder.button(text="⬅️ Отмена", callback_data=ThemeCB(action="open", theme_id=theme.id))
    builder.adjust(1)
    return builder.as_markup()


def word_list(
    theme: Theme,
    words: list[Word],
    page: int,
    total: int,
    can_edit: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for word in words:
        mark = f" · {len(word.similar)}" if word.similar else ""
        builder.button(
            text=f"{word.text}{mark}",
            callback_data=ThemeCB(action="word", theme_id=theme.id, word_id=word.id, page=page),
        )
    builder.adjust(2)

    pager = InlineKeyboardBuilder()
    pages = max(1, (total + WORDS_PAGE_SIZE - 1) // WORDS_PAGE_SIZE)
    if pages > 1:
        if page > 0:
            pager.button(
                text="◀️",
                callback_data=ThemeCB(action="words", theme_id=theme.id, page=page - 1),
            )
        pager.button(text=f"{page + 1}/{pages}", callback_data=ThemeCB(action="noop"))
        if page < pages - 1:
            pager.button(
                text="▶️",
                callback_data=ThemeCB(action="words", theme_id=theme.id, page=page + 1),
            )
    builder.attach(pager)

    tail = InlineKeyboardBuilder()
    if can_edit:
        tail.button(
            text="➕ Добавить слово",
            callback_data=ThemeCB(action="add_word", theme_id=theme.id),
        )
    tail.button(text="⬅️ Назад", callback_data=ThemeCB(action="open", theme_id=theme.id))
    tail.adjust(1)
    builder.attach(tail)
    return builder.as_markup()


def word_card(theme: Theme, word: Word, can_edit: bool, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_edit:
        builder.button(
            text="➕ Добавить похожее слово",
            callback_data=ThemeCB(action="add_similar", theme_id=theme.id, word_id=word.id),
        )
        for similar in word.similar:
            builder.button(
                text=f"🗑 {similar.text}",
                callback_data=ThemeCB(
                    action="del_similar", theme_id=theme.id, word_id=similar.id, page=page
                ),
            )
        builder.button(
            text="🗑 Удалить слово",
            callback_data=ThemeCB(action="del_word", theme_id=theme.id, word_id=word.id, page=page),
        )
    builder.button(
        text="⬅️ Назад",
        callback_data=ThemeCB(action="words", theme_id=theme.id, page=page),
    )
    builder.adjust(1)
    return builder.as_markup()


def cancel_input(theme_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data=ThemeCB(action="open", theme_id=theme_id))
    return builder.as_markup()


def cancel_to_hub() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Отмена", callback_data=ThemeCB(action="hub"))
    return builder.as_markup()
