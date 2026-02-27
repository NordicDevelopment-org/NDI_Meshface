"""Meshyface (working title).

This is a thin wrapper around the meshdash package to provide a stable
"product" entrypoint while the codebase evolves.

The long-term plan is to gradually migrate CLI/help text from "Meshtastic Dashboard"
into Meshyface, without requiring a high-blast-radius rename of the internal package.
"""

from __future__ import annotations

try:
    from meshdash import __version__ as __version__
except ImportError:
    __version__ = "0.0.0"
