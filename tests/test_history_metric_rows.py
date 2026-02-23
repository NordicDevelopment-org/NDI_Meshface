from meshdash.history_metric_rows import (
    build_metric_rollup_values,
    merge_metric_rollup_row,
)


def test_build_metric_rollup_values_initializes_expected_defaults():
    values = build_metric_rollup_values(
        event_unix=100,
        rx_snr=5.5,
        rx_rssi=-110.0,
        hops=3,
    )
    assert values["packet_count"] == 1
    assert values["snr_sum"] == 5.5
    assert values["snr_count"] == 1
    assert values["snr_min"] == 5.5
    assert values["snr_max"] == 5.5
    assert values["rssi_sum"] == -110.0
    assert values["rssi_count"] == 1
    assert values["hops_sum"] == 3
    assert values["hops_count"] == 1
    assert values["hops_min"] == 3
    assert values["hops_max"] == 3
    assert values["last_seen_unix"] == 100


def test_merge_metric_rollup_row_merges_counts_ranges_and_last_seen():
    row = (
        2,      # packet_count
        4.0,    # snr_sum
        1,      # snr_count
        4.0,    # snr_min
        4.0,    # snr_max
        -220.0, # rssi_sum
        2,      # rssi_count
        -120.0, # rssi_min
        -100.0, # rssi_max
        5,      # hops_sum
        2,      # hops_count
        2,      # hops_min
        3,      # hops_max
        95,     # last_seen_unix
    )
    merged = merge_metric_rollup_row(
        row=row,
        event_unix=120,
        rx_snr=6.0,
        rx_rssi=-90.0,
        hops=4,
    )
    assert merged["packet_count"] == 3
    assert merged["snr_sum"] == 10.0
    assert merged["snr_count"] == 2
    assert merged["snr_min"] == 4.0
    assert merged["snr_max"] == 6.0
    assert merged["rssi_sum"] == -310.0
    assert merged["rssi_count"] == 3
    assert merged["rssi_min"] == -120.0
    assert merged["rssi_max"] == -90.0
    assert merged["hops_sum"] == 9
    assert merged["hops_count"] == 3
    assert merged["hops_min"] == 2
    assert merged["hops_max"] == 4
    assert merged["last_seen_unix"] == 120
