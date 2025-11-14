"""Utilities for collecting system metrics."""
from __future__ import annotations

import platform
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import psutil


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


def _top_processes(limit: int = 6) -> List[Dict[str, Any]]:
    procs = []
    for proc in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent"]):
        info = proc.info
        info["cpu_percent"] = round(info.get("cpu_percent") or 0.0, 2)
        info["memory_percent"] = round(info.get("memory_percent") or 0.0, 2)
        procs.append(info)
    procs.sort(key=lambda item: item.get("cpu_percent", 0), reverse=True)
    return procs[:limit]


def collect_metrics() -> Dict[str, Any]:
    """Collect a snapshot of system metrics."""

    cpu_times = psutil.cpu_times_percent(interval=None, percpu=False)
    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "virtual": psutil.virtual_memory()._asdict(),
            "swap": psutil.swap_memory()._asdict(),
        },
        "disks": {
            "root": psutil.disk_usage("/")._asdict(),
            "io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {},
        },
        "network": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
        "temperatures": _temperatures(),
        "top_processes": _top_processes(),
    }
    metrics["memory"]["virtual"]["human"] = {
        "total": _format_bytes(metrics["memory"]["virtual"]["total"]),
        "available": _format_bytes(metrics["memory"]["virtual"]["available"]),
        "used": _format_bytes(metrics["memory"]["virtual"]["used"]),
    }
    return metrics
