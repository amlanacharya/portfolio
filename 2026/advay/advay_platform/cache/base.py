"""Cache interface used by the platform foundation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheAdapter(ABC):
    """Minimal cache contract for Phase 1 wiring."""

    @abstractmethod
    def get(self, key: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def ping(self) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
