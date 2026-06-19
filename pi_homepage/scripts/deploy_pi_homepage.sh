#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deploy_pi_homepage.sh [target] [options]

Examples:
  # First-time bootstrap + deploy (installs venv, systemd service, kiosk autostart)
  ./scripts/deploy_pi_homepage.sh --target pi@raspberrypi.local --bootstrap

  # Fast update to an already-bootstrapped host
  ./scripts/deploy_pi_homepage.sh pi@raspberrypi.local

Options:
  --target <user@host>      SSH deploy target.
  --bootstrap                Prepare a fresh host (venv, deps, service, kiosk autostart).
  --host <bind_host>         HTTP bind host written to homepage.env (default: 0.0.0.0).
  --port <bind_port>         HTTP bind port written to homepage.env (default: 8080).
  --refresh-ms <ms>          Browser status poll interval (default: 10000).
  --health-ttl-seconds <s>   Tile health probe cache TTL (default: 8).
  --kiosk-enable              Install the chromium kiosk autostart entry (default).
  --no-kiosk-enable           Skip installing the kiosk autostart entry.
  --hard-reboot                Reboot the target after deploy.
  -h, --help                    Show this help.

Environment overrides (same names as their --flag, upper-cased with
PI_HOMEPAGE_DEPLOY_ prefix) are read for unset flags, e.g.
PI_HOMEPAGE_DEPLOY_TARGET, PI_HOMEPAGE_DEPLOY_ROOT.
EOF
}

require_arg() {
  local flag="$1"
  local value="${2:-}"
  if [[ -z "${value}" ]]; then
    echo "${flag} requires a value" >&2
    exit 2
  fi
}

TARGET="${PI_HOMEPAGE_DEPLOY_TARGET:-}"
REMOTE_ROOT="${PI_HOMEPAGE_DEPLOY_ROOT:-/opt/pi-homepage}"
APP_DIR="${REMOTE_ROOT}/app"
CONFIG_DIR="${REMOTE_ROOT}/config"
REMOTE_VENV="${REMOTE_ROOT}/venv"
REMOTE_PYTHON="${REMOTE_VENV}/bin/python3"
SERVICE_NAME="${PI_HOMEPAGE_DEPLOY_SERVICE:-pi-homepage}"

BOOTSTRAP=0
BIND_HOST="${PI_HOMEPAGE_DEPLOY_HOST:-0.0.0.0}"
BIND_PORT="${PI_HOMEPAGE_DEPLOY_PORT:-8080}"
REFRESH_MS="${PI_HOMEPAGE_DEPLOY_REFRESH_MS:-10000}"
HEALTH_TTL_SECONDS="${PI_HOMEPAGE_DEPLOY_HEALTH_TTL_SECONDS:-8}"
KIOSK_ENABLE=1
HARD_REBOOT=0

POSITIONAL_TARGET_SET=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      require_arg "$1" "${2:-}"
      TARGET="$2"
      shift 2
      ;;
    --bootstrap)
      BOOTSTRAP=1
      shift
      ;;
    --host)
      require_arg "$1" "${2:-}"
      BIND_HOST="$2"
      shift 2
      ;;
    --port)
      require_arg "$1" "${2:-}"
      BIND_PORT="$2"
      shift 2
      ;;
    --refresh-ms)
      require_arg "$1" "${2:-}"
      REFRESH_MS="$2"
      shift 2
      ;;
    --health-ttl-seconds)
      require_arg "$1" "${2:-}"
      HEALTH_TTL_SECONDS="$2"
      shift 2
      ;;
    --kiosk-enable)
      KIOSK_ENABLE=1
      shift
      ;;
    --no-kiosk-enable)
      KIOSK_ENABLE=0
      shift
      ;;
    --hard-reboot)
      HARD_REBOOT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ "${POSITIONAL_TARGET_SET}" -eq 1 ]]; then
        echo "unexpected extra argument: $1" >&2
        exit 2
      fi
      TARGET="$1"
      POSITIONAL_TARGET_SET=1
      shift
      ;;
  esac
done

if [[ -z "${TARGET}" ]]; then
  echo "missing deploy target (--target user@host or positional)" >&2
  usage >&2
  exit 2
fi

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10)
SCP_OPTS=(-o BatchMode=yes -o ConnectTimeout=10)

ssh_cmd() {
  ssh "${SSH_OPTS[@]}" "$@"
}

scp_cmd() {
  scp "${SCP_OPTS[@]}" "$@"
}

echo "[deploy] target=${TARGET}"
echo "[deploy] remote_root=${REMOTE_ROOT} service=${SERVICE_NAME} bootstrap=${BOOTSTRAP}"
echo "[deploy] bind=${BIND_HOST}:${BIND_PORT} refresh_ms=${REFRESH_MS} health_ttl_seconds=${HEALTH_TTL_SECONDS}"
echo "[deploy] kiosk_enable=${KIOSK_ENABLE}"

ssh_cmd "${TARGET}" "mkdir -p '${REMOTE_ROOT}' '${APP_DIR}' '${CONFIG_DIR}'"

tar \
  -C "${ROOT_DIR}" \
  --warning=no-timestamp \
  --exclude='tests' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='scripts' \
  -cf - \
  . \
| ssh_cmd "${TARGET}" "tar -C '${APP_DIR}' -xf -"

