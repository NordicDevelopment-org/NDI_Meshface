#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


RESULT_RE = re.compile(
    r'<pre[^>]+id=["\']mesh-gui-benchmark-result["\'][^>]*>(?P<json>.*?)</pre>',
    re.IGNORECASE | re.DOTALL,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _browser_candidates() -> list[str]:
    env_browser = os.environ.get("MESH_GUI_BENCH_BROWSER", "").strip()
    candidates = [env_browser] if env_browser else []
    candidates.extend(
        [
            "chromium",
            "chromium-browser",
            "google-chrome",
            "google-chrome-stable",
            "chrome",
        ]
    )
    return [candidate for candidate in candidates if candidate]


def find_browser(explicit: str | None) -> str:
    if explicit:
        resolved = shutil.which(explicit) if os.sep not in explicit else explicit
        if resolved and Path(resolved).exists():
            return resolved
        raise SystemExit(f"Browser not found: {explicit}")
    for candidate in _browser_candidates():
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SystemExit(
        "No Chromium-compatible browser found. Install chromium or pass --browser /path/to/chrome."
    )


def build_benchmark_url(
    base_url: str,
    *,
    iterations: int,
    warmup: int,
    views: str,
    settle_ms: int,
    include_api: bool,
    include_selection: bool,
) -> str:
    parts = urlsplit(base_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update(
        {
            "mesh_gui_bench": "1",
            "mesh_gui_bench_iterations": str(iterations),
            "mesh_gui_bench_warmup": str(warmup),
            "mesh_gui_bench_views": views,
            "mesh_gui_bench_settle_ms": str(settle_ms),
            "mesh_gui_bench_api": "1" if include_api else "0",
            "mesh_gui_bench_select": "1" if include_selection else "0",
            "chat_perf": "1",
            "_mesh_gui_bench": str(os.getpid()),
        }
    )
    path = parts.path or "/"
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), parts.fragment))


def browser_command(
    browser: str,
    url: str,
    *,
    window_size: str,
    virtual_time_budget_ms: int,
    user_data_dir: str,
    headless_flag: str,
    extra_args: list[str],
) -> list[str]:
    return [
        browser,
        headless_flag,
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--disable-sync",
        "--metrics-recording-only",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={user_data_dir}",
        f"--window-size={window_size}",
        f"--virtual-time-budget={virtual_time_budget_ms}",
        "--dump-dom",
        *extra_args,
        url,
    ]


