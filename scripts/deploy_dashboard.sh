#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

TARGET="${1:-${MESH_DASH_DEPLOY_TARGET:-j@192.168.1.241}}"
APP_DIR="${MESH_DASH_DEPLOY_APP_DIR:-/home/j/mesh/app}"
REMOTE_PYTHON="${MESH_DASH_DEPLOY_REMOTE_PYTHON:-/home/j/mesh/.venv/bin/python}"
SERVICE_NAME="${MESH_DASH_DEPLOY_SERVICE:-meshtastic-dashboard}"

if [[ -z "${TARGET}" ]]; then
  echo "deploy target is required" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/mesh_dashboard.py" ]]; then
  echo "mesh_dashboard.py not found under ${ROOT_DIR}" >&2
  exit 1
fi

if [[ ! -f "${ROOT_DIR}/mesh_connection.py" ]]; then
  echo "mesh_connection.py not found under ${ROOT_DIR}" >&2
  exit 1
fi

echo "[deploy] target=${TARGET} app_dir=${APP_DIR} service=${SERVICE_NAME}"

scp \
  "${ROOT_DIR}/mesh_dashboard.py" \
  "${ROOT_DIR}/mesh_connection.py" \
  "${TARGET}:${APP_DIR}/"

tar \
  -C "${ROOT_DIR}" \
  --warning=no-timestamp \
  --exclude='meshdash/__pycache__' \
  --exclude='*.pyc' \
  -cf - \
  meshdash \
| ssh "${TARGET}" "tar -C '${APP_DIR}' -xf -"

ssh -t "${TARGET}" "\
'${REMOTE_PYTHON}' -m compileall -q '${APP_DIR}' && \
sudo systemctl restart '${SERVICE_NAME}' && \
SYSTEMD_PAGER=cat sudo systemctl --no-pager -l status '${SERVICE_NAME}'"
