from meshdash.history_rollups import bucket_minute, clean_node_id, merge_metric


def test_merge_metric_without_sample_preserves_existing_values():
    out = merge_metric(10.0, 2, -5.0, 3.0, None)
    assert out == (10.0, 2, -5.0, 3.0)


def test_merge_metric_with_sample_updates_sum_count_and_extrema():
    out = merge_metric(10.0, 2, -5.0, 3.0, 7.5)
    assert out == (17.5, 3, -5.0, 7.5)


def test_bucket_minute_rounds_down_to_minute_boundary():
    assert bucket_minute(1710000061) == 1710000060
    assert bucket_minute(1710000000) == 1710000000


def test_clean_node_id_filters_invalid_values():
    assert clean_node_id(" !abcd1234 ") == "!abcd1234"
    assert clean_node_id("") is None
    assert clean_node_id("Unknown") is None
    assert clean_node_id("n/a") is None
    assert clean_node_id("^all") is None
