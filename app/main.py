"""FastAPI app exposing system monitoring endpoints and UI."""
from __future__ import annotations

import secrets
import shlex
import subprocess
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .metrics import collect_metrics

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Ubuntu Server Monitor", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_app_settings() -> Settings:
    return get_settings()


def require_api_key(
    settings: Settings = Depends(get_app_settings),
    api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    if not settings.api_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="API token is not configured")
    if not api_key or not secrets.compare_digest(api_key, settings.api_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API token")


@app.get("/", response_class=FileResponse)
async def root_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/metrics")
async def api_metrics(settings: Settings = Depends(get_app_settings)) -> dict:
    data = collect_metrics()
    data["settings"] = {
        "hostname_label": settings.hostname_label,
        "poll_interval_seconds": settings.poll_interval_seconds,
    }
    return data


@app.post("/api/actions/restart", dependencies=[Depends(require_api_key)])
async def restart_server(settings: Settings = Depends(get_app_settings)) -> dict:
    if not settings.allow_restart:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Restart is disabled in configuration")
    try:
        subprocess.Popen(shlex.split(settings.restart_command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to run restart command: {exc}") from exc
    return {"status": "restart-requested"}


@app.get("/api/health")
async def healthcheck() -> dict:
    return {"status": "ok"}
