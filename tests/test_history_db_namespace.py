from meshdash import history_schema as history_schema_module
from meshdash import history_store_connection as history_store_connection_module
from meshdash.history import db as history_db
from meshdash.history_store_policy import HistoryStorePolicy


def test_history_db_namespace_reexports_connection_and_schema_entrypoints():
    assert history_db.initialize_history_schema is history_schema_module.initialize_history_schema
    assert (
        history_db.open_and_initialize_history_connection
        is history_store_connection_module.open_and_initialize_history_connection
    )
    assert (
        history_db.open_and_initialize_history_connection_with_policy
        is history_store_connection_module.open_and_initialize_history_connection_with_policy
    )
    assert history_db.prune_history_connection is history_store_connection_module.prune_history_connection
    assert (
        history_db.prune_history_connection_with_policy
        is history_store_connection_module.prune_history_connection_with_policy
    )


def test_history_db_namespace_open_and_prune_round_trip(tmp_path):
    db_path = tmp_path / "history_db_namespace.sqlite3"
    policy = HistoryStorePolicy(
        max_rows=100,
        event_max_rows=1000,
        retention_seconds=0,
        event_retention_seconds=0,
        rollup_retention_seconds=0,
    )
    conn = history_db.open_and_initialize_history_connection_with_policy(
        db_path=str(db_path),
        policy=policy,
    )
    try:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "packets" in table_names
        assert "chat" in table_names
        assert "connections" in table_names

        history_db.prune_history_connection_with_policy(conn, policy=policy)
        assert conn.execute("SELECT 1").fetchone()[0] == 1
    finally:
        conn.close()
