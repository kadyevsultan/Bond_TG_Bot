"""Реестр роутеров. Порядок включения = порядок проверки апдейтов."""

from aiogram import Router


def get_routers() -> list[Router]:
    from bond_bot.presentation.handlers import menu

    return [menu.router]
