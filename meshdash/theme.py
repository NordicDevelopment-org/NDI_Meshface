import colorsys
import re
from typing import Dict, Optional

# Single source of truth for dashboard theme tokens.
# Keep palette changes here so CSS values stay centralized.
LIGHT_THEME_VARS: Dict[str, str] = {
    "--bg": "#f3f7f1",
    "--ink": "#112015",
    "--panel": "#ffffff",
    "--line": "#c6d6c0",
    "--accent": "#2f855a",
    "--accent-2": "#1f6f53",
    "--theme-base-color": "#2f855a",
    "--danger": "#c53030",
    "--muted": "#5e6e64",
    "--shadow": "0 10px 24px rgba(18, 40, 20, 0.08)",
    "--surface-tint-color": "#2f855a",
    "--surface-tint-intensity": "50",
    "--surface-tint-bg-soft": "#f4faf3",
    "--surface-tint-bg": "#f7fcf7",
    "--surface-tint-bg-alt": "#edf6ec",
    "--surface-tint-bg-hover": "#e7f0ea",
    "--surface-tint-border": "#d2e1d0",
    "--surface-tint-border-strong": "#b8cab9",
    "--surface-tint-text": "#2b4a37",
    "--surface-tint-text-soft": "#4a6958",
    "--surface-tint-divider-bg": "linear-gradient(90deg, #f4faf3, #edf5ea)",
    "--surface-tint-divider-line": "#b8cab9",
    "--surface-tint-start-hue": "145",
    "--surface-tint-end-hue": "176",
    "--surface-tint-outline-hue": "325",
    "--surface-tint-sat-mult": "1",
    "--surface-tint-outline-sat-mult": "1.04",
    "--surface-tint-dark-sat-mult": "1.02",
    "--surface-tint-outline-dark-sat-mult": "1.18",
    "--surface-tint-alpha-mult": "1",
    "--surface-tint-dark-alpha-mult": "1",
}

DARK_THEME_VARS: Dict[str, str] = {
    "--ui-bg": "#0d1117",
    "--ui-bg-elev": "#111827",
    "--ui-panel": "#161b22",
    "--ui-panel-alt": "#1b2430",
    "--ui-border": "#2f3b4b",
    "--ui-text": "#e6edf3",
    "--ui-text-soft": "#9fb0c3",
    "--ui-accent": "#3fb950",
    "--ui-accent-soft": "#2ea043",
    "--theme-base-color": "#2f855a",
    "--ui-link": "#79c0ff",
    "--ui-shadow": "0 10px 24px rgba(1, 4, 9, 0.36)",
    "--workspace-shell-bg": "#08120d",
    "--workspace-shell-bg-alt": "#07140d",
    "--workspace-shell-border": "#2d8f5d",
    "--workspace-shell-border-muted": "#236744",
    "--workspace-shell-border-strong": "#3f8f68",
    "--workspace-shell-text": "#c6ffdb",
    "--workspace-shell-text-soft": "#b8d6c4",
    "--workspace-shell-hover-bg": "#0d1d13",
    "--workspace-shell-active-bg": "#173126",
    "--workspace-shell-active-text": "#8ce7b4",
    "--workspace-shell-divider-bg": "linear-gradient(90deg, #08140d, #0b1a11)",
    "--workspace-shell-divider-line": "#236744",
    "--workspace-shell-divider-line-active": "#2d8f5d",
    "--workspace-shell-shadow": "0 12px 28px rgba(2, 6, 4, 0.5)",
    "--surface-tint-color": "#2d8f5d",
    "--surface-tint-intensity": "50",
    "--surface-tint-bg-soft": "#08140d",
    "--surface-tint-bg": "#08120d",
    "--surface-tint-bg-alt": "#0d1d13",
    "--surface-tint-bg-hover": "#173126",
    "--surface-tint-border": "#236744",
    "--surface-tint-border-strong": "#2d8f5d",
    "--surface-tint-text": "#c6ffdb",
    "--surface-tint-text-soft": "#b8d6c4",
    "--surface-tint-divider-bg": "linear-gradient(90deg, #08140d, #0b1a11)",
    "--surface-tint-divider-line": "#236744",
    "--surface-tint-start-hue": "145",
    "--surface-tint-end-hue": "176",
    "--surface-tint-outline-hue": "154",
    "--surface-tint-sat-mult": "1",
    "--surface-tint-outline-sat-mult": "1.04",
    "--surface-tint-dark-sat-mult": "1.02",
    "--surface-tint-outline-dark-sat-mult": "1.18",
    "--surface-tint-alpha-mult": "1",
    "--surface-tint-dark-alpha-mult": "1",
}

