# Ubuntu Server Web Monitor

A lightweight FastAPI-based dashboard inspired by `btop` that exposes CPU, memory, disk, network, temperatures, and top-process information through a modern web UI. Includes an optional, guarded restart button so you can reboot the box remotely once authenticated.

## Features

- 📈 Real-time metrics powered by `psutil`, refreshed from the browser with no page reloads.
- 🌡️ `psutil` temperature integration (requires `lm-sensors` on Linux).
- 🔒 Token-protected restart endpoint with opt-in execution via environment variable.
- 🧪 Automated tests covering the REST API endpoints.
- 🗂️ Single binary dependency footprint (FastAPI + psutil) and zero database requirement.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MONITOR_API_TOKEN="choose-a-strong-token"
export MONITOR_ALLOW_RESTART=0  # keep disabled until you really need it
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000` to view the dashboard.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MONITOR_API_TOKEN` | _(empty)_ | Token that must be sent via the `X-API-Key` header to trigger restarts. Required for secure deployment. |
| `MONITOR_ALLOW_RESTART` | `false` | When set to `1/true/on`, enables execution of the restart command. |
| `MONITOR_RESTART_COMMAND` | `sudo /sbin/reboot` | Shell command that will be executed when restart is requested. |
| `MONITOR_POLL_INTERVAL` | `2` | Frontend polling interval in seconds. |
| `MONITOR_HOSTNAME_LABEL` | `server` | Friendly name displayed in the UI header. |

> 💡 Install `lm-sensors` (`sudo apt install lm-sensors`) and run `sudo sensors-detect` for full temperature coverage.

## Restart endpoint safety

1. Choose a strong API token and keep it secret—never embed it directly into client-side code.
2. Keep `MONITOR_ALLOW_RESTART=0` unless you explicitly need the button.
3. Use a reverse proxy (nginx, Caddy) with HTTPS and optional IP allowlists.
4. Consider running the restart command via a small wrapper script that records audit logs, e.g. `/usr/local/bin/safe-reboot.sh`.

## Testing

```bash
pytest
```

Tests rely on FastAPI's `TestClient` and stub out restart execution so they won't reboot your development machine.

## Deploying as a service

Create `/etc/systemd/system/server-monitor.service` with:

```ini
[Unit]
Description=Ubuntu Server Web Monitor
After=network.target

[Service]
WorkingDirectory=/opt/server-monitor
EnvironmentFile=/opt/server-monitor/.env
ExecStart=/opt/server-monitor/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
User=monitor
Group=monitor

[Install]
WantedBy=multi-user.target
```

Reload and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now server-monitor
```

Use the `.env` file referenced above to store the environment variables securely (set permissions to `600`).
