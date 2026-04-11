import json
from pathlib import Path
from threading import RLock
from typing import Optional

from .theme import (
    DEFAULT_CUSTOM_THEME_BASE_COLOR,
    DEFAULT_CUSTOM_THEME_COLOR_DEPTH,
    DEFAULT_CUSTOM_THEME_LINE_COLOR,
    DEFAULT_CUSTOM_THEME_TINT_COLOR,
    DEFAULT_CUSTOM_THEME_TINT_INTENSITY,
    DEFAULT_THEME_BASE_COLOR,
    DEFAULT_THEME_COLOR_DEPTH,
    DEFAULT_THEME_LINE_COLOR,
    build_palette_theme_preset,
    normalize_theme_base_color,
    normalize_theme_color_depth,
    normalize_theme_line_color,
    normalize_theme_tint_color,
    normalize_theme_tint_intensity,
)
from .theme_presets import ThemePreset, ThemePresetMap, default_theme_presets, select_theme_preset


def load_selected_theme_preset(settings_path: Optional[str]) -> Optional[str]:
    if not settings_path:
        return None
    try:
        payload = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    selected = payload.get("selected_preset")
    if selected is None:
        return None
    clean = str(selected).strip()
    return clean or None


def save_selected_theme_preset(settings_path: Optional[str], preset_name: str) -> Optional[str]:
    if not settings_path:
        return None
    path = Path(settings_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps({"selected_preset": str(preset_name)}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(path)
    except Exception as exc:
        return str(exc)
    return None


def _default_custom_theme_settings() -> dict[str, object]:
    return {
        "base_color": DEFAULT_CUSTOM_THEME_BASE_COLOR,
        "line_color": DEFAULT_CUSTOM_THEME_LINE_COLOR,
        "color_depth": DEFAULT_CUSTOM_THEME_COLOR_DEPTH,
        "tint_color": DEFAULT_CUSTOM_THEME_TINT_COLOR,
        "tint_intensity": DEFAULT_CUSTOM_THEME_TINT_INTENSITY,
    }


def _int_setting(value: object, default: int) -> int:
    try:
        return int(default if value is None else value)
    except (TypeError, ValueError):
        return int(default)


def _normalize_custom_theme_settings(
    raw_settings: object,
    *,
    fallback: Optional[dict[str, object]] = None,
) -> dict[str, object]:
    base = fallback if isinstance(fallback, dict) else _default_custom_theme_settings()
    payload = raw_settings if isinstance(raw_settings, dict) else {}
    normalized_base_color = normalize_theme_base_color(
        payload.get("base_color"),
        fallback=str(base.get("base_color") or DEFAULT_THEME_BASE_COLOR),
    )
    raw_line_color = payload.get("line_color")
    raw_tint_color = payload.get("tint_color")
    normalized_line_color = normalize_theme_line_color(
        raw_line_color,
        fallback=(
            normalized_base_color
            if raw_line_color is None
            else str(base.get("line_color") or normalized_base_color or DEFAULT_THEME_LINE_COLOR)
        ),
    )
    return {
        "base_color": normalized_base_color,
        "line_color": normalized_line_color,
        "color_depth": normalize_theme_color_depth(
            payload.get("color_depth"),
            fallback=_int_setting(base.get("color_depth"), DEFAULT_THEME_COLOR_DEPTH),
        ),
        "tint_color": normalize_theme_tint_color(
            raw_tint_color,
            fallback=(
                normalized_line_color
                if raw_tint_color is None
                else str(base.get("tint_color") or normalized_line_color or DEFAULT_THEME_LINE_COLOR)
            ),
        ),
        "tint_intensity": normalize_theme_tint_intensity(
            payload.get("tint_intensity"),
            fallback=_int_setting(base.get("tint_intensity"), DEFAULT_CUSTOM_THEME_TINT_INTENSITY),
        ),
    }


def _load_persisted_theme_settings(settings_path: Optional[str]) -> dict[str, object]:
    payload = {
        "selected_preset": None,
        "custom_theme": _default_custom_theme_settings(),
    }
    if not settings_path:
        return payload
    try:
        stored = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    except Exception:
        return payload
    if not isinstance(stored, dict):
        return payload

    selected = stored.get("selected_preset")
    if selected is not None:
        clean = str(selected).strip()
        payload["selected_preset"] = clean or None
    payload["custom_theme"] = _normalize_custom_theme_settings(stored.get("custom_theme"))
    return payload


def _save_persisted_theme_settings(
    settings_path: Optional[str],
    *,
    selected_preset: str,
    custom_theme: dict[str, object],
) -> Optional[str]:
    if not settings_path:
        return None
    path = Path(settings_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(
                {
                    "selected_preset": str(selected_preset),
                    "custom_theme": _normalize_custom_theme_settings(custom_theme),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temp_path.replace(path)
    except Exception as exc:
        return str(exc)
    return None


class ThemePresetSettings:
    def __init__(
        self,
        *,
        presets: ThemePresetMap,
        selected_preset: Optional[str],
        settings_path: Optional[str],
    ) -> None:
        base_presets = dict(presets) if isinstance(presets, dict) else {}
        if "default" not in base_presets:
            base_presets.update(default_theme_presets())

        self._presets = base_presets
        self._settings_path = settings_path
        self._lock = RLock()
        self._custom_theme = _default_custom_theme_settings()

        initial = self._normalize_preset_name(selected_preset)
        persisted = _load_persisted_theme_settings(settings_path)
        persisted_selected = persisted.get("selected_preset")
        if persisted_selected:
            initial = self._normalize_preset_name(str(persisted_selected))
        self._custom_theme = _normalize_custom_theme_settings(persisted.get("custom_theme"))
        self._selected_preset = initial

    def _normalize_preset_name(self, preset_name: Optional[str]) -> str:
        clean = str(preset_name or "").strip()
        if clean == "custom":
            return "custom"
        if clean and clean in self._presets:
            return clean
        if not clean:
            return "custom"
        if "default" in self._presets:
            return "default"
        return next(iter(self._presets.keys()), "custom")

    def available_presets(self) -> list[str]:
        names = [str(name) for name in self.preset_catalog().keys() if str(name) != "default"]
        names.sort()
        return ["default", *names] if "default" in self._presets else names

    def _preset_catalog_for_custom_theme(self, custom_theme: dict[str, object]) -> ThemePresetMap:
        catalog = {name: preset for name, preset in self._presets.items()}
        catalog["custom"] = build_palette_theme_preset(
            custom_theme.get("base_color"),
            line_color=custom_theme.get("line_color"),
            color_depth=_int_setting(custom_theme.get("color_depth"), DEFAULT_THEME_COLOR_DEPTH),
            tint_color=custom_theme.get("tint_color"),
            tint_intensity=_int_setting(custom_theme.get("tint_intensity"), DEFAULT_CUSTOM_THEME_TINT_INTENSITY),
        )
        return catalog

    def _available_preset_names_for_catalog(self, catalog: ThemePresetMap) -> list[str]:
        names = [str(name) for name in catalog.keys() if str(name) != "default"]
        names.sort()
        return ["default", *names] if "default" in self._presets else names

    def _build_settings_payload(
        self,
        *,
        selected_preset: str,
        custom_theme: dict[str, object],
    ) -> dict[str, object]:
        catalog = self._preset_catalog_for_custom_theme(custom_theme)
        return {
            "ok": True,
            "selected_preset": selected_preset,
            "available_presets": self._available_preset_names_for_catalog(catalog),
            "presets": catalog,
            "custom_theme": dict(custom_theme),
        }

    def selected_preset_name(self) -> str:
        with self._lock:
            return self._selected_preset

    def selected_preset_tokens(self) -> ThemePreset:
        with self._lock:
            selected = self._selected_preset
            custom_theme = dict(self._custom_theme)
        if selected == "custom":
            return self._preset_catalog_for_custom_theme(custom_theme)["custom"]
        return select_theme_preset(self._presets, selected)

    def preset_catalog(self) -> ThemePresetMap:
        with self._lock:
            custom_theme = dict(self._custom_theme)
        return self._preset_catalog_for_custom_theme(custom_theme)

    def custom_theme_settings(self) -> dict[str, object]:
        with self._lock:
            return dict(self._custom_theme)

    def get_settings_payload(self) -> dict[str, object]:
        with self._lock:
            selected = self._selected_preset
            custom_theme = dict(self._custom_theme)
        return self._build_settings_payload(
            selected_preset=selected,
            custom_theme=custom_theme,
        )

    def set_selected_preset(self, preset_name: object) -> dict[str, object]:
        return self.apply_settings({"preset_name": preset_name})

    def apply_settings(self, request: object) -> dict[str, object]:
        payload_obj = request if isinstance(request, dict) else {}
        raw_preset = None
        raw_custom_theme = payload_obj.get("custom_theme") if payload_obj else getattr(request, "custom_theme", None)
        preview_only = bool(payload_obj.get("preview_only")) if payload_obj else bool(
            getattr(request, "preview_only", False)
        )
        if payload_obj:
            raw_preset = payload_obj.get("preset_name")
        elif hasattr(request, "preset_name"):
            raw_preset = getattr(request, "preset_name")

        clean = None if raw_preset is None else str(raw_preset or "").strip()
        if clean == "":
            payload = self.get_settings_payload()
            payload["ok"] = False
            payload["error"] = "Theme preset name is required"
            return payload

        with self._lock:
            next_custom_theme = _normalize_custom_theme_settings(
                raw_custom_theme,
                fallback=self._custom_theme,
            )
            selected = self._selected_preset
            if clean is not None:
                available = set(self._preset_catalog_for_custom_theme(next_custom_theme).keys())
                if clean not in available:
                    payload = self.get_settings_payload()
                    payload["ok"] = False
                    payload["error"] = f"Unknown theme preset: {clean}"
                    return payload
                selected = clean
            if preview_only:
                persist_error = None
                payload = self._build_settings_payload(
                    selected_preset=selected,
                    custom_theme=next_custom_theme,
                )
            else:
                self._selected_preset = selected
                self._custom_theme = next_custom_theme
                persist_error = _save_persisted_theme_settings(
                    self._settings_path,
                    selected_preset=self._selected_preset,
                    custom_theme=self._custom_theme,
                )
                payload = self._build_settings_payload(
                    selected_preset=self._selected_preset,
                    custom_theme=dict(self._custom_theme),
                )

        if persist_error:
            payload["persist_error"] = persist_error
        return payload
