"""Run Meshyface.

Usage:
  python -m meshyface [args]

This delegates to the legacy mesh_dashboard.py entrypoint for now.
"""

from __future__ import annotations

from mesh_dashboard import main


if __name__ == "__main__":
    main()
