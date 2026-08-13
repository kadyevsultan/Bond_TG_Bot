from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import Dispatcher
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, ErrorEvent, InaccessibleMessage, Message

from bond_bot.presentation import texts
from bond_bot.presentation.keyboards import game as kb

logger = logging.getLogger(__name__)

IGNORED_BAD_REQUESTS = ("message is not modified", "query is too old", "message to edit not found")


def register(dispatcher: Dispatcher) -> None:
    dispatcher.errors.register(handle_error)


async def handle_error(event: ErrorEvent) -> bool:
    exception = event.exception

    if isinstance(exception, TelegramBadRequest) and _is_ignored(exception):
        logger.info("Пропущен безобидный ответ Telegram: %s", exception.message)
        return True

    logger.exception("Необработанная ошибка в хендлере", exc_info=exception)

    callback = event.update.callback_query
    if callback is not None:
        await _notify_callback(callback)
        return True

    message = event.update.message
    if message is not None:
        await _notify_message(message)
        return True

    return True


def _is_ignored(exception: TelegramBadRequest) -> bool:
    text = exception.message.lower()
    return any(fragment in text for fragment in IGNORED_BAD_REQUESTS)


async def _notify_callback(callback: CallbackQuery) -> None:
    message = callback.message
    if isinstance(message, Message):
        try:
            await message.edit_text(texts.UNEXPECTED_ERROR, reply_markup=kb.main_menu())
        except TelegramBadRequest:
            await message.answer(texts.UNEXPECTED_ERROR, reply_markup=kb.main_menu())
    elif isinstance(message, InaccessibleMessage):
        await callback.bot.send_message(
            message.chat.id,
            texts.UNEXPECTED_ERROR,
            reply_markup=kb.main_menu(),
        )
    with suppress(TelegramBadRequest):
        await callback.answer()


async def _notify_message(message: Message) -> None:
    await message.answer(texts.UNEXPECTED_ERROR, reply_markup=kb.main_menu())
