import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_chat_unread_collection_tracks_messages_across_mesh_channels() -> None:
    unread_src = Path("meshdash/assets/dashboard.js.chat.events.core.notifications.unread.tmpl").read_text()

    assert "function collectChatMessageEntries(state) {{" in unread_src
    assert "if (!messageMatchesActiveMeshChannel(msg)) continue;" not in unread_src
    assert "const meshChannelIndex = messageMeshChannelIndex(msg);" in unread_src
    assert "const entryVisible = isChatEntryVisibleInCurrentContext(entry);" in unread_src
    assert "freshByMeshChannel[key][meshIdx] = Number(freshByMeshChannel[key][meshIdx] || 0) + 1;" in unread_src


def test_dashboard_js_keeps_mesh_channel_unread_routing_for_off_channel_activity() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "const entryVisible = isChatEntryVisibleInCurrentContext(entry);" in js
    assert "const meshIdx = normalizeMeshChannelIndex(entry.meshChannelIndex);" in js
    assert 'addChatMeshChannelUnread(key, rawIdx, count);' in js
