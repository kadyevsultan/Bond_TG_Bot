import random

import pytest

from bond_bot.domain.engine import (
    GameError,
    cast_vote,
    close_voting,
    max_spies,
    open_spy_guess,
    open_voting,
    pending_voters,
    resolve_tie,
    reveal_next,
    start_game,
    submit_spy_guess,
)
from bond_bot.domain.entities import (
    Game,
    Outcome,
    Phase,
    SpyMode,
    ThemeSnapshot,
    TieResolution,
    WordCard,
)

THEME = ThemeSnapshot(
    name="Кухня",
    cards=(
        WordCard("Нож", ("Вилка", "Ложка")),
        WordCard("Чайник", ("Кастрюля",)),
    ),
)
THEME_NO_SIMILAR = ThemeSnapshot(
    name="Пустая",
    cards=(WordCard("Нож"), WordCard("Чайник")),
)


def new_game(players: int = 5, spies: int = 1, mode: SpyMode = SpyMode.CLASSIC) -> Game:
    game = start_game(THEME, players, spies, mode, rng=random.Random(42))
    while game.phase is Phase.DEALING:
        reveal_next(game)
    return game


def vote_all(game: Game, target: int) -> None:
    open_voting(game)
    others = [p.number for p in game.alive if p.number != target]
    for player in game.alive:
        cast_vote(game, player.number, others[0] if player.number == target else target)
    close_voting(game)


def test_deal_assigns_exactly_requested_spies():
    game = new_game(players=7, spies=2)
    assert len(game.spies) == 2
    assert len(game.players) == 7


def test_classic_mode_hides_word_from_spy():
    game = new_game(mode=SpyMode.CLASSIC)
    for player in game.players:
        assert player.word is None if player.is_spy else player.word == game.civilian_word


def test_double_agent_gets_similar_word():
    game = new_game(mode=SpyMode.DOUBLE_AGENT)
    spy = game.spies[0]
    card = next(c for c in THEME.cards if c.text == game.civilian_word)
    assert spy.word in card.similar
    assert spy.word != game.civilian_word


def test_double_agent_falls_back_to_other_theme_word():
    game = start_game(THEME_NO_SIMILAR, 4, 1, SpyMode.DOUBLE_AGENT, rng=random.Random(1))
    spy = game.spies[0]
    assert spy.word != game.civilian_word
    assert spy.word in THEME_NO_SIMILAR.words


def test_dealing_ends_after_last_player():
    game = start_game(THEME, 4, rng=random.Random(0))
    for _ in range(4):
        assert game.phase is Phase.DEALING
        reveal_next(game)
    assert game.phase is Phase.DISCUSSION
    with pytest.raises(GameError):
        reveal_next(game)


def test_rejects_too_few_players_and_too_many_spies():
    with pytest.raises(GameError):
        start_game(THEME, 2)
    with pytest.raises(GameError):
        start_game(THEME, 5, spy_count=max_spies(5) + 1)


def test_spies_may_outnumber_civilians():
    game = new_game(players=5, spies=4)
    assert len(game.spies) == 4
    assert len([p for p in game.players if not p.is_spy]) == 1


def test_at_least_one_civilian_is_required():
    assert max_spies(5) == 4
    with pytest.raises(GameError):
        start_game(THEME, 5, spy_count=5)


def test_eliminated_player_leaves_the_game():
    game = new_game(players=6, spies=1)
    victim = next(p for p in game.players if not p.is_spy)
    vote_all(game, victim.number)

    assert victim.eliminated
    assert victim not in game.alive
    assert game.last_eliminated == [victim]
    assert game.phase is Phase.DISCUSSION

    open_voting(game)
    with pytest.raises(GameError):
        cast_vote(game, victim.number, game.alive[0].number)


def test_civilians_win_when_last_spy_is_out():
    game = new_game(players=6, spies=1)
    vote_all(game, game.spies[0].number)
    assert game.phase is Phase.FINISHED
    assert game.outcome is Outcome.CIVILIANS_BY_VOTE
    assert game.outcome.civilians_won


