from __future__ import annotations

import os

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
    assert response.json()["phase"] == "phase_1"


def test_ready_endpoint_returns_dependency_summary() -> None:
    os.environ["ADVAY_POSTGRES_DSN"] = ""
    os.environ["ADVAY_NEO4J_URI"] = ""
    os.environ["ADVAY_NEO4J_USER"] = ""
    os.environ["ADVAY_NEO4J_PASSWORD"] = ""
    _reset_settings()
    client = TestClient(create_app())

    response = client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert set(payload["dependencies"]) == {"redis", "postgres", "neo4j"}
    assert payload["dependencies"]["postgres"]["detail"] == "not_configured"
    assert payload["dependencies"]["neo4j"]["detail"] == "not_configured"
