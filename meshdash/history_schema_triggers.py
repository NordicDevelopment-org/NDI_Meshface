TRIGGER_SCHEMA_STATEMENTS = [
    # Keep node_saved_counts in sync with node_metrics_1m.
    #
    # The dashboard polls /api/state frequently; computing per-node totals via
    # "SELECT ... GROUP BY node_id" over node_metrics_1m each time is O(N) in
    # history size and gets slow quickly. These triggers convert that into an
    # O(1) read from node_saved_counts.
    """
    CREATE TRIGGER IF NOT EXISTS trg_node_metrics_saved_counts_insert
    AFTER INSERT ON node_metrics_1m
    BEGIN
      INSERT INTO node_saved_counts(node_id, saved_packets, saved_points, saved_last_seen_unix)
      VALUES(NEW.node_id, COALESCE(NEW.packet_count, 0), 1, COALESCE(NEW.last_seen_unix, 0))
      ON CONFLICT(node_id) DO UPDATE SET
        saved_packets = saved_packets + COALESCE(NEW.packet_count, 0),
        saved_points = saved_points + 1,
        saved_last_seen_unix = MAX(saved_last_seen_unix, COALESCE(NEW.last_seen_unix, 0));
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_node_metrics_saved_counts_update
    AFTER UPDATE ON node_metrics_1m
    BEGIN
      INSERT INTO node_saved_counts(node_id, saved_packets, saved_points, saved_last_seen_unix)
      VALUES(
        NEW.node_id,
        COALESCE(NEW.packet_count, 0) - COALESCE(OLD.packet_count, 0),
        0,
        COALESCE(NEW.last_seen_unix, 0)
      )
      ON CONFLICT(node_id) DO UPDATE SET
        saved_packets = saved_packets + (COALESCE(NEW.packet_count, 0) - COALESCE(OLD.packet_count, 0)),
        saved_last_seen_unix = MAX(saved_last_seen_unix, COALESCE(NEW.last_seen_unix, 0));
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_node_metrics_saved_counts_delete
    AFTER DELETE ON node_metrics_1m
    BEGIN
      UPDATE node_saved_counts
      SET
        saved_packets = saved_packets - COALESCE(OLD.packet_count, 0),
        saved_points = saved_points - 1
      WHERE node_id = OLD.node_id;

      DELETE FROM node_saved_counts
      WHERE node_id = OLD.node_id AND saved_points <= 0;
    END
    """,

    # Track per-hour node presence for fast online-activity charts.
    """
    CREATE TRIGGER IF NOT EXISTS trg_node_metrics_hour_seen_insert
    AFTER INSERT ON node_metrics_1m
    BEGIN
      INSERT OR IGNORE INTO node_hour_seen(hour_bucket, node_id)
      VALUES(
        (NEW.bucket_unix - (NEW.bucket_unix % 3600)),
        NEW.node_id
      );
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS trg_node_metrics_hour_seen_update
    AFTER UPDATE ON node_metrics_1m
    BEGIN
      INSERT OR IGNORE INTO node_hour_seen(hour_bucket, node_id)
      VALUES(
        (NEW.bucket_unix - (NEW.bucket_unix % 3600)),
        NEW.node_id
      );
    END
    """,
]
