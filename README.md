# Meshtastic Deep Dashboard

Web dashboard for Meshtastic networks with live map, node tables, chat room, and persisted history.

This repo is focused on running `mesh_dashboard.py` as a website you can open from desktop/mobile on your LAN.

## What This Website Does

- Live network map with node markers and link lines.
- Click-to-select node from map, node list, or chat.
- Node history panel with signal plots (SNR/RSSI) and rollup stats.
- Name-first chat room view with send box at the bottom.
- Recent packets, map stats, raw config views.
- Persisted SQLite history for chat, packets, links, and node rollups.
- Top-bar host disk free indicator with green/yellow/red progress color.

## Repo Files You’ll Use

- `mesh_dashboard.py`: main web app.
- `mesh_connection.py`: serial/TCP connection helper.
- `meshtastic-dashboard.service`: systemd unit for dashboard website.
- `README.md`: setup + operations guide for this dashboard server.

Archived (not active project surface):

- `archive/scripts/`: older utility/test/support scripts.
- `archive/services/`: archived service units not used by the dashboard server.
- `archive/docs/`: archived supplemental docs.

## Requirements

- Python 3.11+ (3.13 works).
- Linux recommended for server (Debian VM works well).
- Dependencies:
  - `meshtastic`
  - `pypubsub`
  - `protobuf`

## Quick Start (Run Locally)

```bash
cd ~/mesh_py
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install meshtastic pypubsub protobuf
python mesh_dashboard.py --mesh-host 192.168.1.109 --mesh-tcp-port 4403 --http-host 0.0.0.0 --http-port 8877
```

Open:

- Local machine: `http://127.0.0.1:8877`
- LAN devices: `http://<your-ip>:8877`

## Recommended Production Setup (Debian VM + systemd)

### 1) Create app folders on VM

```bash
mkdir -p ~/mesh/{app,config,logs}
```

### 2) Copy app files to VM (from your workstation)

```bash
scp ~/mesh_py/mesh_dashboard.py j@192.168.1.241:/home/j/mesh/app/
scp ~/mesh_py/mesh_connection.py j@192.168.1.241:/home/j/mesh/app/
scp ~/mesh_py/meshtastic-dashboard.service j@192.168.1.241:/home/j/
```

### 3) Install runtime on VM

```bash
sudo apt update
sudo apt install -y python3 python3-venv
python3 -m venv /home/j/mesh/.venv
/home/j/mesh/.venv/bin/pip install --upgrade pip
/home/j/mesh/.venv/bin/pip install meshtastic pypubsub protobuf
```

### 4) Configure dashboard environment on VM

```bash
cat > /home/j/mesh/config/dashboard.env <<'EOF'
MESH_HOST=192.168.1.109
MESH_PORT=4403
DASH_HOST=0.0.0.0
DASH_PORT=8877
REFRESH_MS=3000
MESH_DASH_HISTORY_DB=/home/j/mesh/mesh_dashboard_history.sqlite3
PYTHONUNBUFFERED=1
EOF
```

### 5) Install and start service

```bash
sudo cp /home/j/meshtastic-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now meshtastic-dashboard
sudo systemctl status meshtastic-dashboard --no-pager
```

### 6) Open the dashboard

- `http://192.168.1.241:8877`

## Fast Update/Deploy Loop

Use this after editing `mesh_dashboard.py`:

```bash
scp ~/mesh_py/mesh_dashboard.py j@192.168.1.241:/home/j/mesh/app/mesh_dashboard.py
ssh -t j@192.168.1.241 'sudo systemctl restart meshtastic-dashboard && sudo systemctl status meshtastic-dashboard --no-pager'
```

Then hard refresh browser: `Ctrl+Shift+R`.

## History and Storage Behavior

By default, history is enabled and stored in SQLite (`--history-db`).

Important knobs:

- `--history-max-rows` (default `5000`)
- `--history-retention-days` (default `7`)
- `--history-event-max-rows` (default `200000`)
- `--history-event-retention-days` (default `30`)
- `--history-rollup-retention-days` (default `365`)
- `--node-history-hours` (default `72`)
- `--node-history-max-points` (default `1440`)
- `--no-history` disables persistence.

## Chat Send Notes

- Chat send box posts to `/api/chat/send`.
- Current UI sends to broadcast room (`^all`) on channel `0`.
- Message byte limit is enforced (`220` UTF-8 bytes).
- Sent messages are also echoed into dashboard chat history immediately.

## Troubleshooting

Check service status:

```bash
sudo systemctl status meshtastic-dashboard --no-pager
```

Follow logs:

```bash
sudo journalctl -u meshtastic-dashboard -f
```

Verify listener:

```bash
ss -ltnp | grep 8877
```

Verify history DB exists:

```bash
ls -lh /home/j/mesh/mesh_dashboard_history.sqlite3
```

If UI seems stale after deploy, hard-refresh browser (`Ctrl+Shift+R`).

## Security Notes

- Dashboard HTTP has no authentication by default.
- Do not expose it directly to the public internet.
- Restrict to trusted LAN/VPN segments.
