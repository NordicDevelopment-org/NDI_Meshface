from dataclasses import dataclass
from typing import Any, Optional

from .revision import RevisionInfo
from .runtime_types import (
    BuildNodeHistoryLoaderFn,
    BuildOnlineActivityLoaderFn,
    BuildSendChatLoaderFn,
    BuildStateFn,
    BuildStateSnapshotLoaderFn,
    GetLocalNodeIdFn,
    NormalizeSingleEmojiFn,
    SendChatMessageFn,
    SendReactionPacketFn,
    ToIntFn,
    UtcNowFn,
)


@dataclass(frozen=True)
class DashboardRuntimeLoaderDependencies:
    iface: Any
    tracker: Any
    send_lock: Any
    started_at: float
    target: str
    show_secrets: bool
    history_db_path: str
    revision_info: RevisionInfo
    history_store: Optional[Any]
    default_node_history_hours: int
    default_node_history_points: int
    send_chat_message_fn: SendChatMessageFn
    send_reaction_packet_fn: SendReactionPacketFn
    get_local_node_id_fn: GetLocalNodeIdFn
    default_chat_max_bytes: int
    normalize_single_emoji_fn: NormalizeSingleEmojiFn
    to_int_fn: ToIntFn
    utc_now_fn: UtcNowFn
    build_state_fn: BuildStateFn
    build_state_snapshot_loader_fn: BuildStateSnapshotLoaderFn
    build_node_history_loader_fn: BuildNodeHistoryLoaderFn
    build_online_activity_loader_fn: BuildOnlineActivityLoaderFn
    build_send_chat_loader_fn: BuildSendChatLoaderFn
