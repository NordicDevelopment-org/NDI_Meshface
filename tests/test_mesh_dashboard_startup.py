import argparse

import pytest

import mesh_dashboard as md


def test_run_dashboard_requires_meshtastic(monkeypatch):
    monkeypatch.setattr(md, "meshtastic", None)
    monkeypatch.setattr(md, "pub", object())
    with pytest.raises(RuntimeError, match="meshtastic Python package is required"):
        md.run_dashboard(argparse.Namespace())


def test_run_dashboard_requires_pubsub(monkeypatch):
    monkeypatch.setattr(md, "meshtastic", object())
    monkeypatch.setattr(md, "pub", None)
    with pytest.raises(RuntimeError, match="pypubsub is required"):
        md.run_dashboard(argparse.Namespace())


def test_revision_info_prefers_environment(monkeypatch):
    monkeypatch.setenv("MESH_DASH_VERSION", "v9.1.2")
    monkeypatch.setenv("MESH_DASH_GIT_COMMIT", "abc123def")
    info = md._revision_info()
    assert info["version"] == "9.1.2"
    assert info["commit"] == "abc123def"
    assert info["label"] == "Rev: v9.1.2 (abc123def)"


def test_revision_info_uses_nogit_fallback(monkeypatch):
    monkeypatch.delenv("MESH_DASH_VERSION", raising=False)
    monkeypatch.delenv("MESH_DASH_GIT_COMMIT", raising=False)
    monkeypatch.setattr(md, "_detect_git_commit", lambda: None)
    info = md._revision_info()
    assert info["commit"] == md.UNKNOWN_GIT_COMMIT
