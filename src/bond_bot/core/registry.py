from __future__ import annotations

from bond_bot.domain.entities import Game

_games: dict[int, Game] = {}


def put(chat_id: int, game: Game) -> None:
    _games[chat_id] = game


def get(chat_id: int) -> Game | None:
    return _games.get(chat_id)


def drop(chat_id: int) -> None:
    _games.pop(chat_id, None)


def active_count() -> int:
    return len(_games)
