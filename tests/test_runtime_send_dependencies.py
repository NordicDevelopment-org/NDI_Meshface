from meshdash.runtime_send_contracts import SendChatRuntimeDependencies
from meshdash.runtime_send_dependencies import (
    build_send_chat_runtime_dependencies_from_legacy_args,
)


def test_build_send_chat_runtime_dependencies_from_legacy_args_maps_fields():
    captured = {}

    class _Tracker:
        def __init__(self):
            self.record_local_chat = lambda **kwargs: captured.update(kwargs)

    tracker = _Tracker()
    sentinels = {
        "iface": object(),
        "send_lock": object(),
        "send_reaction_packet_fn": object(),
        "chat_max_bytes": 220,
        "normalize_single_emoji_fn": object(),
        "to_int_fn": object(),
        "utc_now_fn": object(),
    }

    deps = build_send_chat_runtime_dependencies_from_legacy_args(
        **sentinels,
        tracker=tracker,
        get_local_node_id_fn=lambda iface: f"!{id(iface)}",
    )

    assert isinstance(deps, SendChatRuntimeDependencies)
    assert deps.iface is sentinels["iface"]
    assert deps.send_lock is sentinels["send_lock"]
    assert deps.send_reaction_packet_fn is sentinels["send_reaction_packet_fn"]
    assert deps.record_local_chat_fn is tracker.record_local_chat
    assert deps.chat_max_bytes == 220
    assert deps.normalize_single_emoji_fn is sentinels["normalize_single_emoji_fn"]
    assert deps.to_int_fn is sentinels["to_int_fn"]
    assert deps.utc_now_fn is sentinels["utc_now_fn"]
    assert deps.local_node_id_fn() == f"!{id(sentinels['iface'])}"
