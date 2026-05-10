from .base import BotApp
from ..games.adventure.engine import AdventureGame
from ..games.zork.engine import ZorkGame


def build_internal_bot_apps() -> list[BotApp]:
    # Keep built-in text adventures internal/core while other bot apps migrate to plugins.
    return [ZorkGame(), AdventureGame()]


__all__ = ["build_internal_bot_apps"]
