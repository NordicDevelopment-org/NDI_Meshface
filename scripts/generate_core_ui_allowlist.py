#!/usr/bin/env python3
"""Generate a minimal core-ui public release allowlist.

This script traces local Python imports from runtime entrypoints and adds
profile-selected frontend templates so the allowlist can stay explicit without
shipping the entire repository.
"""

from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_PROFILE = "core-ui"
DEFAULT_OUTPUT = REPO_ROOT / ".public-release" / "allowlists" / f"{DEFAULT_PROFILE}.allowlist"
ENTRY_MODULES = ("mesh_dashboard", "mesh_connection")
BASE_ALLOWLIST_PATHS = (
    "README.md",
    "mesh_dashboard.py",
    "mesh_connection.py",
    "meshtastic-dashboard.service",
)
STATIC_ASSET_PATHS = (
    "meshdash/assets/dashboard.html.tmpl",
    "meshdash/assets/offline_atlas_na.min.json",
)
CORE_UI_OPTIONAL_PATH_PREFIXES = (
    "meshdash/api_bot.py",
    "meshdash/api_input_bot.py",
    "meshdash/api_input_zork.py",
    "meshdash/api_zork.py",
    "meshdash/bot_",
    "meshdash/bot_apps/",
    "meshdash/games/zork/",
    "meshdash/services_standalone_zork.py",
)


def _module_to_path(module_name: str) -> Path | None:
    if module_name == "mesh_dashboard":
        path = REPO_ROOT / "mesh_dashboard.py"
        return path if path.exists() else None
    if module_name == "mesh_connection":
        path = REPO_ROOT / "mesh_connection.py"
        return path if path.exists() else None
    if module_name == "meshdash":
        path = REPO_ROOT / "meshdash" / "__init__.py"
        return path if path.exists() else None
    if module_name.startswith("meshdash."):
        relative = Path(*module_name.split("."))
        py_path = REPO_ROOT / relative.with_suffix(".py")
        if py_path.exists():
            return py_path
        pkg_init = REPO_ROOT / relative / "__init__.py"
        if pkg_init.exists():
            return pkg_init
    return None


def _normalize_module_candidates(
    *,
    current_module: str,
    base_module: str,
    alias: str | None = None,
) -> list[str]:
    candidates: list[str] = []

    def _add_if_local(candidate: str) -> None:
        if _module_to_path(candidate) is not None and candidate not in candidates:
            candidates.append(candidate)

    if base_module:
        _add_if_local(base_module)
        if alias:
            _add_if_local(f"{base_module}.{alias}")

    if current_module == "meshdash" or current_module.startswith("meshdash."):
        if base_module and "." not in base_module:
            _add_if_local(f"meshdash.{base_module}")
            if alias:
                _add_if_local(f"meshdash.{base_module}.{alias}")
        if not base_module and alias and "." not in alias:
            _add_if_local(f"meshdash.{alias}")

    return candidates


def _parse_import_modules(module_name: str, module_path: Path) -> list[str]:
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(module_path))
    package = module_name.rsplit(".", 1)[0] if "." in module_name else ""
    discovered: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                discovered.extend(
                    _normalize_module_candidates(
                        current_module=module_name,
                        base_module=alias.name,
                    )
                )
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        level = node.level or 0
        raw_module = node.module or ""
        resolved_module = raw_module

        if level:
            base_parts = package.split(".") if package else []
            if level <= len(base_parts) + 1:
                parent_parts = base_parts[: len(base_parts) - level + 1]
                merged = parent_parts + ([raw_module] if raw_module else [])
                resolved_module = ".".join(part for part in merged if part)
            else:
                resolved_module = ""

        for alias in node.names:
            if alias.name == "*":
                discovered.extend(
                    _normalize_module_candidates(
                        current_module=module_name,
                        base_module=resolved_module,
                    )
                )
                continue
            discovered.extend(
                _normalize_module_candidates(
                    current_module=module_name,
                    base_module=resolved_module,
                    alias=alias.name,
                )
            )

    return discovered


def _collect_local_dependency_files(entry_modules: tuple[str, ...]) -> set[Path]:
    queue: deque[str] = deque(entry_modules)
    visited: set[str] = set()
    files: set[Path] = set()

    while queue:
        module_name = queue.popleft()
        if module_name in visited:
            continue
        visited.add(module_name)

        module_path = _module_to_path(module_name)
        if module_path is None:
            continue
        files.add(module_path)

        for dep_module in _parse_import_modules(module_name, module_path):
            if dep_module not in visited:
                queue.append(dep_module)

    return files


