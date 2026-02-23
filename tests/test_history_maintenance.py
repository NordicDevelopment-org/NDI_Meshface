from meshdash.history_maintenance import next_prune_counter, prune_history_tables_now


def test_next_prune_counter_returns_false_until_threshold_then_resets():
    count = 0
    should_prune = False
    for _ in range(49):
        count, should_prune = next_prune_counter(count, prune_every=50)
        assert should_prune is False
    count, should_prune = next_prune_counter(count, prune_every=50)
    assert count == 0
    assert should_prune is True


def test_prune_history_tables_now_passes_expected_arguments():
    captured = {}

    def _prune_stub(conn, **kwargs):
        captured["conn"] = conn
        captured["kwargs"] = kwargs

    conn = object()
    prune_history_tables_now(
        conn,
        retention_seconds=3600,
        event_retention_seconds=7200,
        rollup_retention_seconds=86400,
        max_rows=5000,
        event_max_rows=200000,
        prune_history_tables_fn=_prune_stub,
        now_unix_fn=lambda: 123.9,
    )

    assert captured["conn"] is conn
    assert captured["kwargs"] == {
        "now_unix": 123,
        "retention_seconds": 3600,
        "event_retention_seconds": 7200,
        "rollup_retention_seconds": 86400,
        "max_rows": 5000,
        "event_max_rows": 200000,
    }
