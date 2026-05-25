import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_dashboard_js_includes_meshtastic_favorite_sync_state() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "const meshtasticFavoriteSyncInFlightNodeIds = new Set();" in js
    assert "const meshtasticFavoritePendingDesiredByNodeId = new Map();" in js
    assert 'const meshtasticFavoriteTagPresetId = "meshtastic-favorite";' in js
    assert "function meshtasticFavoriteNodeIdsWithPending(state = latestState)" in js
    assert "function syncNodeTagsWithMeshtasticFavorites(state = latestState)" in js
    assert "const pendingTimeoutMs = 30000;" in js
    assert "function connectedDeviceRoleForFavoriteSync(state = latestState)" in js
    assert "async function requestMeshtasticFavoriteTagSync(nodeId, targetActive)" in js
    assert "function toggleMeshtasticFavoriteNode(nodeId, forceActive = null)" in js
    assert "CLIENT_BASE should only favorite nodes you control. Continue?" in js
    assert "CLIENT_BASE safeguard" in js
    assert 'const command = targetActive ? "set-favorite" : "remove-favorite";' in js
    assert 'const meshtasticShell = document.getElementById("chat-room-meshtastic-shell");' in js
    assert "meshtasticShell.hidden = false;" in js
    assert "No Meshtastic favorites yet." in js
    assert 'action === "favorite"' in js
    assert 'action === "unfavorite"' in js


def test_dashboard_js_boot_and_poll_wire_meshtastic_favorite_sync() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'runBootStep("loadMeshtasticFavoritePinnedSyncIds", () => loadMeshtasticFavoritePinnedSyncIds());' not in js
    assert "syncNodeTagsWithMeshtasticFavorites(rawState);" in js
