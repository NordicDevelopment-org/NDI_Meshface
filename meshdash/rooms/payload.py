"""Rooms payload scaffolding.

This module will eventually own the on-air encoding/decoding for Meshyface rooms.

For now we only provide type-friendly placeholders so the rest of the codebase
has a clear import target.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .ids import normalize_room_id


@dataclass(frozen=True)
class RoomMessage:
    room_id: str
    text: str
    kind: str = "chat"  # chat | advert | topic (planned)


def try_decode_room_message(payload: bytes) -> Optional[RoomMessage]:
    """Attempt to decode a Rooms message payload.

    This is intentionally conservative and returns None for unknown formats.

    The actual wire format will be implemented during the Rooms milestone.
    """

    # Placeholder: no format supported yet.
    _ = payload
    return None


def encode_room_message(msg: RoomMessage) -> bytes:
    """Encode a Rooms message payload.

    The actual wire format will be implemented during the Rooms milestone.
    """

    room_id = normalize_room_id(msg.room_id)
    if not room_id:
        raise ValueError("Invalid room id")

    # Placeholder: raise so callers don't accidentally ship an undefined format.
    raise NotImplementedError("Rooms payload format not implemented yet")
