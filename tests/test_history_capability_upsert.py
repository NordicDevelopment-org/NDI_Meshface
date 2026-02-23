from meshdash.history_capability_upsert import (
    build_node_capability_insert_values,
    merge_node_capability_row,
    normalize_node_capability_inputs,
)


def test_normalize_node_capability_inputs_enforces_ranges():
    assert normalize_node_capability_inputs(last_hops=3, battery_level=80) == (3, 80)
    assert normalize_node_capability_inputs(last_hops=-1, battery_level=80) == (None, 80)
    assert normalize_node_capability_inputs(last_hops=1, battery_level=120) == (1, None)


def test_build_node_capability_insert_values_sets_expected_defaults():
    values = build_node_capability_insert_values(
        node_id="!abc",
        event_unix=200,
        has_position=True,
        clean_hops=4,
        clean_battery=90,
    )
    assert values == ("!abc", 200, 1, 200, 4, 90, 200)


def test_merge_node_capability_row_keeps_existing_values_without_new_data():
    merged = merge_node_capability_row(
        row=(100, 0, None, 5, 75, 95),
        event_unix=120,
        has_position=False,
        clean_hops=None,
        clean_battery=None,
    )
    assert merged["last_seen_unix"] == 120
    assert merged["has_position"] is False
    assert merged["last_position_unix"] is None
    assert merged["last_hops"] == 5
    assert merged["battery_level"] == 75
    assert merged["battery_updated_unix"] == 95


def test_merge_node_capability_row_prefers_new_hops_position_and_battery():
    merged = merge_node_capability_row(
        row=(100, 1, 98, 2, 70, 99),
        event_unix=130,
        has_position=True,
        clean_hops=6,
        clean_battery=88,
    )
    assert merged["last_seen_unix"] == 130
    assert merged["has_position"] is True
    assert merged["last_position_unix"] == 130
    assert merged["last_hops"] == 6
    assert merged["battery_level"] == 88
    assert merged["battery_updated_unix"] == 130
