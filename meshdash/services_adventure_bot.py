from __future__ import annotations

import time
from collections.abc import Callable

from .games.adventure import AdventureGame
from .services_zork_bot import (
    _LIVE_REPLY_ACK_POLL_SECONDS,
    _LIVE_REPLY_ACK_WAIT_SECONDS,
    _LIVE_REPLY_RETRY_LIMIT,
    _LIVE_REPLY_SEGMENT_DELAY_SECONDS,
    ZorkBotService,
)


class AdventureBotService(ZorkBotService):
    """Colossal Cave Adventure bot using the shared ACK-aware game transport."""

    def __init__(
        self,
        *,
        game: AdventureGame | None = None,
        send_lock: object | None = None,
        now_unix_fn: Callable[[], float] = time.time,
        reply_segment_delay_seconds: float = _LIVE_REPLY_SEGMENT_DELAY_SECONDS,
        reply_ack_wait_seconds: float = _LIVE_REPLY_ACK_WAIT_SECONDS,
        reply_ack_poll_seconds: float = _LIVE_REPLY_ACK_POLL_SECONDS,
        reply_retry_limit: int = _LIVE_REPLY_RETRY_LIMIT,
        reply_async: bool = True,
        sleep_fn: Callable[[float], None] = time.sleep,
        get_delivery_state_fn: Callable[[object], object] | None = None,
    ) -> None:
        super().__init__(
            game=game or AdventureGame(),
            send_lock=send_lock,
            now_unix_fn=now_unix_fn,
            reply_segment_delay_seconds=reply_segment_delay_seconds,
            reply_ack_wait_seconds=reply_ack_wait_seconds,
            reply_ack_poll_seconds=reply_ack_poll_seconds,
            reply_retry_limit=reply_retry_limit,
            reply_async=reply_async,
            sleep_fn=sleep_fn,
            get_delivery_state_fn=get_delivery_state_fn,
            public_start_triggers=("adventure", "adv"),
        )


def build_adventure_bot_service(
    *,
    send_lock: object | None = None,
    now_unix_fn: Callable[[], float] = time.time,
    reply_segment_delay_seconds: float = _LIVE_REPLY_SEGMENT_DELAY_SECONDS,
    reply_ack_wait_seconds: float = _LIVE_REPLY_ACK_WAIT_SECONDS,
    reply_ack_poll_seconds: float = _LIVE_REPLY_ACK_POLL_SECONDS,
    reply_retry_limit: int = _LIVE_REPLY_RETRY_LIMIT,
    reply_async: bool = True,
    sleep_fn: Callable[[float], None] = time.sleep,
    get_delivery_state_fn: Callable[[object], object] | None = None,
) -> AdventureBotService:
    return AdventureBotService(
        send_lock=send_lock,
        now_unix_fn=now_unix_fn,
        reply_segment_delay_seconds=reply_segment_delay_seconds,
        reply_ack_wait_seconds=reply_ack_wait_seconds,
        reply_ack_poll_seconds=reply_ack_poll_seconds,
        reply_retry_limit=reply_retry_limit,
        reply_async=reply_async,
        sleep_fn=sleep_fn,
        get_delivery_state_fn=get_delivery_state_fn,
    )


__all__ = ["AdventureBotService", "build_adventure_bot_service"]
