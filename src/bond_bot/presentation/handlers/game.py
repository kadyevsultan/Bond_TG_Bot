from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bond_bot.core import registry
from bond_bot.domain import engine
from bond_bot.domain.entities import Game, Phase, SpyMode, TieResolution
from bond_bot.infrastructure.database.repository import ThemeRepository
from bond_bot.infrastructure.database.session import get_session
from bond_bot.presentation import texts
from bond_bot.presentation.callbacks import GameCB, MenuCB, SetupCB
from bond_bot.presentation.keyboards import game as kb
from bond_bot.presentation.states import Setup

router = Router(name="game")

TIE_ACTIONS = {
    "tie_revote": TieResolution.REVOTE,
    "tie_kick_all": TieResolution.KICK_ALL,
    "tie_extra_round": TieResolution.EXTRA_ROUND,
}

GUESS_VERDICTS = {
    "guess_yes": True,
    "guess_no": False,
}


async def show_theme_choice(callback: CallbackQuery, state: FSMContext) -> None:
    async with get_session() as session:
        repo = ThemeRepository(session)
        themes = await repo.builtin()
        themes += await repo.owned_by(callback.from_user.id)
        options = [(t.id, t.name, t.word_count) for t in themes if t.word_count]

    if not options:
        await callback.message.edit_text(texts.NO_THEMES, reply_markup=kb.back_home())
        return

    await state.set_state(Setup.theme)
    await callback.message.edit_text(texts.CHOOSE_THEME, reply_markup=kb.theme_choice(options))


@router.callback_query(MenuCB.filter(F.action == "new_game"))
async def new_game(callback: CallbackQuery, state: FSMContext) -> None:
    registry.drop(callback.message.chat.id)
    await state.clear()
    await show_theme_choice(callback, state)
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "back_theme"))
async def back_to_theme(callback: CallbackQuery, state: FSMContext) -> None:
    await show_theme_choice(callback, state)
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "theme"))
async def pick_theme(callback: CallbackQuery, callback_data: SetupCB, state: FSMContext) -> None:
    await state.update_data(theme_id=int(callback_data.value))
    await state.set_state(Setup.players)
    await callback.message.edit_text(texts.CHOOSE_PLAYERS, reply_markup=kb.player_count())
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "back_players"))
async def back_to_players(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Setup.players)
    await callback.message.edit_text(texts.CHOOSE_PLAYERS, reply_markup=kb.player_count())
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "players"))
async def pick_players(callback: CallbackQuery, callback_data: SetupCB, state: FSMContext) -> None:
    players = int(callback_data.value)
    await state.update_data(players=players)
    await state.set_state(Setup.spies)
    await callback.message.edit_text(
        texts.choose_spies(players, engine.max_spies(players)),
        reply_markup=kb.spy_count(players),
    )
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "back_spies"))
async def back_to_spies(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    players = data["players"]
    await state.set_state(Setup.spies)
    await callback.message.edit_text(
        texts.choose_spies(players, engine.max_spies(players)),
        reply_markup=kb.spy_count(players),
    )
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "spies"))
async def pick_spies(callback: CallbackQuery, callback_data: SetupCB, state: FSMContext) -> None:
    await state.update_data(spies=int(callback_data.value))
    data = await state.get_data()

    async with get_session() as session:
        theme = await ThemeRepository(session).get(data["theme_id"])
        theme_name = theme.name if theme else "—"

    await state.set_state(Setup.mode)
    await callback.message.edit_text(
        texts.choose_mode(theme_name, data["players"], data["spies"]),
        reply_markup=kb.spy_mode(),
    )
    await callback.answer()


@router.callback_query(SetupCB.filter(F.step == "mode"))
async def pick_mode(callback: CallbackQuery, callback_data: SetupCB, state: FSMContext) -> None:
    data = await state.get_data()

    async with get_session() as session:
        snapshot = await ThemeRepository(session).snapshot(data["theme_id"])

    if snapshot is None:
        await callback.answer("Тема не найдена", show_alert=True)
        return

    try:
        game = engine.start_game(
            theme=snapshot,
            player_count=data["players"],
            spy_count=data["spies"],
            spy_mode=SpyMode(callback_data.value),
        )
    except engine.GameError as error:
        await callback.answer(str(error), show_alert=True)
        return

    registry.put(callback.message.chat.id, game)
    await state.clear()
    await show_pass_phone(callback, game)
    await callback.answer()


async def show_pass_phone(callback: CallbackQuery, game: Game) -> None:
    player = game.players[game.dealt_count]
    await callback.message.edit_text(
        texts.pass_phone(game, player),
        reply_markup=kb.reveal(player),
    )


