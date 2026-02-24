import time
from typing import Any, Callable, Dict, Optional, Tuple

from .helpers import extract_position_fields as _extract_position_fields


def extract_position(
    node_info: Dict[str, Any],
    *,
    extract_position_fields_fn: Callable[[Any], Optional[Tuple[float, float]]] = _extract_position_fields,
) -> Optional[Tuple[float, float]]:
    return extract_position_fields_fn(node_info.get("position"))


def safe_nodes_items(
    iface: Any,
    *,
    retries: int = 3,
    sleep_seconds: float = 0.01,
) -> list[Tuple[Any, Any]]:
    for _ in range(max(1, int(retries))):
        try:
            return list((iface.nodesByNum or {}).items())
        except RuntimeError:
            time.sleep(sleep_seconds)
    return []
