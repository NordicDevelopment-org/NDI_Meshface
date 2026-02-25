from dataclasses import dataclass
from typing import Any

from .runtime_types import (
    LocalNodeIdFn,
    NormalizeSingleEmojiFn,
    RecordLocalChatFn,
    SendReactionPacketFn,
    ToIntFn,
    UtcNowFn,
)


@dataclass(frozen=True)
class SendChatRuntimeDependencies:
    iface: Any
    send_lock: Any
    send_reaction_packet_fn: SendReactionPacketFn
    local_node_id_fn: LocalNodeIdFn
    record_local_chat_fn: RecordLocalChatFn
    chat_max_bytes: int
    normalize_single_emoji_fn: NormalizeSingleEmojiFn
    to_int_fn: ToIntFn
    utc_now_fn: UtcNowFn
