import json
from pathlib import Path
from threading import RLock
from typing import Optional

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

        initial = self._normalize_preset_name(selected_preset)
        persisted = load_selected_theme_preset(settings_path)
        if persisted:
            initial = self._normalize_preset_name(persisted)
        self._selected_preset = initial

    def _normalize_preset_name(self, preset_name: Optional[str]) -> str:
        clean = str(preset_name or "").strip()
        if clean and clean in self._presets:
            return clean
        if "default" in self._presets:
            return "default"
        return next(iter(self._presets.keys()), "default")

    def available_presets(self) -> list[str]:
        names = [str(name) for name in self._presets.keys() if str(name) != "default"]
        names.sort()
        return ["default", *names] if "default" in self._presets else names

    def selected_preset_name(self) -> str:
        with self._lock:
            return self._selected_preset

    def selected_preset_tokens(self) -> ThemePreset:
        with self._lock:
            selected = self._selected_preset
        return select_theme_preset(self._presets, selected)

    def preset_catalog(self) -> ThemePresetMap:
        return {name: preset for name, preset in self._presets.items()}

    def get_settings_payload(self) -> dict[str, object]:
        with self._lock:
            selected = self._selected_preset
        return {
            "ok": True,
            "selected_preset": selected,
            "available_presets": self.available_presets(),
            "presets": self.preset_catalog(),
        }

    def set_selected_preset(self, preset_name: object) -> dict[str, object]:
        clean = str(preset_name or "").strip()
        if not clean:
            payload = self.get_settings_payload()
            payload["ok"] = False
            payload["error"] = "Theme preset name is required"
            return payload
        if clean not in self._presets:
            payload = self.get_settings_payload()
            payload["ok"] = False
            payload["error"] = f"Unknown theme preset: {clean}"
            return payload

        with self._lock:
            self._selected_preset = clean
            selected = self._selected_preset
            persist_error = save_selected_theme_preset(self._settings_path, selected)

        payload = {
            "ok": True,
            "selected_preset": selected,
            "available_presets": self.available_presets(),
            "presets": self.preset_catalog(),
        }
        if persist_error:
            payload["persist_error"] = persist_error
        return payload
