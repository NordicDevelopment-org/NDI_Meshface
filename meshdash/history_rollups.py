from typing import Any, Optional, Tuple

from .helpers import to_float as _to_float


def merge_metric(
    sum_value: Any,
    count_value: Any,
    min_value: Any,
    max_value: Any,
    sample: Optional[float],
) -> Tuple[float, int, Optional[float], Optional[float]]:
    merged_sum = float(sum_value or 0.0)
    merged_count = int(count_value or 0)
    merged_min = _to_float(min_value)
    merged_max = _to_float(max_value)

    if sample is None:
        return merged_sum, merged_count, merged_min, merged_max

    merged_sum += sample
    merged_count += 1
    merged_min = sample if merged_min is None else min(merged_min, sample)
    merged_max = sample if merged_max is None else max(merged_max, sample)
    return merged_sum, merged_count, merged_min, merged_max


def bucket_minute(epoch_seconds: int) -> int:
    return int(epoch_seconds) - (int(epoch_seconds) % 60)


def clean_node_id(node_id: Any) -> Optional[str]:
    value = str(node_id or "").strip()
    if not value or value in ("Unknown", "n/a", "^all"):
        return None
    return value