DEFAULT_THEME_BASE_COLOR = LIGHT_THEME_VARS["--accent"]
DEFAULT_THEME_LINE_COLOR = DEFAULT_THEME_BASE_COLOR
DEFAULT_THEME_COLOR_DEPTH = 58
DEFAULT_THEME_TINT_COLOR = LIGHT_THEME_VARS["--surface-tint-color"]
DEFAULT_THEME_TINT_INTENSITY = int(LIGHT_THEME_VARS["--surface-tint-intensity"])
DEV_THEME_BASE_COLOR = "#2563eb"
DEFAULT_CUSTOM_THEME_BASE_COLOR = DEV_THEME_BASE_COLOR
DEFAULT_CUSTOM_THEME_LINE_COLOR = "#9a9996"
DEFAULT_CUSTOM_THEME_COLOR_DEPTH = 50
DEFAULT_CUSTOM_THEME_TINT_COLOR = DEFAULT_CUSTOM_THEME_LINE_COLOR
DEFAULT_CUSTOM_THEME_TINT_INTENSITY = 50
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def normalize_theme_base_color(
    value: object,
    *,
    fallback: str = DEFAULT_THEME_BASE_COLOR,
) -> str:
    clean = str(value or "").strip()
    if not _HEX_COLOR_RE.fullmatch(clean):
        clean = str(fallback).strip()
    if len(clean) == 4:
        clean = "#" + "".join(ch * 2 for ch in clean[1:])
    return clean.lower()


def normalize_theme_line_color(
    value: object,
    *,
    fallback: str = DEFAULT_THEME_LINE_COLOR,
) -> str:
    return normalize_theme_base_color(value, fallback=fallback)


def normalize_theme_color_depth(
    value: object,
    *,
    fallback: int = DEFAULT_THEME_COLOR_DEPTH,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = int(fallback)
    return max(0, min(100, parsed))


def normalize_theme_tint_color(
    value: object,
    *,
    fallback: str = DEFAULT_THEME_TINT_COLOR,
) -> str:
    return normalize_theme_base_color(value, fallback=fallback)


def normalize_theme_tint_intensity(
    value: object,
    *,
    fallback: int = DEFAULT_THEME_TINT_INTENSITY,
) -> int:
    return normalize_theme_color_depth(value, fallback=fallback)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    clean = normalize_theme_base_color(value)
    return (
        int(clean[1:3], 16),
        int(clean[3:5], 16),
        int(clean[5:7], 16),
    )


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(round(rgb[0])))),
        max(0, min(255, int(round(rgb[1])))),
        max(0, min(255, int(round(rgb[2])))),
    )


