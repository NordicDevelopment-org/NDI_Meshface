from meshdash.history_capabilities import (
    decode_node_capabilities_rows,
    decode_node_saved_counts_rows,
)


def test_decode_node_saved_counts_rows_filters_empty_ids():
    rows = [
        ("!a", 10, 2, 100),
        ("", 5, 1, 50),
    ]
    out = decode_node_saved_counts_rows(rows)
    assert list(out.keys()) == ["!a"]
    assert out["!a"]["saved_packets"] == 10
    assert out["!a"]["saved_points"] == 2
    assert out["!a"]["saved_last_seen"] is not None


def test_decode_node_capabilities_rows_maps_fields():
    rows = [
        ("!a", 100, 1, 95, 2, 87, 90),
        ("", 50, 0, None, None, None, None),
    ]
    out = decode_node_capabilities_rows(rows)
    assert list(out.keys()) == ["!a"]
    node = out["!a"]
    assert node["last_seen_unix"] == 100
    assert node["has_position"] is True
    assert node["last_position_unix"] == 95
    assert node["last_hops"] == 2
    assert node["battery_level"] == 87
    assert node["battery_updated_unix"] == 90
