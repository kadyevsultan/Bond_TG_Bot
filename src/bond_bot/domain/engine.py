from __future__ import annotations

import random
from collections import Counter

from bond_bot.domain.entities import (
    Game,
    Outcome,
    Phase,
    Player,
    SpyMode,
    ThemeSnapshot,
    TieResolution,
)

MIN_PLAYERS = 3


class GameError(Exception):
    pass


def max_spies(player_count: int) -> int:
    return player_count - 1


def start_game(
    theme: ThemeSnapshot,
    player_count: int,
    spy_count: int = 1,
    spy_mode: SpyMode = SpyMode.CLASSIC,
    rng: random.Random | None = None,
) -> Game:
    rng = rng or random.Random()

    if player_count < MIN_PLAYERS:
        raise GameError(f"Нужно минимум {MIN_PLAYERS} игрока")
    if not 1 <= spy_count <= max_spies(player_count):
        raise GameError(f"Шпионов должно быть от 1 до {max_spies(player_count)}")
    if not theme.cards:
        raise GameError("В теме нет слов")

    card = rng.choice(theme.cards)
    spy_numbers = set(rng.sample(range(1, player_count + 1), spy_count))

    players: list[Player] = []
    for number in range(1, player_count + 1):
        is_spy = number in spy_numbers
        if not is_spy:
            word = card.text
        elif spy_mode is SpyMode.DOUBLE_AGENT:
            word = _spy_word(card.text, card.similar, theme, rng)
        else:
            word = None
        players.append(Player(number=number, is_spy=is_spy, word=word))

    return Game(
        theme_name=theme.name,
        civilian_word=card.text,
        spy_mode=spy_mode,
        players=players,
        theme_words=theme.words,
    )


def _spy_word(
    civilian_word: str,
    similar: tuple[str, ...],
    theme: ThemeSnapshot,
    rng: random.Random,
) -> str | None:
    if similar:
        return rng.choice(list(similar))
    others = [word for word in theme.words if word != civilian_word]
    return rng.choice(others) if others else None


def reveal_next(game: Game) -> Player:
    if game.phase is not Phase.DEALING:
        raise GameError("Раздача уже завершена")
    player = game.players[game.dealt_count]
    game.dealt_count += 1
    if game.dealt_count == len(game.players):
        game.phase = Phase.DISCUSSION
    return player


def open_voting(game: Game) -> None:
    if game.phase not in (Phase.DISCUSSION, Phase.TIE):
        raise GameError("Сейчас нельзя начать голосование")
    game.votes.clear()
    game.phase = Phase.VOTING


def cast_vote(game: Game, voter: int, target: int) -> None:
    if game.phase is not Phase.VOTING:
        raise GameError("Голосование не идёт")
    if game.player(voter).eliminated or game.player(target).eliminated:
        raise GameError("Выбывшие игроки не участвуют в голосовании")
    if voter == target:
        raise GameError("Нельзя голосовать за себя")
    game.votes[voter] = target


def pending_voters(game: Game) -> list[Player]:
    return [p for p in game.alive if p.number not in game.votes]


def leaders(game: Game) -> list[int]:
    if not game.votes:
        return []
    tally = Counter(game.votes.values())
    top = max(tally.values())
    return sorted(number for number, count in tally.items() if count == top)


def close_voting(game: Game) -> list[int]:
    if game.phase is not Phase.VOTING:
        raise GameError("Голосование не идёт")
    if pending_voters(game):
        raise GameError("Не все игроки проголосовали")

    top = leaders(game)
    if len(top) > 1:
        game.phase = Phase.TIE
        return top

    _eliminate(game, top)
    return top


def resolve_tie(game: Game, resolution: TieResolution) -> list[int]:
    if game.phase is not Phase.TIE:
        raise GameError("Ничьей нет")

    match resolution:
        case TieResolution.REVOTE:
            open_voting(game)
            return []
        case TieResolution.EXTRA_ROUND:
            game.votes.clear()
            game.round_number += 1
            game.phase = Phase.DISCUSSION
            return []
        case TieResolution.KICK_ALL:
            tied = leaders(game)
            _eliminate(game, tied)
            return tied


def _eliminate(game: Game, numbers: list[int]) -> None:
    game.last_eliminated = [game.player(n) for n in numbers]
    for player in game.last_eliminated:
        player.eliminated = True

    game.votes.clear()
    game.round_number += 1

    if not game.alive_spies:
        _finish(game, Outcome.CIVILIANS_BY_VOTE)
    elif len(game.alive) <= 2:
        _finish(game, Outcome.SPIES_BY_SURVIVAL)
    else:
        game.phase = Phase.DISCUSSION


def open_spy_guess(game: Game) -> None:
    if game.is_finished:
        raise GameError("Партия окончена")
    if game.spy_mode is SpyMode.DOUBLE_AGENT:
        raise GameError("В режиме «Двойной агент» шпион не знает, что он шпион")
    game.phase = Phase.SPY_GUESS


def submit_spy_guess(game: Game, word: str) -> bool:
    if game.phase is not Phase.SPY_GUESS:
        raise GameError("Шпион сейчас не называет слово")

    correct = word == game.civilian_word
    _finish(
        game,
        Outcome.SPIES_BY_GUESS if correct else Outcome.CIVILIANS_BY_WRONG_GUESS,
    )
    return correct


def _finish(game: Game, outcome: Outcome) -> None:
    game.outcome = outcome
    game.phase = Phase.FINISHED
