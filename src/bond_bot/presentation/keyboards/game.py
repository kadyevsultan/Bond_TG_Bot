from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bond_bot.domain.engine import max_spies
from bond_bot.domain.entities import Game, Player, SpyMode
from bond_bot.presentation.callbacks import GameCB, GuessCB, MenuCB, SetupCB

MIN_PLAYERS = 3
MAX_PLAYERS = 20


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Новая игра", callback_data=MenuCB(action="new_game"))
    builder.button(text="📚 Темы", callback_data=MenuCB(action="themes"))
    builder.button(text="ℹ️ Правила", callback_data=MenuCB(action="rules"))
    builder.adjust(1)
    return builder.as_markup()


def theme_choice(themes: list[tuple[int, str, int]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for theme_id, name, count in themes:
        builder.button(
            text=f"{name} · {count}",
            callback_data=SetupCB(step="theme", value=str(theme_id)),
        )
    builder.button(text="⬅️ Назад", callback_data=MenuCB(action="home"))
    builder.adjust(2)
    return builder.as_markup()


def player_count() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for count in range(MIN_PLAYERS, MAX_PLAYERS + 1):
        builder.button(text=str(count), callback_data=SetupCB(step="players", value=str(count)))
    builder.button(text="⬅️ Назад", callback_data=SetupCB(step="back_theme"))
    builder.adjust(5)
    return builder.as_markup()


def spy_count(players: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for count in range(1, max_spies(players) + 1):
        builder.button(text=str(count), callback_data=SetupCB(step="spies", value=str(count)))
    builder.button(text="⬅️ Назад", callback_data=SetupCB(step="back_players"))
    builder.adjust(5)
    return builder.as_markup()


def spy_mode() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🕵️ Классика",
        callback_data=SetupCB(step="mode", value=SpyMode.CLASSIC.value),
    )
    builder.button(
        text="🎭 Двойной агент",
        callback_data=SetupCB(step="mode", value=SpyMode.DOUBLE_AGENT.value),
    )
    builder.button(text="⬅️ Назад", callback_data=SetupCB(step="back_spies"))
    builder.adjust(1)
    return builder.as_markup()


def reveal(player: Player) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"👀 {player.label}, показать слово", callback_data=GameCB(action="reveal"))
    builder.button(text="🛑 Отменить игру", callback_data=GameCB(action="cancel"))
    builder.adjust(1)
    return builder.as_markup()


def hide(is_last: bool) -> InlineKeyboardMarkup:
    text = "✅ Скрыть и начать игру" if is_last else "➡️ Скрыть и передать дальше"
    builder = InlineKeyboardBuilder()
    builder.button(text=text, callback_data=GameCB(action="hide"))
    return builder.as_markup()


def discussion(game: Game) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🗳 Начать голосование", callback_data=GameCB(action="open_voting"))
    if game.spy_mode is SpyMode.CLASSIC:
        builder.button(text="🎯 Шпион называет слово", callback_data=GameCB(action="spy_guess"))
    builder.button(text="🛑 Завершить игру", callback_data=GameCB(action="cancel"))
    builder.adjust(1)
    return builder.as_markup()


def vote_targets(game: Game, voter: Player) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for player in game.alive:
        if player.number == voter.number:
            continue
        builder.button(
            text=player.label,
            callback_data=GameCB(action="vote", value=player.number),
        )
    builder.adjust(2)
    return builder.as_markup()


def tie() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔁 Переголосовать", callback_data=GameCB(action="tie_revote"))
    builder.button(text="🚪 Выгнать всех", callback_data=GameCB(action="tie_kick_all"))
    builder.button(text="💬 Ещё один раунд", callback_data=GameCB(action="tie_extra_round"))
    builder.adjust(1)
    return builder.as_markup()


def spy_guess_confirm() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎯 Шпион готов назвать слово", callback_data=GameCB(action="guess_open"))
    builder.button(text="⬅️ Отмена", callback_data=GameCB(action="guess_cancel"))
    builder.adjust(1)
    return builder.as_markup()


def guess_words(words: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, word in enumerate(words):
        builder.button(text=word, callback_data=GuessCB(index=index))
    builder.adjust(2)
    return builder.as_markup()


def finished() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Играть ещё", callback_data=MenuCB(action="new_game"))
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(1)
    return builder.as_markup()


def back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data=MenuCB(action="home").pack())]
        ]
    )
