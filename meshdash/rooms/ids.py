"""Room id normalization.

Room ids are intended to be human-friendly, URL-ish slugs:
  - lowercase
  - a-z, 0-9
  - optional '_' or '-' in the middle

We keep the rules strict to:
  - prevent UI injection weirdness
  - keep packet payloads small
  - make it easy to create stable keys (room:<id>)
"""

from __future__ import annotations

import re
from typing import Optional

_ROOM_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")


def normalize_room_id(value: object) -> Optional[str]:
    """Normalize a candidate room id.

    Returns a normalized slug, or None if invalid.
    """

    raw = str(value or "").strip().lower()
    if not raw:
        return None
    if _ROOM_ID_RE.match(raw) is None:
        return None
    return raw