def _rgb_to_hls(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    return colorsys.rgb_to_hls(
        max(0.0, min(1.0, float(rgb[0]) / 255.0)),
        max(0.0, min(1.0, float(rgb[1]) / 255.0)),
        max(0.0, min(1.0, float(rgb[2]) / 255.0)),
    )


def _mix_rgb(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    ratio: float,
) -> tuple[int, int, int]:
    clamped = max(0.0, min(1.0, float(ratio)))
    return tuple(
        int(round((channel_start * (1.0 - clamped)) + (channel_end * clamped)))
        for channel_start, channel_end in zip(start, end, strict=True)
    )


def _channel_luminance(channel: int) -> float:
    normalized = max(0.0, min(1.0, float(channel) / 255.0))
    if normalized <= 0.04045:
        return normalized / 12.92
    return ((normalized + 0.055) / 1.055) ** 2.4


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    red = _channel_luminance(rgb[0])
    green = _channel_luminance(rgb[1])
    blue = _channel_luminance(rgb[2])
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


def _ensure_min_luminance(
    rgb: tuple[int, int, int],
    minimum: float,
) -> tuple[int, int, int]:
    out = rgb
    for _ in range(8):
        if _relative_luminance(out) >= minimum:
            break
        out = _mix_rgb(out, (255, 255, 255), 0.2)
    return out


def _ensure_max_luminance(
    rgb: tuple[int, int, int],
    maximum: float,
) -> tuple[int, int, int]:
    out = rgb
    for _ in range(8):
        if _relative_luminance(out) <= maximum:
            break
        out = _mix_rgb(out, (0, 0, 0), 0.18)
    return out


def _depth_mix(depth: int, low: float, high: float) -> float:
    ratio = normalize_theme_color_depth(depth) / 100.0
    return low + ((high - low) * ratio)


def _format_alpha(alpha: float) -> str:
    return f"{max(0.0, min(1.0, alpha)):.3f}".rstrip("0").rstrip(".")


def _format_number(value: float) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def _rgba(rgb: tuple[int, int, int], alpha: float) -> str:
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {_format_alpha(alpha)})"


def _intensity_mix(intensity: int, low: float, high: float) -> float:
    ratio = normalize_theme_tint_intensity(intensity) / 100.0
    ratio = 1.0 - ((1.0 - ratio) ** 1.35)
    return low + ((high - low) * ratio)


