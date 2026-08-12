"""Главное меню и команда /start."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="menu")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "🕵️ <b>Шпион</b>\n\n"
        "Бесплатный бот для игры в «Шпиона» — все темы открыты, "
        "свои темы создаются без ограничений.\n\n"
        "Меню появится здесь на следующем шаге разработки."
    )
