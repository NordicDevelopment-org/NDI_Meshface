from collections.abc import Callable, Sequence


def test_dashboard_js_includes_gui_responsiveness_benchmark(
    dashboard_js: str,
    assert_tokens_present: Callable[[str, Sequence[str]], None],
) -> None:
    assert_tokens_present(
        dashboard_js,
        (
            "window.__meshDashboardBenchmark",
            'meshGuiBenchmarkBoolQuery("mesh_gui_bench")',
            "meshGuiBenchmarkForcePoll",
            "meshGuiBenchmarkFetchJson",
            "meshGuiBenchmarkSummarizeSamples",
            'const stateProfiles = ["default", "chat", "network", "status", "console"];',
            "mesh-gui-benchmark-result",
        ),
    )
