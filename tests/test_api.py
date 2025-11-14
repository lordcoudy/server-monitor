"""Tests for the server monitor FastAPI app."""
from __future__ import annotations

from app import main
from app.config import Settings
from fastapi.testclient import TestClient

client = TestClient(main.app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_metrics_endpoint_has_core_fields():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    payload = response.json()
    for field in ("cpu", "memory", "disks", "network"):
        assert field in payload


def test_restart_guard(monkeypatch):
    custom_settings = Settings(api_token="secret", allow_restart=False, restart_command="echo noop")
    monkeypatch.setattr(main, "get_settings", lambda: custom_settings)
    response = client.post("/api/actions/restart", headers={"X-API-Key": "secret"})
    assert response.status_code == 403


def test_restart_success(monkeypatch):
    custom_settings = Settings(api_token="secret", allow_restart=True, restart_command="echo noop")
    monkeypatch.setattr(main, "get_settings", lambda: custom_settings)

    recorded = {}

    def fake_popen(cmd, stdout=None, stderr=None):
        recorded["cmd"] = cmd
        class _Proc:
            pass
        return _Proc()

    monkeypatch.setattr(main.subprocess, "Popen", fake_popen)
    response = client.post("/api/actions/restart", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    assert response.json()["status"] == "restart-requested"
    assert recorded["cmd"][0] == "sudo" or recorded["cmd"][0] == "echo"
