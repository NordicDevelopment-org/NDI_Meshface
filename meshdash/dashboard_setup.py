from typing import Any, Callable, Optional


def open_optional_history_store(
    args: Any,
    *,
    history_store_cls: Any,
    history_db_path: str,
    print_fn: Callable[[str], None] = print,
) -> Optional[Any]:
    if args.no_history:
        return None
    try:
        return history_store_cls(
            db_path=history_db_path,
            max_rows=args.history_max_rows,
            retention_days=args.history_retention_days,
            event_max_rows=args.history_event_max_rows,
            event_retention_days=args.history_event_retention_days,
            rollup_retention_days=args.history_rollup_retention_days,
        )
    except Exception as exc:
        print_fn(f"History disabled: cannot open {history_db_path}: {exc}")
        return None


def seed_tracker_if_empty(
    tracker: Any,
    iface: Any,
    *,
    seed_tracker_fn: Callable[[Any, Any], None],
) -> None:
    if tracker.has_recent_packets():
        return
    seed_tracker_fn(tracker, iface)