def test_game_continues_while_a_spy_remains():
    game = new_game(players=7, spies=2)
    vote_all(game, game.spies[0].number)
    assert game.phase is Phase.DISCUSSION
    assert len(game.alive_spies) == 1


def test_spies_win_when_only_two_players_remain():
    game = new_game(players=5, spies=1)
    civilians = [p.number for p in game.players if not p.is_spy]
    vote_all(game, civilians[0])
    assert game.phase is Phase.DISCUSSION
    vote_all(game, civilians[1])
    assert game.phase is Phase.DISCUSSION
    vote_all(game, civilians[2])

    assert len(game.alive) == 2
    assert game.phase is Phase.FINISHED
    assert game.outcome is Outcome.SPIES_BY_SURVIVAL


def test_voting_requires_everyone_alive():
    game = new_game(players=5)
    open_voting(game)
    cast_vote(game, 1, 2)
    assert len(pending_voters(game)) == 4
    with pytest.raises(GameError):
        close_voting(game)


def test_cannot_vote_for_self():
    game = new_game()
    open_voting(game)
    with pytest.raises(GameError):
        cast_vote(game, 1, 1)


def test_revote_replaces_earlier_choice():
    game = new_game(players=5)
    open_voting(game)
    cast_vote(game, 1, 2)
    cast_vote(game, 1, 3)
    assert game.votes[1] == 3


def tie_game() -> Game:
    game = new_game(players=4, spies=1)
    open_voting(game)
    cast_vote(game, 1, 2)
    cast_vote(game, 3, 2)
    cast_vote(game, 2, 1)
    cast_vote(game, 4, 1)
    assert close_voting(game) == [1, 2]
    assert game.phase is Phase.TIE
    return game


def test_tie_revote_keeps_everyone():
    game = tie_game()
    assert resolve_tie(game, TieResolution.REVOTE) == []
    assert game.phase is Phase.VOTING
    assert game.votes == {}
    assert len(game.alive) == 4


def test_tie_extra_round_returns_to_discussion():
    game = tie_game()
    assert resolve_tie(game, TieResolution.EXTRA_ROUND) == []
    assert game.phase is Phase.DISCUSSION
    assert len(game.alive) == 4


def test_tie_kick_all_eliminates_every_leader():
    game = tie_game()
    assert resolve_tie(game, TieResolution.KICK_ALL) == [1, 2]
    assert game.player(1).eliminated
    assert game.player(2).eliminated
    assert game.phase is Phase.FINISHED


def test_resolve_tie_without_tie_fails():
    game = new_game()
    with pytest.raises(GameError):
        resolve_tie(game, TieResolution.REVOTE)


def test_correct_guess_wins_for_spies():
    game = new_game()
    open_spy_guess(game)
    assert submit_spy_guess(game, game.civilian_word) is True
    assert game.outcome is Outcome.SPIES_BY_GUESS
    assert not game.outcome.civilians_won


def test_wrong_guess_loses_immediately():
    game = new_game()
    wrong = next(w for w in game.theme_words if w != game.civilian_word)
    open_spy_guess(game)
    assert submit_spy_guess(game, wrong) is False
    assert game.outcome is Outcome.CIVILIANS_BY_WRONG_GUESS


def test_guess_is_final_and_cannot_be_repeated():
    game = new_game()
    open_spy_guess(game)
    submit_spy_guess(game, game.civilian_word)
    with pytest.raises(GameError):
        submit_spy_guess(game, game.civilian_word)
    with pytest.raises(GameError):
        open_spy_guess(game)


def test_double_agent_mode_has_no_spy_guess():
    game = new_game(mode=SpyMode.DOUBLE_AGENT)
    with pytest.raises(GameError):
        open_spy_guess(game)


def test_classic_mode_keeps_spy_guess():
    game = new_game(mode=SpyMode.CLASSIC)
    open_spy_guess(game)
    assert game.phase is Phase.SPY_GUESS
