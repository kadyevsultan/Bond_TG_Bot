from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bond_bot.core import registry
from bond_bot.presentation import texts
from bond_bot.presentation.callbacks import MenuCB
from bond_bot.presentation.keyboards import game as kb

router = Router(name="menu")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    registry.drop(message.chat.id)
    await message.answer(texts.GREETING, reply_markup=kb.main_menu())


@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(texts.RULES, reply_markup=kb.back_home())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    registry.drop(message.chat.id)
    await message.answer(texts.GAME_CANCELLED, reply_markup=kb.main_menu())


@router.callback_query(MenuCB.filter(F.action == "home"))
async def go_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.GREETING, reply_markup=kb.main_menu())
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "rules"))
async def show_rules(callback: CallbackQuery) -> None:
    await callback.message.edit_text(texts.RULES, reply_markup=kb.back_home())
    await callback.answer()
