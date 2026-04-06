import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_dashboard_js_registers_console_node_lookup_commands() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'name: "node"' in js
    assert 'usage: "node <id|name>"' in js
    assert 'name: "lookup"' in js
    assert 'usage: "lookup <id|name>"' in js
    assert 'resolveConsoleNodeLookupMatches' in js


def test_dashboard_js_registers_console_nodes_aliases() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'name: "nodes"' in js
    assert 'usage: "nodes [-v|-vv|-vvv|-vvvv] [pattern]' in js
    assert 'name: "--nodes"' in js
    assert 'usage: "--nodes [-v|-vv|-vvv|-vvvv] [pattern]' in js
    assert 'name: "list"' not in js
    assert "runConsoleNodeListCommand" in js


def test_dashboard_js_registers_console_traceroute_commands() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'name: "traceroute"' in js
    assert 'usage: "traceroute <id|name|num>' in js
    assert 'name: "--traceroute"' in js
    assert 'usage: "--traceroute <id|name|num>' in js
    assert "resolveConsoleNodeTarget" in js
    assert "postNetworkToolCommand" in js


def test_dashboard_js_includes_console_tab_autocomplete() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "let consoleAutocompleteState = null;" in js
    assert "function parseConsoleTokenRanges(line)" in js
    assert "function normalizeConsoleAutocompleteCandidate(candidate)" in js
    assert "function handleConsoleTabAutocomplete(inputEl, state = latestState, reverse = false)" in js
    assert "function resolveConsoleAutocompleteGhostSuffix(inputEl, state = latestState)" in js
    assert "function resolveConsoleAutocompleteGhostRemainder(rawToken, candidate)" in js
    assert "resolveConsoleAutocompleteCandidates(context, state)" in js
    assert 'if (ev.key === "Tab" && !ev.ctrlKey && !ev.metaKey && !ev.altKey)' in js
    assert 'class="console-completion-ghost"' in js
