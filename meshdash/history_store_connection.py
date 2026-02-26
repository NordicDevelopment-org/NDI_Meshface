"""Compatibility facade for history DB connection/prune helpers.

New code should prefer `meshdash.history.db`.
"""

from .history.db import (
    open_and_initialize_history_connection,
    open_and_initialize_history_connection_with_policy,
    prune_history_connection,
    prune_history_connection_with_policy,
)

__all__ = [
    "open_and_initialize_history_connection",
    "open_and_initialize_history_connection_with_policy",
    "prune_history_connection",
    "prune_history_connection_with_policy",
]
