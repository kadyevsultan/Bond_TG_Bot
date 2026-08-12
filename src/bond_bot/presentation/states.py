from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Setup(StatesGroup):
    theme = State()
    players = State()
    spies = State()
    mode = State()


class ThemeEditor(StatesGroup):
    name = State()
    word = State()
    similar = State()
