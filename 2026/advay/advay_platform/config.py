"""Runtime settings for the Phase 1 platform foundation."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import os


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str = field(default_factory=lambda: os.getenv("ADVAY_ENV", "local"))
    log_level: str = field(default_factory=lambda: os.getenv("ADVAY_LOG_LEVEL", "INFO"))
    api_host: str = field(default_factory=lambda: os.getenv("ADVAY_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: _get_int("ADVAY_API_PORT", 8000))
    ui_port: int = field(default_factory=lambda: _get_int("ADVAY_UI_PORT", 8501))
    redis_url: str = field(default_factory=lambda: os.getenv("ADVAY_REDIS_URL", "redis://localhost:6379/0"))
    postgres_dsn: str = field(default_factory=lambda: os.getenv("ADVAY_POSTGRES_DSN", ""))
    neo4j_uri: str = field(default_factory=lambda: os.getenv("ADVAY_NEO4J_URI", ""))
    neo4j_user: str = field(default_factory=lambda: os.getenv("ADVAY_NEO4J_USER", ""))
    neo4j_password: str = field(default_factory=lambda: os.getenv("ADVAY_NEO4J_PASSWORD", ""))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
