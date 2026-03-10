from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from advay_platform.api import create_app
from advay_platform.config import get_settings


def _reset_settings() -> None:
    get_settings.cache_clear()


def test_health_endpoint_returns_ok() -> None:
    _reset_settings()
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["phase"] == "phase_2"


def test_ready_endpoint_returns_dependency_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADVAY_POSTGRES_DSN", "")
    monkeypatch.setenv("ADVAY_NEO4J_URI", "")
    monkeypatch.setenv("ADVAY_NEO4J_USER", "")
    monkeypatch.setenv("ADVAY_NEO4J_PASSWORD", "")
    _reset_settings()
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["phase"] == "phase_2"
    assert set(payload["dependencies"]) == {"redis", "postgres", "neo4j"}
    assert payload["dependencies"]["postgres"]["detail"] == "not_configured"
    assert payload["dependencies"]["neo4j"]["detail"] == "not_configured"