def run_browser(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def parse_result(dump_dom: str) -> dict:
    match = RESULT_RE.search(dump_dom)
    if not match:
        tail = dump_dom[-2000:].strip()
        raise ValueError(
            "Benchmark result marker was not found in browser output."
            + (f"\nLast browser output:\n{tail}" if tail else "")
        )
    payload = html.unescape(match.group("json"))
    return json.loads(payload)


def run_benchmark(args: argparse.Namespace) -> dict:
    browser = find_browser(args.browser)
    url = build_benchmark_url(
        args.url,
        iterations=args.iterations,
        warmup=args.warmup,
        views=args.views,
        settle_ms=args.settle_ms,
        include_api=not args.no_api,
        include_selection=not args.no_selection,
    )
    extra_args = list(args.browser_arg or [])
    with tempfile.TemporaryDirectory(prefix="mesh-gui-bench-") as user_data_dir:
        cmd = browser_command(
            browser,
            url,
            window_size=args.window_size,
            virtual_time_budget_ms=args.virtual_time_budget_ms,
            user_data_dir=user_data_dir,
            headless_flag="--headless=new",
            extra_args=extra_args,
        )
        proc = run_browser(cmd, args.timeout)
        if proc.returncode != 0 and "--headless=new" in cmd:
            fallback_cmd = browser_command(
                browser,
                url,
                window_size=args.window_size,
                virtual_time_budget_ms=args.virtual_time_budget_ms,
                user_data_dir=user_data_dir,
                headless_flag="--headless",
                extra_args=extra_args,
            )
            fallback_proc = run_browser(fallback_cmd, args.timeout)
            if fallback_proc.returncode == 0:
                proc = fallback_proc
            else:
                proc = proc
        if proc.returncode != 0:
            raise SystemExit(
                "Browser benchmark failed with exit code "
                f"{proc.returncode}.\nSTDERR:\n{proc.stderr[-4000:]}"
            )
        try:
            result = parse_result(proc.stdout)
        except Exception as exc:
            stderr_tail = proc.stderr[-4000:].strip()
            raise SystemExit(
                f"{exc}\nBrowser stderr:\n{stderr_tail}" if stderr_tail else str(exc)
            ) from exc
    result["_runner"] = {
        "browser": browser,
        "url": args.url,
        "window_size": args.window_size,
        "virtual_time_budget_ms": args.virtual_time_budget_ms,
    }
    return result


def _fmt_ms(value: object) -> str:
    try:
        return f"{float(value):.1f} ms"
    except (TypeError, ValueError):
        return "n/a"


def print_summary(result: dict) -> None:
    summary = result.get("summary") or {}
    total = summary.get("totalMs") or {}
    frame_max = summary.get("frameMaxMs") or {}
    frame_p95 = summary.get("frameP95Ms") or {}
    state = result.get("state") or {}
    print("Mesh GUI responsiveness benchmark")
    print(f"  ok: {result.get('ok')}")
    print(f"  duration: {_fmt_ms(result.get('durationMs'))}")
    print(
        "  state: "
        f"{state.get('nodes', 0)} visible nodes, "
        f"{state.get('rawNodes', 0)} raw nodes, "
        f"{state.get('historyCaps', 0)} history caps, "
        f"{state.get('recentChat', 0)} recent chat rows"
    )
    print(
        "  sample total: "
        f"p50 {_fmt_ms(total.get('p50'))}, "
        f"p95 {_fmt_ms(total.get('p95'))}, "
        f"max {_fmt_ms(total.get('max'))}"
    )
    print(
        "  frame delay: "
        f"p95 {_fmt_ms(frame_p95.get('p95'))}, "
        f"max {_fmt_ms(frame_max.get('max'))}, "
        f"long tasks {summary.get('longTaskCount', 0)}"
    )
    api_rows = result.get("api") or []
    if api_rows:
        print("  API timings:")
        for row in api_rows:
            label = row.get("label", "api")
            status = row.get("status", "err")
            size = row.get("bytes", 0)
            total_ms = row.get("totalMs", 0)
            ok = "ok" if row.get("ok") else "fail"
            print(f"    {label}: {ok} HTTP {status}, {_fmt_ms(total_ms)}, {size} bytes")
    by_label = summary.get("byLabel") or {}
    if by_label:
        print("  Slowest labels by p95 total:")
        ranked = sorted(
            by_label.items(),
            key=lambda item: (((item[1].get("totalMs") or {}).get("p95") or 0), item[0]),
            reverse=True,
        )
        for label, data in ranked[:8]:
            stats = data.get("totalMs") or {}
            frame_stats = data.get("frameMaxMs") or {}
            print(
                f"    {label}: p95 {_fmt_ms(stats.get('p95'))}, "
                f"max frame {_fmt_ms(frame_stats.get('max'))}, "
                f"long tasks {data.get('longTaskCount', 0)}"
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Meshyface in-browser GUI responsiveness benchmark with headless Chromium."
    )
    parser.add_argument("--url", default="http://127.0.0.1:8877/", help="Dashboard base URL.")
    parser.add_argument("--browser", default=None, help="Chromium/Chrome executable path or name.")
    parser.add_argument("--iterations", type=_positive_int, default=5, help="Measured iterations per view.")
    parser.add_argument("--warmup", type=_non_negative_int, default=1, help="Initial unmeasured poll warmups.")
    parser.add_argument(
        "--views",
        default="chat,network:map,network:graph,history,settings,console",
        help="Comma-separated views; network subviews use view:subview.",
    )
    parser.add_argument("--settle-ms", type=_non_negative_int, default=80, help="Delay between measured actions.")
    parser.add_argument("--window-size", default="1366,900", help="Headless browser window size.")
    parser.add_argument(
        "--virtual-time-budget-ms",
        type=_positive_int,
        default=90000,
        help="Chromium virtual-time budget for the benchmark page.",
    )
    parser.add_argument("--timeout", type=_positive_int, default=120, help="Browser process timeout in seconds.")
    parser.add_argument("--output-json", type=Path, default=None, help="Write full benchmark JSON to this path.")
    parser.add_argument("--json", action="store_true", help="Print full benchmark JSON instead of text summary.")
    parser.add_argument("--no-api", action="store_true", help="Skip direct API timing probes.")
    parser.add_argument("--no-selection", action="store_true", help="Skip node selection timing probes.")
    parser.add_argument(
        "--browser-arg",
        action="append",
        default=[],
        help="Extra argument passed through to Chromium. May be repeated.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    result = run_benchmark(args)
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_summary(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
