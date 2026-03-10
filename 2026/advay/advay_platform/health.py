"""Health and readiness helpers for the Phase 1 platform."""

from __future__ import annotations

from advay_platform import __version__
from advay_platform.cache.redis_adapter import RedisCacheAdapter
from advay_platform.config import Settings
from advay_platform.db.neo4j import Neo4jConnector
from advay_platform.db.postgres import PostgresConnector


def build_health_payload(settings: Settings) -> dict[str, str]:
    return {
        "status": "ok",
        "service": "advay-api",
        "phase": "phase_1",
        "environment": settings.env,
        "version": __version__,
    }


def _dependency_entry(configured: bool, available: bool, detail: str) -> dict[str, object]:
    return {
        "configured": configured,
        "available": available,
        "detail": detail,
    }


def build_readiness_payload(settings: Settings) -> tuple[dict[str, object], int]:
    redis_adapter = RedisCacheAdapter(settings.redis_url)
    redis_ok, redis_detail = redis_adapter.ping()
    redis_adapter.close()

    postgres = PostgresConnector(settings.postgres_dsn)
    postgres_ok, postgres_detail = postgres.ping()

    neo4j = Neo4jConnector(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    neo4j_ok, neo4j_detail = neo4j.ping()

    dependencies = {
        "redis": _dependency_entry(True, redis_ok, redis_detail),
        "postgres": _dependency_entry(postgres.is_configured(), postgres_ok, postgres_detail),
        "neo4j": _dependency_entry(neo4j.is_configured(), neo4j_ok, neo4j_detail),
    }

    overall_ok = all(item["available"] for item in dependencies.values())
    payload = {
        "status": "ready" if overall_ok else "degraded",
        "service": "advay-api",
        "phase": "phase_1",
        "dependencies": dependencies,
    }
    return payload, 200 if overall_ok else 503
