from __future__ import annotations

import random

from bond_bot.domain import engine
from bond_bot.domain.entities import Phase, SpyMode, ThemeSnapshot, TieResolution, WordCard
from bond_bot.presentation import texts
from bond_bot.presentation.handlers import get_routers
from bond_bot.presentation.keyboards import game as kb

THEME = ThemeSnapshot(
    name="Кухня",
    cards=(
        WordCard("Нож", ("Вилка", "Ложка")),
        WordCard("Чайник", ("Кастрюля",)),
    ),
)


def played_game(mode: SpyMode = SpyMode.CLASSIC):
    game = engine.start_game(THEME, 5, 1, mode, rng=random.Random(7))
    while game.phase is Phase.DEALING:
        engine.reveal_next(game)
    return game


def test_routers_load_without_conflicts():
    from aiogram import Dispatcher

    dispatcher = Dispatcher()
    dispatcher.include_routers(*get_routers())
    assert [r.name for r in get_routers()] == ["menu", "themes", "game"]


def test_every_text_renders_for_both_modes():
    for mode in SpyMode:
        game = engine.start_game(THEME, 5, 2, mode, rng=random.Random(3))
        assert texts.pass_phone(game, game.players[0])
        while game.phase is Phase.DEALING:
            player = engine.reveal_next(game)
            card = texts.word_card(game, player)
            assert "None" not in card
            if player.is_spy and mode is not SpyMode.DOUBLE_AGENT:
                assert game.civilian_word not in card
        assert texts.discussion(game)


def test_elimination_line_names_the_role():
    game = played_game()
    spy = game.spies[0]
    engine.open_voting(game)
    for player in game.alive:
        target = spy.number if player.number != spy.number else game.alive[0].number
        engine.cast_vote(game, player.number, target)
    engine.close_voting(game)

    assert "шпионом" in texts.eliminated_line(game)
    assert texts.finished(game)


def test_keyboards_build_for_each_phase():
    game = played_game()
    assert kb.main_menu().inline_keyboard
    assert kb.theme_choice([(1, "Кухня", 20)]).inline_keyboard
    assert kb.player_count().inline_keyboard
    assert kb.spy_count(5).inline_keyboard
    assert kb.spy_mode().inline_keyboard
    assert kb.reveal(game.players[0]).inline_keyboard
    assert kb.hide(is_last=True).inline_keyboard
    assert kb.discussion(game).inline_keyboard
    assert kb.tie().inline_keyboard
    assert kb.finished().inline_keyboard
    assert kb.back_home().inline_keyboard


def test_vote_keyboard_excludes_voter_and_eliminated():
    game = played_game()
    game.player(2).eliminated = True
    voter = game.player(1)
    labels = {
        button.text
        for row in kb.vote_targets(game, voter).inline_keyboard
        for button in row
    }
    assert voter.label not in labels
    assert "Игрок 2" not in labels
    assert labels == {"Игрок 3", "Игрок 4", "Игрок 5"}


def test_guess_verdict_keyboard_has_yes_and_no():
    actions = {
        button.callback_data
        for row in kb.guess_verdict().inline_keyboard
        for button in row
    }
    assert actions == {"game:guess_yes:0", "game:guess_no:0"}


def test_tie_texts_and_resolutions_are_covered():
    game = engine.start_game(THEME, 4, 1, rng=random.Random(11))
    while game.phase is Phase.DEALING:
        engine.reveal_next(game)
    engine.open_voting(game)
    engine.cast_vote(game, 1, 2)
    engine.cast_vote(game, 3, 2)
    engine.cast_vote(game, 2, 1)
    engine.cast_vote(game, 4, 1)
    leaders = engine.close_voting(game)

    assert "Игрок 1" in texts.tie(leaders)
    assert set(TieResolution) == {
        TieResolution.REVOTE,
        TieResolution.KICK_ALL,
        TieResolution.EXTRA_ROUND,
    }


def test_guess_button_hidden_only_for_double_agent():
    def labels(mode):
        game = played_game(mode)
        return {b.text for row in kb.discussion(game).inline_keyboard for b in row}

    assert any("называет слово" in t for t in labels(SpyMode.CLASSIC))
    assert any("называет слово" in t for t in labels(SpyMode.MUSIC))
    assert not any("называет слово" in t for t in labels(SpyMode.DOUBLE_AGENT))


def test_music_mode_texts_mention_tracks():
    game = played_game(SpyMode.MUSIC)
    spy = game.spies[0]
    civilian = next(p for p in game.players if not p.is_spy)
    assert "трек" in texts.word_card(game, civilian)
    assert "трек" in texts.word_card(game, spy)
    assert "трек" in texts.discussion(game)


def test_user_text_is_escaped_in_html():
    card = texts.theme_card("Мемы <b>крутые", 5, "вы")
    assert "&lt;b&gt;крутые" in card
    assert "<b>крутые" not in card

    word_card = texts.editor_word_card("Тим & Ко", ["a<b"])
    assert "&amp;" in word_card
    assert "a&lt;b" in word_card

    assert "&amp;" in texts.added_words(["Тим & Ко"], ["a<b"])
    assert "&lt;" in texts.confirm_delete("<i>тема")
    assert "&lt;" in texts.ask_word("<i>тема")
    assert "&lt;" in texts.ask_similar("<i>слово")
    assert "&lt;" in texts.word_list("<i>тема", 3)