def _collect_profile_assets(profile_name: str) -> set[Path]:
    from meshdash.html_css import _DASHBOARD_CSS_TEMPLATE_PARTS  # noqa: WPS433
    from meshdash.html_js import _template_parts_for_profile  # noqa: WPS433

    assets = {
        (REPO_ROOT / "meshdash" / "assets" / template_name)
        for template_name in _template_parts_for_profile(profile_name)
    }
    assets.update(
        (REPO_ROOT / "meshdash" / "assets" / template_name)
        for template_name in _DASHBOARD_CSS_TEMPLATE_PARTS
    )
    assets.update(REPO_ROOT / rel for rel in STATIC_ASSET_PATHS)
    return {path for path in assets if path.exists()}


def _build_allowlist_lines(profile_name: str) -> list[str]:
    base_paths = {REPO_ROOT / rel for rel in BASE_ALLOWLIST_PATHS}
    local_deps = _collect_local_dependency_files(ENTRY_MODULES)
    profile_assets = _collect_profile_assets(profile_name)
    all_paths = sorted(base_paths | local_deps | profile_assets)
    if profile_name == "core-ui":
        filtered: list[Path] = []
        for path in all_paths:
            rel = str(path.relative_to(REPO_ROOT))
            if any(rel.startswith(prefix) for prefix in CORE_UI_OPTIONAL_PATH_PREFIXES):
                continue
            filtered.append(path)
        all_paths = filtered

    header = [
        f"# Auto-generated core runtime allowlist for profile: {profile_name}",
        "# Generated by: scripts/generate_core_ui_allowlist.py",
        "# Keep this explicit list in source control for safe public release diffs.",
        "",
    ]
    body = [str(path.relative_to(REPO_ROOT)) for path in all_paths]
    return header + body + [""]


def _write_allowlist(output_path: Path, lines: list[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _print_diff_summary(old_text: str, new_text: str, output_path: Path) -> None:
    old_set = {line.strip() for line in old_text.splitlines() if line and not line.startswith("#")}
    new_set = {line.strip() for line in new_text.splitlines() if line and not line.startswith("#")}
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    print(f"[allowlist] {output_path}")
    print(f"[allowlist] entries old={len(old_set)} new={len(new_set)}")
    print(f"[allowlist] added={len(added)} removed={len(removed)}")


def _validate_minimal_tree(allowlist_lines: list[str], profile_name: str) -> None:
    entries = [
        line.strip()
        for line in allowlist_lines
        if line.strip() and not line.startswith("#")
    ]
    with tempfile.TemporaryDirectory(prefix="mesh-core-ui-allowlist-") as temp_dir:
        temp_root = Path(temp_dir)
        for relative in entries:
            src = REPO_ROOT / relative
            dst = temp_root / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

        checks = [
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "mesh_dashboard.py",
                "mesh_connection.py",
                "meshdash",
            ],
            [
                sys.executable,
                "-c",
                "import mesh_dashboard; print('import_mesh_dashboard_ok')",
            ],
            [
                sys.executable,
                "-c",
                (
                    "from meshdash.html import render_html; "
                    "html = render_html("
                    "refresh_ms=3000, packet_limit=250, show_secrets=False, history_enabled=True, "
                    "history_max_rows=1000, history_retention_days=7, node_history_hours=72, "
                    "node_history_max_points=1440, revision_label='Rev', revision_title='Rev', "
                    f"ui_profile='{profile_name}'"
                    "); print('render_html_ok', len(html))"
                ),
            ],
        ]
        for cmd in checks:
            subprocess.run(cmd, cwd=temp_root, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate minimal core-ui public allowlist.")
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE,
        help="UI profile to resolve template dependencies from (default: core-ui).",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Allowlist output path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the existing allowlist differs from generated output.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated list by compiling/importing from a temp minimal tree.",
    )
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    new_lines = _build_allowlist_lines(args.profile)
    new_text = "\n".join(new_lines)
    old_text = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
    _print_diff_summary(old_text, new_text, output_path)

    if args.check:
        if old_text != new_text:
            print("[allowlist] mismatch detected (run generator without --check).")
            return 1
        print("[allowlist] up to date.")
        return 0

    _write_allowlist(output_path, new_lines)
    print(f"[allowlist] wrote {output_path}")

    if args.validate:
        _validate_minimal_tree(new_lines, args.profile)
        print("[allowlist] validation passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
