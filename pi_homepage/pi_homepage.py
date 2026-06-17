import argparse
import json
import logging
import os
from pathlib import Path

from health import TileHealthMonitor
from server import build_homepage_server, render_homepage_html
from theme import DARK_THEME_VARS, LIGHT_THEME_VARS, build_theme_css

logger = logging.getLogger(__name__)

APP_TITLE = "Meshyface Pi Homepage"

DEFAULT_HTTP_HOST = os.environ.get("PI_HOMEPAGE_HOST", "0.0.0.0")
DEFAULT_HTTP_PORT = int(os.environ.get("PI_HOMEPAGE_PORT", "8080"))
DEFAULT_TILES_CONFIG = os.environ.get(
    "PI_HOMEPAGE_TILES_CONFIG",
    str(Path(__file__).resolve().parent / "config" / "tiles.json"),
)
DEFAULT_REFRESH_MS = int(os.environ.get("PI_HOMEPAGE_REFRESH_MS", "10000"))
DEFAULT_HEALTH_TTL_SECONDS = float(os.environ.get("PI_HOMEPAGE_HEALTH_TTL_SECONDS", "8"))
DEFAULT_LOG_LEVEL = os.environ.get("PI_HOMEPAGE_LOG_LEVEL", "INFO")

# Docker container management and firmware flashing are deferred to a later
# phase; this MVP is shell + launcher + health badges only.


def load_tiles(config_path: str) -> list:
    path = Path(config_path)
    if not path.exists():
        logger.warning("Tiles config not found at %s; starting with an empty launcher.", path)
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    raw_tiles = data.get("tiles", []) if isinstance(data, dict) else data
    return [tile for tile in raw_tiles if isinstance(tile, dict) and tile.get("id")]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Raspberry Pi kiosk homepage / app launcher")
    parser.add_argument("--host", default=DEFAULT_HTTP_HOST, help="Bind host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_HTTP_PORT, help="Bind port (default: %(default)s)")
    parser.add_argument(
        "--tiles-config",
        default=DEFAULT_TILES_CONFIG,
        help="Path to tiles.json (default: %(default)s)",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=DEFAULT_REFRESH_MS,
        help="Browser status poll interval in ms (default: %(default)s)",
    )
    parser.add_argument(
        "--health-ttl-seconds",
        type=float,
        default=DEFAULT_HEALTH_TTL_SECONDS,
        help="Cache TTL for tile health probes in seconds (default: %(default)s)",
    )
    return parser


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, str(DEFAULT_LOG_LEVEL).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = build_arg_parser().parse_args()

    tiles = load_tiles(args.tiles_config)
    health_monitor = TileHealthMonitor(tiles, cache_ttl_seconds=args.health_ttl_seconds)
    health_monitor.start_background_refresh()

    theme_css = build_theme_css(light_vars=LIGHT_THEME_VARS, dark_vars=DARK_THEME_VARS)

    def _html_provider() -> str:
        return render_homepage_html(
            app_title=APP_TITLE,
            tiles=tiles,
            theme_css=theme_css,
            refresh_ms=args.refresh_ms,
        )

    server = build_homepage_server(
        host=args.host,
        port=args.port,
        html_provider=_html_provider,
        health_monitor=health_monitor,
    )
    logger.info("Pi homepage listening on http://%s:%s (%d tiles loaded)", args.host, args.port, len(tiles))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        health_monitor.stop()
        server.shutdown()


if __name__ == "__main__":
    main()
