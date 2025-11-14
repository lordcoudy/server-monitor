"""Utilities for collecting system metrics with lightweight caching."""
from __future__ import annotations

import copy
import platform
import socket
import time
from datetime import datetime, timezone
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, List

import psutil

if TYPE_CHECKING:
    from .config import Settings


_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = Lock()
_LIGHT_TS: float = 0.0
_HEAVY_TS: float = 0.0


def _format_bytes(value: float) -> Dict[str, float]:
    return {
        "bytes": value,
        "kb": value / 1024,
        "mb": value / 1024 ** 2,
        "gb": value / 1024 ** 3,
    }


def _uptime_seconds() -> float:
    return time.time() - psutil.boot_time()


def _temperatures() -> List[Dict[str, Any]]:
    temps = []
    try:
        data = psutil.sensors_temperatures()
    except (NotImplementedError, AttributeError):
        data = {}
    for label, entries in data.items():
        for entry in entries:
            temps.append(
                {
                    "sensor": label,
                    "label": entry.label or entry.__class__.__name__,
                    "current": entry.current,
                    "high": entry.high,
                    "critical": entry.critical,
                }
            )
    return temps


def _top_processes(limit: int, scan_limit: int) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    scanned = 0
    for proc in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent"]):
        if scanned >= scan_limit:
            break
        scanned += 1
        try:
            info = proc.info
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        info["cpu_percent"] = round(info.get("cpu_percent") or 0.0, 2)
        info["memory_percent"] = round(info.get("memory_percent") or 0.0, 2)
        entries.append(info)
    entries.sort(key=lambda item: item.get("cpu_percent", 0), reverse=True)
    return entries[:limit]


def _collect_light_metrics() -> Dict[str, Any]:
    cpu_times = psutil.cpu_times_percent(interval=None, percpu=False)
    virtual = psutil.virtual_memory()
    swap = psutil.swap_memory()
    metrics = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "load_avg": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [0.0, 0.0, 0.0],
        "uptime_seconds": _uptime_seconds(),
        "cpu": {
            "usage_percent": psutil.cpu_percent(interval=None),
            "per_core": psutil.cpu_percent(interval=None, percpu=True),
            "count": psutil.cpu_count(logical=True),
            "times_percent": cpu_times._asdict(),
            "frequency_mhz": getattr(psutil.cpu_freq(), "current", None),
        },
        "memory": {
            "virtual": virtual._asdict(),
            "swap": swap._asdict(),
        },
    }
    metrics["memory"]["virtual"]["human"] = {
        "total": _format_bytes(virtual.total),
        "available": _format_bytes(virtual.available),
        "used": _format_bytes(virtual.used),
    }
    return metrics


def _collect_heavy_metrics(settings: "Settings") -> Dict[str, Any]:
    disk_usage = psutil.disk_usage("/")._asdict()
    disk_io_raw = psutil.disk_io_counters()
    net_io_raw = psutil.net_io_counters()
    return {
        "disks": {
            "root": disk_usage,
            "io": disk_io_raw._asdict() if disk_io_raw else {},
        },
        "network": net_io_raw._asdict() if net_io_raw else {},
        "temperatures": _temperatures(),
        "top_processes": _top_processes(settings.top_process_limit, settings.process_scan_limit),
    }


def collect_metrics(settings: "Settings") -> Dict[str, Any]:
    """Collect a snapshot of system metrics with cached heavy sections."""

    global _CACHE, _LIGHT_TS, _HEAVY_TS
    now = time.time()
    with _CACHE_LOCK:
        if not _CACHE or now - _LIGHT_TS >= settings.metrics_refresh_seconds:
            _CACHE.update(_collect_light_metrics())
            _LIGHT_TS = now
        if not _CACHE or now - _HEAVY_TS >= settings.heavy_metrics_refresh_seconds:
            _CACHE.update(_collect_heavy_metrics(settings))
            _HEAVY_TS = now
        snapshot = copy.deepcopy(_CACHE)
    snapshot["timestamp"] = datetime.now(timezone.utc).isoformat()
    return snapshot
