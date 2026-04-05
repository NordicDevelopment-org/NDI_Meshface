import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js
from meshdash.html_template import render_html


def test_render_html_includes_chat_node_details_notes_tab() -> None:
    html = render_html(
        refresh_ms=1000,
        packet_limit=200,
        show_secrets=False,
        history_enabled=True,
        history_max_rows=200,
        history_retention_days=7,
        node_history_hours=24,
        node_history_max_points=240,
        revision_label="test",
        revision_title="test",
    )

    assert 'id="chat-node-details-tab-notes"' in html
    assert 'data-drawer-tab="notes"' in html
    assert 'id="chat-node-details-panel-notes"' in html
    assert 'id="chat-node-details-notes-host"' in html


def test_dashboard_js_routes_notes_into_the_drawer_panel() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'if (clean === "notes") return "notes";' in js
    assert 'const notesTabBtn = document.getElementById("chat-node-details-tab-notes");' in js
    assert 'const notesPanel = document.getElementById("chat-node-details-panel-notes");' in js
    assert 'const notesHost = document.getElementById("chat-node-details-notes-host");' in js
    assert 'const renderNotesInDrawer = (' in js
    assert 'notesHost.innerHTML = renderNotesInDrawer ? notesSection : "";' in js