if [[ "${BOOTSTRAP}" -eq 1 ]]; then
  echo "[deploy] bootstrapping runtime"
  ssh_cmd -tt "${TARGET}" "\
if ! command -v python3 >/dev/null 2>&1; then \
  sudo apt-get update && sudo apt-get install -y python3; \
fi"
  ssh_cmd -tt "${TARGET}" "\
PY_MM=\$(python3 -c 'import sys; print(str(sys.version_info.major)+\".\"+str(sys.version_info.minor))') && \
sudo apt-get update && \
(sudo apt-get install -y python3-venv python\${PY_MM}-venv || sudo apt-get install -y python3-venv)"
  ssh_cmd "${TARGET}" "\
if [[ ! -x '${REMOTE_VENV}/bin/python' ]]; then \
  python3 -m venv '${REMOTE_VENV}'; \
fi"
  ssh_cmd "${TARGET}" "'${REMOTE_VENV}/bin/pip' install --upgrade pip"

  REMOTE_LOGIN_USER="${TARGET%@*}"

  local_service="$(mktemp "${TMPDIR:-/tmp}/pi-homepage-service.XXXXXX")"
  cat > "${local_service}" <<EOF
[Unit]
Description=Pi Homepage Kiosk Launcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${REMOTE_LOGIN_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${CONFIG_DIR}/homepage.env
ExecStart=${REMOTE_PYTHON} ${APP_DIR}/pi_homepage.py --host \${PI_HOMEPAGE_HOST} --port \${PI_HOMEPAGE_PORT} --tiles-config \${PI_HOMEPAGE_TILES_CONFIG} --refresh-ms \${PI_HOMEPAGE_REFRESH_MS} --health-ttl-seconds \${PI_HOMEPAGE_HEALTH_TTL_SECONDS}
Restart=always
RestartSec=2
KillSignal=SIGINT
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF
  tmp_service="/tmp/${SERVICE_NAME}.service"
  scp_cmd "${local_service}" "${TARGET}:${tmp_service}"
  rm -f "${local_service}"
  ssh_cmd -tt "${TARGET}" "\
sudo install -m 0644 '${tmp_service}' '/etc/systemd/system/${SERVICE_NAME}.service' && \
rm -f '${tmp_service}' && \
sudo systemctl daemon-reload"

  if [[ "${KIOSK_ENABLE}" -eq 1 ]]; then
    echo "[deploy] installing kiosk autostart entry for ${REMOTE_LOGIN_USER}"
    ssh_cmd "${TARGET}" "mkdir -p ~/.config/autostart"
    scp_cmd "${ROOT_DIR}/scripts/pi-homepage-kiosk.sh" "${TARGET}:${APP_DIR}/pi-homepage-kiosk.sh"
    ssh_cmd "${TARGET}" "chmod +x '${APP_DIR}/pi-homepage-kiosk.sh'"
    local_desktop="$(mktemp "${TMPDIR:-/tmp}/pi-homepage-kiosk.XXXXXX")"
    cat > "${local_desktop}" <<EOF
[Desktop Entry]
Type=Application
Name=Pi Homepage Kiosk
Exec=${APP_DIR}/pi-homepage-kiosk.sh ${BIND_HOST} ${BIND_PORT}
X-GNOME-Autostart-enabled=true
EOF
    scp_cmd "${local_desktop}" "${TARGET}:~/.config/autostart/pi-homepage-kiosk.desktop"
    rm -f "${local_desktop}"
  fi
fi

echo "[deploy] writing ${CONFIG_DIR}/homepage.env"
ssh_cmd "${TARGET}" "cat > '${CONFIG_DIR}/homepage.env' <<EOF
PI_HOMEPAGE_HOST=${BIND_HOST}
PI_HOMEPAGE_PORT=${BIND_PORT}
PI_HOMEPAGE_TILES_CONFIG=${CONFIG_DIR}/tiles.json
PI_HOMEPAGE_REFRESH_MS=${REFRESH_MS}
PI_HOMEPAGE_HEALTH_TTL_SECONDS=${HEALTH_TTL_SECONDS}
PYTHONUNBUFFERED=1
EOF"

ssh_cmd "${TARGET}" "test -f '${CONFIG_DIR}/tiles.json' || cp '${APP_DIR}/config/tiles.json' '${CONFIG_DIR}/tiles.json'"

if ! ssh_cmd "${TARGET}" "test -x '${REMOTE_PYTHON}'"; then
  echo "remote python not found at ${REMOTE_PYTHON}; rerun with --bootstrap" >&2
  exit 1
fi

if [[ "${BOOTSTRAP}" -eq 1 ]]; then
  ssh_cmd -tt "${TARGET}" "\
sudo systemctl enable '${SERVICE_NAME}' && \
sudo systemctl restart '${SERVICE_NAME}' && \
SYSTEMD_PAGER=cat sudo systemctl --no-pager -l status '${SERVICE_NAME}'"
else
  if ! ssh_cmd "${TARGET}" "systemctl list-unit-files --type=service --all | grep -q '^${SERVICE_NAME}\.service'"; then
    echo "service ${SERVICE_NAME}.service is not installed on target; rerun with --bootstrap" >&2
    exit 1
  fi
  ssh_cmd -tt "${TARGET}" "\
sudo systemctl restart '${SERVICE_NAME}' && \
SYSTEMD_PAGER=cat sudo systemctl --no-pager -l status '${SERVICE_NAME}'"
fi

target_host="${TARGET#*@}"
if [[ "${HARD_REBOOT}" -eq 1 ]]; then
  ssh_cmd -tt "${TARGET}" "sudo reboot" || true
  echo "[deploy] reboot requested; wait for ${target_host} to come back before opening the UI"
  exit 0
fi

echo "[deploy] complete"
echo "[deploy] open: http://${target_host}:${BIND_PORT}"
