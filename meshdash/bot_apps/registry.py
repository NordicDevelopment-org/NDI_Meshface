from .base import BotApp
from ..games.zork import ZorkGame


def build_builtin_bot_apps() -> list[BotApp]:
    # Register additional copy-pasted bot apps here.
    return [
        ZorkGame(),
    ]


__all__ = ["build_builtin_bot_apps"]
