from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    action: str


class SetupCB(CallbackData, prefix="setup"):
    step: str
    value: str = ""


class GameCB(CallbackData, prefix="game"):
    action: str
    value: int = 0


class GuessCB(CallbackData, prefix="guess"):
    index: int


class ThemeCB(CallbackData, prefix="theme"):
    action: str
    theme_id: int = 0
    word_id: int = 0
    page: int = 0
