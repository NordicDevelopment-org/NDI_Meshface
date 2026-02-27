import os
import shutil
import time
from typing import Optional


_DISK_CACHE: dict[str, object] = {
    "probe": None,
    "ts": 0.0,
    "payload": None,
}


def disk_space_info(path: Optional[str]) -> dict[str, object]:
    probe = os.path.abspath(os.path.expanduser(path or "."))
    if os.path.isfile(probe):
        probe = os.path.dirname(probe) or "."
    # Disk usage changes slowly; cache for a short window to reduce syscalls
    # during UI polling bursts.
    try:
        now = time.time()
        if (
            _DISK_CACHE.get("payload") is not None
            and _DISK_CACHE.get("probe") == probe
            and (now - float(_DISK_CACHE.get("ts") or 0.0)) < 30.0
        ):
            cached = _DISK_CACHE.get("payload")
            if isinstance(cached, dict):
                return dict(cached)
    except Exception:
        pass
    try:
        usage = shutil.disk_usage(probe)
        total = int(usage.total)
        free = int(usage.free)
        used = int(usage.used)
        free_pct = round((free / total) * 100.0, 1) if total > 0 else None
        used_pct = round((used / total) * 100.0, 1) if total > 0 else None
        payload = {
            "path": probe,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "free_pct": free_pct,
            "used_pct": used_pct,
        }
    except Exception as exc:
        payload = {"path": probe, "error": str(exc)}
        try:
            _DISK_CACHE["probe"] = probe
            _DISK_CACHE["ts"] = time.time()
            _DISK_CACHE["payload"] = payload
        except Exception:
            pass
        return payload

    try:
        _DISK_CACHE["probe"] = probe
        _DISK_CACHE["ts"] = time.time()
        _DISK_CACHE["payload"] = payload
    except Exception:
        pass
    return payload
