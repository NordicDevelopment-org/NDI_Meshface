import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_css import build_dashboard_css
from meshdash.theme import DARK_THEME_VARS, build_theme_css


def test_dark_theme_exposes_shared_workspace_shell_tokens() -> None:
    theme_css = build_theme_css(indent="")

    assert DARK_THEME_VARS["--workspace-shell-bg"] == "#08120d"
    assert DARK_THEME_VARS["--workspace-shell-bg-alt"] == "#07140d"
    assert DARK_THEME_VARS["--workspace-shell-border"] == "#2d8f5d"
    assert DARK_THEME_VARS["--workspace-shell-border-muted"] == "#236744"
    assert DARK_THEME_VARS["--workspace-shell-border-strong"] == "#3f8f68"
    assert DARK_THEME_VARS["--workspace-shell-active-bg"] == "#173126"
    assert DARK_THEME_VARS["--workspace-shell-active-text"] == "#8ce7b4"
    assert "--workspace-shell-bg: #08120d;" in theme_css
    assert "--workspace-shell-bg-alt: #07140d;" in theme_css
    assert "--workspace-shell-border: #2d8f5d;" in theme_css
    assert "--workspace-shell-divider-bg: linear-gradient(90deg, #08140d, #0b1a11);" in theme_css


def test_workspace_views_reuse_shared_shell_tokens() -> None:
    css = build_dashboard_css(theme_css="")

    assert "--network-pane-head-bg: var(--workspace-shell-bg-alt);" in css
    assert "--network-pane-body-bg: var(--workspace-shell-bg);" in css
    assert "--network-pane-head-border: var(--workspace-shell-border);" in css
    assert "--saved-pane-head-border: var(--workspace-shell-border);" in css
    assert "--history-pane-head-border: var(--workspace-shell-border);" in css
    assert "background: var(--workspace-shell-bg, #08110d);" in css
    assert "background: var(--workspace-shell-bg-alt);" in css
    assert "border-color: var(--workspace-shell-border);" in css
