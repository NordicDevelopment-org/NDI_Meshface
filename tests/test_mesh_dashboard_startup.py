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
