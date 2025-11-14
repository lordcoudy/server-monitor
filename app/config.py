"""Application configuration helpers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Settings loaded from environment variables."""

    api_token: str = os.getenv("MONITOR_API_TOKEN", "")
    allow_restart: bool = _to_bool(os.getenv("MONITOR_ALLOW_RESTART"), default=False)
    restart_command: str = os.getenv("MONITOR_RESTART_COMMAND", "sudo /sbin/reboot")
    poll_interval_seconds: float = float(os.getenv("MONITOR_POLL_INTERVAL", "2"))
    hostname_label: str = os.getenv("MONITOR_HOSTNAME_LABEL", "server")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