@router.callback_query(GameCB.filter(F.action == "reveal"))
async def reveal_word(callback: CallbackQuery) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    is_last = game.dealt_count == len(game.players) - 1
    player = engine.reveal_next(game)
    await callback.message.edit_text(
        texts.word_card(game, player),
        reply_markup=kb.hide(is_last),
    )
    await callback.answer()


@router.callback_query(GameCB.filter(F.action == "hide"))
async def hide_word(callback: CallbackQuery) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    if game.phase is Phase.DEALING:
        await show_pass_phone(callback, game)
    else:
        await show_discussion(callback, game)
    await callback.answer()


async def show_discussion(callback: CallbackQuery, game: Game) -> None:
    await callback.message.edit_text(texts.discussion(game), reply_markup=kb.discussion(game))


@router.callback_query(GameCB.filter(F.action == "open_voting"))
async def open_voting(callback: CallbackQuery) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    engine.open_voting(game)
    await ask_next_voter(callback, game)
    await callback.answer()


async def ask_next_voter(callback: CallbackQuery, game: Game) -> None:
    voter = engine.pending_voters(game)[0]
    await callback.message.edit_text(
        texts.ask_vote(game, voter),
        reply_markup=kb.vote_targets(game, voter),
    )


@router.callback_query(GameCB.filter(F.action == "vote"))
async def cast_vote(callback: CallbackQuery, callback_data: GameCB) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None or game.phase is not Phase.VOTING:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    voter = engine.pending_voters(game)[0]
    try:
        engine.cast_vote(game, voter.number, callback_data.value)
    except engine.GameError as error:
        await callback.answer(str(error), show_alert=True)
        return

    if engine.pending_voters(game):
        await ask_next_voter(callback, game)
    else:
        await finish_voting(callback, game)
    await callback.answer()


async def finish_voting(callback: CallbackQuery, game: Game) -> None:
    leaders = engine.close_voting(game)
    if game.phase is Phase.TIE:
        await callback.message.edit_text(texts.tie(leaders), reply_markup=kb.tie())
    else:
        await show_after_elimination(callback, game)


async def show_after_elimination(callback: CallbackQuery, game: Game) -> None:
    if game.is_finished:
        await show_result(callback, game)
    else:
        await show_discussion(callback, game)


@router.callback_query(GameCB.filter(F.action.in_(TIE_ACTIONS)))
async def resolve_tie(callback: CallbackQuery, callback_data: GameCB) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None or game.phase is not Phase.TIE:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    engine.resolve_tie(game, TIE_ACTIONS[callback_data.action])

    if game.phase is Phase.VOTING:
        await ask_next_voter(callback, game)
    else:
        await show_after_elimination(callback, game)
    await callback.answer()


@router.callback_query(GameCB.filter(F.action == "spy_guess"))
async def spy_guess_warning(callback: CallbackQuery) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    await callback.message.edit_text(
        texts.SPY_GUESS_WARNING,
        reply_markup=kb.spy_guess_confirm(),
    )
    await callback.answer()


@router.callback_query(GameCB.filter(F.action == "guess_cancel"))
async def spy_guess_cancel(callback: CallbackQuery) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    await show_discussion(callback, game)
    await callback.answer()


@router.callback_query(GameCB.filter(F.action == "guess_open"))
async def spy_guess_open(callback: CallbackQuery) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    try:
        engine.open_spy_guess(game)
    except engine.GameError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.message.edit_text(
        texts.SPY_GUESS_VERDICT,
        reply_markup=kb.guess_verdict(),
    )
    await callback.answer()


@router.callback_query(GameCB.filter(F.action.in_(GUESS_VERDICTS)))
async def spy_guess_verdict(callback: CallbackQuery, callback_data: GameCB) -> None:
    game = registry.get(callback.message.chat.id)
    if game is None or game.phase is not Phase.SPY_GUESS:
        await callback.answer(texts.NO_ACTIVE_GAME, show_alert=True)
        return

    engine.resolve_spy_guess(game, GUESS_VERDICTS[callback_data.action])
    await show_result(callback, game)
    await callback.answer()


async def show_result(callback: CallbackQuery, game: Game) -> None:
    registry.drop(callback.message.chat.id)
    await callback.message.edit_text(texts.finished(game), reply_markup=kb.finished())


@router.callback_query(GameCB.filter(F.action == "cancel"))
async def cancel_game(callback: CallbackQuery, state: FSMContext) -> None:
    registry.drop(callback.message.chat.id)
    await state.clear()
    await callback.message.edit_text(texts.GAME_CANCELLED, reply_markup=kb.main_menu())
    await callback.answer()
