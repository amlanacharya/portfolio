"""Redis-backed cache adapter with safe Phase 1 fallbacks."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from advay_platform.cache.base import CacheAdapter


class RedisCacheAdapter(CacheAdapter):
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._client = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        redis_module = import_module("redis")
        self._client = redis_module.Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def get(self, key: str) -> Any:
        return self._get_client().get(key)

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        return bool(self._get_client().set(name=key, value=value, ex=ttl_seconds))

    def delete(self, key: str) -> bool:
        return bool(self._get_client().delete(key))

    def ping(self) -> tuple[bool, str]:
        try:
            self._get_client().ping()
            return True, "reachable"
        except ModuleNotFoundError:
            return False, "redis_driver_missing"
        except Exception as exc:  # pragma: no cover - exact driver errors vary
            return False, str(exc)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
