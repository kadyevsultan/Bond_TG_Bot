from aiogram import Router


def get_routers() -> list[Router]:
    from bond_bot.presentation.handlers import game, menu, themes

    return [menu.router, themes.router, game.router]
