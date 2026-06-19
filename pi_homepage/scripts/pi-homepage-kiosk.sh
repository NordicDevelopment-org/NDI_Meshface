#!/usr/bin/env bash
set -euo pipefail

BIND_HOST="${1:-127.0.0.1}"
BIND_PORT="${2:-8080}"

# 0.0.0.0 is a bind address, not something a browser can open.
BROWSE_HOST="${BIND_HOST}"
if [[ "${BROWSE_HOST}" == "0.0.0.0" ]]; then
  BROWSE_HOST="127.0.0.1"
fi

URL="http://${BROWSE_HOST}:${BIND_PORT}/"

wait_for_homepage() {
  local tries=0
  local max_tries=60
  while (( tries < max_tries )); do
    if curl --silent --fail --max-time 2 --output /dev/null "${URL}"; then
      return 0
    fi
    tries=$((tries + 1))
    sleep 1
  done
  return 1
}

wait_for_homepage || true

if command -v chromium-browser >/dev/null 2>&1; then
  BROWSER_BIN="chromium-browser"
elif command -v chromium >/dev/null 2>&1; then
  BROWSER_BIN="chromium"
else
  echo "no chromium-browser/chromium binary found on PATH" >&2
  exit 1
fi

exec "${BROWSER_BIN}" \
  --kiosk \
  --noerrdialogs \
  --disable-session-crashed-bubble \
  "${URL}"
