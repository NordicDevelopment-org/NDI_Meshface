# GUI Responsiveness Benchmarks

The local test suite includes an opt-in `gui_benchmark` pytest test. It starts a local dashboard, runs the headless browser benchmark, saves JSON output, and fails if `local_thresholds.json` budgets are exceeded.

Normal `pytest` skips the browser benchmark so quick unit-test runs do not launch Chromium. Run the local performance gate with:

```bash
python -m pytest -m gui_benchmark --run-gui-benchmark
```

The local run is a smoke budget because it does not include the large live mesh database. To run the stricter real-data guard against the deployed dashboard:

```bash
MESH_GUI_BENCH_URL=http://192.168.1.87:8877/ \
MESH_GUI_BENCH_THRESHOLDS=benchmarks/gui_responsiveness/live_target_thresholds.json \
MESH_GUI_BENCH_OUTPUT=benchmarks/gui_responsiveness/results/local-live-target.json \
python -m pytest -m gui_benchmark --run-gui-benchmark
```

For one-off comparisons, use `scripts/benchmark_gui_responsiveness.py` directly and commit the dated result JSON or markdown summary that captures the before/after data.