def build_palette_theme_preset(
    base_color: object,
    *,
    line_color: object = None,
    tint_color: object = None,
    color_depth: int = DEFAULT_THEME_COLOR_DEPTH,
    tint_intensity: int = DEFAULT_THEME_TINT_INTENSITY,
) -> dict[str, Dict[str, str]]:
    base_hex = normalize_theme_base_color(base_color)
    line_hex = normalize_theme_line_color(line_color, fallback=base_hex)
    tint_hex = normalize_theme_tint_color(tint_color, fallback=line_hex)
    depth = normalize_theme_color_depth(color_depth)
    intensity = normalize_theme_tint_intensity(tint_intensity)
    base_rgb = _hex_to_rgb(base_hex)
    line_rgb = _hex_to_rgb(line_hex)
    tint_rgb = _hex_to_rgb(tint_hex)
    deep_base_rgb = _mix_rgb(base_rgb, (0, 0, 0), 0.34)

    light_accent_rgb = _ensure_max_luminance(base_rgb, 0.34)
    light_accent_strong_rgb = _ensure_max_luminance(
        _mix_rgb(light_accent_rgb, (0, 0, 0), _depth_mix(depth, 0.16, 0.24)),
        0.22,
    )
    dark_accent_soft_rgb = _ensure_min_luminance(base_rgb, 0.22)
    dark_accent_rgb = _ensure_min_luminance(
        _mix_rgb(dark_accent_soft_rgb, (255, 255, 255), _depth_mix(depth, 0.12, 0.24)),
        0.4,
    )

    light_bg_rgb = _mix_rgb(_hex_to_rgb(LIGHT_THEME_VARS["--bg"]), base_rgb, _depth_mix(depth, 0.08, 0.16))
    light_panel_rgb = _mix_rgb(
        _hex_to_rgb(LIGHT_THEME_VARS["--panel"]),
        base_rgb,
        _depth_mix(depth, 0.02, 0.05),
    )
    light_line_source_rgb = _mix_rgb(line_rgb, _hex_to_rgb(LIGHT_THEME_VARS["--ink"]), 0.18)
    light_line_rgb = _ensure_max_luminance(
        _mix_rgb(
            _hex_to_rgb(LIGHT_THEME_VARS["--line"]),
            light_line_source_rgb,
            _depth_mix(depth, 0.62, 0.82),
        ),
        0.34,
    )
    light_ink_rgb = _ensure_max_luminance(
        _mix_rgb(_hex_to_rgb(LIGHT_THEME_VARS["--ink"]), light_accent_strong_rgb, _depth_mix(depth, 0.08, 0.14)),
        0.06,
    )
    light_muted_rgb = _ensure_max_luminance(
        _mix_rgb(_hex_to_rgb(LIGHT_THEME_VARS["--muted"]), light_accent_strong_rgb, _depth_mix(depth, 0.08, 0.16)),
        0.2,
    )

    dark_ui_bg_rgb = _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--ui-bg"]), deep_base_rgb, _depth_mix(depth, 0.08, 0.18))
    dark_ui_bg_elev_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--ui-bg-elev"]),
        deep_base_rgb,
        _depth_mix(depth, 0.1, 0.2),
    )
    dark_ui_panel_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--ui-panel"]),
        deep_base_rgb,
        _depth_mix(depth, 0.12, 0.24),
    )
    dark_ui_panel_alt_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--ui-panel-alt"]),
        deep_base_rgb,
        _depth_mix(depth, 0.14, 0.28),
    )
    dark_line_rgb = _ensure_min_luminance(line_rgb, 0.16)
    dark_ui_border_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--ui-border"]),
        dark_line_rgb,
        _depth_mix(depth, 0.6, 0.78),
    )
    dark_ui_text_rgb = _ensure_min_luminance(
        _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--ui-text"]), dark_accent_rgb, _depth_mix(depth, 0.04, 0.1)),
        0.76,
    )
    dark_ui_text_soft_rgb = _ensure_min_luminance(
        _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--ui-text-soft"]), dark_accent_soft_rgb, _depth_mix(depth, 0.06, 0.12)),
        0.4,
    )
    dark_ui_link_rgb = _ensure_min_luminance(
        _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--ui-link"]), dark_accent_rgb, _depth_mix(depth, 0.24, 0.46)),
        0.5,
    )

    workspace_bg_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-bg"]),
        deep_base_rgb,
        _depth_mix(depth, 0.24, 0.42),
    )
    workspace_bg_alt_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-bg-alt"]),
        deep_base_rgb,
        _depth_mix(depth, 0.22, 0.4),
    )
    workspace_border_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-border"]),
        dark_line_rgb,
        _depth_mix(depth, 0.72, 0.86),
    )
    workspace_line_muted_source_rgb = _mix_rgb(dark_line_rgb, workspace_bg_rgb, 0.28)
    workspace_border_muted_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-border-muted"]),
        workspace_line_muted_source_rgb,
        _depth_mix(depth, 0.66, 0.82),
    )
    workspace_line_strong_source_rgb = _mix_rgb(dark_line_rgb, (255, 255, 255), 0.16)
    workspace_border_strong_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-border-strong"]),
        workspace_line_strong_source_rgb,
        _depth_mix(depth, 0.74, 0.9),
    )
    workspace_text_rgb = _ensure_min_luminance(
        _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--workspace-shell-text"]), dark_accent_rgb, _depth_mix(depth, 0.08, 0.16)),
        0.72,
    )
    workspace_text_soft_rgb = _ensure_min_luminance(
        _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--workspace-shell-text-soft"]), dark_accent_soft_rgb, _depth_mix(depth, 0.08, 0.14)),
        0.5,
    )
    workspace_hover_bg_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-hover-bg"]),
        dark_accent_soft_rgb,
        _depth_mix(depth, 0.14, 0.24),
    )
    workspace_active_bg_rgb = _mix_rgb(
        _hex_to_rgb(DARK_THEME_VARS["--workspace-shell-active-bg"]),
        dark_accent_soft_rgb,
        _depth_mix(depth, 0.18, 0.3),
    )
    workspace_active_text_rgb = _ensure_min_luminance(
        _mix_rgb(_hex_to_rgb(DARK_THEME_VARS["--workspace-shell-active-text"]), dark_accent_rgb, _depth_mix(depth, 0.12, 0.24)),
        0.64,
    )
    divider_start_rgb = _mix_rgb(workspace_bg_rgb, dark_accent_soft_rgb, _depth_mix(depth, 0.06, 0.12))
    divider_end_rgb = _mix_rgb(workspace_bg_alt_rgb, dark_accent_rgb, _depth_mix(depth, 0.08, 0.14))

    tint_hue, _, tint_saturation = _rgb_to_hls(tint_rgb)
    tint_hue_degrees = (tint_hue * 360.0) % 360.0
    tint_start_hue = int(round(tint_hue_degrees)) % 360
    tint_end_hue = int(round(tint_hue_degrees + 28.0)) % 360
    tint_outline_hue = int(round(tint_hue_degrees + (8.0 if tint_saturation >= 0.06 else 0.0))) % 360
    tint_intensity_ratio = _intensity_mix(intensity, 0.0, 1.0)
    tint_sat_mult = min(1.08, tint_intensity_ratio * tint_saturation * 1.9)
    tint_outline_sat_mult = min(1.16, tint_intensity_ratio * tint_saturation * 2.1)
    tint_dark_sat_mult = min(1.12, tint_intensity_ratio * tint_saturation * 2.0)
    tint_outline_dark_sat_mult = min(1.2, tint_intensity_ratio * tint_saturation * 2.2)
    tint_alpha_mult = tint_intensity_ratio
    tint_dark_alpha_mult = max(0.0, min(1.0, tint_alpha_mult * 0.86))

    light_surface_soft_rgb = _mix_rgb((255, 255, 255), tint_rgb, _intensity_mix(intensity, 0.0, 0.18))
    light_surface_bg_rgb = _mix_rgb((255, 255, 255), tint_rgb, _intensity_mix(intensity, 0.0, 0.26))
    light_surface_bg_alt_rgb = _mix_rgb((255, 255, 255), tint_rgb, _intensity_mix(intensity, 0.0, 0.34))
    light_surface_hover_rgb = _mix_rgb((255, 255, 255), tint_rgb, _intensity_mix(intensity, 0.0, 0.42))
    light_surface_border_rgb = _ensure_max_luminance(
        _mix_rgb(_hex_to_rgb(LIGHT_THEME_VARS["--line"]), tint_rgb, _intensity_mix(intensity, 0.0, 0.68)),
        0.34,
    )
    light_surface_border_strong_rgb = _ensure_max_luminance(
        _mix_rgb(light_surface_border_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.54)),
        0.28,
    )
    light_surface_text_rgb = _ensure_max_luminance(
        _mix_rgb(light_ink_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.16)),
        0.08,
    )
    light_surface_text_soft_rgb = _ensure_max_luminance(
        _mix_rgb(light_muted_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.22)),
        0.22,
    )
    light_surface_divider_start_rgb = _mix_rgb(light_surface_soft_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.06))
    light_surface_divider_end_rgb = _mix_rgb(light_surface_bg_alt_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.12))

    dark_surface_soft_rgb = _mix_rgb(workspace_bg_alt_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.18))
    dark_surface_bg_rgb = _mix_rgb(workspace_bg_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.24))
    dark_surface_bg_alt_rgb = _mix_rgb(workspace_bg_alt_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.32))
    dark_surface_hover_rgb = _mix_rgb(workspace_hover_bg_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.4))
    dark_surface_border_rgb = _mix_rgb(workspace_border_muted_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.52))
    dark_surface_border_strong_rgb = _mix_rgb(workspace_border_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.64))
    dark_surface_text_rgb = _ensure_min_luminance(
        _mix_rgb(workspace_text_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.14)),
        0.72,
    )
    dark_surface_text_soft_rgb = _ensure_min_luminance(
        _mix_rgb(workspace_text_soft_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.2)),
        0.5,
    )
    dark_surface_divider_start_rgb = _mix_rgb(dark_surface_soft_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.08))
    dark_surface_divider_end_rgb = _mix_rgb(dark_surface_bg_alt_rgb, tint_rgb, _intensity_mix(intensity, 0.0, 0.14))

    light_tokens = {
        "--bg": _rgb_to_hex(light_bg_rgb),
        "--ink": _rgb_to_hex(light_ink_rgb),
        "--panel": _rgb_to_hex(light_panel_rgb),
        "--line": _rgb_to_hex(light_line_rgb),
        "--accent": _rgb_to_hex(light_accent_rgb),
        "--accent-2": _rgb_to_hex(light_accent_strong_rgb),
        "--theme-base-color": base_hex,
        "--danger": LIGHT_THEME_VARS["--danger"],
        "--muted": _rgb_to_hex(light_muted_rgb),
        "--shadow": f"0 10px 24px {_rgba(_mix_rgb(base_rgb, (0, 0, 0), 0.74), _depth_mix(depth, 0.08, 0.14))}",
        "--surface-tint-color": tint_hex,
        "--surface-tint-intensity": str(intensity),
        "--surface-tint-bg-soft": _rgb_to_hex(light_surface_soft_rgb),
        "--surface-tint-bg": _rgb_to_hex(light_surface_bg_rgb),
        "--surface-tint-bg-alt": _rgb_to_hex(light_surface_bg_alt_rgb),
        "--surface-tint-bg-hover": _rgb_to_hex(light_surface_hover_rgb),
        "--surface-tint-border": _rgb_to_hex(light_surface_border_rgb),
        "--surface-tint-border-strong": _rgb_to_hex(light_surface_border_strong_rgb),
        "--surface-tint-text": _rgb_to_hex(light_surface_text_rgb),
        "--surface-tint-text-soft": _rgb_to_hex(light_surface_text_soft_rgb),
        "--surface-tint-divider-bg": f"linear-gradient(90deg, {_rgb_to_hex(light_surface_divider_start_rgb)}, {_rgb_to_hex(light_surface_divider_end_rgb)})",
        "--surface-tint-divider-line": _rgb_to_hex(light_surface_border_strong_rgb),
        "--surface-tint-start-hue": str(tint_start_hue),
        "--surface-tint-end-hue": str(tint_end_hue),
        "--surface-tint-outline-hue": str(tint_outline_hue),
        "--surface-tint-sat-mult": _format_number(tint_sat_mult),
        "--surface-tint-outline-sat-mult": _format_number(tint_outline_sat_mult),
        "--surface-tint-dark-sat-mult": _format_number(tint_dark_sat_mult),
        "--surface-tint-outline-dark-sat-mult": _format_number(tint_outline_dark_sat_mult),
        "--surface-tint-alpha-mult": _format_number(tint_alpha_mult),
        "--surface-tint-dark-alpha-mult": _format_number(tint_dark_alpha_mult),
    }
    dark_tokens = {
        "--ui-bg": _rgb_to_hex(dark_ui_bg_rgb),
        "--ui-bg-elev": _rgb_to_hex(dark_ui_bg_elev_rgb),
        "--ui-panel": _rgb_to_hex(dark_ui_panel_rgb),
        "--ui-panel-alt": _rgb_to_hex(dark_ui_panel_alt_rgb),
        "--ui-border": _rgb_to_hex(dark_ui_border_rgb),
        "--ui-text": _rgb_to_hex(dark_ui_text_rgb),
        "--ui-text-soft": _rgb_to_hex(dark_ui_text_soft_rgb),
        "--ui-accent": _rgb_to_hex(dark_accent_rgb),
        "--ui-accent-soft": _rgb_to_hex(dark_accent_soft_rgb),
        "--theme-base-color": base_hex,
        "--ui-link": _rgb_to_hex(dark_ui_link_rgb),
        "--ui-shadow": f"0 10px 24px {_rgba(_mix_rgb(base_rgb, (0, 0, 0), 0.84), _depth_mix(depth, 0.36, 0.44))}",
        "--workspace-shell-bg": _rgb_to_hex(workspace_bg_rgb),
        "--workspace-shell-bg-alt": _rgb_to_hex(workspace_bg_alt_rgb),
        "--workspace-shell-border": _rgb_to_hex(workspace_border_rgb),
        "--workspace-shell-border-muted": _rgb_to_hex(workspace_border_muted_rgb),
        "--workspace-shell-border-strong": _rgb_to_hex(workspace_border_strong_rgb),
        "--workspace-shell-text": _rgb_to_hex(workspace_text_rgb),
        "--workspace-shell-text-soft": _rgb_to_hex(workspace_text_soft_rgb),
        "--workspace-shell-hover-bg": _rgb_to_hex(workspace_hover_bg_rgb),
        "--workspace-shell-active-bg": _rgb_to_hex(workspace_active_bg_rgb),
        "--workspace-shell-active-text": _rgb_to_hex(workspace_active_text_rgb),
        "--workspace-shell-divider-bg": f"linear-gradient(90deg, {_rgb_to_hex(divider_start_rgb)}, {_rgb_to_hex(divider_end_rgb)})",
        "--workspace-shell-divider-line": _rgb_to_hex(workspace_border_muted_rgb),
        "--workspace-shell-divider-line-active": _rgb_to_hex(workspace_border_rgb),
        "--workspace-shell-shadow": f"0 12px 28px {_rgba(_mix_rgb(base_rgb, (0, 0, 0), 0.88), _depth_mix(depth, 0.46, 0.56))}",
        "--surface-tint-color": tint_hex,
        "--surface-tint-intensity": str(intensity),
        "--surface-tint-bg-soft": _rgb_to_hex(dark_surface_soft_rgb),
        "--surface-tint-bg": _rgb_to_hex(dark_surface_bg_rgb),
        "--surface-tint-bg-alt": _rgb_to_hex(dark_surface_bg_alt_rgb),
        "--surface-tint-bg-hover": _rgb_to_hex(dark_surface_hover_rgb),
        "--surface-tint-border": _rgb_to_hex(dark_surface_border_rgb),
        "--surface-tint-border-strong": _rgb_to_hex(dark_surface_border_strong_rgb),
        "--surface-tint-text": _rgb_to_hex(dark_surface_text_rgb),
        "--surface-tint-text-soft": _rgb_to_hex(dark_surface_text_soft_rgb),
        "--surface-tint-divider-bg": f"linear-gradient(90deg, {_rgb_to_hex(dark_surface_divider_start_rgb)}, {_rgb_to_hex(dark_surface_divider_end_rgb)})",
        "--surface-tint-divider-line": _rgb_to_hex(dark_surface_border_rgb),
        "--surface-tint-start-hue": str(tint_start_hue),
        "--surface-tint-end-hue": str(tint_end_hue),
        "--surface-tint-outline-hue": str(tint_outline_hue),
        "--surface-tint-sat-mult": _format_number(tint_sat_mult),
        "--surface-tint-outline-sat-mult": _format_number(tint_outline_sat_mult),
        "--surface-tint-dark-sat-mult": _format_number(tint_dark_sat_mult),
        "--surface-tint-outline-dark-sat-mult": _format_number(tint_outline_dark_sat_mult),
        "--surface-tint-alpha-mult": _format_number(tint_alpha_mult),
        "--surface-tint-dark-alpha-mult": _format_number(tint_dark_alpha_mult),
    }
    return {
        "light": light_tokens,
        "dark": dark_tokens,
    }


def _render_vars(selector: str, vars_map: Dict[str, str], indent: str) -> str:
    lines = [f"{indent}{selector} {{"]
    for key, value in vars_map.items():
        lines.append(f"{indent}  {key}: {value};")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def build_theme_css(
    indent: str = "    ",
    *,
    light_vars: Optional[Dict[str, str]] = None,
    dark_vars: Optional[Dict[str, str]] = None,
) -> str:
    light_tokens = light_vars if isinstance(light_vars, dict) else LIGHT_THEME_VARS
    dark_tokens = dark_vars if isinstance(dark_vars, dict) else DARK_THEME_VARS
    parts = [
        _render_vars(":root", light_tokens, indent),
        f"{indent}/* Readability-first dark theme override */",
        _render_vars('[data-theme="dark"]', dark_tokens, indent),
    ]
    return "\n".join(parts)
